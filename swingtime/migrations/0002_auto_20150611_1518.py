# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swingtime', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookinglocation',
            name='location',
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE, to='places.Room'),
        ),
    ]
