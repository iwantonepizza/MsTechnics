from __future__ import annotations

import structlog

from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.services import notification_dispatcher

logger = structlog.get_logger(__name__)


def create_and_dispatch_notification(*, template_name: str, recipient, context: dict, target=None):
    try:
        template = NotificationTemplate.objects.get(name=template_name)
    except NotificationTemplate.DoesNotExist:
        logger.warning("notification_template_missing", template=template_name)
        return None

    try:
        rendered_text = template.text.format(**context)
    except KeyError as exc:
        logger.warning("notification_context_missing_key", template=template_name, key=str(exc))
        return None

    notification = Notification.objects.create(
        template=template,
        recipient=recipient,
        rendered_text=rendered_text,
        context=context,
        related_target=target,
    )
    try:
        notification_dispatcher.dispatch(notification)
    except Exception:
        logger.exception("notification_dispatch_failed", notification_id=notification.id)
    return notification
