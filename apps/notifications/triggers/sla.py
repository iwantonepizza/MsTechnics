from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.core.users.models import MsUser
from apps.notifications.models import Notification
from apps.notifications.triggers.utils import create_and_dispatch_notification
from apps.workflow.applications.models import Application

ACTIVE_STATUSES = ("sent_to_control", "apply_in_control", "sent_to_service", "work_in_service")


def notify_overdue_applications(*, threshold_hours: int = 4) -> int:
    threshold = timezone.now() - timedelta(hours=threshold_hours)
    overdue = Application.objects.select_related("display", "display__city", "cell", "status").filter(
        status__name__in=ACTIVE_STATUSES,
        last_update_date_time__lt=threshold,
    )
    sent = 0
    for application in overdue:
        if _already_sent_today(application):
            continue
        city = getattr(application.display, "city", None)
        recipients = MsUser.objects.filter(permission__in=["control", "admin", "all"])
        if city:
            recipients = recipients.filter(Q(permission__in=["admin", "all"]) | Q(allowed_city=city))

        hours_overdue = int((timezone.now() - application.last_update_date_time).total_seconds() // 3600)
        context = {
            "application_id": application.id,
            "hours_overdue": hours_overdue,
            "current_status": application.status.name,
        }
        for user in recipients.distinct():
            create_and_dispatch_notification(
                template_name="application_sla_overdue",
                recipient=user,
                context=context,
                target=application,
            )
            sent += 1
    return sent


def _already_sent_today(application) -> bool:
    return Notification.objects.filter(
        related_target_ct__model="application",
        related_target_id=str(application.id),
        template__name="application_sla_overdue",
        created_at__date=timezone.localdate(),
    ).exists()
