from __future__ import unicode_literals
import logging

from bulk_update.helper import bulk_update
from django.db import models
from django.contrib.postgres.fields import JSONField

log = logging.getLogger(__name__)


class TermManager(models.Manager):
    def import_vcs_terms(self, vcs_terms):
        """
        Creates/updates term objects passed from the parsed terminology files.

        :param VCSTerm vcs_terms: a list of terms imported from the filesystem/vcs.
        """
        def update_db_translations(db_translations, vcs_translations):
            db_translations.update(vcs_translations)

        db_terms = {}
        for term in Term.objects.all():
            db_terms[term.term_id] = term

        new_terms = []
        update_terms = []
        updated_records = 0
        for term in vcs_terms:
            try:
                # import ipdb; ipdb.set_trace()

                db_term = db_terms[term.id] #self.get(term_id=term.id)
                db_term.note = term.note
                db_term.description = term.description
                update_db_translations(db_term.translations, term.translations)
                update_terms.append(db_term)
                updated_records += 1
            except KeyError:
                new_terms.append(
                    Term(
                        term_id=term.id,
                        source_term=term.source_text,
                        note=term.note,
                        description=term.description,
                        translations=term.translations,
                    )
                )

        if update_terms:
            bulk_update(update_terms, update_fields=['note', 'description', 'translations'], batch_size=10)
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

    def __unicode__(self):
        return self.source_term
