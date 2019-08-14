from __future__ import print_function, unicode_literals

#######################
#######################
import calendar
import itertools
from datetime import date, datetime, time, timedelta

#-------------------------------------------------------------------------------
import vobject
from dateutil import parser
from django import http
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.timezone import now as datetime_now
from django.views.generic.list import ListView

from latex.djangoviews import LaTeX_ListView
from swingtime import forms, utils
from swingtime.conf import settings as swingtime_settings
from swingtime.models import BookingLocation, Event, Occurrence

from . import libvevent
from .forms import LocationSelectForm

if swingtime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(swingtime_settings.CALENDAR_FIRST_WEEKDAY)

#-------------------------------------------------------------------------------

try:
    import guardian
except ImportError:
    use_guardian = False
else:
    use_guardian = True

if use_guardian:
    from guardian.shortcuts import get_objects_for_user


def forbidden_response(request, error_message):
    return render(
        request, '403.html', {'test_fail_msg': error_message}, status=403)


def get_location_list(user, perm='swingtime.book_can_view'):
    """
    Get a filtered list of locations.
    Returns a queryset.
    """
    if user.has_perm(perm):
        location_list = BookingLocation.objects.all()
    elif use_guardian and user.is_authenticated:
        location_list = get_objects_for_user(user, perm, BookingLocation)
    else:
        location_list = BookingLocation.objects.none()

    location_list = location_list.filter(active=True)
    return location_list


def check_permission(user, perm, obj):
    """
    Check if the user has the permission with the object.
    This checks both object permission and global.
    """
    return user.has_perm(perm, obj) or user.has_perm(perm)


def get_location_or_404(slug):
    try:
        return BookingLocation.objects.get_by_slug(slug)
    except BookingLocation.NotFound:
        raise Http404


#-------------------------------------------------------------------------------


class CalendarList_View(ListView):

    template_name = 'swingtime/calendar_list.html'
    model = BookingLocation
    context_object_name = 'location_list'

    def get_queryset(self):
        return get_location_list(self.request.user)


calendar_list = login_required(CalendarList_View.as_view())

#-------------------------------------------------------------------------------


@login_required
def event_listing(request,
                  calendar_slug,
                  template='swingtime/event_list.html',
                  events=None,
                  **extra_context):
    '''
    View all ``events``.

    If ``events`` is a queryset, clone it. If ``None`` default to all ``Event``s.

    Context parameters:

    events
        an iterable of ``Event`` objects

    ???
        all values passed in via **extra_context
    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    if not events:
        events = Event.objects.all()
    elif hasattr(events, '_clone'):
        events = events._clone()

    return render(
        request,
        template,
        dict(extra_context, events=events, location=location),
    )


#-------------------------------------------------------------------------------


@login_required
def event_view(request,
               calendar_slug,
               event_pk,
               template='swingtime/event_detail.html',
               event_form_class=forms.EventForm,
               recurrence_form_class=forms.MultipleOccurrenceForm):
    '''
    View an ``Event`` instance and optionally update either the event or its
    occurrences.

    Context parameters:

    event
        the event keyed by ``event_pk``

    event_form
        a form object for updating the event

    recurrence_form
        a form object for adding occurrences
    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    event = get_object_or_404(Event, pk=event_pk, location=location)
    event_form = recurrence_form = None

    if request.method == 'POST':
        if '_update' in request.POST:
            if not check_permission(request.user, 'swingtime.book_can_edit',
                                    location):
                return forbidden_response(
                    request, 'You cannot edit events at this location')
            event_form = event_form_class(request.POST, instance=event)

        elif '_add' in request.POST:
            if not check_permission(request.user, 'swingtime.book_can_add',
                                    location):
                return forbidden_response(
                    request, 'You cannot add events at this location')
            recurrence_form = recurrence_form_class(request.POST)
        else:
            return http.HttpResponseBadRequest('Bad Request')

    event_form = event_form or event_form_class(instance=event)
    location_list = get_location_list(request.user)
    event_form.fields["location"].queryset = location_list

    if request.method == 'POST':
        if '_update' in request.POST:
            if event_form.is_valid():
                event_form.save(event)
                return http.HttpResponseRedirect(request.path)
        elif '_add' in request.POST:
            if recurrence_form.is_valid():
                recurrence_form.save(event)
                return http.HttpResponseRedirect(request.path)
        else:
            return http.HttpResponseBadRequest('Bad Request')

    if not recurrence_form:
        recurrence_form = recurrence_form_class(
            initial=dict(dtstart=datetime_now()))
    #recurrence_form.fields['location'].queryset = location_list

    return render(
        request,
        template,
        dict(
            event=event,
            event_form=event_form,
            recurrence_form=recurrence_form,
            location=location),
    )


#-------------------------------------------------------------------------------


