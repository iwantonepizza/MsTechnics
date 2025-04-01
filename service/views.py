from django.shortcuts import redirect, render
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from zip.models import Display, Panels, Cell
from main.Db.orm_query import replace_panel_in_cell, change_panel_condition
from django.views.decorators.csrf import csrf_exempt
from get_time import get_time_setting_tz
from application.models import ApplicationHistoryReport
from application.utils import get_display_application
from main_menu.models import DisplayHistoryReport, PanelHistoryReport
from main.models import Cities
from django.db.models import Count
import json
from django.http import JsonResponse


@login_required
def index(request):
    all_city = Cities.objects.annotate(display_count=Count('display')).filter(
        display_count__gt=0)  # Только города с экранами

    context = {'title': 'Меню сервис',
               'all_city': all_city,

               'department': 'service'}
    return render(request, f'main_menu/main_department_menu.html', context)


@csrf_exempt
@login_required
def service_main(request, city_name, display_name):
    get_position = request.GET.get('position', None)
    panel_name = request.GET.get('panel_id', None)
    application_box_chosen = request.GET.get('application_box_chosen', 'received')

    user_cities = request.user.allowed_city.all()  # Получаем Queryset всех городов
    user_access = any(city.name == city_name for city in user_cities)

    display = (
        Display.objects
        .prefetch_related(
            "cell_set__panel__application_status__color",  # Цвета заявок
            "cell_set__panel__application_status__color_text",  # Цвета текста заявок
            "cell_set__panel__application_status",  # Цвета заявок
            "cell_set__panel__condition",  # Состояние панели
            "cell_set__panel__condition__icon",
            "cell_set__panel__department",
            "cell_set__panel__display"
        )

        .get(name=display_name)
    )

    if panel_name:
        panel = Panels.objects.get(name=panel_name)
    else:
        panel = None

    # почему-то ниже передается текстом None (str) найти как и покарать
    if get_position is not None and get_position != 'None':
        cell = Cell.objects.filter(display=display)
        cell = next((c for c in cell if c.position == get_position), None)

        try:
            info_cell = DisplayHistoryReport.objects.filter(display=display, slot=cell).order_by('-time')
        except DisplayHistoryReport.DoesNotExist:
            info_cell = None
    else:
        info_cell = None
        cell = None

    applications = get_display_application(display_name=display_name)
    free_panels = Panels.objects.filter(department='zip', display__name=display_name)

    if panel:
        panel_report_history = PanelHistoryReport.objects.filter(panel=panel).order_by('-time')
    else:
        panel_report_history = None

    # тут должно быть айди, но к модели ячейки привязано только поле дисплей.нейм
    display_id = display.name
    if cell:
        if cell.panel:
            empty_slot = False
        else:
            empty_slot = True
    else:
        empty_slot = True

    application_report = ApplicationHistoryReport.objects.order_by('-time')

    context = {
        'title': f'Сервис {display.description}',

        'cell': cell,  # экземпляр ячейки
        'info_cell': info_cell,  # инфа по координатам дисплея
        'display': display,
        'applications': applications,
        'panel': panel,  # параметры выбранной панели
        'position': get_position,  # позиция на экране
        'empty_slot': empty_slot,  # статус слота
        'application_box_chosen': application_box_chosen,
        'free_panels': free_panels,  # рабочие панели готовые к установке
        'display_id': display_id,
        'panel_report_history': panel_report_history,  # инфа о выбранной панели
        'user_access': user_access,
        'application_report': application_report,
        'department': 'service'

    }

    return render(request, f'service/service_base.html', context)


@login_required
def change_condition(request):
    if request.method == 'POST':
        comment = request.POST.get('comment', None)
        panel_id = request.POST.get('panel_id', None)
        new_condition = request.POST.get('new_condition', None)
        user = request.user
        current_datetime = get_time_setting_tz()
        try:
            if panel_id and new_condition:
                panel = Panels.objects.get(id=panel_id)
                if panel:
                    if panel.application_status.name == 'default':
                        if change_panel_condition(panel, new_condition, time_report=current_datetime,
                                                  comment=comment,
                                                  user=user):
                            messages.success(request, f"Статус панели {panel.name} изменен!")
                        else:
                            messages.error(request, f"ошибка в функции change_panel_condition!")
                    else:
                        messages.error(request, f"Нельзя поменять статус ,есть активная заявка!")
                else:
                    messages.error(request, f"Не найдена панель!")
            else:
                messages.error(request, f"Не переданы параметры")
        except Exception as e:
            messages.error(request, f"Ошибка в : change_condition ,{e}!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def change_panel_in_cell(request):
    comment = request.POST.get('comment', None)
    new_panel_id = request.POST.get('panel_id', None)
    display_id = request.POST.get('display_id', None)
    if display_id:
        user = request.user
        cell_id = request.POST.get('cell_id', None)
        with_application = request.POST.get('with_application', 'False')
        if with_application == 'True':
            with_application = True
        else:
            with_application = False
        try:
            if cell_id:
                cell = Cell.objects.filter(id=cell_id, display=display_id).first()
                if not cell:
                    messages.error(request, f"Не удалось загрузить ячейку")

                    return redirect(request.META['HTTP_REFERER'])

                if new_panel_id and new_panel_id != 'None':
                    new_panel = Panels.objects.get(name=new_panel_id)
                    all_ok, message_text = replace_panel_in_cell(cell=cell, new_panel=new_panel, user=user,
                                                                 comment=comment, with_application=with_application)
                    if all_ok:
                        messages.success(request, f"{message_text}")
                    else:
                        messages.error(request, f"{message_text}")

                else:
                    all_ok, message_text = replace_panel_in_cell(cell=cell, user=user, comment=comment,
                                                                 with_application=with_application)
                    if all_ok:
                        messages.success(request, f"{message_text}")
                    else:
                        messages.error(request, f"{message_text}")

            else:
                messages.error(request, f"Не передана или не найдена ячейка экрана!")

        except Exception as e:
            messages.error(request, f'{e} f-change_panel_in_cell')
    else:
        messages.error(request, f"Не передан параметр экрана!")

    return redirect(request.META['HTTP_REFERER'])


@login_required()
def change_panel_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Загружаем JSON
            return render(request, "modals/change_panel.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)
