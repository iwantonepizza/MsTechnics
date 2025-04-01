from application.models import ApplicationHistoryReport
from get_time import get_time_setting_tz
from zip.models import *

from datetime import datetime
from main.models import Condition, Department
from main_menu.models import PanelHistoryReport, DailyTaskHistoryReport, DisplayHistoryReport
from django.db.models import Case, When, Value, CharField, BooleanField, ExpressionWrapper, Q


def available_to_use(display_id):
    return Panels.objects.filter(
        Q(display=Display.objects.get(name=display_id)) | Q(display=None) | Q(department=None) | Q(
            application_status=None))


def change_panel_condition(panel: str | Panels, new_condition: str, time_report: datetime,
                           comment: str = 'Комментарий не передан', user=None):
    if type(panel) is str:
        panel = Panels.objects.get(name=panel)

    if Panels:
        old_condition = panel.condition.description
        panel.condition = Condition.objects.get(name=new_condition)
        panel.save()
        PanelHistoryReport.objects.create(panel=panel,
                                          description=f'{panel.condition.icon} {old_condition} -> {panel.condition.description}',
                                          comment=comment,
                                          type_report='condition', time=time_report, user=user)
        return True
    return False





def get_formated_panel_history_report(panel_report_history):
    panel_move_report = panel_report_history.filter(type_report='moving')
    panel_breakdown_report = panel_report_history.filter(type_report='breakdown')
    panel_condition_report = panel_report_history.filter(type_report='condition')
    panel_service_report = panel_report_history.filter(type_report='service')
    panel_none_type_report = panel_report_history.filter(type_report='none_type')

    panel_report_history = {
        'moving': panel_move_report,
        'breakdown': panel_breakdown_report,
        'condition': panel_condition_report,
        'service': panel_service_report,
        'none_type': panel_none_type_report
    }
    return panel_report_history


def get_today_daily(city_name: str):
    task = DailyTask.objects.filter(city=city_name).annotate(
        smile=Case(
            When(status='not_ready', then=Value('🔒')),
            When(status='ready', then=Value('🟢')),
            When(status='deadline', then=Value('🔥')),
            When(status='done', then=Value('✅')),
            When(status='undone', then=Value('❌')),
            default=Value('❓'),
            output_field=CharField()
        ), is_ready=ExpressionWrapper(
            Q(status__in=['ready', 'deadline']),
            output_field=BooleanField())).order_by('start_time')

    return task


def done_daily(id_daily, user, result) -> bool | None:
    task = DailyTask.objects.get(id=id_daily)
    current_datetime = get_time_setting_tz()
    if task.complete_task(current_datetime):
        DailyTaskHistoryReport.objects.create(task=task, user=user, result=result, time=current_datetime)
        return presend_filters(text=f'✅ {task.name} выполнен! ✅',
                               type_msg='daily'
                               ) == 200
    else:
        return None


def replace_panel_in_cell(cell: Cell, new_panel: Panels | None = None, user=None, comment: str | None = None,
                          with_application: bool = False) -> tuple[bool, str]:
    current_time = get_time_setting_tz()
    panel = cell.panel
    current_panel_check = None
    new_panel_check = None
    if panel:
        current_panel_check = True

        PanelHistoryReport.objects.create(panel=panel,
                                          description=f'⬆️ {panel.display.description} {cell.position}',
                                          type_report='moving', time=current_time, user=user, comment=comment)
        DisplayHistoryReport.objects.create(display=panel.display, slot=cell,
                                            description=f'⬆️ {panel.name}',
                                            type_event='moving', time=current_time, user=user, comment=comment)

        if with_application:
            panel.department = Department.objects.get(name='service')
            PanelHistoryReport.objects.create(panel=panel,
                                              description=f'⚙️ Снят в сервис с {panel.display.description} {cell.position}',
                                              type_report='service', time=current_time, user=user, comment=comment)
            ApplicationHistoryReport.objects.create(application_id=panel.application.first().id,
                                                    description='Снята панель по заявке',
                                                    comment=comment, time=current_time, user=user)
        else:
            panel.department = Department.objects.get(name='zip')
        panel.save()
        cell.panel = None
        cell.save()
    if new_panel:
        new_panel_check = True
        if new_panel.department.name == 'monitor':
            return False, 'Новая панель уже на экране'

        new_panel.department = Department.objects.get(name='monitor')
        new_panel.save()
        cell.panel = new_panel

        PanelHistoryReport.objects.create(panel=cell.panel,
                                          description=f'⬇️ {cell.panel.display.description} {cell.position}',
                                          type_report='moving', time=current_time, user=user, comment=comment)
        DisplayHistoryReport.objects.create(display=cell.panel.display, slot=cell,
                                            description=f'⬇️ {cell.panel}',
                                            type_event='moving', time=current_time, user=user, comment=comment)
        cell.save()
    if current_panel_check:
        if new_panel_check:
            return True, f'Панель {panel.name}  заменена на панель {new_panel.name} в ячейке {cell.position}!'
        else:
            return True, f'Панель {panel.name} снята с ячейки {cell.position}!'
    elif new_panel_check:
        return True, f'Панель {new_panel} поставлена на ячейку {cell.position}!'
    else:
        return False, 'Ошибка в replace_panel_in_cell'
