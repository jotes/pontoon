from __future__ import unicode_literals
from collections import defaultdict
import logging
import string

from bulk_update.helper import bulk_update
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property

from pontoon.base.models import (
    Entity,
    Locale,
)


log = logging.getLogger(__name__)


class TermManager(models.Manager):
    @cached_property
    def term_index(self):
        """
        Keeps a memory index of terms for a faster lookups. However, the first call will always take a moment.
        """
        index = defaultdict(list)
        for term_pk, term_text in self.get_queryset().order_by('-source_term').values_list('pk', 'source_term'):
            for word in self.get_words(term_text):
                index[word].append((term_pk, term_text))
        return index

    def get_words(self, s):
        """
        Retrieves an unified list of words from string (removes whitespaces, punctuation etc.).
        """
        return (
            (' '.join(s.split()))
                .translate(string.whitespace)
                .translate(string.punctuation)
                .lower()
                .strip()
                .split()
        )

    def find_terms(self, string):
        """Return terms ids that are in string."""
        string_copy = string
        terms = []
        candidate_terms = reduce(
            # Concatenate lists of candidates returned from the term_index.
            lambda x, y: x + y,
            [self.term_index.get(word, []) for word in self.get_words(string_copy)]
        )
        sorted_terms = sorted(candidate_terms, key=lambda t: t[1], reverse=True)
        for term_pk, term_text in sorted_terms:
            if string_copy.find(term_text) != -1:
                terms.append(term_pk)
                string_copy = string_copy.replace(term_text, '')

        return terms


    def assign_terms_to_entities(self, entities):
        entity_terms = []

        EntityToTerm = Term.entities.through

        # Remove existing terms relations.
        EntityToTerm.objects.filter(entity__in=[e[0] for e in entities]).delete()

        for entity_pk, string, string_plural in entities:
            if string:
                entity_terms.extend([
                    (entity_pk, term_pk) for term_pk in self.find_terms(string)
                ])

            if string_plural:
                entity_terms.extend([
                    (entity_pk, term_pk) for term_pk in self.find_terms(string_plural)
                ])

        entity_terms = set(entity_terms)
        EntityToTerm.objects.bulk_create(
            (EntityToTerm(entity_id=e, term_id=t) for (e, t) in entity_terms),
            10000
        )
        terms_count = len({term_pk for _, term_pk in entity_terms})
        entities_count = len({entity_pk for entity_pk, _ in entity_terms})
        log.info('Assigned {} terms to {} entities.'.format(terms_count, entities_count))

    def import_terms(self, vcs_terms):
        """
        Creates/updates term objects passed from the parsed terminology files.

        :param VCSTerm vcs_terms: a list of terms imported from the filesystem/vcs.
        """
        db_terms = {}
        vcs_term_map = {term.id: term for term in vcs_terms}

        for term in Term.objects.all():
            db_terms[term.term_id] = term

        new_terms = []
        update_terms = []
        updated_records = 0

        for term in vcs_terms:
            try:
                db_term = db_terms[term.id]
                db_term.note = term.note
                db_term.description = term.description
                update_terms.append(db_term)
                updated_records += 1
            except KeyError:
                new_terms.append(
                    Term(
                        term_id=term.id,
                        source_term=term.source_text,
                        note=term.note,
                        description=term.description,
                    )
                )

        if update_terms:
            bulk_update(update_terms, update_fields=['note', 'description'], batch_size=100)
            log.info('Updated {} existing terms.'.format(updated_records))

        if new_terms:
            self.bulk_create(new_terms, 1000)
            log.info('Inserted {} new terms.'.format(len(new_terms)))

        changed_terms = (new_terms + update_terms)
        TermTranslation.objects.filter(term__in=changed_terms).delete()

        locale_cache = {locale.code: locale for locale in Locale.objects.all()}
        update_translations = []
        for term in changed_terms:
            vcs_term = vcs_term_map[term.term_id]
            for locale_code, translations in vcs_term.translations.items():
                for translation in translations:
                    update_translations.append(
                        TermTranslation(
                            locale=locale_cache[locale_code],
                            text=translation,
                            term=term,
                        )
                    )
        TermTranslation.objects.bulk_create(update_translations)

        log.info('Updated {} translations of terms.'.format(len(update_translations)))

        self.assign_terms_to_entities(Entity.objects.values_list('pk', 'string', 'string_plural'))




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

    entities = models.ManyToManyField(Entity, related_name='terminology_terms')
    objects = TermManager()

    def __unicode__(self):
        return self.source_term

    def serialize(self, locale):
        if hasattr(self, 'cached_translations'):
            translations = self.cached_translations
        else:
            translations = self.translations.all()
        return {
            'term': self.source_term,
            'note': self.note,
            'description': self.description,
            'translations': [
                t.text for t in translations
            ]
        }


class TermTranslation(models.Model):
    """
    Map of translations, locales codes are keys and translations are values.
    """
    locale = models.ForeignKey(Locale, related_name='terms_translations')
    term = models.ForeignKey(Term, related_name='translations')

    text = models.TextField()

