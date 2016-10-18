"""
Parsing resource files.

See base.py for the ParsedResource base class.
"""
import os.path

from pkg_resources import iter_entry_points

from pontoon.sync.formats import lang, po, silme, xliff, l20n, ftl

# To add support for a new resource format, add an entry to this dict
# where the key is the extension you're parsing and the value is a
# callable returning an instance of a ParsedResource subclass.
SUPPORTED_FORMAT_PARSERS = {
    '.lang': lang.parse,
    '.po': po.parse,
    '.pot': po.parse,
    '.xliff': xliff.parse,
    '.dtd': silme.parse_dtd,
    '.properties': silme.parse_properties,
    '.ini': silme.parse_ini,
    '.inc': silme.parse_inc,
    '.l20n': l20n.parse,
    '.ftl': ftl.parse,
}



for entry_point in iter_entry_points(group='pontoon.sync.plugins', name=None):
    entry = entry_point.load()
    if not hasattr(entry_point, 'plugin'):
        for supported_format in entry.supported_formats:
            SUPPORTED_FORMAT_PARSERS[supported_format] = entry.parse


def parse(path, source_path=None, locale=None):
    """
    Parse the resource file at the given path and return a
    ParsedResource with its translations.

    :param path:
        Path to the resource file to parse.
    :param source_path:
        Path to the corresponding resource file in the source directory
        for the resource we're parsing. Asymmetric formats need this
        for saving. Defaults to None.
    :param locale:
        Object which describes information about currently processed locale.
        Some of the formats require information about things like e.g. plural form.
    """
    root, extension = os.path.splitext(path)
    if extension in SUPPORTED_FORMAT_PARSERS:
        return SUPPORTED_FORMAT_PARSERS[extension](path, source_path=source_path, locale=locale)
    else:
        raise ValueError('Translation format {0} is not supported.'
                         .format(extension))
