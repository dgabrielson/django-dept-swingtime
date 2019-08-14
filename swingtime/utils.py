'''
Common features and functions for swingtime

'''
#######################
from __future__ import print_function, unicode_literals

import itertools
#######################
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from dateutil import rrule
from django.conf import global_settings, settings
from django.db.models.query import QuerySet
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe
from django.utils.timezone import (get_current_timezone, is_aware, make_aware,
                                   make_naive)
from django.utils.timezone import now as datetime_now

from . import libvevent
from .conf import settings as swingtime_settings

#-------------------------------------------------------------------------------

# Safely get the current USE_TZ setting, falling back to defaults in needed.
USE_TZ = getattr(settings, 'USE_TZ', getattr(global_settings, 'USE_TZ'))

#-------------------------------------------------------------------------------


def force_aware(dt, timezone=None):
    """
    Convert the given datetime object to the current timezone, if
    it has no timezone.

    Also, converts pure date objects to datetime.
    """
    if not USE_TZ:
        return dt
    if timezone is None:
        timezone = get_current_timezone()
    if isinstance(dt, datetime):
        if is_aware(dt):
            return dt
        return make_aware(dt, timezone)
    if isinstance(dt, date):
        return datetime.combine(dt, time(0, tzinfo=timezone))
    return dt


#-------------------------------------------------------------------------------


def force_naive(dt, timezone=None):
    """
    Convert the given datetime object to the current timezone, if
    it has no timezone.

    Also, converts pure date objects to datetime.
    """
    if timezone is None:
        timezone = get_current_timezone()
    return make_naive(dt, timezone)


#-------------------------------------------------------------------------------


def time_from_offset(offset):
    hour = offset // 60**2
    minute = (offset - hour * 60**2) // 60
    second = (hour * 60 + minute) * 60 - offset
    return time(hour=hour, minute=minute, second=second)


#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
def html_mark_safe(func):
    '''
    Decorator for functions return strings that should be treated as template
    safe.

    '''

    def decorator(*args, **kws):
        return mark_safe(func(*args, **kws))

    return decorator


#-------------------------------------------------------------------------------
def time_delta_total_seconds(time_delta):
    '''
    Calculate the total number of seconds represented by a
    ``datetime.timedelta`` object

    '''
    return time_delta.days * 24 * 60**2 + time_delta.seconds


#-------------------------------------------------------------------------------
def month_boundaries(dt=None):
    '''
    Return a 2-tuple containing the datetime instances for the first and last
    dates of the current month or using ``dt`` as a reference.

    '''
    import calendar
    dt = force_aware(dt or date.today())
    wkday, ndays = calendar.monthrange(dt.year, dt.month)
    start = force_aware(datetime(dt.year, dt.month, 1, tzinfo=tzinfo))
    return (start, start + timedelta(ndays - 1))


#-------------------------------------------------------------------------------
def css_class_cycler():
    '''
    Return a dictionary keyed by ``EventType`` abbreviations, whose values are an
    iterable or cycle of CSS class names.

    '''
    from .models import BookingLocation
    return defaultdict(
        lambda: itertools.cycle(('evt-even', 'evt-odd')).next,
        ((o.slug,
          itertools.cycle(
              ('evt-%s-even' % o.slug, 'evt-%s-odd' % o.slug)).next)
         for o in BookingLocation.objects.filter(active=True)))


#===============================================================================


@python_2_unicode_compatible
class BaseOccurrenceProxy(object):
    '''
    A simple wrapper class for handling the presentational aspects of an
    ``Occurrence`` instance.

    '''

    #---------------------------------------------------------------------------
    def __init__(self, occurrence, col, show_event_links):
        self.column = col
        self._occurrence = occurrence
        self.event_class = ''
        self.show_event_links = show_event_links

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        return getattr(self._occurrence, name)

    #---------------------------------------------------------------------------
    def __str__(self):
        return self.title


#===============================================================================


@python_2_unicode_compatible
class DefaultOccurrenceProxy(BaseOccurrenceProxy):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(DefaultOccurrenceProxy, self).__init__(*args, **kws)
        if self.get_absolute_url is not None and self.show_event_links:
            link = '<a href="%s">%s</a>' % (self.get_absolute_url(),
                                            self.title)
        else:
            link = self.title

        self._str = itertools.chain((link, ), itertools.repeat(r'\\\///'))

    #---------------------------------------------------------------------------
    @html_mark_safe
    def __str__(self):
        return next(self._str)


