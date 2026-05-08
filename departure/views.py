from django.shortcuts import redirect, render
from shared.http import safe_redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from get_time import get_time_setting_tz
from departure.models import Departure, Executor, DepartureHistoryReport
from departure.utils import create_new_departure, mark_departure_done, dell_departure
import json
from django.http import JsonResponse


@login_required
def index(request):
    context = {
        'title': 'Выезды',
    }
    return render(request, 'base.html', context)


@login_required
def create(request):
    time = request.POST.get('time', None)
    description = request.POST.get('description', None)
    executor_id = request.POST.get('executor', None)
    comment = request.POST.get('comment', 'не передан')
    if create_new_departure(description, time, executor_id, user=request.user, comment=comment):
        messages.success(request, f"Выезд ,создан!")
    else:
        messages.error(request, f"Выезд ,не создан!")

    return safe_redirect(request)


@login_required()
def create_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            executors = Executor.objects.all()
            data['executors'] = executors
            return render(request, "modals/create_departure.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def complete(request):
    time_data = request.POST.get('time', None)
    departure_id = request.POST.get('departure_id', None)
    comment = request.POST.get('comment', 'не передан')

    if not departure_id:
        messages.error(request, f"Не получен id выезда!")
    else:
        try:
            if mark_departure_done(departure_id=departure_id, time_data=time_data, user=request.user, comment=comment):
                messages.success(request, f"Выезд ,выполнен!")
            else:
                messages.error(request, f"Выезд ,не выполнен!")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")

    return safe_redirect(request)


@login_required()
def complete_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/confirm_departure.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def delete(request):
    departure_id = request.POST.get('departure_id', None)
    comment = request.POST.get('comment', 'не передан')
    if not departure_id:
        messages.error(request, f"Не получен id выезда!")
    else:
        try:
            if dell_departure(departure_id=departure_id, user=request.user, comment=comment):
                messages.success(request, f"Выезд ,удален!")
            else:
                messages.error(request, f"Выезд ,не удален!")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")
    return safe_redirect(request)


@login_required()
def delete_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/dell_departure.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def change_executor(request):
    comment = request.POST.get('comment', 'не передан')
    executor_id = request.POST.get('executor', None)
    departure_id = request.POST.get('departure_id', None)
    current_time = get_time_setting_tz()
    try:
        departure = Departure.objects.get(id=departure_id)
        executor = Executor.objects.get(id=executor_id)
        departure.executor = executor
        departure.time_updated = current_time
        departure.save()
        DepartureHistoryReport.objects.create(departure=departure, description="Исполнитель изменен", comment=comment,
                                              time=current_time, user=request.user)
        messages.success(request, f"Исполнитель изменен!")
    except Exception as e:
        messages.error(request, e)

    return safe_redirect(request)


@login_required()
def change_executor_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            data['executors'] = Executor.objects.all()
            return render(request, "modals/departure_executor.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def archivebate(request):
    comment = request.POST.get('comment', 'не передан')
    departure_id = request.POST.get('departure_id', None)
    current_time = get_time_setting_tz()
    try:
        departure = Departure.objects.get(id=departure_id)
        departure.time_updated = current_time
        departure.status = 'В архиве'
        departure.save()
        DepartureHistoryReport.objects.create(departure=departure, description="Архивирован", comment=comment,
                                              time=current_time, user=request.user)
        messages.success(request, f"Выезд архивирован!")
    except Exception as e:
        messages.error(request, e)

    return safe_redirect(request)


@login_required()
def archive_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/departure_archive.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)
