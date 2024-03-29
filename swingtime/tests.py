#!/usr/bin/env python
#######################
from __future__ import print_function, unicode_literals

from datetime import date, datetime, time, timedelta
from io import StringIO
#######################
from pprint import pformat, pprint

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils.timezone import is_aware

from swingtime import utils
from swingtime.models import *

expected_table_1 = '''\
| 15:00 |          |          |          |          |          |
| 15:15 | zelda    |          |          |          |          |
| 15:30 | zelda    | alpha    |          |          |          |
| 15:45 |          | alpha    |          |          |          |
| 16:00 | bravo    | alpha    | foxtrot  |          |          |
| 16:15 | bravo    | alpha    | foxtrot  | charlie  |          |
| 16:30 | bravo    | alpha    | foxtrot  | charlie  | delta    |
| 16:45 |          | alpha    |          | charlie  | delta    |
| 17:00 |          | alpha    |          |          | delta    |
| 17:15 | echo     | alpha    |          |          |          |
| 17:30 | echo     | alpha    |          |          |          |
| 17:45 | echo     |          |          |          |          |
| 18:00 |          |          |          |          |          |
'''

expected_table_2 = '''\
| 15:30 | zelda    | alpha    |          |          |          |
| 15:45 |          | alpha    |          |          |          |
| 16:00 | bravo    | alpha    | foxtrot  |          |          |
| 16:15 | bravo    | alpha    | foxtrot  | charlie  |          |
| 16:30 | bravo    | alpha    | foxtrot  | charlie  | delta    |
| 16:45 |          | alpha    |          | charlie  | delta    |
| 17:00 |          | alpha    |          |          | delta    |
| 17:15 | echo     | alpha    |          |          |          |
| 17:30 | echo     | alpha    |          |          |          |
'''

expected_table_3 = '''\
| 16:00 | alpha    | bravo    | foxtrot  |          |          |
| 16:15 | alpha    | bravo    | foxtrot  | charlie  |          |
| 16:30 | alpha    | bravo    | foxtrot  | charlie  | delta    |
| 16:45 | alpha    |          |          | charlie  | delta    |
| 17:00 | alpha    |          |          |          | delta    |
| 17:15 | alpha    | echo     |          |          |          |
| 17:30 | alpha    | echo     |          |          |          |
'''

expected_table_4 = '''\
| 18:00 |          |          |          |          |
| 18:15 |          |          |          |          |
| 18:30 |          |          |          |          |
| 18:45 |          |          |          |          |
| 19:00 |          |          |          |          |
| 19:15 |          |          |          |          |
| 19:30 |          |          |          |          |
'''

expected_table_5 = '''\
| 16:30 | alpha    | bravo    | foxtrot  | charlie  | delta    |
'''


#===============================================================================
class TableTest(TestCase):

    fixtures = ['swingtime_test']

    #---------------------------------------------------------------------------
    def setUp(self):
        self._dt = utils.force_aware(datetime(2008, 12, 11))

    #---------------------------------------------------------------------------
    def table_as_string(self, table):
        timefmt = '| %-5s'
        cellfmt = '| %-8s'
        out = StringIO()
        for tm, cells in table:
            print(timefmt % tm.strftime('%H:%M'), end='', file=out)
            for cell in cells:
                if cell:
                    print(cellfmt % cell.event.title, end='', file=out)
                else:
                    print(cellfmt % '', end='', file=out)
            print('|', file=out)

        return out.getvalue()

    #---------------------------------------------------------------------------
    def _do_test(self, start, end, expect):
        import pdb
        start = time(*start)
        dtstart = utils.force_aware(datetime.combine(self._dt, start))
        etd = utils.force_aware(datetime.combine(self._dt,
                                                 time(*end))) - dtstart

        self.assertTrue(is_aware(self._dt))
        self.assertTrue(is_aware(dtstart))

        # pdb.set_trace()
        location = BookingLocation.objects.get(pk=1)
        table = utils.create_timeslot_table(
            location, dt=self._dt, start_time=start, end_time_delta=etd)

        actual = self.table_as_string(table)
        out = 'Expecting:\n%s\nActual:\n%s' % (expect, actual)
        print(out)
        self.assertEqual(actual, expect, out)

    #---------------------------------------------------------------------------
    def test_slot_table_1(self):
        self._do_test((15, 0), (18, 0), expected_table_1)

    #---------------------------------------------------------------------------
    def test_slot_table_2(self):
        self._do_test((15, 30), (17, 30), expected_table_2)

    #---------------------------------------------------------------------------
    def test_slot_table_3(self):
        self._do_test((16, 0), (17, 30), expected_table_3)

    #---------------------------------------------------------------------------
    def test_slot_table_4(self):
        self._do_test((18, 0), (19, 30), expected_table_4)

    #---------------------------------------------------------------------------
    def test_slot_table_5(self):
        self._do_test((16, 30), (16, 30), expected_table_5)


