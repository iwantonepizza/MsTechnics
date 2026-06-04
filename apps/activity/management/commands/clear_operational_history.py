from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

HISTORY_MODELS = (
    ("activity", "ActivityLog"),
    ("workflow_applications", "ApplicationEvent"),
    ("workflow_applications", "ApplicationHistoryReport"),
    ("workflow_departures", "DepartureHistoryReport"),
    ("main_menu", "PanelHistoryReport"),
    ("main_menu", "DisplayHistoryReport"),
    ("main_menu", "DailyTaskHistoryReport"),
)


class Command(BaseCommand):
    help = "Clear operational history tables. Default is dry-run; users and current entities stay intact."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply", action="store_true", help="Apply deletion. Default is dry-run."
        )
        parser.add_argument(
            "--preserve-username",
            default="thecreator",
            help="Username whose presence is verified before and after cleanup.",
        )

    def handle(self, *_args, **options) -> None:
        apply_changes = options["apply"]
        preserve_username = options["preserve_username"]
        user_model = get_user_model()
        user_count_before = user_model.objects.count()
        preserve_exists_before = user_model.objects.filter(username=preserve_username).exists()
        counts = {
            model_name: apps.get_model(app_label, model_name)._default_manager.count()
            for app_label, model_name in HISTORY_MODELS
        }

        for model_name, count in counts.items():
            self.stdout.write(f"{model_name}: {count}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING("DRY RUN: no rows deleted. Use --apply after backup.")
            )
            return
        if not preserve_exists_before:
            raise CommandError(
                f"Preserved user {preserve_username!r} does not exist; cleanup refused."
            )

        with transaction.atomic():
            for app_label, model_name in HISTORY_MODELS:
                apps.get_model(app_label, model_name)._default_manager.all().delete()

            user_count_after = user_model.objects.count()
            preserve_exists_after = user_model.objects.filter(username=preserve_username).exists()
            if user_count_after != user_count_before:
                raise CommandError(
                    "User count changed during history cleanup; transaction rolled back."
                )
            if preserve_exists_before and not preserve_exists_after:
                raise CommandError(
                    f"Preserved user {preserve_username!r} disappeared; transaction rolled back."
                )

        deleted = sum(counts.values())
        self.stdout.write(
            self.style.SUCCESS(
                f"APPLIED: deleted={deleted}; users={user_count_before}; "
                f"{preserve_username}={'present' if preserve_exists_after else 'not present before cleanup'}"
            )
        )
