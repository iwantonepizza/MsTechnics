from django.shortcuts import redirect, render
from django.contrib import messages

from MsServiceControl.settings import ALLOWED_DEPARTMENT
from django.contrib.auth.decorators import login_required
from zip.models import Display, Panels, Cell
from core_mechanic.Data.Db.orm_query import get_filter_panels, get_formated_panel_history_report, \
    replace_panel_in_cell, change_panel_condition
from django.views.decorators.csrf import csrf_exempt
from core_mechanic.get_time import get_time_setting_tz
from application.models import ApplicationHistoryReport
from application.utils import get_display_application
from main_menu.models import DisplayHistoryReport
from main.models import Cities


@login_required
def index(request):
    all_city = Cities.objects.all()

    context = {'title': 'Меню сервис',
               'all_city': all_city,
               'allowed': ALLOWED_DEPARTMENT,

               'department': 'service'}
    return render(request, f'main_menu/main_department_menu.html', context)


@csrf_exempt
@login_required
def service_main(request, city_name, display_name):
    get_position = request.GET.get('position', None)
    panel_id = request.GET.get('panel_id', None)
    left_bar_status = request.GET.get('left_bar_status', 'received')
    central_bar_status = request.GET.get('central_bar_status', 'service_display')

    display = Display.objects.get(name=display_name)

    if panel_id:
        panel = get_filter_panels(panel_id).first()
    else:
        panel = None

    # поечму то ниже передается текстом None (str) найти как и покарать
    if get_position is not None and get_position != 'None':
        cell = Cell.objects.filter(display=display)
        cell = next((c for c in cell if c.position() == get_position), None)

        try:
            info_cell = DisplayHistoryReport.objects.filter(display=display, slot=cell)
        except DisplayHistoryReport.DoesNotExist:
            info_cell = None
    else:
        info_cell = None
        cell = None

    applications = get_display_application(display_name=display_name)
    free_panels = get_filter_panels(name_display=display_name, free=True)

    applications_history = ApplicationHistoryReport.objects.all()
    panel_report_history = get_formated_panel_history_report(id_panel=panel)

    # тут должно быть айди, но к модели ячейки привязано только поле дисплей.нейм
    display_id = display.name

    context = {
        'title': f'Сервис {display.description}',

        'cell': cell,  # экземпляр ячейки
        'info_cell': info_cell,  # инфа по координатам дисплея
        'display': display,
        'applications': applications,
        'panel': panel,  # параметры выбранной панели
        'position': get_position,  # позиция на экране
        'empty_slot': cell and not cell.panel,  # статус слота
        'left_bar_status': left_bar_status,
        'central_bar_status': central_bar_status,  # статус отображения инфы справа
        'free_panels': free_panels,  # рабочие панели готовые к установке
        'display_id': display_id,
        'applications_history': applications_history,
        'panel_report_history': panel_report_history,  # инфа о выбранной панели

        'allowed': ALLOWED_DEPARTMENT,
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
                panel = get_filter_panels(name_panel=panel_id).first()
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
            messages.error(request, f"Ошибка: ,{e}!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def change_panel_in_cell(request):
    comment = request.POST.get('comment', None)
    new_panel_id = request.POST.get('new_panel_id', None)
    display_id = request.POST.get('display_id', None)
    print(display_id, "в контроллере")

    if display_id:
        user = request.user

        cell_id = request.POST.get('cell_id', None)
        cell = Cell.objects.filter(id=cell_id, display=display_id).first()
        print(cell)
        try:
            if cell:
                if new_panel_id and new_panel_id != 'None':
                    new_panel = Panels.objects.get(name=new_panel_id)

                    all_ok, message_text = replace_panel_in_cell(cell=cell, new_panel=new_panel, user=user,
                                                                 comment=comment)
                    if all_ok:
                        messages.success(request, f"{message_text}")
                    else:
                        messages.error(request, f"{message_text}")

                else:
                    all_ok, message_text = replace_panel_in_cell(cell=cell, user=user, comment=comment)
                    if all_ok:
                        messages.success(request, f"{message_text}")
                    else:
                        messages.error(request, f"{message_text}")

            else:
                messages.error(request, f"Не передана или не найдена ячейка экрана!")

        except Exception as e:
            messages.error(request, f"Ошибка: ,{e}!")
    else:
        messages.error(request, f"Не передан параметр экрана!")

    return redirect(request.META['HTTP_REFERER'])


@login_required
def change_problem_panel(request):
    problem_panel_id = request.POST.get('problem_panel_id', None)
    if problem_panel_id:
        user = request.user
        application_id = request.POST.get('application_id', None)
        comment = request.POST.get('comment', None)
        try:
            if application_id:
                messages.error(request, 'Ошибка в обработке')

            else:
                messages.error(request, f"а где заявка")

        except Exception as e:
            messages.error(request, f"Ошибка: ,{e}!")
    else:
        messages.error(request, f"Не передан айди панели!")

    return redirect(request.META['HTTP_REFERER'])
