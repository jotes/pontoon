import logging

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from celery import shared_task

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from pontoon.base.models import (ChangedEntityLocale,
    Entity,
    Translation)

from pontoon.base.tasks import PontoonTask

from pontoon.translation_memory.indexes import create_translation_index

log = logging.getLogger(__name__)

@shared_task(base=PontoonTask)
def sync_translation_memory(project_pk=None):
    """
    Updates translation memory (Elasticsearch) with latest approved translations.
    """
    def translation_to_action((pk, entity_pk, target, source, locale, plural_form)):
        """
        Maps translation instance into one of elasticsearch's actions.
        """
        return {
            '_id': pk,
            '_index': settings.TM_ELASTICSEARCH_INDEX,
            '_type': settings.TM_ELASTICSEARCH_TYPE,
            'entity_pk': entity_pk,
            'source': source,
            'target': target,
            'locale': locale,
            'plural_form': plural_form,
        }
    translation_query = {}

    if project_pk:
        translation_query['entity__in'] = Entity.objects.filter(resource__project=project_pk).values_list('pk', flat=True)

    es = Elasticsearch(**settings.TM_ELASTICSEARCH_CONNECTION)

    create_translation_index(es)

    translations = Translation.objects.filter(approved=True, suggested=False, fuzzy=False, **translation_query)\
        .values_list('pk', 'entity__pk', 'string', 'entity__string','locale__code', 'plural_form'
    )
    # @TODO: add transaction and marking translations as suggested

    bulk(es, map(translation_to_action, translations))
    log.info("Indexed translations: {}".format(translations.count()))
