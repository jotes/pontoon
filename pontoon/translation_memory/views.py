import json
import logging

from elasticsearch import Elasticsearch

from django.conf import settings
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.shortcuts import render


def translation_memory():
    """Get translations from internal translations."""
    try:
        text, locale, pk = request.GET['text'], request.GET['locale'], int(request.GET['pk'])
    except (MultiValueDictKeyError, ValueError) as e:
        log.error(e)
        return HttpResponse('error')

    es = Elasticsearch(**settings.TM_ELASTICSEARCH_CONNECTION)
    translations = es.suggest(index=settings.TM_ELASTICSEARCH_INDEX, body={
        'text': text,
        'simple_phrase': {
            'field': 'source',
            'context': {
                'locale': locale
            }
        }
    })

    context = {
        'translations': filter(lambda t: t['pk'] != pk, translations)
    }

    return HttpResponse(json.dumps(context))
