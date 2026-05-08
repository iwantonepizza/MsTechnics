from django.core.management.base import BaseCommand

from apps.notifications.triggers.sla import notify_overdue_applications


class Command(BaseCommand):
    help = "Checks overdue applications and sends SLA notifications"

    def add_arguments(self, parser):
        parser.add_argument("--threshold-hours", type=int, default=4)

    def handle(self, *args, **options):
        sent = notify_overdue_applications(threshold_hours=options["threshold_hours"])
        self.stdout.write(self.style.SUCCESS(f"SLA notifications sent: {sent}"))
