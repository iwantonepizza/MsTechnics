from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from application.models import Application, ApplicationHistoryReport
from application.utils import create_application, delete_application, apply_application
from get_time import get_time_setting_tz
from departure.models import Executor
from zip.models import Panels
import json
from django.http import JsonResponse


@login_required
def index(request, application_id=None):
    context = {
        'title': 'Выезды',
    }
    return render(request, 'base.html', context)


@login_required
def create(request):
    if request.method == 'POST':
        comment = request.POST.get('comment', None)
        panel_id = request.POST.get('panel_id', None)
        user = request.user
        current_datetime = get_time_setting_tz()
        try:
            if panel_id and panel_id != 'ПУСТО':
                panel = Panels.objects.get(pk=panel_id)
                if panel:
                    if panel.application_status.name == 'default':
                        if create_application(panel=panel, comment=comment,
                                              time_event=current_datetime,
                                              user=user):
                            messages.success(request, f"Заявка, на панель {panel.name} создана!")
                        else:
                            messages.error(request, f"Панель имеет неподходящее состояние!")

                    else:
                        messages.error(request, f"У панели уже есть заявка!")
                else:
                    messages.error(request, f"Не найдена панель!")
            else:
                messages.error(request, f"Не передан panel_id или выбранная пустая ячейка!")

        except Exception as e:
            messages.error(request, f"Ошибка: ,{e}!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def next_step(request):
    if request.method == 'POST':
        application_id = request.POST.get('application_id', None)
        if application_id:
            target_step = request.POST.get('target_step', None)
            if target_step:
                comment = request.POST.get('comment', None)
                user = request.user
                current_datetime = get_time_setting_tz()
                try:
                    if apply_application(app_id=application_id, comment=comment, target_department=target_step,
                                         time_event=current_datetime, user=user):

                        messages.success(request, f"Заявка отправлена!")

                    else:
                        messages.error(request, f"xxxxxx ошибка в функции")

                except Exception as e:
                    messages.error(request, f"Ошибка: ,{e}!")
            else:
                messages.error(request, f"Не передано новое место назначение!")
        else:
            messages.error(request, f"Не передан номер заявки!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def delete(request):
    if request.method == 'POST':
        comment = request.POST.get('comment', None)
        application_id = request.POST.get('application_id', None)
        user = request.user
        current_datetime = get_time_setting_tz()

        if application_id:
            try:
                if delete_application(app_id=application_id, user=user, comment=comment, time_event=current_datetime):
                    messages.success(request, f"Заявка, {application_id} удалена!")
                else:
                    messages.error(request, f"Заявку нельзя удалить! ")

            except Exception as e:
                messages.error(request, f"Ошибка: ,{e}!")
        else:
            messages.error(request, f"Не передан id заявки!")
    return redirect(request.META['HTTP_REFERER'])


@login_required
def change_executor(request):
    if request.method == 'POST':
        application_id = request.POST.get('application_id', None)
        if application_id:
            executor = request.POST.get('executor', None)
            if executor:
                comment = request.POST.get('comment', None)
                user = request.user
                current_datetime = get_time_setting_tz()
                try:
                    application = Application.objects.get(id=application_id)
                    executor = Executor.objects.get(id=executor)
                    if application.executor:
                        ApplicationHistoryReport.objects.create(application_id=application.id,
                                                                description=f'Изменен исполнитель на {executor}',
                                                                comment=comment, time=current_datetime, user=user)
                    else:
                        ApplicationHistoryReport.objects.create(application_id=application.id,
                                                                description=f'Выбран исполнитель {executor}',
                                                                comment=comment, time=current_datetime, user=user)
                    application.executor = executor
                    application.save()
                    messages.success(request, f"Исполнитель изменен!")


                except Exception as e:
                    messages.error(request, f"Ошибка: ,{e}!")
            else:
                messages.error(request, f"Не передан исполнитель!")
        else:
            messages.error(request, f"Не передан номер заявки!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def modal_change_executor(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            executors = Executor.objects.all()
            data['executors'] = executors
            return render(request, "modals/change_executor.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def modal_next_step(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/application_next_step.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def modal_dell_application(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/delete_application.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)
