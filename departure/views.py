from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core_mechanic.telegram_connect import send_tg_notification
from departure.utils import create_new_departure, mark_departure_done, dell_departure


@login_required
def index(request):
    context = {
        'title': 'Выезды',
    }
    return render(request, 'base.html', context)


@login_required
def create(request, description=None):
    time = request.POST.get('time', None)
    if not description:
        description = request.POST.get('description', None)
    if create_new_departure(description, time):
        messages.success(request, f"Выезд ,создан!")
    else:
        messages.error(request, f"Выезд ,не создан!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def complete(request):
    time_data = request.POST.get('time', None)
    departure_id = request.POST.get('departure_id', None)
    if not departure_id:
        messages.error(request, f"Не получен id выезда!")
    else:
        try:
            if mark_departure_done(departure_id=departure_id, time_data=time_data):
                messages.success(request, f"Выезд ,выполнен!")
            else:
                messages.error(request, f"Выезд ,не выполнен!")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def delete(request):
    time_data = request.POST.get('time', None)
    departure_id = request.POST.get('departure_id', None)
    if not departure_id:
        messages.error(request, f"Не получен id выезда!")
    else:
        try:
            if dell_departure(departure_id=departure_id, time_data=time_data):
                messages.success(request, f"Выезд ,удален!")
            else:
                messages.error(request, f"Выезд ,не удален!")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")
    # send_tg_notification(type_msg='departure', text=f'Выезд совершен успешно: {description}\n'
    #                                                 f'Время - {datetime.strftime(current_datetime, '%d.%m.%Y %H:%M:%S ')}\n'
    #                                                 f'Создатель: {user.first_name} {user.last_name}')
    # send_tg_notification(type_msg='departure', text=f'Выезд отменен: {description}\n'
    #                                                 f'Время - {datetime.strftime(current_datetime, '%d.%m.%Y %H:%M:%S ')}\n'
    #                                                 f'Создатель: {user.first_name} {user.last_name}')
    # send_tg_notification(type_msg='departure', text=f'Создан выезд: {description}\n'
    #                                                 f'Время - {datetime.strftime(current_datetime, '%d.%m.%Y %H:%M:%S ')}\n'
    #                                                 f'Создатель: {user.first_name} {user.last_name}')
    return redirect(request.META['HTTP_REFERER'])
