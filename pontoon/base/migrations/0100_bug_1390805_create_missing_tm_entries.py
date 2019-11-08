# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-16 11:37
from __future__ import unicode_literals

from django.db import migrations


def create_missing_translation_memory_entries(apps, schema_editor):
    Translation = apps.get_model("base", "Translation")
    TranslationMemoryEntry = apps.get_model("base", "TranslationMemoryEntry")

    translations_to_create_translation_memory_entries_for = Translation.objects.filter(
        approved=True, memory_entries__isnull=True
    ).prefetch_related("entity__resource__project")

    memory_entries = [
        TranslationMemoryEntry(
            source=t.entity.string,
            target=t.string,
            locale_id=t.locale_id,
            entity_id=t.entity.pk,
            translation_id=t.pk,
            project=t.entity.resource.project,
        )
        for t in translations_to_create_translation_memory_entries_for
    ]

    TranslationMemoryEntry.objects.bulk_create(memory_entries)


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0099_bug_1390113_unescape_quotes"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_translation_memory_entries, migrations.RunPython.noop
        ),
    ]
