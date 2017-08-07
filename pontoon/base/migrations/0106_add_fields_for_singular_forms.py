# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-28 00:24
from __future__ import unicode_literals

from bulk_update.helper import bulk_update
from django.db import migrations, models

from pontoon.base.utils import get_singulars


def update_singulars_fields(apps, schema):
    """
    Update all entities with their singular forms.
    """
    Entity = apps.get_model('base', 'entity')
    entities_to_update = []

    for entity in Entity.objects.all():
        entity.string_singulars = ' '.join(get_singulars(entity.string))
        entity.string_plural_singulars = ' '.join(get_singulars(entity.string_plural))

        entities_to_update.append(entity)

    bulk_update(
        entities_to_update,
        update_fields=[
            'string_singulars',
            'string_plural_singulars'
        ],
        batch_size=1000
    )


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0105_unescape_quotes_from_android_strings_dtd_in_translation_memory')
    ]

    operations = [
        migrations.AddField(
            model_name='entity',
            name='string_plural_singulars',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='entity',
            name='string_singulars',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(
            update_singulars_fields,
            migrations.RunPython.noop
        )
    ]