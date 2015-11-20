"""Definitions of mappings for indexes required by translation memory."""

from django.conf import settings

IndexSettings = {
    "index":{
        "analysis": {
            "analyzer": {
                "analyzer_keyword": {
                    "tokenizer": "keyword",
                    "filter": "lowercase"
                }
            }
        }
    }
}
TranslationMapping = {
    "properties": {
        "entity_pk": {"type": "integer"},
        "source": {"type": "string"},
        "target": {"type": "string"},
        "locale": {"type": "string"},
        "plural_form": {"type": "integer"},
    }
}


def get_index_name(locale_code):
    """
    Returns name of the index
    :param locale_code: code of locale
    :return: name of type in elastic search
    """
    return settings.TM_ELASTICSEARCH_INDEX.format(locale_code=locale_code.lower())
