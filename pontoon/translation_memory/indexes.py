"""Definitions of mappings for indexes required by translation memory."""

from django.conf import settings

TranslationMapping = {
    "properties": {
        "entity_pk": {"type": "integer"},
        "source": {
            "type": "completion",
            "context": {
                "locale": {
                    "type": "category",
                    "path": "locale"
                }
            }
        },
        "target": {"type": "string"},
        "locale": {"type": "string"},
        "plural_form": {"type": "integer"},
    }
}

def create_translation_index(es_connection):
    """
    Creates indices required by translation memory.
    :param es_connection: connection to elasticsearch instance.
    """
    es_connection.indices.create(index=settings.TM_ELASTICSEARCH_INDEX, doc_type=settings.TM_ELASTICSEARCH_TYPE,
        ignore=400)
    es_connection.indices.put_mapping(index=settings.TM_ELASTICSEARCH_INDEX, doc_type=settings.TM_ELASTICSEARCH_TYPE,
        body=TranslationMapping)
