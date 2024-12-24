import pytz
from datetime import datetime
from django.conf import settings


def get_time_setting_tz() -> datetime:
    local_tz = pytz.timezone(settings.TIME_ZONE)
    return datetime.now(local_tz)
