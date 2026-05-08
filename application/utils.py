import structlog

logger = structlog.get_logger(__name__)
from application.models import *
from zip.models import Display, Panels, Cell, Condition
from apps.core.users.models import MsUser
from datetime import datetime

from django.db.models import Q
from asgiref.sync import async_to_sync
from sorting_message import presend_filters

def create_application(panel: Panels, comment: str, time_event, user, file=None) -> bool:
    if panel.condition in ('work', 'unrecoverable'):
        return False
    cell = Cell.objects.get(panel=panel)
    created_application = Application.objects.create(display=panel.display,
                                                     panel=panel,
                                                     cell=cell,
                                                     status=ApplicationStatus.objects.get(
                                                         name='sent_to_control'),
                                                     comment_monitoring=comment, time_monitoring=time_event,
                                                     last_update_date_time=time_event, file_monitoring=file,
                                                     user_monitoring=f'{user.first_name} {user.last_name}')
    panel.application_status = ApplicationStatus.objects.get(name='sent_to_control')
    panel.save()
    logger.info(f'Создана заявка c id - {created_application.id}\n')
    async_to_sync(presend_filters)(text=f'Создана заявка c id - {created_application.id}\n'
                         f'------------------------ \n' 
                         f'Время создания - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                         f'Экран - {created_application.display} {cell.position}\n'
                         f'Панель - {created_application.panel}\n'
                         f'Статус - {created_application.status.description}\n'
                         f'Комментарий - {comment}\n'
                         f'Работник - {user.first_name} {user.last_name}\n',
                    type_msg='create_application'
                    )
    ApplicationHistoryReport.objects.create(application_id=created_application.id, description='Создание заявки',
                                            comment=comment, time=time_event, user=user)
    return True


def delete_application(app_id: str, user: MsUser, comment: str, time_event: datetime) -> bool:
    app = Application.objects.get(pk=int(app_id))
    statuses = ApplicationStatus.objects.all()
    allowed_statuses = statuses.filter(
        name__in=['sent_to_control', 'archive']).values_list('name', flat=True)
    if app.status.name in allowed_statuses:
        cell = Cell.objects.filter(panel=app.panel).first()
        app.panel.application_status = statuses.filter(name='default').first()
        app.panel.save()
        saved_text = (f'Удалена заявка {app_id}\n'
                      f'Время удаления - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                      f' ------------------------ \n'
                      f'Экран - {app.display} {cell.position}\n'
                      f'Панель - {app.panel}\n'
                      f'Статус перед удалением - {app.status.description}\n'
                      f'------------------------ \n'
                      f'Комментарии - {comment}\n'
                      f'------------------------ \n'
                      f'Работник - {user.first_name} {user.last_name}')
        app.delete()

        async_to_sync(presend_filters)(text=saved_text,
                        type_msg='delete_application'
                        )
        return True
    else:
        return False


# переделать потом это в квери запрос кастомный
def get_filter_application(display=None):
    if display:
        application = Application.objects.select_related('status', 'display', 'panel').filter(display=display.name)
    else:
        application = Application.objects.select_related('status', 'display', 'panel').all()
    return application.order_by('-last_update_date_time')


