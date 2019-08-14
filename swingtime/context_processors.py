#from datetime import datetime
from django.utils.timezone import now as datetime_now


#-------------------------------------------------------------------------------
def current_datetime(request):
    return dict(current_datetime=datetime_now())
