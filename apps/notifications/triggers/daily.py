from __future__ import annotations

from django.utils import timezone

from apps.core.users.models import MsUser
from apps.notifications.models import Notification
from apps.notifications.triggers.utils import create_and_dispatch_notification


def notify_overdue_daily_tasks() -> int:
    try:
        from apps.workflow.daily_tasks.models import DailyTask
    except ImportError:
        return 0

    sent = 0
    tasks = DailyTask.objects.filter(status="undone", lost_notification_sent=True)
    recipients = MsUser.objects.filter(permission__in=["admin", "all", "control"]).distinct()
    for task in tasks:
        if _already_sent_today(task):
            continue
        context = {"task_name": task.name}
        for user in recipients:
            create_and_dispatch_notification(
                template_name="daily_task_overdue",
                recipient=user,
                context=context,
                target=task,
            )
            sent += 1
    return sent


def _already_sent_today(task) -> bool:
    return Notification.objects.filter(
        related_target_ct__model="dailytask",
        related_target_id=str(task.id),
        template__name="daily_task_overdue",
        created_at__date=timezone.localdate(),
    ).exists()
