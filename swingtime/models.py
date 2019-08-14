from __future__ import print_function, unicode_literals

from datetime import date, datetime, timedelta

from dateutil import rrule
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now as datetime_now
from django.utils.translation import ugettext_lazy as _

from places.models import Room
from webcal.utils import make_vevent_list

from .utils import force_aware, force_naive

__all__ = (
    'Note',
    #     'EventType',
    'Event',
    'Occurrence',
    'create_event',
    'BookingLocation',
)

#===============================================================================


@python_2_unicode_compatible
class Note(models.Model):
    '''
    A generic model for adding simple, arbitrary notes to other models such as
    ``Event`` or ``Occurrence``.

    '''
    note = models.TextField(_('note'))
    created = models.DateTimeField(_('created'), auto_now_add=True)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(_('object id'))
    content_object = GenericForeignKey('content_type', 'object_id')

    #===========================================================================
    class Meta:
        verbose_name = _('note')
        verbose_name_plural = _('notes')

    #---------------------------------------------------------------------------
    def __str__(self):
        return self.note


#===============================================================================


class BookingLocation_Manager(models.Manager):
    def get_by_slug(self, slug):
        return self.get(
            active=True, location__active=True, location__slug=slug)


@python_2_unicode_compatible
class BookingLocation(models.Model):
    """
    Pointer to a particular Room that is used for booking.
    """
    active = models.BooleanField(default=True)
    created = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name='creation time')
    modified = models.DateTimeField(
        auto_now=True, editable=False, verbose_name='last modification time')

    location = models.OneToOneField(Room, on_delete=models.PROTECT)

    objects = BookingLocation_Manager()

    class Meta:
        permissions = (
            ('book_can_add', 'Can add new events'),
            ('book_can_edit', 'Can edit events'),
            ('book_can_delete', 'Can delete events'),
            ('book_can_view', 'Can view events'),
        )

    def __str__(self):
        return "{}".format(self.location)

    def get_absolute_url(self):
        return reverse(
            'swingtime-current-month', kwargs={'calendar_slug': self.slug})

    @property
    def slug(self):
        return self.location.slug

    def calendar_events(self, include_set_events=True):
        """
        Return the vevent list for this location
        NOTE: We cannot name this 'vevent_list' or things will recurse
        """
        results = []
        results.extend(make_vevent_list(self.location, include_set_events))
        if hasattr(self.location, 'classroom'):
            results.extend(
                make_vevent_list(self.location.classroom, include_set_events))
        if hasattr(self.location, 'office'):
            results.extend(
                make_vevent_list(self.location.office, include_set_events))
        return results

    @property
    def scheduled_events(self):
        return self.calendar_events()


@python_2_unicode_compatible
class Event(models.Model):
    '''
    Container model for general metadata and associated ``Occurrence`` entries.
    '''
    title = models.CharField(_('title'), max_length=32)
    location = models.ForeignKey(
        BookingLocation,
        on_delete=models.CASCADE,
        limit_choices_to={'active': True})

    description = models.CharField(
        _('description'), max_length=100, blank=True)
    notes = GenericRelation(Note, verbose_name=_('notes'))

    #===========================================================================
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ('title', )

    #---------------------------------------------------------------------------
    def __str__(self):
        return self.title

    #---------------------------------------------------------------------------
    def get_absolute_url(self):
        return reverse(
            'swingtime-event', args=[self.location.slug,
                                     str(self.id)])

    #---------------------------------------------------------------------------
    def add_occurrences(self, start_time, end_time, **rrule_params):
        '''
        Add one or more occurences to the event using a comparable API to
        ``dateutil.rrule``.

        If ``rrule_params`` does not contain a ``freq``, one will be defaulted
        to ``rrule.DAILY``.

        Because ``rrule.rrule`` returns an iterator that can essentially be
        unbounded, we need to slightly alter the expected behavior here in order
        to enforce a finite number of occurrence creation.

        If both ``count`` and ``until`` entries are missing from ``rrule_params``,
        only a single ``Occurrence`` instance will be created using the exact
        ``start_time`` and ``end_time`` values.
        '''
        rrule_params.setdefault('freq', rrule.DAILY)

        if 'count' not in rrule_params and 'until' not in rrule_params:
            self.occurrence_set.create(
                start_time=start_time, end_time=end_time)
        else:
            # weird things can happen with timezones here if we hit
            #   a daylight savings time transition...
            #   So make everything naive and then convert back to aware.
            start_time = force_naive(start_time)
            end_time = force_naive(end_time)
            if 'until' in rrule_params:
                rrule_params['until'] = force_naive(rrule_params['until'])
            delta = end_time - start_time

            for ev in rrule.rrule(dtstart=start_time, **rrule_params):
                ev_start = force_aware(ev)
                ev_end = force_aware(ev + delta)
                self.occurrence_set.create(
                    start_time=ev_start, end_time=ev_end)

    #---------------------------------------------------------------------------
    def upcoming_occurrences(self):
        '''
        Return all occurrences that are set to start on or after the current
        time.
        '''
        return self.occurrence_set.filter(start_time__gte=datetime_now())

    #---------------------------------------------------------------------------
    def next_occurrence(self):
        '''
        Return the single occurrence set to start on or after the current time
        if available, otherwise ``None``.
        '''
        upcoming = self.upcoming_occurrences()
        return upcoming and upcoming[0] or None

    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None):
        '''
        Convenience method wrapping ``Occurrence.objects.daily_occurrences``.
        '''
        return Occurrence.objects.daily_occurrences(dt=dt, event=self)


