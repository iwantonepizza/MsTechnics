import datetime

from django.core.management.base import BaseCommand

from apps.notifications.triggers.daily import notify_overdue_daily_tasks
from apps.workflow.daily_tasks.models import DailyTask
from get_time import get_time_setting_tz


class Command(BaseCommand):
    help = "Updates DailyTask statuses and sends overdue notifications"

    def handle(self, *args, **options):
        current_datetime = get_time_setting_tz()
        updated = 0

        for task in DailyTask.objects.all().iterator():
            before = (
                task.status,
                task.notified_stages,
                task.alert_notification_sent,
                task.deadline_notification_sent,
                task.lost_notification_sent,
                task.start_notification_sent,
                task.completed_notification_sent,
            )
            task.check_iteration(current_datetime)
            task.refresh_from_db()
            after = (
                task.status,
                task.notified_stages,
                task.alert_notification_sent,
                task.deadline_notification_sent,
                task.lost_notification_sent,
                task.start_notification_sent,
                task.completed_notification_sent,
            )
            if after != before:
                updated += 1

        if current_datetime.time() > datetime.time(23, 58, 59):
            for task in DailyTask.objects.all().iterator():
                task.reset_task()
                updated += 1

        sent = notify_overdue_daily_tasks()
        self.stdout.write(
            self.style.SUCCESS(f"Daily tasks updated: {updated}; notifications sent: {sent}")
        )