@login_required
def occurrence_view(request,
                    calendar_slug,
                    event_pk,
                    occurrence_pk,
                    template='swingtime/occurrence_detail.html',
                    form_class=forms.SingleOccurrenceForm):
    '''
    View a specific occurrence and optionally handle any updates.

    Context parameters:

    occurrence
        the occurrence object keyed by ``pk``

    form
        a form object for updating the occurrence
    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    occurrence = get_object_or_404(
        Occurrence,
        pk=occurrence_pk,
        event__pk=event_pk,
        event__location=location)
    if request.method == 'POST':
        if not check_permission(request.user, 'swingtime.book_can_edit',
                                location):
            return forbidden_response(
                request, 'You cannot edit bookings at this location')
        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            form.save()
            return http.HttpResponseRedirect(request.path)
    else:
        form = form_class(instance=occurrence)

    return render(
        request,
        template,
        dict(occurrence=occurrence, form=form, location=location),
    )


@login_required
def occurrence_delete(
        request,
        calendar_slug,
        event_pk,
        occurrence_pk,
        template_name='swingtime/occurrence_delete.html',
):
    """
    Delete an occurrence
    """
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_delete',
                            location):
        return forbidden_response(request,
                                  'You cannot delete at this location')

    event = get_object_or_404(Event, pk=event_pk, location=location)
    occurrence = get_object_or_404(Occurrence, pk=occurrence_pk, event=event)

    if request.method == 'POST':
        if '_delete' in request.POST:
            dt = occurrence.start_time
            occurrence.delete()
            if event.occurrence_set.count() == 0:
                # delete the event as well.
                event.delete()
                return http.HttpResponseRedirect(
                    reverse(
                        'swingtime-daily-view',
                        kwargs={
                            'year': dt.year,
                            'month': dt.month,
                            'day': dt.day,
                            'calendar_slug': location.slug,
                        }))
            else:
                return http.HttpResponseRedirect(event.get_absolute_url())
        else:
            return http.HttpResponseBadRequest('Bad Request')

    return render(
        request,
        template_name,
        dict(occurrence=occurrence, event=event, location=location),
    )


#-------------------------------------------------------------------------------


@login_required
def add_event(request,
              calendar_slug,
              template='swingtime/add_event.html',
              event_form_class=forms.EventForm,
              recurrence_form_class=forms.MultipleOccurrenceForm):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.

    Context parameters:

    dtstart
        a datetime.datetime object representing the GET request value if present,
        otherwise None

    event_form
        a form object for updating the event

    recurrence_form
        a form object for adding occurrences

    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_add', location):
        return forbidden_response(request,
                                  'You cannot add events for this location')

    location_list = get_location_list(request.user, 'swingtime.book_can_add')
    dtstart = None
    if request.method == 'POST':
        event_form = event_form_class(request.POST)
        event_form.fields['location'].queryset = location_list
        recurrence_form = recurrence_form_class(request.POST)
        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save()
            recurrence_form.save(event)
            return http.HttpResponseRedirect(event.get_absolute_url())

    else:
        if 'dtstart' in request.GET:
            try:
                dtstart = parser.parse(request.GET['dtstart'])
                print('GET dtstart', dtstart)
            except:
                # TODO A badly formatted date is passed to add_event
                print('Badly formatted!')
                dtstart = datetime_now()

        event_form = event_form_class(initial=dict(location=location.id))
        event_form.fields['location'].queryset = location_list
        recurrence_form = recurrence_form_class(initial=dict(dtstart=dtstart))

    return render(
        request,
        template,
        dict(
            dtstart=dtstart,
            event_form=event_form,
            recurrence_form=recurrence_form,
            location=location),
    )


#-------------------------------------------------------------------------------


@login_required
def _datetime_view(request,
                   calendar_slug,
                   template,
                   dt,
                   timeslot_factory=None,
                   items=None,
                   params=None):  # this view is not called directly.
    '''
    Build a time slot grid representation for the given datetime ``dt``. See
    utils.create_timeslot_table documentation for items and params.

    Context parameters:

    day
        the specified datetime value (dt)

    next_day
        day + 1 day

    prev_day
        day - 1 day

    timeslots
        time slot grid of (time, cells) rows

    DCG: show foreign events in this view (done in utils.create_timeslot_table).
    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    timeslot_factory = timeslot_factory or utils.create_timeslot_table
    params = params or {}
    data = dict(
        day=dt,
        next_day=dt + timedelta(days=+1),
        prev_day=dt + timedelta(days=-1),
        timeslots=timeslot_factory(
            location,
            check_permission(request.user, 'swingtime.book_can_view',
                             location),
            dt,
            items,
            css_class_cycles=None,
            **params),
        location=location,
    )

    return render(request, template, data)


#-------------------------------------------------------------------------------


