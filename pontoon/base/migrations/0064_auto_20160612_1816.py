# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-06-12 18:16
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0063_remove_has_changed'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreferredLocale',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField()),
                ('locale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Locale')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.UserProfile')),
            ],
            options={
                'ordering': ('-position',),
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='preferred_locales',
            field=models.ManyToManyField(through='base.PreferredLocale', to='base.Locale'),
        ),
        migrations.AlterUniqueTogether(
            name='preferredlocale',
            unique_together=set([('locale', 'user_profile', 'position')]),
        ),
    ]
