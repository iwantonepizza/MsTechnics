from datetime import timedelta

import structlog
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.integrations.gmail_alarms.models import AlarmEvent
from apps.notifications.models import Notification
from apps.notifications.triggers.utils import create_and_dispatch_notification

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Notify monitoring users about unresolved VNNOX faulty alarms."

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold-minutes",
            type=int,
            default=settings.VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES,
        )

    def handle(self, *args, **options):
        threshold_minutes = options["threshold_minutes"]
        threshold_time = timezone.now() - timedelta(minutes=threshold_minutes)
        content_type = ContentType.objects.get_for_model(AlarmEvent)
        alarms = (
            AlarmEvent.objects.filter(
                type=AlarmEvent.Type.FAULTY,
                resolved_at__isnull=True,
                occurred_at__lt=threshold_time,
                display__isnull=False,
            )
            .select_related("display__city", "cell")
            .order_by("occurred_at")
        )

        notified = 0
        for alarm in alarms:
            if Notification.objects.filter(
                related_target_ct=content_type,
                related_target_id=str(alarm.id),
                template__name="vnnox_alarm_unresolved",
            ).exists():
                continue
            for user in _monitoring_recipients(alarm):
                create_and_dispatch_notification(
                    template_name="vnnox_alarm_unresolved",
                    recipient=user,
                    context=_notification_context(alarm),
                    target=alarm,
                )
                notified += 1

        logger.info("vnnox_unresolved_alarm_check_finished", alarms=alarms.count(), notified=notified)
        self.stdout.write(f"Checked {alarms.count()} alarms, sent {notified} notifications")


def _monitoring_recipients(alarm: AlarmEvent):
    from apps.core.users.models import MsUser
    from apps.core.users.permissions import role_membership_q

    return (
        MsUser.objects.filter(role_membership_q("monitoring", "admin"))
        .filter(allowed_city=alarm.display.city)
        .distinct()
        .order_by("id")
    )


def _notification_context(alarm: AlarmEvent) -> dict:
    minutes = int((timezone.now() - alarm.occurred_at).total_seconds() // 60)
    return {
        "minutes": minutes,
        "display_description": alarm.display.description or alarm.display.name,
        "cell_position": alarm.cell.position if alarm.cell else str(alarm.receiving_card_no).zfill(2),
        "raw_position": alarm.raw_position,
    }
