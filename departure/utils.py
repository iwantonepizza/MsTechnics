from get_time import get_time_setting_tz, datetime
from departure.models import Departure, Executor, DepartureHistoryReport
from apps.core.users.models import MsUser


def create_new_departure(description: str = None, time_start: datetime = None, executor_id: str = None,
                         user: MsUser = None, comment: str = 'не передан') -> bool:
    time_created = get_time_setting_tz()
    if not time_start:
        time_start = time_created
    else:
        time_start = datetime.fromisoformat(str(time_start))
    if executor_id:
        executor = Executor.objects.get(id=executor_id)
    else:
        executor = None
    created = Departure.objects.create(description=description, time_start=time_start, time_created=time_created,
                                       executor=executor, time_updated=time_created)
    if created:
        DepartureHistoryReport.objects.create(departure=created, description="Выезд создан", comment=comment,
                                              time=time_created, user=user)
        return True
    else:
        return False


def mark_departure_done(departure_id: int, time_data: datetime, user: MsUser, comment: str = 'не передан') -> bool:
    current_time = get_time_setting_tz()
    if not time_data:
        time_data = get_time_setting_tz()
    else:
        time_data = datetime.fromisoformat(str(time_data))
    departure = Departure.objects.get(id=departure_id)
    if departure:
        departure.time_updated = current_time
        departure.time_end = time_data
        departure.status = 'выполнено'
        departure.save()
        DepartureHistoryReport.objects.create(departure=departure, description="Выезд совершен", comment=comment,
                                              time=current_time, user=user)
        return True
    else:
        return False


def dell_departure(departure_id: int, user: MsUser, comment: str) -> bool:
    current_time = get_time_setting_tz()

    departure = Departure.objects.get(id=departure_id)
    if departure:
        DepartureHistoryReport.objects.create(departure=departure, description="Выезд удален", comment=comment,
                                              time=current_time, user=user)
        departure.delete()
        return True
    else:
        return False
