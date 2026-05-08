from django.core.management.base import BaseCommand

from apps.notifications.triggers.daily import notify_overdue_daily_tasks


class Command(BaseCommand):
    help = "Checks overdue DailyTask rows and sends notifications"

    def handle(self, *args, **options):
        sent = notify_overdue_daily_tasks()
        self.stdout.write(self.style.SUCCESS(f"Daily task notifications sent: {sent}"))
