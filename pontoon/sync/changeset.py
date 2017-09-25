import logging
from collections import defaultdict

from bulk_update.helper import bulk_update
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.template.defaultfilters import pluralize
from notifications.signals import notify

from pontoon.base.checks import check_translations
from pontoon.base.models import (
    Entity,
    Locale,
    Translation,
    TranslationMemoryEntry,
    FailingCheck
)
from pontoon.base.utils import match_attr

log = logging.getLogger(__name__)


class ChangeSet(object):
    """
    Stores a set of changes to be made to the database and the
    translations stored in VCS. Once all the necessary changes have been
    stored, execute all the changes at once efficiently.
    """

    def __init__(self, db_project, vcs_project, now, locale=None):
        """
        :param now:
            Datetime to use for marking when approvals happened.
        """
        self.db_project = db_project
        self.vcs_project = vcs_project
        self.now = now
        self.locale = locale

        # Store locales and resources for FK relationships.
        self.locales = {l.code: l for l in Locale.objects.all()}
        self.resources = {r.path: r for r in self.db_project.resources.all()}

        self.executed = False
        self.changes = {
            'update_vcs': [],
            'update_db': [],
            'obsolete_db': [],
            'create_db': []
        }

        self.entities_to_update = []
        self.translations_to_update = {}
        self.translations_to_create = []
        self.failing_checks = defaultdict(list)
        self.commit_authors_per_locale = defaultdict(list)
        self.locales_to_commit = set()

    def update_vcs_entity(self, locale, db_entity, vcs_entity):
        """
        Replace the translations in VCS with the translations from the
        database.
        Updates only entities that has been changed.
        """
        if db_entity.has_changed(locale):
            self.changes['update_vcs'].append((locale.code, db_entity, vcs_entity))
            self.locales_to_commit.add(locale)

    def create_db_entity(self, vcs_entity):
        """Create a new entity in the database."""
        self.changes['create_db'].append(vcs_entity)

    def update_db_entity(self, locale, db_entity, vcs_entity):
        """Update the database with translations from VCS."""
        self.changes['update_db'].append((locale.code, db_entity, vcs_entity))

    def update_db_source_entity(self, db_entity, vcs_entity):
        """Update the entities with the latest data from vcs."""
        self.changes['update_db'].append((None, db_entity, vcs_entity))

    def obsolete_db_entity(self, db_entity):
        """Mark the given entity as obsolete."""
        self.changes['obsolete_db'].append(db_entity.pk)

    def execute(self):
        """
        Execute the changes stored in this changeset. Execute can only
        be called once per changeset; subsequent calls raise a
        RuntimeError, even if the changes failed.
        """
        if self.executed:
            raise RuntimeError('execute() can only be called once per changeset.')
        else:
            self.executed = True

        # Perform the changes and fill the lists for bulk creation and
        # updating.
        self.execute_update_vcs()
        self.execute_create_db()
        self.execute_update_db()
        self.execute_obsolete_db()

        # Apply the built-up changes to the DB
        self.bulk_update_entities()
        self.bulk_create_translations()
        self.bulk_update_translations()
        self.bulk_create_translaton_memory_entries()

    def execute_update_vcs(self):
        resources = self.vcs_project.resources
        changed_resources = set()

        for locale_code, db_entity, vcs_entity in self.changes['update_vcs']:
            changed_resources.add(resources[db_entity.resource.path])
            vcs_translation = vcs_entity.translations[locale_code]
            db_translations = db_entity.translation_set.filter(
                approved=True,
                locale__code=locale_code
            )
            vcs_translation.update_from_db(db_translations)

            # Track which translators were involved.
            self.commit_authors_per_locale[locale_code].extend(
                [t.user for t in db_translations if t.user]
            )

        for resource in changed_resources:
            resource.save(self.locale)

    def get_entity_updates(self, vcs_entity, db_entity=None):
        """
        Return a dict of the properties and values necessary to create
        or update a database entity from a VCS entity.
        """
        return {
            'resource': self.resources[vcs_entity.resource.path],
            'string': vcs_entity.string,
            'string_plural': vcs_entity.string_plural,
            'key': vcs_entity.key,
            'comment': '\n'.join(vcs_entity.comments),
            # one timestamp per import, unlike timezone.now()
            'date_created': db_entity.date_created if db_entity else self.now,
            'order': vcs_entity.order,
            'source': vcs_entity.source,
        }

    def send_notifications(self, new_entities):
        """
        Notify project contributors if new entities have been added.
        """
        count = len(new_entities)

        if count > 0:
            log.info('Sending new string notifications for project {}.'.format(self.db_project))

            verb = 'updated with {} new string{}'.format(count, pluralize(count))
            contributors = User.objects.filter(
                translation__entity__resource__project=self.db_project
            ).distinct()

            for contributor in contributors:
                notify.send(
                    self.db_project,
                    recipient=contributor,
                    verb=verb
                )

            log.info('New string notifications for project {} sent.'.format(self.db_project))

    def execute_create_db(self):
        new_entities = []

        for vcs_entity in self.changes['create_db']:
            # We can't use bulk_create since we need a PK
            entity, created = Entity.objects.get_or_create(**self.get_entity_updates(vcs_entity))

            if created:
                new_entities.append(entity)

            for locale_code, vcs_translation in vcs_entity.translations.items():
                for plural_form, string in vcs_translation.strings.items():
                    self.translations_to_create.append(Translation(
                        entity=entity,
                        locale=self.locales[locale_code],
                        string=string,
                        plural_form=plural_form,
                        approved=not vcs_translation.fuzzy,
                        approved_date=self.now if not vcs_translation.fuzzy else None,
                        fuzzy=vcs_translation.fuzzy
                    ))

        self.send_notifications(new_entities)

    def update_entity_translations_from_vcs(
            self, db_entity, locale_code, vcs_translation,
            user=None, db_translations=None, db_translations_approved_before_sync=None
    ):
        if db_translations is None:
            db_translations = db_entity.translation_set.filter(
                locale__code=locale_code,
            )

        if db_translations_approved_before_sync is None:
            db_translations_approved_before_sync = db_translations.filter(
                approved_date__lte=self.now
            )

        approved_translations = []
        fuzzy_translations = []

        for plural_form, string in vcs_translation.strings.items():
            db_translation = match_attr(db_translations, plural_form=plural_form, string=string)

            # Modify existing translation.
            if db_translation:
                if not db_translation.approved and not vcs_translation.fuzzy:
                    db_translation.approved = True
                    db_translation.approved_user = user
                    db_translation.approved_date = self.now
                db_translation.rejected = False
                db_translation.fuzzy = vcs_translation.fuzzy
                db_translation.extra = vcs_translation.extra

                if db_translation.is_dirty():
                    self.translations_to_update[db_translation.pk] = db_translation
                if db_translation.fuzzy:
                    fuzzy_translations.append(db_translation)
                else:
                    approved_translations.append(db_translation)

            # Create new translation.
            else:
                self.translations_to_create.append(Translation(
                    entity=db_entity,
                    locale=self.locales[locale_code],
                    string=string,
                    plural_form=plural_form,
                    approved=not vcs_translation.fuzzy,
                    approved_user=user,
                    approved_date=self.now if not vcs_translation.fuzzy else None,
                    user=user,
                    fuzzy=vcs_translation.fuzzy,
                    extra=vcs_translation.extra
                ))

        # Unapprove translations that were approved before the sync job started unless sync
        # resolves them as active approved translations.
        # Note: If translations get approved after the sync starts, duplicate approvals can arise.
        # We take care of that at the and of the sync job in tasks.py.
        for translation in db_translations_approved_before_sync:
            if translation not in approved_translations:
                # Use the translation instance already set for update if it exists.
                translation = self.translations_to_update.get(translation.pk, translation)
                translation.approved = False
                translation.approved_user = None
                translation.approved_date = None

                # Reject translations unless they became fuzzy during sync. Condition is sufficient
                # because they were approved previously.
                if not translation.fuzzy:
                    translation.rejected = True
                    translation.rejected_user = user
                    translation.rejected_date = self.now

                if translation.is_dirty():
                    self.translations_to_update[translation.pk] = translation

        # Unfuzzy existing translations unless sync resolves them as active fuzzy translations.
        # Note: Translations cannot get fuzzy after the sync job starts, because they cannot be
        # made fuzzy in Pontoon.
        for translation in db_translations:
            if translation not in fuzzy_translations:
                # Use the translation instance already set for update if it exists.
                translation = self.translations_to_update.get(translation.pk, translation)
                translation.fuzzy = False

                if translation.is_dirty():
                    self.translations_to_update[translation.pk] = translation

    def prefetch_entity_translations(self):
        prefetched_entities = {}

        locale_entities = {}
        for locale_code, db_entity, vcs_entity in self.changes['update_db']:
            locale_entities.setdefault(locale_code, []).append(db_entity.pk)

        for locale in locale_entities.keys():
            entities_qs = Entity.objects.filter(
                pk__in=locale_entities[locale],
            ).prefetch_related(
                Prefetch(
                    'translation_set',
                    queryset=Translation.objects.filter(locale__code=locale),
                    to_attr='db_translations'
                )
            ).prefetch_related(
                Prefetch(
                    'translation_set',
                    queryset=Translation.objects.filter(
                        locale__code=locale,
                        approved_date__lte=self.now
                    ),
                    to_attr='db_translations_approved_before_sync'
                )
            )
            prefetched_entities[locale] = {entity.id: entity for entity in entities_qs}

        return prefetched_entities

    def execute_update_db(self):
        if self.changes['update_db']:
            entities_with_translations = self.prefetch_entity_translations()

        for locale_code, db_entity, vcs_entity in self.changes['update_db']:
            for field, value in self.get_entity_updates(vcs_entity, db_entity).items():
                setattr(db_entity, field, value)

            if db_entity.is_dirty(check_relationship=True):
                self.entities_to_update.append(db_entity)

            if locale_code is not None:
                # Update translations for the entity.
                vcs_translation = vcs_entity.translations[locale_code]
                prefetched_entity = entities_with_translations[locale_code][db_entity.id]
                self.update_entity_translations_from_vcs(
                    db_entity,
                    locale_code,
                    vcs_translation,
                    None,
                    prefetched_entity.db_translations,
                    prefetched_entity.db_translations_approved_before_sync
                )

    def execute_obsolete_db(self):
        (Entity.objects
            .filter(pk__in=self.changes['obsolete_db'])
            .update(obsolete=True))

    def bulk_update_entities(self):
        if len(self.entities_to_update) > 0:
            bulk_update(self.entities_to_update, update_fields=[
                'resource',
                'string',
                'string_plural',
                'key',
                'comment',
                'order',
                'source',
            ])

    def bulk_create_failing_checks(self, translations):
        failing_checks = []
        # Group translations by their respective resources
        # In order to create a table of references
        resource_translations = defaultdict(list)

        for translation in translations.prefetch_related('entity__resource'):
            resource_translations[translation.entity.resource].append(translation)

        FailingCheck.objects.filter(
            translation__in=translations
        ).delete()

        for resource, translations in resource_translations.items():
            for translation_pk, errors in check_translations(resource, translations).items():
                for severity, message in errors:
                    failing_checks.append(
                        FailingCheck(
                            translation=translation,
                            severity=severity,
                            message=message
                        )
                    )

        FailingCheck.objects.bulk_create(failing_checks)

    def bulk_create_translations(self):
        Translation.objects.bulk_create(self.translations_to_create)
        self.bulk_create_failing_checks(
            Translation.objects.filter(pk__in=[t.pk for t in self.translations_to_create]).prefetch_related('entity')
        )

    def bulk_update_translations(self):
        if len(self.translations_to_update) > 0:
            bulk_update(self.translations_to_update.values(), update_fields=[
                'entity',
                'locale',
                'string',
                'plural_form',
                'approved',
                'approved_user_id',
                'approved_date',
                'rejected',
                'fuzzy',
                'extra'
            ])
            self.bulk_create_failing_checks(
                Translation.objects.filter(pk__in=[t for t in self.translations_to_update]).prefetch_related('entity')
            )


    def bulk_create_translaton_memory_entries(self):
        """
        Create Translation Memory entries for:
            - new translations
            - updated translations that are approved and don't have a TM entry yet
        """
        translations_to_create_translaton_memory_entries_for = (
            self.translations_to_create +
            list(
                Translation.objects.filter(
                    pk__in=[pk for pk, t in self.translations_to_update.items() if t.approved],
                    memory_entries__isnull=True
                )
            )
        )

        memory_entries = [TranslationMemoryEntry(
            source=t.entity.string,
            target=t.string,
            locale_id=t.locale_id,
            entity_id=t.entity.pk,
            translation_id=t.pk,
            project=self.db_project,
        ) for t in translations_to_create_translaton_memory_entries_for]

        TranslationMemoryEntry.objects.bulk_create(memory_entries)
