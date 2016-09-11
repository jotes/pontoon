from abc import ABCMeta, abstractproperty


class MissingSourceTerm(Exception):
    """Couldn't find a term for the any of the source locales
    e.g. en-gb or en-us."""


class VCSTerm(object):
    """
    This abstract class is a bridge to have easy
    import of terms from various formats of files.
    """
    __metaclass__ = ABCMeta

    @abstractproperty
    def source_text(self):
        """A en-us/en-gb version of string that describes term."""

    @abstractproperty
    def note(self):
        """Contains additional information about the term e.g. a part of speech"""

    @abstractproperty
    def description(self):
        """Describes an entry in the source language."""

    @abstractproperty
    def translations(self):
        """Map of locales and translations of the source terminology entry."""