#===============================================================================
class NewEventFormTest(TestCase):

    fixtures = ['swingtime_test']

    #---------------------------------------------------------------------------
    def test_new_event_simple(self):
        from swingtime.forms import EventForm, MultipleOccurrenceForm

        data = dict(
            title='QWERTY',
            location='1',
            day='2008-12-11',
            start_time_delta='28800',
            end_time_delta='29700',
            year_month_ordinal_day='2',
            month_ordinal_day='2',
            holidays='skip',
            year_month_ordinal='1',
            month_option='each',
            repeats='count',
            freq='2',
            occurences='2',
            month_ordinal='1')

        evt_form = EventForm(data)
        occ_form = MultipleOccurrenceForm(data)
        self.assertTrue(evt_form.is_valid(), evt_form.errors.as_text())
        self.assertTrue(occ_form.is_valid(), occ_form.errors.as_text())

        target_dt = utils.force_aware(datetime(2008, 12, 11, 8))
        self.assertEqual(
            occ_form.cleaned_data['start_time'], target_dt,
            'Bad start_time: %s\n vs %r' % (pformat(occ_form.cleaned_data),
                                            target_dt))


#-------------------------------------------------------------------------------
def doc_tests():
    '''
        >>> from dateutil import rrule
        >>> from datetime import datetime
        >>> from swingtime.models import *
        >>> evt_types = [EventType.objects.create(abbr=l.lower(),label=l) for l in ['Foo', 'Bar', 'Baz']]
        >>> evt_types
        [<EventType: Foo>, <EventType: Bar>, <EventType: Baz>]
        >>> e = Event.objects.create(location=1, title='Hello, world', description='Happy New Year')
        >>> e
        <Event: Hello, world>
        >>> e.add_occurrences(datetime(2008,1,1), datetime(2008,1,1,1), freq=rrule.YEARLY, count=7)
        >>> e.occurrence_set.all()
        [<Occurrence: Hello, world: 2008-01-01T00:00:00>, <Occurrence: Hello, world: 2009-01-01T00:00:00>, <Occurrence: Hello, world: 2010-01-01T00:00:00>, <Occurrence: Hello, world: 2011-01-01T00:00:00>, <Occurrence: Hello, world: 2012-01-01T00:00:00>, <Occurrence: Hello, world: 2013-01-01T00:00:00>, <Occurrence: Hello, world: 2014-01-01T00:00:00>]
        >>> e = create_event(location=1, 'Bicycle repairman')
        >>> e.occurrence_set.count()
        1
        >>> e = create_event(
        ...     'Something completely different',
        ...     start_time=datetime(2008,12,1, 12),
        ...     freq=rrule.WEEKLY,
        ...     byweekday=(rrule.TU, rrule.TH),
        ...     until=datetime(2008,12,31)
        ... )
        >>> for o in e.occurrence_set.all():
        ...     print( o.start_time, o.end_time)
        ... 
        2008-12-02 12:00:00 2008-12-02 13:00:00
        2008-12-04 12:00:00 2008-12-04 13:00:00
        2008-12-09 12:00:00 2008-12-09 13:00:00
        2008-12-11 12:00:00 2008-12-11 13:00:00
        2008-12-16 12:00:00 2008-12-16 13:00:00
        2008-12-18 12:00:00 2008-12-18 13:00:00
        2008-12-23 12:00:00 2008-12-23 13:00:00
        2008-12-25 12:00:00 2008-12-25 13:00:00
        2008-12-30 12:00:00 2008-12-30 13:00:00
    '''
    pass
