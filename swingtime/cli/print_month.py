"""
Print the LaTeX code for a month room schedule.
"""
#######################
from __future__ import print_function, unicode_literals

import calendar
import itertools
import sys
from datetime import datetime, time, timedelta

from django.template.loader import render_to_string

from latex import LaTeX_Document
from swingtime import libvevent
from swingtime.conf import settings as swingtime_settings
from swingtime.models import BookingLocation, Event, Occurrence

#######################
DJANGO_COMMAND = 'main'
OPTION_LIST = ()
ARGS_USAGE = '<room-slug> YYYY MM'
HELP_TEXT = __doc__.strip()

TEMPLATE_FILENAME = 'swingtime/print/monthly.tex'

if swingtime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(swingtime_settings.CALENDAR_FIRST_WEEKDAY)

#############################################################

#############################################################


def load_data(room_slug, year, month):
    """
    This is a copy-paste of swingtime.views.month_view, more or less.
    """
    location = BookingLocation.objects.get_by_slug(room_slug)

    year, month = int(year), int(month)

    cal = calendar.monthcalendar(year, month)
    dtstart = datetime(year, month, 1)
    last_day = max(cal[-1])
    dtend = datetime(year, month, last_day)

    queryset = Occurrence.objects.select_related()

    occurrences = queryset.filter(
        start_time__year=year, start_time__month=month)
    occurrences = occurrences.filter(event__location=location)

    vevents = libvevent.filter_list_by_month(location.scheduled_events,
                                             dtstart)
    occ_vev = [libvevent.OccurenceWrapper(ev) for ev in vevents]
    all_occurrences = sorted(
        list(occurrences) + occ_vev, key=lambda o: o.start_time)

    # itertools.groupby() makes assumptions about sortedness...
    by_day = dict([(dom, list(items)) for dom, items in itertools.groupby(
        all_occurrences, lambda o: o.start_time.day)])
    # by_day is a mapping of days of the month, to a list of occurence objects

    data = dict(
        today=datetime.now(),
        calendar=[[(d, by_day.get(d, [])) for d in row] for row in cal],
        this_month=dtstart,
        next_month=dtstart + timedelta(days=+last_day),
        last_month=dtstart + timedelta(days=-1),
        base_main_page_has_no_rightbar=
        True,  # -- supress rightbar in month view.
        location=location,
    )
    return data


def main(options, args):
    t = render_to_string(TEMPLATE_FILENAME, load_data(*args))
    print(t)


if __name__ == '__main__':
    room_slug = sys.argv[1]
    year = sys.argv[2]
    month = sys.argv[3]
    main(room_slug, year, month)
