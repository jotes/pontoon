import codecs
import fnmatch
import functools
import os
import pytz
import re
import requests
import tempfile
import time
import zipfile

from datetime import datetime, timedelta

from guardian.decorators import (
    permission_required as guardian_permission_required
)

from django.utils.text import slugify
from six import (
    text_type,
    StringIO,
)
from xml.sax.saxutils import (
    escape as xml_escape,
    quoteattr,
)

from django.db.models import Prefetch
from django.db.models.query import QuerySet
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import trans_real

from translate.storage.placeables import base, general, parse
from translate.storage.placeables.interfaces import BasePlaceable


def split_ints(s):
    """Splits string by comma and maps items to the integer."""
    integers = filter(None, (s or '').split(','))
    return map(int, integers)


def get_project_locale_from_request(request, locales):
    """Get Pontoon locale from Accept-language request header."""

    header = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    accept = trans_real.parse_accept_lang_header(header)

    for a in accept:
        try:
            return locales.get(code__iexact=a[0]).code
        except BaseException:
            continue


class NewlineEscapePlaceable(base.Ph):
    """Placeable handling newline escapes."""
    istranslatable = False
    regex = re.compile(r'\\n')
    parse = classmethod(general.regex_parse)


class TabEscapePlaceable(base.Ph):
    """Placeable handling tab escapes."""
    istranslatable = False
    regex = re.compile(r'\t')
    parse = classmethod(general.regex_parse)


class EscapePlaceable(base.Ph):
    """Placeable handling escapes."""
    istranslatable = False
    regex = re.compile(r'\\')
    parse = classmethod(general.regex_parse)


class SpacesPlaceable(base.Ph):
    """Placeable handling spaces."""
    istranslatable = False
    regex = re.compile('^ +| +$|[\r\n\t] +| {2,}')
    parse = classmethod(general.regex_parse)


class PythonFormatNamedPlaceable(base.Ph):
    """Placeable handling named format string in python"""
    istranslatable = False
    regex = re.compile(
        r'%\([[\w\d\!\.,\[\]%:$<>\+\-= ]*\)[+|-|0\d+|#]?[\.\d+]?[s|d|e|f|g|o|x|c|%]',
        re.IGNORECASE
    )
    parse = classmethod(general.regex_parse)


class PythonFormatPlaceable(base.Ph):
    """Placeable handling new format strings in python"""
    istranslatable = False
    regex = re.compile(r'\{{?[[\w\d\!\.,\[\]%:$<>\+\-= ]*\}?}', )
    parse = classmethod(general.regex_parse)


class JsonPlaceholderPlaceable(base.Ph):
    """
    Placeable handling placeholders in JSON format
    as used by the WebExtensions API
    """
    istranslatable = False
    regex = re.compile(r'\$[A-Z0-9_]+\$', )
    parse = classmethod(general.regex_parse)