#-------------------------------------------------------------------------------
def create_timeslot_table(
        location,
        show_event_links=True,
        dt=None,
        items=None,
        start_time=swingtime_settings.TIMESLOT_START_TIME,
        end_time_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
        time_delta=swingtime_settings.TIMESLOT_INTERVAL,
        min_columns=swingtime_settings.TIMESLOT_MIN_COLUMNS,
        css_class_cycles=css_class_cycler,
        proxy_class=DefaultOccurrenceProxy):
    '''
    Create a grid-like object representing a sequence of times (rows) and
    columns where cells are either empty or reference a wrapper object for
    event occasions that overlap a specific time slot.

    Currently, there is an assumption that if an occurrence has a ``start_time``
    that falls with the temporal scope of the grid, then that ``start_time`` will
    also match an interval in the sequence of the computed row entries.

    * ``dt`` - a ``datetime.datetime`` instance or ``None`` to default to now
    * ``items`` - a queryset or sequence of ``Occurrence`` instances. If
      ``None``, default to the daily occurrences for ``dt``
    * ``start_time`` - a ``datetime.time`` instance
    * ``end_time_delta`` - a ``datetime.timedelta`` instance
    * ``time_delta`` - a ``datetime.timedelta`` instance
    * ``min_column`` - the minimum number of columns to show in the table
    * ``css_class_cycles`` - if not ``None``, a callable returning a dictionary
      keyed by desired ``EventType`` abbreviations with values that iterate over
      progressive CSS class names for the particular abbreviation.
    * ``proxy_class`` - a wrapper class for accessing an ``Occurrence`` object.
      This class should also expose ``event_type`` and ``event_type`` attrs, and
      handle the custom output via its __str__ method.

    '''
    from swingtime.models import Occurrence
    dt = dt or datetime_now()
    dtstart = make_aware(datetime.combine(dt.date(), start_time), dt.tzinfo)
    assert is_aware(dtstart)

    dtend = dtstart + end_time_delta
    assert is_aware(dtend)

    if isinstance(items, QuerySet):
        items = items._clone()
    elif not items:
        items = Occurrence.objects.daily_occurrences(
            location, dt).select_related('event')

        vevents = libvevent.filter_list_by_day(location.scheduled_events, dt)
        occ_vev = [libvevent.OccurenceWrapper(ev) for ev in vevents]
        all_items = sorted(list(items) + occ_vev, key=lambda o: o.start_time)

    print(len(all_items))

    # build a mapping of timeslot "buckets"
    timeslots = dict()
    n = dtstart
    while n <= dtend:
        timeslots[n] = {}
        n += time_delta

    # fill the timeslot buckets with occurrence proxies
    for item in all_items:  #sorted(items):
        if item.end_time <= dtstart:
            # this item began before the start of our schedule constraints
            # print(item, '!! ends before dtstart')
            continue

        if item.start_time > dtstart:
            rowkey = current = item.start_time
        else:
            rowkey = current = dtstart

        timeslot = timeslots.get(rowkey, None)
        if timeslot is None:
            # print(item.title, '!! timeslot is None')
            # TODO fix atypical interval boundry spans
            # This is rather draconian, we should probably try to find a better
            # way to indicate that this item actually occurred between 2 intervals
            # and to account for the fact that this item may be spanning cells
            # but on weird intervals
            continue

        colkey = 0
        while 1:
            # keep searching for an open column to place this occurrence
            if colkey not in timeslot:
                proxy = proxy_class(item, colkey, show_event_links)
                timeslot[colkey] = proxy

                while current < item.end_time:
                    rowkey = current
                    row = timeslots.get(rowkey, None)
                    if row is None:
                        break

                    # we might want to put a sanity check in here to ensure that
                    # we aren't trampling some other entry, but by virtue of
                    # sorting all occurrence that shouldn't happen
                    row[colkey] = proxy
                    current += time_delta
                break

            colkey += 1

    # determine the number of timeslot columns we should show
    column_lens = [len(x) for x in timeslots.values()]
    column_count = max((min_columns, max(column_lens) if column_lens else 0))
    column_range = range(column_count)
    empty_columns = ['' for x in column_range]

    if css_class_cycles:
        column_classes = dict([(i, css_class_cycles()) for i in column_range])
    else:
        column_classes = None

    # create the chronological grid layout
    table = []
    for rowkey in sorted(timeslots.keys()):
        cols = empty_columns[:]
        for colkey in timeslots[rowkey]:
            proxy = timeslots[rowkey][colkey]
            cols[colkey] = proxy
            if not proxy.event_class and column_classes:
                #proxy.event_class = column_classes[colkey][proxy.event_type.abbr]()

                proxy.event_class = column_classes[colkey]["{}".format(
                    proxy.location)]()

        table.append((rowkey, cols))

    return table
