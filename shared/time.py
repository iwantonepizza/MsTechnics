"""
shared/time.py — утилиты для работы со временем.

Перенесено из корневого get_time.py (T-2-011).
Compat-shim: get_time.py → from shared.time import get_time_setting_tz
"""
from datetime import datetime

import pytz
from django.conf import settings


def get_time_setting_tz() -> datetime:
    """Возвращает текущее время в timezone из settings.TIME_ZONE."""
    tz = pytz.timezone(settings.TIME_ZONE)
    return datetime.now(tz)
