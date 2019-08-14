# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingLocation',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('active', models.BooleanField(default=True)),
                ('created',
                 models.DateTimeField(
                     auto_now_add=True, verbose_name=b'creation time')),
                ('modified',
                 models.DateTimeField(
                     auto_now=True, verbose_name=b'last modification time')),
                ('location',
                 models.ForeignKey(
                     on_delete=models.deletion.CASCADE,
                     to='places.Room',
                     unique=True)),
            ],
            options={
                'permissions':
                (('book_can_add', 'Can add new events'), ('book_can_edit',
                                                          'Can edit events'),
                 ('book_can_delete',
                  'Can delete events'), ('book_can_view', 'Can view events')),
            },
            bases=(models.Model, ),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('title', models.CharField(
                    max_length=32, verbose_name='title')),
                ('description',
                 models.CharField(
                     max_length=100, verbose_name='description', blank=True)),
                ('location',
                 models.ForeignKey(
                     on_delete=models.deletion.CASCADE,
                     to='swingtime.BookingLocation')),
            ],
            options={
                'ordering': ('title', ),
                'verbose_name': 'event',
                'verbose_name_plural': 'events',
            },
            bases=(models.Model, ),
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('note', models.TextField(verbose_name='note')),
                ('created',
                 models.DateTimeField(
                     auto_now_add=True, verbose_name='created')),
                ('object_id',
                 models.PositiveIntegerField(verbose_name='object id')),
                ('content_type',
                 models.ForeignKey(
                     on_delete=models.deletion.CASCADE,
                     verbose_name='content type',
                     to='contenttypes.ContentType')),
            ],
            options={
                'verbose_name': 'note',
                'verbose_name_plural': 'notes',
            },
            bases=(models.Model, ),
        ),
        migrations.CreateModel(
            name='Occurrence',
            fields=[
                ('id',
                 models.AutoField(
                     verbose_name='ID',
                     serialize=False,
                     auto_created=True,
                     primary_key=True)),
                ('start_time',
                 models.DateTimeField(verbose_name='start time')),
                ('end_time', models.DateTimeField(verbose_name='end time')),
                ('event',
                 models.ForeignKey(
                     on_delete=models.deletion.CASCADE,
                     editable=False,
                     to='swingtime.Event',
                     verbose_name='event')),
            ],
            options={
                'ordering': ('start_time', 'end_time'),
                'verbose_name': 'occurrence',
                'verbose_name_plural': 'occurrences',
            },
            bases=(models.Model, ),
        ),
    ]
