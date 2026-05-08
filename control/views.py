from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from Config.settings import ALLOWED_DEPARTMENT
from application.models import Application, ApplicationHistoryReport
from main.Db.orm_query import get_today_daily
from application.utils import get_display_application
from zip.models import Display, Cell, Panels
from main.models import Cities
from main_menu.models import DailyTaskHistoryReport, DisplayHistoryReport, PanelHistoryReport
from django.db.models import Count


@login_required
def index_control(request):
    all_city = Cities.objects.annotate(display_count=Count('display')).filter(
        display_count__gt=0)  # Только города с экранами

    applications = Application.objects.select_related(
        'panel',
        'display__city',
        'cell',
        'status',
        'executor'
    ).exclude(status__in=['archive_done', 'archive_unable']).order_by('-last_update_date_time')

    context = {'title': 'Меню Контроль',

               'all_city': all_city,
               'applications': applications,

               'allowed': ALLOWED_DEPARTMENT,
               'department': 'control'}
    return render(request, f'main_menu/main_department_menu.html', context)


@login_required
def control_main(request, city_name, display_name):
    panel_name = request.GET.get('panel_id', None)
    application_box_chosen = request.GET.get('application_box_chosen', 'received')
    tasks = get_today_daily(city_name)
    position = request.GET.get('position', None)

    display = (
        Display.objects
        .prefetch_related(
            "cell_set__panel__application_status",  # Цвета заявок
            "cell_set__panel__condition",  # Состояние панели
            "cell_set__panel__condition__icon",
            "cell_set__panel__department",
            "cell_set__panel__display"
        ).get(name=display_name)

    )
    application_report = ApplicationHistoryReport.objects.order_by('-time')

    if panel_name and panel_name != 'ПУСТО':
        panel = Panels.objects.get(name=panel_name)
    else:
        panel = None

    if position:
        cell = Cell.objects.get(panel=panel)
        try:
            info_cell = DisplayHistoryReport.objects.filter(display=display, slot=cell).order_by('-time')
        except DisplayHistoryReport.DoesNotExist:
            info_cell = None
    else:
        info_cell = None
        cell = None

    applications = get_display_application(display_name=display_name)

    new_application_status = applications['sent_to_control'].exists()
    if panel:
        panel_report_history = PanelHistoryReport.objects.filter(panel=panel)
    else:
        panel_report_history = None
    daily_history_report = DailyTaskHistoryReport.objects.all()

    context = {'title': f'Контроль {display.description}',

               'application_box_chosen': application_box_chosen,
               'applications': applications,
               'new_application_check': new_application_status,
               'panel': panel,
               'daily': tasks,
               'display': display,
               'cell': cell,  # экземпляр ячейки
               'info_cell': info_cell,  # инфа по координатам дисплея
               'position': position,
               'panel_report_history': panel_report_history,
               'daily_history_report': daily_history_report,
               'application_report': application_report,

               'allowed': ALLOWED_DEPARTMENT,
               'department': 'control'}
    return render(request, f'control/control_base.html', context)
