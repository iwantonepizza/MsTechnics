from asgiref.sync import sync_to_async
import structlog

from apps.core.users.models import MsUser
from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.services import notification_dispatcher

logger = structlog.get_logger(__name__)


def get_workers(type_msg: str) -> list[MsUser]:
    workers = MsUser.objects.all()
    if type_msg == 'create_application':
        workers = workers.filter(permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'delete_application':
        workers = workers.filter(permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'daily':
        workers = workers.filter(permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'apply_application':
        workers = workers.filter(permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'manage_control':
        workers = workers.filter(permission__in=('admin', 'technical'))
    elif type_msg == 'departure':
        workers = workers.filter(permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    else:
        workers = workers.filter(permission__in=('admin',))
    return list(workers)


@sync_to_async
def dispatch_legacy_message(type_msg: str, text: str) -> int:
    template, _ = NotificationTemplate.objects.get_or_create(
        name="legacy_message",
        defaults={
            "description": "Compat-шаблон для legacy presend_filters",
            "text": "{text}",
        },
    )
    sent = 0
    for worker in get_workers(type_msg):
        notification = Notification.objects.create(
            template=template,
            recipient=worker,
            rendered_text=text,
            context={"type_msg": type_msg, "text": text},
        )
        notification_dispatcher.dispatch(notification)
        sent += 1
    return sent


async def presend_filters(type_msg: str, text: str) -> None:
    """Compat API для legacy-кода: отправляет через новый notification stack."""
    try:
        sent = await dispatch_legacy_message(type_msg, text)
        logger.info("legacy_presend_filters_dispatched", type_msg=type_msg, recipients=sent)
    except Exception:
        logger.exception("legacy_presend_filters_failed", type_msg=type_msg)
