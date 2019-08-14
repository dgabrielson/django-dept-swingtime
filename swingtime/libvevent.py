"""
All vevent objects are assumed to have the following attributes (at a minimum):
    * DTSTART
    * DTEND
    * DTSTAMP
    * SUMMARY
    * LOCATION

"""
#######################
from __future__ import print_function, unicode_literals

import datetime
import itertools

import vobject
from django.utils.timezone import is_naive, make_aware
from django.utils.timezone import now as datetime_now

#######################

###############################################################


def has_overlap(vevent, start, end):
    """
    Returns True if the given vevent has some overlap with the given start and end datetimes.
    """
    event_start = vevent.dtstart.value
    event_end = vevent.dtend.value

    assert not is_naive(start), 'start dt is naive'
    assert not is_naive(end), 'end dt is naive'
    assert not is_naive(event_start), 'event_start dt is naive'
    assert not is_naive(event_end), 'event_end dt is naive'

    if start <= event_start <= end:  # starts today
        return True
    if start <= event_end <= end:  # ends today
        return True
    if event_start <= start and end <= event_end:  # spans over today
        return True
    return False


###############################################################


def filter_list_by_day(vevent_seq, dt=None):
    """
    if dt is None, default to today.
    """
    dt = dt or datetime_now()
    if is_naive(dt):
        dt = make_aware(dt)
    start = datetime.datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
    end = start.replace(hour=23, minute=59, second=59)
    return (vevent for vevent in vevent_seq if has_overlap(vevent, start, end))


###############################################################


def filter_list_by_month(vevent_seq, dt=None):
    """
    if dt is None, default to this month.
    """
    dt = dt or datetime_now()
    if is_naive(dt):
        dt = make_aware(dt)
    assert not is_naive(dt), "dt {!r} is naive".format(dt)
    start = datetime.datetime(dt.year, dt.month, 1, tzinfo=dt.tzinfo)
    # the following loop tries day 31, 30, 29, 28 until it no longer raises ValueError.
    day = 31
    while True:
        try:
            end = start.replace(day=day, hour=23, minute=59, second=59)
            break
        except ValueError:
            day -= 1

    assert not is_naive(start), "start {!r} is naive".format(start)
    assert not is_naive(end), "end {!r} is naive".format(end)

    return (vevent for vevent in vevent_seq if has_overlap(vevent, start, end))


###############################################################


def from_occurrence(o):
    """
    Return a vevent from an occurrence object.
    """
    cal = vobject.iCalendar()
    ev = cal.add('vevent')
    ev.add('dtstamp').value = o.start_time
    ev.add('dtstart').value = o.start_time
    ev.add('dtend').value = o.end_time
    ev.add('summary').value = o.event.title
    ev.add('location').value = "{}".format(o.event.location)

    desc = ''
    if o.event.description:
        desc += o.event.description
    for n in o.event.notes.all():
        desc += '\n' + n
    for n in o.notes.all():
        desc += '\n' + n
    desc = desc.strip()
    if desc:
        ev.add('description').value = desc

    return ev


###############################################################


class EventWrapper:
    def __init__(self, vevent):
        self.title = vevent.summary.value
        self.location = vevent.summary.value


###############################################################


class OccurenceWrapper:
    """
    For display purposes, return a dictionary faking an occurence object.
    """

    def __init__(self, vevent):
        self.start_time = vevent.dtstart.value
        self.end_time = vevent.dtend.value
        print(self.start_time, '--', self.end_time)

        self.event = EventWrapper(vevent)
        self.title = self.event.title
        self.location = self.event.location
        self.notes = []
        self.get_absolute_url = None


###############################################################