@login_required
def day_view(request,
             calendar_slug,
             year,
             month,
             day,
             template='swingtime/daily_view.html',
             **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    dt = utils.force_aware(date(int(year), int(month), int(day)))
    return _datetime_view(request, calendar_slug, template, dt, **params)


#-------------------------------------------------------------------------------


@login_required
def today_view(request,
               calendar_slug,
               template='swingtime/daily_view.html',
               **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    return _datetime_view(request, calendar_slug, template, datetime_now(),
                          **params)


#-------------------------------------------------------------------------------


@login_required
def year_view(request,
              calendar_slug,
              year,
              template='swingtime/yearly_view.html',
              queryset=None):
    '''

    Context parameters:

    year
        an integer value for the year in questin

    next_year
        year + 1

    last_year
        year - 1

    by_month
        a sorted list of (month, occurrences) tuples where month is a
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months
        which have at least 1 occurrence is represented in the list

    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    year = int(year)
    if queryset:
        queryset = queryset._clone()
    else:
        queryset = Occurrence.objects.select_related()

    occurrences = queryset.filter(
        models.Q(start_time__year=year) | models.Q(end_time__year=year), )
    occurrences = occurrences.filter(event__location=location)

    def grouper_key(o):
        if o.start_time.year == year:
            return datetime(year, o.start_time.month, 1)

        return datetime(year, o.end_time.month, 1)

    by_month = [(dt, list(items))
                for dt, items in itertools.groupby(occurrences, grouper_key)]

    return render(
        request,
        template,
        dict(
            year=year,
            by_month=by_month,
            next_year=year + 1,
            last_year=year - 1,
            location=location),
    )


#-------------------------------------------------------------------------------


@login_required
def month_view(request,
               calendar_slug,
               year,
               month,
               template='swingtime/monthly_view.html',
               queryset=None):
    '''
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:

    today
        the current datetime.datetime value

    calendar
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day

    this_month
        a datetime.datetime representing the first day of the month

    next_month
        this_month + 1 month

    last_month
        this_month - 1 month

    DCG: show foreign events in this view.
    '''
    location = get_location_or_404(calendar_slug)
    if not check_permission(request.user, 'swingtime.book_can_view', location):
        return forbidden_response(request, 'You cannot view this location')

    year, month = int(year), int(month)

    cal = calendar.monthcalendar(year, month)
    dtstart = utils.force_aware(datetime(year, month, 1))
    last_day = max(cal[-1])
    dtend = utils.force_aware(datetime(year, month, last_day))

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    if queryset:
        queryset = queryset._clone()
    else:
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
        today=datetime_now(),
        calendar=[[(d, by_day.get(d, [])) for d in row] for row in cal],
        this_month=dtstart,
        next_month=dtstart + timedelta(days=+last_day),
        last_month=dtstart + timedelta(days=-1),
        base_main_page_has_no_rightbar=
        True,  # -- supress rightbar in month view.
        location=location,
    )

    return render(request, template, data)


#-------------------------------------------------------------------------------


@login_required
def current_month_view(request, calendar_slug):
    dt = datetime_now()
    return month_view(request, calendar_slug, dt.year, dt.month)


#-------------------------------------------------------------------------------


@login_required
def current_year_view(request, calendar_slug):
    dt = datetime_now()
    return month_view(request, calendar_slug, dt.year)


#-------------------------------------------------------------------------------


def calendar_to_response(cal, filename):
    if not filename.endswith('.ics'):
        filename += '.ics'
    icalstream = cal.serialize()
    response = HttpResponse(icalstream, content_type='text/calendar')
    response['Filename'] = filename  # IE needs this
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response


def webcal(request, room_slug):
    try:
        location = BookingLocation.objects.get_by_slug(room_slug)
    except BookingLocation.DoesNotExist:
        raise Http404

    occurrences = Occurrence.objects.filter(event__location=location)
    vevents = [libvevent.from_occurrence(o) for o in occurrences]
    vevents.extend(location.scheduled_events)

    cal = vobject.iCalendar()
    cal.add('method').value = 'PUBLISH'  # IE/Outlook needs this
    cal.add('x-wr-calname').value = "{}".format(location)
    cal.add('x-published-ttl').value = 'PT15M'
    for vev in vevents:
        cal.add(vev)

    return calendar_to_response(cal, room_slug)


#-------------------------------------------------------------------------------


def load_month_data(room_slug, year, month):
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
        today=datetime_now(),
        calendar=[[(d, by_day.get(d, [])) for d in row] for row in cal],
        this_month=dtstart,
        next_month=dtstart + timedelta(days=+last_day),
        last_month=dtstart + timedelta(days=-1),
        base_main_page_has_no_rightbar=
        True,  # -- supress rightbar in month view.
        location=location,
    )
    return data


class PrintMonthSource_View(ListView):
    """
    Show the LaTeX source for the given room and month
    """
    queryset = Event.objects.none()
    template_name = 'swingtime/print/monthly.tex'

    def get_context_data(self, **kwargs):
        return load_month_data(self.kwargs['room'], self.kwargs['year'],
                               self.kwargs['month'])


print_month_source = PrintMonthSource_View.as_view()


class PrintMonth_View(LaTeX_ListView):
    """
    Show the printable version of the given room and month
    """
    queryset = Event.objects.none()
    template_name = 'swingtime/print/monthly.tex'

    def get_context_data(self, **kwargs):
        return load_month_data(self.kwargs['room_slug'], self.kwargs['year'],
                               self.kwargs['month'])


print_month = PrintMonth_View.as_view()
