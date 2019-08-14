from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from swingtime import views
from swingtime.models import BookingLocation

urlpatterns = [
    url(
        r'^$',
        login_required(
            views.CalendarList_View.as_view(
                template_name='swingtime/choose_location.html')),
        name='swingtime-choose-location',
    ),
    url(
        r'^calendar-feeds',
        login_required(
            views.CalendarList_View.as_view(
                template_name='swingtime/location_feeds.html')),
        name='swingtime-calendar-feeds',
    ),
    url(r'^(?P<calendar_slug>[\w_-]+)/calendar/$',
        views.today_view,
        name='swingtime-today'),
    url(r'^(?P<calendar_slug>[\w_-]+)/$',
        views.current_month_view,
        name='swingtime-current-month'),
    url(r'^(?P<calendar_slug>[\w_-]+)/current-year$',
        views.current_year_view,
        name='swingtime-current-year'),
    url(r'^(?P<calendar_slug>[\w_-]+)/(?P<year>\d{4})/$',
        views.year_view,
        name='swingtime-yearly-view'),
    url(r'^(?P<calendar_slug>[\w_-]+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/$',
        views.month_view,
        name='swingtime-monthly-view'),
    url(r'^(?P<calendar_slug>[\w_-]+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/(?P<day>[0-3]?\d)/$',
        views.day_view,
        name='swingtime-daily-view'),
    url(r'^(?P<calendar_slug>[\w_-]+)/events/$',
        views.event_listing,
        name='swingtime-events'),
    url(r'^(?P<calendar_slug>[\w_-]+)/events/add/$',
        views.add_event,
        name='swingtime-add-event'),
    url(r'^(?P<calendar_slug>[\w_-]+)/events/(?P<event_pk>\d+)/$',
        views.event_view,
        name='swingtime-event'),
    url(
        r'^(?P<calendar_slug>[\w_-]+)/events/(?P<event_pk>\d+)/(?P<occurrence_pk>\d+)/$',
        views.occurrence_view,
        name='swingtime-occurrence',
    ),
    url(
        r'^(?P<calendar_slug>[\w_-]+)/events/(?P<event_pk>\d+)/(?P<occurrence_pk>\d+)/delete/$',
        views.occurrence_delete,
        name='swingtime-occurrence-delete',
    ),
    ## TODO: update these to calendar_slug
    url(
        r'^webcal/(?P<room_slug>[\w_-]+)$',
        views.webcal,
        name='swingtime-webcal',
    ),
    url(
        r'^print-calendar/(?P<room_slug>[\w_-]+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/$',
        views.print_month,
        name='swingtime-month-print',
    ),
    url(
        r'^print-calendar-source/(?P<room_slug>[\w_-]+)/(?P<year>\d{4})/(?P<month>0?[1-9]|1[012])/$',
        views.print_month_source,
        name='swingtime-month-print-source',
    ),
]