def apply_application(time_event: datetime, app_id: str, comment: str = None, target_department: str = None, user=None,
                      file=None):
    application = Application.objects.get(pk=int(app_id))
    if application:

        if target_department == 'control_apply':
            application.time_control_apply = application.last_update_date_time = time_event
            if comment:
                application.comment_control_apply = comment
            if file:
                application.file_control_apply = file
            if user:
                application.user_control_apply = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_apply = f'не передан'

            application.status = ApplicationStatus.objects.get(name='apply_in_control')
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Принята в контроле',
                                                    comment=comment, time=time_event, user=user)

            application.save()

            application.panel.condition = Condition.objects.get(name='error')
            application.panel.application_status = application.status
            application.panel.save()

        elif target_department == 'control_send':
            application.time_control_send = application.last_update_date_time = time_event
            if comment:
                application.comment_control_send = comment
            if file:
                application.file_control_send = file
            if user:
                application.user_control_send = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_send = f'не передан'

            application.status = ApplicationStatus.objects.get(name='sent_to_service')
            application.save()

            application.panel.application_status = application.status
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Отправлена в сервис',
                                                    comment=comment, time=time_event, user=user)

        elif target_department == 'service_apply':
            application.time_service_apply = application.last_update_date_time = time_event
            if comment:
                application.comment_service_apply = comment
            if file:
                application.file_service_apply = file
            if user:
                application.user_service_apply = f'{user.first_name} {user.last_name}'
            else:
                application.user_service_apply = f'не передан'

            application.status = ApplicationStatus.objects.get(name='work_in_service')
            application.save()

            application.panel.application_status = application.status
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Принята сервисом',
                                                    comment=comment, time=time_event, user=user)

        elif target_department == 'service_complete':
            application.time_control_at_work = application.last_update_date_time = time_event
            if comment:
                application.comment_control_at_work = comment
            if file:
                application.file_control_at_work = file
            if user:
                application.user_control_at_work = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_at_work = f'не передан'

            application.status = ApplicationStatus.objects.get(name='done')
            application.save()

            application.panel.condition = Condition.objects.get(name='work')
            application.panel.application_status = application.status
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Ремонт выполнен',
                                                    comment=comment, time=time_event, user=user)

        elif target_department == 'service_unable':
            application.time_control_unable = application.last_update_date_time = time_event
            if comment:
                application.comment_control_unable = comment
            if file:
                application.file_control_unable = file
            if user:
                application.user_control_unable = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_unable = f'не передан'

            application.status = ApplicationStatus.objects.get(name='unable')
            application.save()

            application.panel.application_status = application.status
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Ремонт невозможен',
                                                    comment=comment, time=time_event, user=user)

        elif target_department == 'archive_done':
            application.time_control_archive = application.last_update_date_time = time_event
            if comment:
                application.comment_control_archive = comment
            if file:
                application.file_control_archive = file
            if user:
                application.user_control_archive = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_archive = f'не передан'

            application.status = ApplicationStatus.objects.get(name='archive_done')
            application.save()

            application.panel.application_status = ApplicationStatus.objects.get(name='default')
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Отправлена в архив',
                                                    comment=comment, time=time_event, user=user)

        elif target_department == 'archive_unable':
            application.time_control_archive = application.last_update_date_time = time_event
            if comment:
                application.comment_control_archive = comment
            if file:
                application.file_control_archive = file
            if user:
                application.user_control_archive = f'{user.first_name} {user.last_name}'
            else:
                application.user_control_archive = f'не передан'

            application.status = ApplicationStatus.objects.get(name='archive_unable')
            application.save()

            application.panel.application_status = ApplicationStatus.objects.get(name='default')
            application.panel.save()
            ApplicationHistoryReport.objects.create(application_id=application.id, description='Отправлена в архив',
                                                    comment=comment, time=time_event, user=user)

        saved_text = (f'Обновление статуса заявки- id {application.id}:\n'
                      f'Время обновления - {datetime.strftime(time_event, '%d.%m.%Y %H:%M:%S ')}\n'
                      f'{application.status.description}\n'
                      f'------------------------ \n'
                      f'Экран - {application.display} {application.cell.position}\n'
                      f'Панель - {application.panel}\n'
                      f'Комментарии - {comment}\n'
                      f'Создатель - {user.first_name} {user.last_name}')

        async_to_sync(presend_filters)(text=saved_text,
                        type_msg='apply_application'
                        )
    return True


def get_display_application(display_name: str | None = None) -> list[str:Application.objects]:
    if display_name:
        applications_at_display = get_filter_application(Display.objects.get(name=display_name))
        return {'sent_to_control': applications_at_display.filter(status='sent_to_control'),
                'apply_in_control': applications_at_display.filter(
                    status='apply_in_control'),
                'sent_to_service': applications_at_display.filter(status='sent_to_service'),
                'work_in_service': applications_at_display.filter(status='work_in_service'),
                'done': applications_at_display.filter(status='done'),
                'unable': applications_at_display.filter(status='unable'),
                'archive': applications_at_display.filter(Q(status='archive_done') | Q(status='archive_unable')),
                'all': applications_at_display.exclude(status__in=('archive_done', 'archive_unable')),
                'all_new': applications_at_display,
                }
    else:
        return False
