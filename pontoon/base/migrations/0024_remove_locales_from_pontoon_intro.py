# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def remove_locales_from_pontoon_intro(apps, schema_editor):
	Project = apps.get_model("base", "Project")
	Locale = apps.get_model("base", "Locale")

	pontoon_intro = Project.objects.get(slug='pontoon-intro')
	pontoon_intro.locales.clear()
	pontoon_intro.locales.add(Locale.objects.get(code='en-US'))


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0023_auto_20150916_0642'),
    ]

    operations = [
    	migrations.RunPython(remove_locales_from_pontoon_intro)
    ]
