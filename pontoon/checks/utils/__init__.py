from django.http import JsonResponse

import compare
import translate_toolkit


def get_quality_checks(entity, locale, plural_form, string, ignore_warnings):
    """
    Main function that performs all quality checks from frameworks handled in Pontoon.

    :arg pontoon.base.models.Entity entity: Source entity
    :arg pontoon.base.models.Locale locale: Locale of a translation
    :arg basestring string: a translation
    :arg int plural_form: plural form of a translation
    :arg bool ignore_warnings: omit warnings
    :return: Return types:
        * JsonResponse - If there are errors or
        * None - If there's no errors and non-omitted warnings.
    """

    try:
        cl_checks = compare.quality_check(entity, locale.code, string, plural_form)
    except compare.UnsupportedResourceTypeError:
        cl_checks = None

    resource_ext = entity.resource.format

    # Some of checks from compare-locales overlap checks from Translate Toolkit
    tt_disabled_checks = set()

    if cl_checks is not None:
        if resource_ext == 'properties':
            tt_disabled_checks = {
                'escapes',
                'nplurals',
                'printf'
            }

    tt_checks = translate_toolkit.quality_check(entity.string, string, locale, tt_disabled_checks)

    checks = dict(
        tt_checks,
        **(cl_checks or {})
    )

    if (not ignore_warnings and checks) or ('clErrors' in checks):
        return JsonResponse({
            'checks': checks
        })
