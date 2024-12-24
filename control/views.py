from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from MsServiceControl.settings import ALLOWED_DEPARTMENT
from core_mechanic.Data.Db.orm_query import get_today_daily, get_filter_panels, get_formated_panel_history_report
from application.utils import get_filter_application, get_display_application
from zip.models import Display, Cell
from main.models import Cities
from main_menu.models import DailyTaskHistoryReport, DisplayHistoryReport


@login_required
def index_control(request):
    all_city = Cities.objects.all()
    applications = get_filter_application()
    context = {'title': 'Меню Контроль',

               'all_city': all_city,
               'applications': applications,

               'allowed': ALLOWED_DEPARTMENT,
               'department': 'control'}
    return render(request, f'main_menu/main_department_menu.html', context)


@login_required
def control_main(request, city_name, display_name):
    panel_id = request.GET.get('panel_id', None)
    left_bar_status = request.GET.get('left_bar_status', 'received')
    tasks = get_today_daily(city_name)
    display = Display.objects.get(name=display_name)
    get_position = request.GET.get('position', None)

    if panel_id and panel_id != 'ПУСТО':
        panel = get_filter_panels(panel_id).first()
    else:
        panel = None

    if get_position is not None and get_position != 'None':
        cell = Cell.objects.get(pk=get_position)
        try:
            info_cell = DisplayHistoryReport.objects.filter(display=display, slot=cell)
        except DisplayHistoryReport.DoesNotExist:
            info_cell = None
    else:
        info_cell = None
        cell = None

    applications = get_display_application(display_name=display_name)

    new_application_status = applications['application_sent_to_control'].exists()

    # узнать нужны ли парамеры ниже
    panel_report_history = get_formated_panel_history_report(id_panel=panel)
    daily_history_report = DailyTaskHistoryReport.objects.all()

    context = {'title': f'Контроль {display.description}',

               'left_bar_status': left_bar_status,
               'applications': applications,
               'new_application_check': new_application_status,
               'panel': panel,
               'daily': tasks,
               'display': display,
               'cell': cell,  # экземпляр ячейки
               'info_cell': info_cell,  # инфа по координатам дисплея

               'panel_report_history': panel_report_history,
               'daily_history_report': daily_history_report,

               'allowed': ALLOWED_DEPARTMENT,
               'department': 'control'}
    return render(request, f'control/control_base.html', context)
