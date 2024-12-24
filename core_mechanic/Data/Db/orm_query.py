from django.db.models import Q

from core_mechanic.get_time import get_time_setting_tz
from zip.models import *

from user.models import MsUser
from datetime import datetime
from main.models import Condition, Department
from main_menu.models import PanelHistoryReport, DailyTaskHistoryReport, DisplayHistoryReport


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
                                          description=f'Изменения состояния: {old_condition} -> {panel.condition.description}',
                                          comment=comment,
                                          type_report='condition', time=time_report, user=user)
        return True
    return False


def get_filter_panels(name_panel: str = None, name_display: str = None, free: bool = False):
    result = Panels.objects.all().select_related('condition__icon')
    if name_panel:
        result = result.filter(name=name_panel)
    if name_display:
        result = result.filter(display=name_display)
    if free:
        result = result.filter(department='zip')
    return result


def q_panels_change_department(user: MsUser, id_panel: str, new_department: str, comment: str,
                               description: str = f'описание не получено',
                               type_report: str = 'none_type'):
    panel = Panels.objects.select_related('department').filter(name__exact=id_panel).first()
    if panel.department.name == new_department:
        return
    new_department = Department.objects.get(name=new_department)
    panel.department = new_department
    panel.save()

    current_time = get_time_setting_tz()
    event = PanelHistoryReport.objects.create(panel=panel, description=description, comment=comment,
                                              type_report=type_report, time=current_time,
                                              user=f'{user.first_name} {user.last_name}')


def get_panel_history_report(id_panel: str = None, type_report: str = None, time_report: datetime = None,
                             worker: str = None):
    if not id_panel:
        panel = None
    else:
        try:
            panel = Panels.objects.get(name__exact=id_panel)
        except Panels.DoesNotExist:
            return None  # Если панель не найдена, возвращаем None
    if panel:
        # Получаем все записи PanelHistoryReport для этой панели
        result = PanelHistoryReport.objects.filter(panel_id=panel)
    else:
        result = PanelHistoryReport.objects.all()
    # Применяем дополнительные фильтры, если они переданы
    if type_report:
        result = result.filter(type_report=type_report)
    if time_report:
        result = result.filter(time__gte=time_report)
    if worker:
        result = result.filter(worker=worker)
    return result


def get_formated_panel_history_report(id_panel: str):
    panel_report_history = get_panel_history_report(id_panel=id_panel)
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


def get_display_at_city(city_name: str):
    return Display.objects.filter(city=city_name)


def get_today_daily(city_name: str):
    x = {'not_ready': '🔒',
         'ready': '🟢',
         'deadline': '🔥',
         'done': '✅',
         'undone': '❌'}

    result = []
    for task in DailyTask.objects.filter(city=city_name).order_by('start_time'):
        result.append({'id': task.id, 'name': task.name, 'description': task.description, 'status': task.status,
                       'is_ready': task.check_available_status(),
                       'smile': x[task.status], 'link': task.link})
    return result


def done_daily(id_daily, user, result) -> bool | None:
    task = DailyTask.objects.get(id=id_daily)
    current_datetime = get_time_setting_tz()
    if task.complete_task(current_datetime):
        DailyTaskHistoryReport.objects.create(task=task, user=user, result=result, time=current_datetime)
        return send_tg_notification(text=f'✅ {task.name} выполнен! ✅',
                                    type_msg='daily'
                                    ) == 200
    else:
        return None


def replace_panel_in_cell(cell: Cell, new_panel: Panels | None = None, user=None, comment: str | None = None) -> tuple:
    current_time = get_time_setting_tz()
    panel = cell.panel
    current_panel_check = None
    new_panel_check = None

    if panel:
        current_panel_check = True

        PanelHistoryReport.objects.create(panel=panel,
                                          description=f'снята с экрана - {panel.display.description}, место {cell.position()}',
                                          type_report='moving', time=current_time, user=user, comment=comment)
        DisplayHistoryReport.objects.create(display=panel.display, slot=cell,
                                            description=f'снята панель - {panel.name}, место {cell.position()}',
                                            type_event='moving', time=current_time, user=user, comment=comment)
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
                                          description=f'поставлена на экрана - {cell.panel.display.description}, место {cell.position()}',
                                          type_report='moving', time=current_time, user=user, comment=comment)
        DisplayHistoryReport.objects.create(display=cell.panel.display, slot=cell,
                                            description=f'поставлена панель - {cell.panel}, место {cell.position()}',
                                            type_event='moving', time=current_time, user=user, comment=comment)
        cell.save()
    if current_panel_check and new_panel_check:
        return True, f'Панель {panel.name}  заменена на панель {new_panel.name} в ячейке {cell.position()}!'
    elif current_panel_check:
        return True, f'Панель {panel.name} снята с ячейки {cell.position()}!'
    elif new_panel_check:
        return True, f'Панель {panel.name} поставлена на ячейку {cell.position()}!'
    else:
        return False, 'Ошибка в replace_panel_in_cell'


def remove_broken_panel_with_application(cell: Cell, comment: str | None = None, user=None):
    panel = cell.panel
    current_time = get_time_setting_tz()
    PanelHistoryReport.objects.create(panel=cell.panel,
                                      description=f'снята с экрана - {cell.panel.display}, место {cell.position()}',
                                      type_report='breakdown', time=current_time, user=user, comment=comment)

    DisplayHistoryReport.objects.create(display=cell.panel.display, slot=cell,
                                        description=f'снята панель - {cell.panel}, место {cell.position()}',
                                        type_event='moving', time=current_time, user=user, comment=comment)
    panel.department = Department.objects.get(name='service')
    panel.save()
    cell.panel = None
    cell.save()
