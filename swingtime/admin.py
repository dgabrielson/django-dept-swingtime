from django.conf import settings
from django.contrib import admin

from swingtime.models import *

MyModelAdmin = None
if getattr(settings, 'GUARDED_MODEL_ADMIN_ENABLED', True):
    # automatically use guardian, if installed
    try:
        from guardian.admin import GuardedModelAdmin
    except ImportError:
        pass
    else:
        MyModelAdmin = GuardedModelAdmin
if MyModelAdmin is None:
    MyModelAdmin = admin.ModelAdmin


#======================================================================
class NoteAdmin(admin.ModelAdmin):
    list_display = ('note', 'created')


#======================================================================
class OccurrenceInline(admin.TabularInline):
    model = Occurrence


#======================================================================
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'description')
    list_filter = ('location', )
    search_fields = ('title', 'description')
    inlines = [
        OccurrenceInline,
    ]


admin.site.register(Event, EventAdmin)

#======================================================================


class BookingLocation_Admin(MyModelAdmin):
    pass


admin.site.register(BookingLocation, BookingLocation_Admin)

#======================================================================
