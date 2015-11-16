# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0045_remove_can_localize'),
    ]

    operations = [
        migrations.AddField(
            model_name='translation',
            name='suggested',
            field=models.BooleanField(default=False),
        ),
    ]