#===============================================================================
class OccurrenceManager(models.Manager):

    #---------------------------------------------------------------------------
    def daily_occurrences(self, location, dt=None, event=None):
        '''
        Returns a queryset of for instances that have any overlap with a
        particular day.

        * ``dt`` may be either a datetime.datetime, datetime.date object, or
          ``None``. If ``None``, default to the current day.

        * ``event`` can be an ``Event`` instance for further filtering.
        '''
        dt = dt or datetime_now()
        start = datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
        end = start.replace(hour=23, minute=59, second=59)
        qs = self.filter(
            models.Q(
                start_time__gte=start,
                start_time__lte=end,
            ) | models.Q(
                end_time__gte=start,
                end_time__lte=end,
            ) | models.Q(start_time__lt=start, end_time__gt=end),
            event__location=location,
        )

        return qs.filter(event=event) if event else qs


#===============================================================================


@python_2_unicode_compatible
class Occurrence(models.Model):
    '''
    Represents the start end time for a specific occurrence of a master ``Event``
    object.
    '''
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'))
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name=_('event'),
        editable=False)
    notes = GenericRelation(Note, verbose_name=_('notes'))

    objects = OccurrenceManager()

    #===========================================================================
    class Meta:
        verbose_name = _('occurrence')
        verbose_name_plural = _('occurrences')
        ordering = ('start_time', 'end_time')
        base_manager_name = 'objects'

    #---------------------------------------------------------------------------
    def __str__(self):
        return '%s: %s' % (self.title, self.start_time.isoformat())

    #---------------------------------------------------------------------------
    def get_absolute_url(self):
        return reverse(
            'swingtime-occurrence',
            args=[self.location.slug,
                  str(self.event.id),
                  str(self.id)])

    #---------------------------------------------------------------------------
    def __cmp__(self, other):
        return cmp(self.start_time, other.start_time)

    #---------------------------------------------------------------------------
    @property
    def title(self):
        return self.event.title

    #---------------------------------------------------------------------------
#     @property
#     def event_type(self):
#         return self.event.event_type

#---------------------------------------------------------------------------

    @property
    def location(self):
        return self.event.location


#-------------------------------------------------------------------------------
def create_event(
        title,
        location,
        #    event_type,
        description='',
        start_time=None,
        end_time=None,
        note=None,
        **rrule_params):
    '''
    Convenience function to create an ``Event``, optionally create an
    ``EventType``, and associated ``Occurrence``s. ``Occurrence`` creation
    rules match those for ``Event.add_occurrences``.

    Returns the newly created ``Event`` instance.

    Parameters

    ``event_type``
        can be either an ``EventType`` object or 2-tuple of ``(abbreviation,label)``,
        from which an ``EventType`` is either created or retrieved.

    ``start_time``
        will default to the current hour if ``None``

    ``end_time``
        will default to ``start_time`` plus swingtime_settings.DEFAULT_OCCURRENCE_DURATION
        hour if ``None``

    ``freq``, ``count``, ``rrule_params``
        follow the ``dateutils`` API (see http://labix.org/python-dateutil)

    '''
    from swingtime.conf import settings as swingtime_settings

    #     if isinstance(event_type, tuple):
    #         event_type, created = EventType.objects.get_or_create(
    #             abbr=event_type[0],
    #             label=event_type[1]
    #         )

    event = Event.objects.create(
        title=title, description=description, location=location)

    if note is not None:
        event.notes.create(note=note)

    start_time = start_time or datetime_now().replace(
        minute=0, second=0, microsecond=0)

    end_time = end_time or start_time + swingtime_settings.DEFAULT_OCCURRENCE_DURATION
    event.add_occurrences(start_time, end_time, **rrule_params)
    return event
