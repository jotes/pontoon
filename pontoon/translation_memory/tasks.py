import logging

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q

from django.utils import timezone

from celery import shared_task

from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.helpers import bulk

from pontoon.base.models import (ChangedEntityLocale,
    Entity,
    Translation,
    Locale)

from pontoon.base.tasks import PontoonTask

from pontoon.base.errors import send_exception
from pontoon.translation_memory.indexes import get_index_name, TranslationMapping, IndexSettings

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
            '_index': get_index_name(locale),
            '_type': 'entities',
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

    for locale_code in Locale.objects.all().values_list('code', flat=True):
        index_name = get_index_name(locale_code)
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name)
            es.indices.close(   index_name)
            es.indices.put_settings(index=index_name, body=IndexSettings)
            es.indices.put_mapping(index=index_name, doc_type='entities', body=TranslationMapping)
            es.indices.close(index=index_name)

    translations = Translation.objects.filter(approved=True, suggested=False, fuzzy=False, **translation_query)\
            .filter(Q(plural_form__isnull=True)|Q(plural_form=0))\
        .values_list('pk', 'entity__pk', 'string', 'entity__string','locale__code', 'plural_form'
    )

    log.info("Indexing translations: {}".format(translations.count()))
    with transaction.atomic():
        bulk(es, map(translation_to_action, translations))
        translations.update(suggested=True)