def mark_placeables(text):
    """Wrap placeables to easily distinguish and manipulate them"""

    PARSERS = [
        NewlineEscapePlaceable.parse,
        TabEscapePlaceable.parse,
        EscapePlaceable.parse,

        # The spaces placeable can match '\n  ' and mask the newline,
        # so it has to come later.
        SpacesPlaceable.parse,

        # The XML placeables must be marked before variable placeables
        # to avoid marking variables, but leaving out tags. See:
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1334926
        general.XMLTagPlaceable.parse,
        general.AltAttrPlaceable.parse,
        general.XMLEntityPlaceable.parse,

        PythonFormatNamedPlaceable.parse,
        PythonFormatPlaceable.parse,
        general.PythonFormattingPlaceable.parse,
        general.JavaMessageFormatPlaceable.parse,
        general.FormattingPlaceable.parse,

        JsonPlaceholderPlaceable.parse,

        # The Qt variables can consume the %1 in %1$s which will mask a printf
        # placeable, so it has to come later.
        general.QtFormattingPlaceable.parse,

        general.UrlPlaceable.parse,
        general.FilePlaceable.parse,
        general.EmailPlaceable.parse,
        general.CapsPlaceable.parse,
        general.CamelCasePlaceable.parse,
        general.OptionPlaceable.parse,
        general.PunctuationPlaceable.parse,
        general.NumberPlaceable.parse,
    ]

    TITLES = {
        'NewlineEscapePlaceable': "Escaped newline",
        'TabEscapePlaceable': "Escaped tab",
        'EscapePlaceable': "Escaped sequence",
        'SpacesPlaceable': "Unusual space in string",
        'AltAttrPlaceable': "'alt' attribute inside XML tag",
        'NewlinePlaceable': "New-line",
        'NumberPlaceable': "Number",
        'QtFormattingPlaceable': "Qt string formatting variable",
        'PythonFormattingPlaceable': "Python string formatting variable",
        'JavaMessageFormatPlaceable': "Java Message formatting variable",
        'FormattingPlaceable': "String formatting variable",
        'UrlPlaceable': "URI",
        'FilePlaceable': "File location",
        'EmailPlaceable': "Email",
        'PunctuationPlaceable': "Punctuation",
        'XMLEntityPlaceable': "XML entity",
        'CapsPlaceable': "Long all-caps string",
        'CamelCasePlaceable': "Camel case string",
        'XMLTagPlaceable': "XML tag",
        'OptionPlaceable': "Command line option",
        'PythonFormatNamedPlaceable': "Python format string",
        'PythonFormatPlaceable': "Python format string",
        'JsonPlaceholderPlaceable': "JSON placeholder",
    }

    output = u""

    # Get a flat list of placeables and StringElem instances
    flat_items = parse(text, PARSERS).flatten()

    for item in flat_items:

        # Placeable: mark
        if isinstance(item, BasePlaceable):
            class_name = item.__class__.__name__
            placeable = text_type(item)

            # CSS class used to mark the placeable
            css = {
                'TabEscapePlaceable': "escape ",
                'EscapePlaceable': "escape ",
                'SpacesPlaceable': "space ",
                'NewlinePlaceable': "escape ",
            }.get(class_name, "")

            title = TITLES.get(class_name, "Unknown placeable")

            # Correctly render placeables in translation editor
            content = {
                'TabEscapePlaceable': u'\\t',
                'EscapePlaceable': u'\\',
                'NewlinePlaceable': {
                    u'\r\n': u'\\r\\n<br/>\n',
                    u'\r': u'\\r<br/>\n',
                    u'\n': u'\\n<br/>\n',
                }.get(placeable),
                'PythonFormatPlaceable':
                    placeable.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                'PythonFormatNamedPlaceable':
                    placeable.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                'XMLEntityPlaceable': placeable.replace('&', '&amp;'),
                'XMLTagPlaceable':
                    placeable.replace('<', '&lt;').replace('>', '&gt;'),
            }.get(class_name, placeable)

            output += ('<mark class="%splaceable" title="%s">%s</mark>') \
                % (css, title, content)

        # Not a placeable: skip
        else:
            output += text_type(item).replace('<', '&lt;').replace('>', '&gt;')

    return output


def first(collection, test, default=None):
    """
    Return the first item that, when passed to the given test function,
    returns True. If no item passes the test, return the default value.
    """
    return next((c for c in collection if test(c)), default)


def match_attr(collection, **attributes):
    """
    Return the first item that has matching values for the given
    attributes, or None if no item is found to match.
    """
    return first(
        collection,
        lambda i: all(getattr(i, attrib) == value
                      for attrib, value in attributes.items()),
        default=None
    )


def aware_datetime(*args, **kwargs):
    """Return an aware datetime using Django's configured timezone."""
    return timezone.make_aware(datetime(*args, **kwargs))


def extension_in(filename, extensions):
    """
    Check if the extension for the given filename is in the list of
    allowed extensions. Uses os.path.splitext rules for getting the
    extension.
    """
    filename, extension = os.path.splitext(filename)
    if extension and extension[1:] in extensions:
        return True
    else:
        return False


def get_object_or_none(model, *args, **kwargs):
    """
    Get an instance of the given model, returning None instead of
    raising an error if an instance cannot be found.
    """
    try:
        return model.objects.get(*args, **kwargs)
    except model.DoesNotExist:
        return None


