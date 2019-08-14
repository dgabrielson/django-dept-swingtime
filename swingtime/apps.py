#########################################################################

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

#########################################################################


class SwingtimeConfig(AppConfig):
    name = "swingtime"
    verbose_name = _("Room Bookings")

    def ready(self):
        """
        Any app specific startup code, e.g., register signals,
        should go here.
        """


#########################################################################
