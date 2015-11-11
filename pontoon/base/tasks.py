<<<<<<< HEAD
import sys

from celery import Task
=======
from celery import Task, shared_task
from celery.batches import Batches
from django.conf import settings
>>>>>>> Added task to update elasticsearch

from elasticsearch import ElasticSearch
from elasticsearch.helpers import bulk
from pontoon.base.errors import send_exception

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

@shared_task(base=PontoonBatchesTask, flush_every=settings.TM_FLUSH_EVERY,
    flush_interval=settings.TM_FLUSH_INTERVAL)
def update_memory_translation(translations):
    def translation_to_action(translation):
        translation_pk = translation.pop('pk')
        return {
            '_id': translation_pk,
            '_index': settings.TM_ELASTICSEARCH_INDEX,
            '_type': settings.TM_ELASTICSEARCH_TYPE,
            '_source': translation
        }
    es = ElasticSearch(**settings.TM_ELASTICSEARCH_CONNECTION)
    bulk(es, map(translation_to_action, translations))
>>>>>>> Added task to update elasticsearch
