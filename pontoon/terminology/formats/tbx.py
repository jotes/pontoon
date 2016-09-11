"""
This module tries to implement subset of The TBX Basic format.

First version of the implementation allows to import files download
from The Microsoft Language Portal.

However, there's a lot corner-cases that aren't handled and they will
be implemented in the future versions.

As the name suggest, TBX is the xml complaint format, that can be parsed by
the any xml library.

We try to wrap all xml structures in python classes to make the code more readable.

For the more informations about The TBX Basic format you can look at:

"""
from defusedxml.minidom import parseString

from pontoon.terminology.formats import (
    VCSTerm,
    MissingSourceTerm
)


class TBXObject(object):
    """
    All tbx objects will share the same constructor that
    will receive an instance of a xml object.
    """
    def __init__(self, xml_node):
        self.xml_node = xml_node

    @property
    def description(self):
        """
        Most of the object in tbx file have a description property.
        """
        for child in self.xml_node.childNodes:
            if child.tagName == 'descrip':
                return child.childNodes[0].data

            elif child.tagName == 'descripGrp':
                return child.childNodes[0].childNodes[0].data


class Translation(TBXObject):
    @property
    def text(self):
        return self.xml_node.getElementsByTagName('term')[0].childNodes[0].data

    @property
    def notes(self):
        notes_ = {}
        for note in self.xml_node.getElementsByTagName('termNote'):
            note_type = str(note.getAttribute('type'))
            note_text = str(note.childNodes[0].data)

            notes_[note_type] = note_text
        return notes_

    @property
    def term_type(self):
        return self.notes.get('type')

    @property
    def part_of_speech(self):
        return self.notes.get('partOfSpeech')


class LangSet(TBXObject):
    @property
    def lang(self):
        return self.xml_node.getAttribute('xml:lang')

    @property
    def translations(self):
        return map(Translation, self.xml_node.getElementsByTagName('ntig'))


class TBXVCSTerm(TBXObject):
    """
    TBX files contains a set of elements called entryTerms, they contains
    langset and translation of the term.
    This is a proxy class that will help to map those into objects that will
    be later imported to pontoon database.
    """
    @property
    def id(self):
        return self.xml_node.getAttribute('id')

    @property
    def langsets(self):
        """
        A map of locale codes to their respective langset objects.
        """
        results = {}
        for lang_set in map(LangSet, self.xml_node.getElementsByTagName('langSet')):
            results[lang_set.lang] = lang_set
        return results

    @property
    def source_langset(self):
        """
        Most of the code/structure in pontoon assume that base source
        strings are in en-GB or en-US. That implies that we'll need
        strings from these locales to perform join between existing
        entities and terms from the new terminology module.
        """
        langsets = self.langsets
        langset = langsets.get('en-GB', langsets.get('en-US'))
        if not langset:
            raise MissingSourceTerm()

        return langset

    @property
    def source_term(self):
        return self.source_langset.terms[0]

    @property
    def source_text(self):
        return self.source_term.text

    @property
    def note(self):
        return self.source_term.part_of_speech

    @property
    def description(self):
        return self.source_term.description or self.source_langset.description

    @property
    def translations(self):
        trans = {}
        for langset in self.entryTerm.langsets.values():
            for term in langset.translations:
                trans.setdefault(langset.lang, []).append(term.text)

        return trans


def parse_terms(file_contents):
    """
    Parse a TBX file and return possiby all terms that are inside.

    :param str file_contents: contents of a tbx file
    :returns: a list of VCSTerm complaint objects
    """
    xml_file = parseString(file_contents)

    return (TBXVCSTerm(entryTerm) for entryTerm in xml_file.getElementsByTagName('termEntry'))


VCSTerm.register(TBXVCSTerm)
