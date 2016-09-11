from __future__ import unicode_literals
import logging

from django.db import models
from django.contrib.postgres.fields import JSONField

log = logging.getLogger(__name__)


class TermManager(models.Manager):
    def import_vcs_terms(self, vcs_terms):
        """
        Creates/updates term objects passed from the parsed terminology files.

        :param VCSTerm vcs_terms: a list of terms imported from the filesystem/vcs.
        """
        new_terms = []
        updated_records = 0
        for term in vcs_terms:
            try:
                db_term = self.get(term_id=term.id)
                db_term.note = term.note
                db_term.description = term.description
                db_term.translations.update(term.translations)
                db_term.save()
                updated_records += 1
            except Term.DoesNotExist:
                new_terms.append(
                    Term(
                        term_id=term.id,
                        source_term=term.source_text,
                        note=term.note,
                        description=term.description,
                        translations=term.translations,
                    )
                )
        log.info('Updated {} existing terms.'.format(updated_records))

        if new_terms:
            self.bulk_create(new_terms, 1000)

        log.info('Inserted {} new terms.'.format(len(new_terms)))


class Term(models.Model):
    """
    Defines a single term entry.
    """

    """Unique identified of term imported from the tbx file."""
    term_id = models.CharField(max_length=30, unique=True)

    """Source string (in en-US) that contains value to search in strings."""
    source_term = models.TextField(db_index=True)

    """Contains the part of speech."""
    note = models.TextField()

    """Description of term, adds more context."""
    description = models.TextField()

    """Map of translations, locales codes are keys and translations are values."""
    translations = JSONField()

    objects = TermManager()
