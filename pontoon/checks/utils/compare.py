from collections import (
    namedtuple,
)

from compare_locales.checks import getChecker
from compare_locales.parser import (
    FluentParser,
)

CommentEntity = namedtuple(
    'Comment', (
        'all',
    )
)

File = namedtuple(
    'File', (
        'file',
        'locale',
    )
)

# Because we can't pass the context to all entities passed to compare locales,
# we have to create our equivalents of compare-locale's internal classes.
ComparePropertiesEntity = namedtuple(
    'ComparePropertiesEntity',
    (
        'key',
        'val',

        # We'll remove these fields at some point, currently they're required because of the current
        # implementation property files in compare-locales.
        'raw_val',
        'pre_comment',
    )
)
CompareDTDEntity = namedtuple(
    'CompareDTDEntity',
    (
        'key',
        'val',
        'raw_val',
        'pre_comment',
        'all',
    )
)
CompareFluentEntity = namedtuple(
    'FluentCompareEntity',
    (
        'entry',
    )
)


DTD_ENTITY_TMPL = '<!ENTITY %s \"%s\">'


class UnsupportedResourceTypeError(Exception):
    """Raise if compare-locales doesn't support given resource-type."""
    pass


def cast_to_compare_locales(resource_ext, entity, string, plural_form):
    """
    Cast a Pontoon's translation object into Entities supported by `compare-locales`.

    :arg basestring resource_ext: extension of a resource.
    :arg pontoon.base.models.Entity entity: Source entity
    :arg basestring string: a translation
    :arg pontoon.base.models.Locale locale: Locale of a translation
    :arg int plural_form: plural form of a translation
    :return: source entity and translation entity that will be compatible a compare-locales checker.
        Type of those entities depends on the resource_ext.
    """
    if resource_ext == '.properties':
        if plural_form:
            entity_string = entity.string_plural
        else:
            entity_string = entity.string

        return (
            ComparePropertiesEntity(
                entity.key,
                entity_string,
                entity_string,
                CommentEntity(entity.comment)
            ),
            ComparePropertiesEntity(
                entity.key,
                string,
                string,
                CommentEntity(entity.comment),
            )
        )

    elif resource_ext == '.dtd':
        return (
            CompareDTDEntity(
                entity.key,
                entity.string,
                entity.string,
                CommentEntity(entity.comment),
                DTD_ENTITY_TMPL % (entity.key, entity.string)
            ),
            CompareDTDEntity(
                entity.key,
                string,
                string,
                CommentEntity(entity.comment),
                DTD_ENTITY_TMPL % (entity.key, entity.string)
            )
        )

    elif resource_ext == '.ftl':
        parser = FluentParser()

        parser.readContents(entity.string)
        refEntity, = list(parser)

        parser.readContents(string)
        trEntity, = list(parser)
        return (
            refEntity,
            trEntity,
        )

    raise UnsupportedResourceTypeError(resource_ext)


def quality_check(entity, locale, string, plural_form):
    """
    Run all compare-locales checks on provided translation and entity.
    :arg pontoon.base.models.Entity entity: Source entity instance
    :arg basestring string: translation string
    :arg pontoon.base.models.Locale locale: Locale of a translation
    :arg int plural_form: plural form of a translation

    :return: Dictionary with the following structure:
        {
            'clErrors': [
                'Error1',
            ],
            'clWarnings': [
                'Warning1',
            ]
        }
        Both keys are optional.
    """
    resource_ext = ".{}".format(entity.resource.format)

    source_ent, translation_ent = cast_to_compare_locales(
        resource_ext,
        entity,
        string,
        plural_form
    )

    checker = getChecker(
        File(entity.resource.path, locale),
        {'android-dtd'}
    )

    # Currently, references are required only by DTD files but that may change in the future.
    if checker.needs_reference:
        references = [
            CompareDTDEntity(
                e.key,
                e.string,
                e.string,
                e.comment,
                DTD_ENTITY_TMPL % (e.key, e.string)
            )
            for e in entity.resource.entities.all()
        ]
        checker.set_reference(references)

    errors = {}

    for (severity, _, message, _) in checker.check(source_ent, translation_ent):
        errors.setdefault("cl%ss" % severity.capitalize(), []).append(message)

    return errors

