from django.core.management.base import BaseCommand, CommandError

from apps.activity.models import ActivityLog
from apps.workflow.applications.models import ApplicationHistoryReport
from apps.workflow.departures.models import DepartureHistoryReport
from main_menu.models import DailyTaskHistoryReport, DisplayHistoryReport, PanelHistoryReport

SOURCE_MODELS = [
    ("panel_history", PanelHistoryReport),
    ("display_history", DisplayHistoryReport),
    ("application_history", ApplicationHistoryReport),
    ("departure_history", DepartureHistoryReport),
    ("daily_history", DailyTaskHistoryReport),
]


class Command(BaseCommand):
    help = "Verify counts between legacy history tables and activity_log backfill."

    def handle(self, *_args, **_options) -> None:
        mismatches: list[str] = []

        for label, model in SOURCE_MODELS:
            src_count = model.objects.count()
            dst_count = ActivityLog.objects.filter(legacy_source=label).count()
            status = "OK" if src_count == dst_count else "MISMATCH"
            if status != "OK":
                mismatches.append(label)
            self.stdout.write(f"{label}: src={src_count} dst={dst_count} [{status}]")

        if mismatches:
            raise CommandError(f"ActivityLog backfill mismatches: {', '.join(mismatches)}")
