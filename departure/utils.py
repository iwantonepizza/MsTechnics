from core_mechanic.get_time import get_time_setting_tz, datetime
from departure.models import Departure


def create_new_departure(description: str = None, time_start: datetime = None) -> bool:
    time_created = get_time_setting_tz()
    if not time_start:
        time_start = time_created
    else:
        time_start = datetime.fromisoformat(str(time_start))
    created = Departure.objects.create(description=description, time_start=time_start, time_created=time_created)
    if created:
        return True
    else:
        return False


def mark_departure_done(departure_id: int, time_data: datetime) -> bool:
    if not time_data:
        time_data = get_time_setting_tz()
    else:
        time_data = datetime.fromisoformat(str(time_data))
    departure = Departure.objects.get(id=departure_id)
    if departure:
        departure.time_end = time_data
        departure.status = 'done'
        departure.save()
        return True
    else:
        return False


def dell_departure(departure_id: int, time_data: datetime) -> bool:
    # потом можно запись в базу сделать об удалении
    if not time_data:
        time_data = get_time_setting_tz()
    else:
        time_data = datetime.fromisoformat(str(time_data))
    departure = Departure.objects.get(id=departure_id)
    if departure:
        departure.delete()
        return True
    else:
        return False
