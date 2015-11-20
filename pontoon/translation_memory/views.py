import json
import logging

from elasticsearch import Elasticsearch

from django.conf import settings
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.shortcuts import render
from pontoon.translation_memory.indexes import get_index_name


def translation_memory(request):
    """Get translations from internal translations."""
    try:
        text, locale, pk = request.GET['text'], request.GET['locale'], int(request.GET['pk'])
    except (MultiValueDictKeyError, ValueError) as e:
        log.error(e)
        return HttpResponse('error')

    es = Elasticsearch(**settings.TM_ELASTICSEARCH_CONNECTION)
    translations = es.search(index=get_index_name(locale), doc_type='entities', body={
        'query':{'fuzzy': {
            'source': {
                'value': text,
                'fuzziness': 1
            },
        }}
    })
    # import ipdb; ipdb.set_trace()
    context = {
        'translations': translations, #filter(lambda t: t['pk'] != pk, translations['suggest-translation'][0]['options'])
    }

    return HttpResponse(json.dumps(context))
