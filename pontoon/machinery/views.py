import logging
import requests
import urllib
import xml.etree.ElementTree as ET

from collections import defaultdict
from django.conf import settings
from django.db import DataError
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.datastructures import MultiValueDictKeyError
from suds.client import Client, WebFault

from pontoon.base import utils
from pontoon.base.models import Locale, TranslationMemoryEntry


log = logging.getLogger('pontoon')


def machinery(request):
    locale = utils.get_project_locale_from_request(
        request, Locale.objects) or 'en-GB'

    return render(request, 'machinery/machinery.html', {
        'locale': Locale.objects.get(code__iexact=locale),
        'locales': Locale.objects.all(),
    })


def translation_memory(request):
    """Get translations from internal translations memory."""
    try:
        text = request.GET['text']
        locale = request.GET['locale']
        pk = request.GET['pk']
    except MultiValueDictKeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    max_results = 5
    locale = get_object_or_404(Locale, code__iexact=locale)
    entries = TranslationMemoryEntry.objects.minimum_levenshtein_ratio(text).filter(locale=locale)

    # Exclude existing entity
    if pk:
        entries = entries.exclude(entity__pk=pk)

    entries = entries.values('source', 'target', 'quality').order_by('-quality')
    suggestions = defaultdict(lambda: {'count': 0, 'quality': 0})

    try:
        for entry in entries:
            if entry['target'] not in suggestions or entry['quality'] > suggestions[entry['target']]['quality']:
                suggestions[entry['target']].update(entry)
            suggestions[entry['target']]['count'] += 1
    except DataError as e:
        # Catches 'argument exceeds the maximum length of 255 bytes' Error
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    return JsonResponse(sorted(suggestions.values(), key=lambda e: e['count'], reverse=True)[:max_results], safe=False)


def machine_translation(request):
    """Get translation from machine translation service."""
    try:
        text = request.GET['text']
        locale_code = request.GET['locale']
    except MultiValueDictKeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    if hasattr(settings, 'MICROSOFT_TRANSLATOR_API_KEY'):
        api_key = settings.MICROSOFT_TRANSLATOR_API_KEY
    else:
        log.error("MICROSOFT_TRANSLATOR_API_KEY not set")
        return HttpResponse("apikey")

    locale = get_object_or_404(Locale, code=locale_code)
    obj = {}

    # On first run, check if target language supported
    if not locale.ms_translator_code:
        return HttpResponse("not-supported")
    else:
        obj['locale'] = locale.ms_translator_code

    url = "http://api.microsofttranslator.com/V2/Http.svc/Translate"
    payload = {
        "appId": api_key,
        "text": text,
        "from": "en",
        "to": locale.ms_translator_code,
        "contentType": "text/html",
    }
    try:
        r = requests.get(url, params=payload)
        # Parse XML response
        root = ET.fromstring(r.content)
        translation = root.text
        obj['translation'] = translation

        return JsonResponse(obj)

    except Exception as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))


def microsoft_terminology(request):
    """Get translations from Microsoft Terminology Service."""
    try:
        text = request.GET['text']
        locale_code = request.GET['locale']
    except MultiValueDictKeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    obj = {}
    locale = get_object_or_404(Locale, code=locale_code)
    url = 'http://api.terminology.microsoft.com/Terminology.svc?singleWsdl'
    client = Client(url)

    # On first run, check if target language supported
    if not locale.ms_terminology_code:
        return HttpResponse("not-supported")
    else:
        obj['locale'] = locale.code

    sources = client.factory.create('ns0:TranslationSources')
    sources["TranslationSource"] = ['Terms', 'UiStrings']

    payload = {
        'text': text,
        'from': 'en-US',
        'to': locale.ms_terminology_code,
        'sources': sources,
        'maxTranslations': 5
    }
    try:
        r = client.service.GetTranslations(**payload)
        translations = []

        if len(r) != 0:
            for translation in r.Match:
                translations.append({
                    'source': translation.OriginalText,
                    'target': translation.Translations[0][0].TranslatedText,
                    'quality': translation.ConfidenceLevel,
                })

            obj['translations'] = translations

        return JsonResponse(obj)

    except WebFault as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))


def amagama(request):
    """Get open source translations from amaGama service."""
    try:
        text = request.GET['text']
        locale = request.GET['locale']
    except MultiValueDictKeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    try:
        text = urllib.quote(text.encode('utf-8'))
    except KeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    # No trailing slash at the end or slash becomes part of the source text
    url = (
        u'https://amagama-live.translatehouse.org/api/v1/en/{locale}/unit/'
        .format(locale=locale)
    )

    payload = {
        'source': text,
        'max_candidates': 5,
        'min_similarity': 70,
    }

    try:
        r = requests.get(url, params=payload)
        return JsonResponse(r.json(), safe=False)

    except Exception as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))


def transvision(request):
    """Get Mozilla translations from Transvision service."""
    try:
        text = request.GET['text']
        locale = request.GET['locale']
    except MultiValueDictKeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    try:
        text = urllib.quote(text.encode('utf-8'))
    except KeyError as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))

    url = (
        u'https://transvision.mozfr.org/api/v1/tm/global/en-US/{locale}/{text}/'
        .format(locale=locale, text=text)
    )

    payload = {
        'max_results': 5,
        'min_quality': 70,
    }

    try:
        r = requests.get(url, params=payload)
        if 'error' in r.json():
            error = r.json()['error']
            log.error('Transvision error: {error}'.format(error))
            return HttpResponseBadRequest('Bad Request: {error}'.format(error=error))

        return JsonResponse(r.json(), safe=False)

    except Exception as e:
        return HttpResponseBadRequest('Bad Request: {error}'.format(error=e))
