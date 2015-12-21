# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_translation_memory_entries(apps, schema):
    Translation = apps.get_model('base', 'Translation')
    TranslationMemoryEntry = apps.get_model('base', 'TranslationMemoryEntry')
    def get_memory_entry(translation):
        return TranslationMemoryEntry(
            source=translation.entity.string,
            target=translation.string,
            locale=translation.locale,
        )
    translations = Translation.objects.filter(approved=True, fuzzy=False)\
                                      .filter(models.Q(plural_form__isnull=True) | models.Q(plural_form=0))\
                                      .prefetch_related('entity')
    TranslationMemoryEntry.objects.bulk_create(map(get_memory_entry, translations), 1000)


def remove_translation_memory_entries(apps, schema):
    TranslationMemoryEntry = apps.get_model('base', 'TranslationMemoryEntry')
    TranslationMemoryEntry.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('base', '0048_translationmemoryentry'),
    ]

    operations = [
        migrations.RunPython(create_translation_memory_entries, remove_translation_memory_entries)
    ]
