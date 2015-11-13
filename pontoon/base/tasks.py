import sys

from celery import Task
import logging

from celery import Task, shared_task
from celery.contrib.batches import Batches

from django.conf import settings

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from pontoon.base.errors import send_exception

log = logging.getLogger(__name__)

class FailureMixin(object):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Celery throws away the traceback instance and creates its own,
        # but inspect can't process their custom class.
        _, _, traceback = sys.exc_info()
        send_exception(exc, exc_info=(einfo.type, exc, traceback))


class PontoonTask(Task, FailureMixin):
    """Common functionality for all Pontoon celery tasks."""
    abstract = True

class PontoonBatchesTask(Batches, FailureMixin):
    """Common functionality for all batch-like tasks."""
    abstract=True


@shared_task(base=PontoonBatchesTask, bind=True, flush_every=settings.TM_FLUSH_EVERY,
    flush_interval=settings.TM_FLUSH_INTERVAL)
def update_translation_memory(self, translations):
    """
    Tasks takes a batches of translations.
    :param translations: list of translations, batched by Batches task class.
    """
    def translation_to_action(translation):
        translation_pk = translation.pop('pk')
        return {
            '_id': translation_pk,
            '_index': settings.TM_ELASTICSEARCH_INDEX,
            '_type': settings.TM_ELASTICSEARCH_TYPE,
            '_source': translation
        }
    es = Elasticsearch(**settings.TM_ELASTICSEARCH_CONNECTION)
    bulk(es, map(translation_to_action, translations))
    log.info("Indexed {} translations.".format(len(translations)))
