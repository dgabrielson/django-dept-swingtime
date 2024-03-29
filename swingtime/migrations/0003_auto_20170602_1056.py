# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-02 15:56
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swingtime', '0002_auto_20150611_1518'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='occurrence',
            options={
                'base_manager_name': 'objects',
                'ordering': ('start_time', 'end_time'),
                'verbose_name': 'occurrence',
                'verbose_name_plural': 'occurrences'
            },
        ),
        migrations.AlterField(
            model_name='bookinglocation',
            name='location',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT, to='places.Room'),
        ),
    ]
