from application.models import *
from main.models import Condition
from zip.models import *
from user.models import MsUser
from datetime import datetime

from django.db.models import Q


def create_application(display_name: str, panel: Panels, comment: str, time_event, user) -> bool:
    if panel.condition in ('work', 'unrecoverable'):
        return False
    created_application = Application.objects.create(display=Display.objects.get(name=display_name),
                                                     panel=panel,
                                                     status=ApplicationStatus.objects.get(
                                                         name='application_sent_to_control'),
                                                     comment_monitoring=comment, time_monitoring=time_event)
    panel.application_status = ApplicationStatus.objects.get(name='application_sent_to_control')
    panel.save()
    cell = Cell.objects.filter(panel=panel).first()
    send_tg_notification(text=f'Создана заявка c id - {created_application.id}\n'
                              f'------------------------ \n'
                              f'Время создания - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                              f'Экран - {created_application.display} {cell.position()}\n'
                              f'Панель - {created_application.panel}\n'
                              f'Статус - {created_application.status.description}\n'
                              f'Комментарий - {comment}\n'
                              f'Работник - {user.first_name} {user.last_name}\n',
                         type_msg='create_application'
                         )
    return True


def delete_application(app_id: str, user: MsUser, comment: str, time_event: datetime):
    app = Application.objects.get(pk=int(app_id))
    statuses = ApplicationStatus.objects.all()
    allowed_statuses = statuses.filter(
        name__in=['application_sent_to_control', 'archive']).values_list('name', flat=True)
    if app.status.name in allowed_statuses:
        cell = Cell.objects.filter(panel=app.panel).first()
        app.panel.application_status = statuses.filter(name='default').first()
        app.panel.save()
        saved_text = (f'Удалена заявка {app_id}\n'
                      f'Время удаления - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                      f' ------------------------ \n'
                      f'Экран - {app.display} {cell.position()}\n'
                      f'Панель - {app.panel}\n'
                      f'Статус перед удалением - {app.status.description}\n'
                      f'------------------------ \n'
                      f'Комментарии - {comment}\n'
                      f'------------------------ \n'
                      f'Работник - {user.first_name} {user.last_name}')
        app.delete()
        send_tg_notification(text=saved_text,
                             type_msg='delete_application'
                             )
        return True
    else:
        return False


# переделать потом это в квери запрос кастомный
def get_filter_application(display=None):
    application = Application.objects.all()
    if display:
        application = Application.objects.filter(display=display.name)
    return application


def apply_application(time_event: datetime, app_id: str, comment: str = None, target_department: str = None, user=None):
    application = Application.objects.get(pk=int(app_id))
    if application:
        department_dict = {'control_apply': {'new_status': 'application_apply_in_control',
                                             'panel_problem': 'error',
                                             'comment_name': 'comment_control',
                                             'history_message': 'Принята Контролем'},
                           'control_send': {'new_status': 'application_sent_to_service',
                                            'panel_problem': 'doesnt_change',
                                            'comment_name': 'comment_control',
                                            'history_message': 'Отправлено в Обслуживание'},
                           'service_apply': {'new_status': 'application_work_in_service',
                                             'panel_problem': 'doesnt_change',
                                             'comment_name': 'comment_service',
                                             'history_message': 'Принята в Обслуживание'},
                           'service_complete': {'new_status': 'done',
                                                'panel_problem': 'work',
                                                'comment_name': 'comment_service',
                                                'history_message': 'Ремонт выполнен'},
                           'service_unable': {'new_status': 'application_unable',
                                              'panel_problem': 'unrecoverable',
                                              'comment_name': 'comment_service',
                                              'history_message': 'Помечена как ремонт невозможен'},
                           'archive_done': {'new_status': 'archive_done',
                                            'panel_problem': 'doesnt_change',
                                            'comment_name': 'comment_service',
                                            'history_message': 'Добавлена в архив'},
                           'archive_unable': {'new_status': 'archive_unable',
                                              'panel_problem': 'doesnt_change',
                                              'comment_name': 'comment_service',
                                              'history_message': 'Добавлена в архив'}
                           }

        if department_dict[target_department]['comment_name'] == 'comment_control':
            application.comment_control = comment
            application.time_control = time_event

        elif department_dict[target_department]['comment_name'] == 'comment_service':
            application.comment_service = comment
            application.time_service = time_event

        application.status = ApplicationStatus.objects.get(name=department_dict[target_department]['new_status'])
        application.save()
        if department_dict[target_department]['panel_problem'] != 'doesnt_change':
            application.panel.condition = Condition.objects.get(
                name=department_dict[target_department]['panel_problem'])
        if application.status == 'archive_done' or application.status == 'archive_unable':
            application.panel.application_status = 'default'
        else:
            application.panel.application_status = application.status
        application.panel.save()
        cell = Cell.objects.filter(panel=application.panel).first()
        saved_text = (f'Обновление статуса заявки- id {application.id}:\n'
                      f'Время обновления - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                      f'{application.status.description}\n'
                      f'------------------------ \n'
                      f'Экран - {application.display} {cell.position()}\n'
                      f'Панель - {application.panel}\n'
                      f'Комментарии - {comment}\n'
                      f'Создатель - {user.first_name} {user.last_name}')

        send_tg_notification(text=saved_text,
                             type_msg='apply_application'
                             )
    return True


def get_display_application(display_name: str | None = None) -> list[str:Application.objects]:
    if display_name:
        applications_at_display = get_filter_application(Display.objects.get(name=display_name))
        return {'application_sent_to_control': applications_at_display.filter(status='application_sent_to_control'),
                'application_apply_in_control': applications_at_display.filter(
                    status='application_apply_in_control'),
                'application_sent_to_service': applications_at_display.filter(status='application_sent_to_service'),
                'application_work_in_service': applications_at_display.filter(status='application_work_in_service'),
                'done': applications_at_display.filter(status='done'),
                'application_unable': applications_at_display.filter(status='application_unable'),
                'archive': applications_at_display.filter(Q(status='archive_done') | Q(status='archive_unable')),
                'all': applications_at_display
                }
    else:
        return False