def require_AJAX(f):
    """
    AJAX request required decorator
    """
    @functools.wraps(f)  # Required by New Relic
    def wrap(request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseBadRequest('Bad Request: Request must be AJAX')
        return f(request, *args, **kwargs)
    return wrap


def permission_required(perm, *args, **kwargs):
    """Wrapper for guardian permission_required decorator.

    If the request is not permitted and user is anon then it returns 404
    otherwise 403.
    """

    def wrapper(f):

        @functools.wraps(f)
        def wrap(request, *_args, **_kwargs):
            perm_kwargs = (
                dict(return_404=True)
                if request.user.is_anonymous
                else dict(return_403=True))
            perm_kwargs.update(kwargs)
            protected = guardian_permission_required(perm, *args, **perm_kwargs)
            return protected(f)(request, *_args, **_kwargs)
        return wrap
    return wrapper


def _download_file(prefixes, dirnames, vcs_project, relative_path):
    for prefix in prefixes:
        for dirname in dirnames:
            if vcs_project.configuration:
                locale = vcs_project.locales[0]
                absolute_path = os.path.join(vcs_project.source_directory_path, relative_path)
                absolute_l10n_path = vcs_project.configuration.l10n_path(locale, absolute_path)
                relative_l10n_path = os.path.relpath(
                    absolute_l10n_path,
                    vcs_project.locale_directory_paths[locale.code],
                )
                url = prefix.format(locale_code=relative_l10n_path)
            else:
                url = os.path.join(prefix.format(locale_code=dirname), relative_path)

            r = requests.get(url, stream=True)
            if not r.ok:
                continue

            extension = os.path.splitext(relative_path)[1]
            with tempfile.NamedTemporaryFile(
                prefix='strings' if extension == '.xml' else '',
                suffix=extension,
                delete=False,
            ) as temp:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        temp.write(chunk)
                temp.flush()

            return temp.name


def _get_relative_path_from_part(slug, part):
    """Check if part is a Resource path or Subpage name."""
    # Avoid circular import; someday we should refactor to avoid.
    from pontoon.base.models import Subpage
    try:
        subpage = Subpage.objects.get(project__slug=slug, name=part)
        return subpage.resources.first().path
    except Subpage.DoesNotExist:
        return part


def get_download_content(slug, code, part):
    """
    Get content of the file to be downloaded.

    :arg str slug: Project slug.
    :arg str code: Locale code.
    :arg str part: Resource path or Subpage name.
    """
    # Avoid circular import; someday we should refactor to avoid.
    from pontoon.sync import formats
    from pontoon.sync.vcs.models import VCSProject
    from pontoon.base.models import Entity, Locale, Project, Resource

    project = get_object_or_404(Project, slug=slug)
    locale = get_object_or_404(Locale, code=code)
    vcs_project = VCSProject(project, locales=[locale])

    # Download a ZIP of all files if project has > 1 and < 10 resources
    resources = Resource.objects.filter(project=project, translatedresources__locale=locale)
    isZipable = 1 < len(resources) < 10
    if isZipable:
        s = StringIO()
        zf = zipfile.ZipFile(s, "w")

    # Download a single file if project has 1 or >= 10 resources
    else:
        relative_path = _get_relative_path_from_part(slug, part)
        resources = [get_object_or_404(Resource, project__slug=slug, path=relative_path)]

    for resource in resources:
        # Get locale file
        locale_prefixes = (
            project.repositories.filter(permalink_prefix__contains='{locale_code}')
            .values_list('permalink_prefix', flat=True)
            .distinct()
        )
        dirnames = set([locale.code, locale.code.replace('-', '_')])
        locale_path = _download_file(locale_prefixes, dirnames, vcs_project, resource.path)
        if not locale_path and not resource.is_asymmetric:
            return None, None

        # Get source file if needed
        source_path = None
        if resource.is_asymmetric:
            source_prefixes = (
                project.repositories
                .values_list('permalink_prefix', flat=True)
                .distinct()
            )
            dirnames = VCSProject.SOURCE_DIR_NAMES
            source_path = _download_file(source_prefixes, dirnames, vcs_project, resource.path)
            if not source_path:
                return None, None

            # If locale file doesn't exist, create it
            if not locale_path:
                extension = os.path.splitext(resource.path)[1]
                with tempfile.NamedTemporaryFile(
                    prefix='strings' if extension == '.xml' else '',
                    suffix=extension,
                    delete=False,
                ) as temp:
                    temp.flush()
                locale_path = temp.name

        # Update file from database
        resource_file = formats.parse(locale_path, source_path)
        entities_dict = {}
        entities_qs = Entity.objects.filter(
            changedentitylocale__locale=locale,
            resource__project=project,
            resource__path=resource.path,
            obsolete=False
        )

        for e in entities_qs:
            entities_dict[e.key] = e.translation_set.filter(approved=True, locale=locale)

        for vcs_translation in resource_file.translations:
            key = vcs_translation.key
            if key in entities_dict:
                entity = entities_dict[key]
                vcs_translation.update_from_db(entity)

        resource_file.save(locale)

        if not locale_path:
            return None, None

        if isZipable:
            zf.write(locale_path, resource.path)
        else:
            with codecs.open(locale_path, 'r', 'utf-8') as f:
                content = f.read()
            filename = os.path.basename(resource.path)

        # Remove temporary files
        os.remove(locale_path)
        if source_path:
            os.remove(source_path)

    if isZipable:
        zf.close()
        content = s.getvalue()
        filename = project.slug + '.zip'

    return content, filename


def handle_upload_content(slug, code, part, f, user):
    """
    Update translations in the database from uploaded file.

    :arg str slug: Project slug.
    :arg str code: Locale code.
    :arg str part: Resource path or Subpage name.
    :arg UploadedFile f: UploadedFile instance.
    :arg User user: User uploading the file.
    """
    # Avoid circular import; someday we should refactor to avoid.
    from pontoon.sync import formats
    from pontoon.sync.changeset import ChangeSet
    from pontoon.sync.vcs.models import VCSProject
    from pontoon.base.models import (
        ChangedEntityLocale,
        Entity,
        Locale,
        Project,
        Resource,
        TranslatedResource,
        Translation,
    )

    relative_path = _get_relative_path_from_part(slug, part)
    project = get_object_or_404(Project, slug=slug)
    locale = get_object_or_404(Locale, code=code)
    resource = get_object_or_404(Resource, project__slug=slug, path=relative_path)

    # Store uploaded file to a temporary file and parse it
    extension = os.path.splitext(f.name)[1]
    with tempfile.NamedTemporaryFile(
        prefix='strings' if extension == '.xml' else '',
        suffix=extension,
    ) as temp:
        for chunk in f.chunks():
            temp.write(chunk)
        temp.flush()
        resource_file = formats.parse(temp.name)

    # Update database objects from file
    changeset = ChangeSet(
        project,
        VCSProject(project, locales=[locale]),
        timezone.now()
    )
    entities_qs = Entity.objects.filter(
        resource__project=project,
        resource__path=relative_path,
        obsolete=False
    ).prefetch_related(
        Prefetch(
            'translation_set',
            queryset=Translation.objects.filter(locale=locale),
            to_attr='db_translations'
        )
    ).prefetch_related(
        Prefetch(
            'translation_set',
            queryset=Translation.objects.filter(locale=locale, approved_date__lte=timezone.now()),
            to_attr='db_translations_approved_before_sync'
        )
    )
    entities_dict = {entity.key: entity for entity in entities_qs}

    for vcs_translation in resource_file.translations:
        key = vcs_translation.key
        if key in entities_dict:
            entity = entities_dict[key]
            changeset.update_entity_translations_from_vcs(
                entity, locale.code, vcs_translation, user,
                entity.db_translations, entity.db_translations_approved_before_sync
            )

    changeset.bulk_create_translations()
    changeset.bulk_update_translations()

    if changeset.changed_translations:
        # Update 'active' status of all changed translations and their siblings,
        # i.e. translations of the same entity to the same locale.
        changed_pks = {t.pk for t in changeset.changed_translations}
        (
            Entity.objects
            .filter(translation__pk__in=changed_pks)
            .reset_active_translations(locale=locale)
        )

        # Run checks and create TM entries for translations that pass them
        valid_translations = changeset.bulk_check_translations()
        changeset.bulk_create_translation_memory_entries(valid_translations)

    TranslatedResource.objects.get(resource=resource, locale=locale).calculate_stats()

    # Mark translations as changed
    changed_entities = {}
    existing = ChangedEntityLocale.objects.values_list('entity', 'locale').distinct()
    for t in changeset.changed_translations:
        key = (t.entity.pk, t.locale.pk)
        # Remove duplicate changes to prevent unique constraint violation
        if key not in existing:
            changed_entities[key] = ChangedEntityLocale(entity=t.entity, locale=t.locale)

    ChangedEntityLocale.objects.bulk_create(changed_entities.values())

    # Update latest translation
    if changeset.translations_to_create:
        changeset.translations_to_create[-1].update_latest_translation()


def latest_datetime(datetimes):
    """
    Return the latest datetime in the given list of datetimes,
    gracefully handling `None` values in the list. Returns `None` if all
    values in the list are `None`.
    """
    if all(map(lambda d: d is None, datetimes)):
        return None

    min_datetime = timezone.make_aware(datetime.min)
    datetimes = map(lambda d: d or min_datetime, datetimes)
    return max(datetimes)


def parse_time_interval(interval):
    """
    Return start and end time objects from time interval string in the format
    %d%m%Y%H%M-%d%m%Y%H%M. Also, increase interval by one minute due to
    truncation to a minute in Translation.counts_per_minute QuerySet.
    """
    def parse_timestamp(timestamp):
        return timezone.make_aware(datetime.strptime(timestamp, '%Y%m%d%H%M'), timezone=pytz.UTC)

    start, end = interval.split('-')

    return parse_timestamp(start), parse_timestamp(end) + timedelta(minutes=1)


def convert_to_unix_time(my_datetime):
    """
    Convert datetime object to UNIX time
    """
    return int(time.mktime(my_datetime.timetuple()) * 1000)


def build_translation_memory_file(creation_date, locale_code, entries):
    """
    TMX files will contain large amount of entries and it's impossible to render all the data with
    django templates.
    Rendering of string in memory is a lot faster.
    :arg datetime creation_date: when TMX file is being created.
    :arg str locale_code: code of a locale
    :arg list entries: A list which contains tuples with following items:
                         * resource_path - path of a resource,
                         * key - key of an entity,
                         * source - source string of entity,
                         * target - translated string,
                         * project_name - name of a project,
                         * project_slug - slugified name of a project,
    """
    yield (
        u'<?xml version="1.0" encoding="utf-8" ?>'
        u'\n<tmx version="1.4">'
        u'\n\t<header'
        u' adminlang="en-US"'
        u' creationtoolversion="0.1"'
        u' creationtool="pontoon"'
        u' datatype="plaintext"'
        u' segtype="sentence"'
        u' o-tmf="plain text"'
        u' srclang="en-US"'
        u' creationdate="%(creation_date)s">'
        u'\n\t</header>'
        u'\n\t<body>' % {
            'creation_date': creation_date.isoformat()
        }
    )
    for resource_path, key, source, target, project_name, project_slug in entries:
        tuid = ':'.join((project_slug, slugify(resource_path), slugify(key)))
        yield (
            u'\n\t\t<tu tuid=%(tuid)s srclang="en-US">'
            u'\n\t\t\t<tuv xml:lang="en-US">'
            u'\n\t\t\t\t<seg>%(source)s</seg>'
            u'\n\t\t\t</tuv>'
            u'\n\t\t\t<tuv xml:lang=%(locale_code)s>'
            u'\n\t\t\t\t<seg>%(target)s</seg>'
            u'\n\t\t\t</tuv>'
            u'\n\t\t</tu>' % {
                'tuid': quoteattr(tuid),
                'source': xml_escape(source),
                'locale_code': quoteattr(locale_code),
                'target': xml_escape(target),
                'project_name': xml_escape(project_name),
            }
        )

    yield (
        u'\n\t</body>'
        u'\n</tmx>'
    )


def glob_to_regex(glob):
    """This util uses python's fnmatch to convert a glob to a regex in a way
    that can then be used with django's `__regex` queryset selector.

    It prefixes the regex with `^`, and replaces the more complex match ending
    provided by fnmatch, with the simpler `$`

    Python 3: The behaviour of fnmatch was changed in
    """
    regex = re.findall(r'\(\?s:(.*)\)\\Z', fnmatch.translate(glob))[0]
    return '^%s$' % regex


def get_m2m_changes(current_qs, new_qs):
    """
    Get difference between states of a many to many relation.

    :arg django.db.models.QuerySet `current_qs`: objects from the current state of relation.
    :arg django.db.models.QuerySet `final_qs`: objects from the future state of m2m
    :returns: A tuple with 2 querysets for added and removed items from m2m
    """

    add_items = new_qs.exclude(
        pk__in=current_qs.values_list('pk', flat=True)
    )

    remove_items = current_qs.exclude(
        pk__in=new_qs.values_list('pk', flat=True)
    )

    return list(add_items), list(remove_items)


def is_same(same_translations, can_translate):
    """
    Check if translation is the same
    :arg QuerySet `same_translations`: translations that have the same string
        as a suggestion/translation.
    :arg boolean `can_translate`: user is able to submit translations.
    :returns: True if same translation already exists.
    """
    if not same_translations:
        return False

    st = same_translations[0]

    if can_translate:
        if st.approved and not st.fuzzy:
            return True
    else:
        return True

    return False


def readonly_exists(projects, locale):
    """
    :arg list projects: a list of Project instances.
    :arg Locale locale: Locale instance.
    :returns: True if a read-only ProjectLocale instance for given Projects and
        Locale exists.
    """
    # Avoid circular import; someday we should refactor to avoid.
    from pontoon.base.models import ProjectLocale

    if not isinstance(projects, (QuerySet, tuple, list)):
        projects = [projects]

    return ProjectLocale.objects.filter(
        project__in=projects,
        locale=locale,
        readonly=True,
    ).exists()
