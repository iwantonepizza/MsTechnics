from __future__ import annotations

from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.activity.models import ActivityLog
from apps.core.users.models import MsUser
from apps.workflow.applications.models import Application, ApplicationHistoryReport
from apps.workflow.daily_tasks.models import DailyTask
from apps.workflow.departures.models import Departure, DepartureHistoryReport
from main_menu.models import DailyTaskHistoryReport, DisplayHistoryReport, PanelHistoryReport
from zip.models import Display as LegacyDisplay
from zip.models import Panels as LegacyPanel

PANEL_EVENT_TYPE_MAP = {
    "moving": "panel.moved",
    "condition": "panel.condition_changed",
    "breakdown": "panel.breakdown",
    "service": "panel.service_note",
    "none_type": "panel.comment_added",
}

SOURCE_LABELS = {
    "panel": "panel_history",
    "display": "display_history",
    "application": "application_history",
    "departure": "departure_history",
    "daily": "daily_history",
}


@dataclass(frozen=True)
class BackfillSource:
    key: str
    label: str
    queryset: object


class Command(BaseCommand):
    help = "Backfill legacy history tables into activity_log."

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._content_type_cache: dict[type[object], ContentType] = {}

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=1000)
        parser.add_argument(
            "--source",
            choices=["panel", "display", "application", "departure", "daily", "all"],
            default="all",
        )

    def handle(self, *_args, **options) -> None:
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        source = options["source"]

        for item in self._select_sources(source):
            self._migrate_source(item, batch_size=batch_size, dry_run=dry_run)

    def _select_sources(self, source: str) -> list[BackfillSource]:
        source_map = {
            "panel": BackfillSource(
                key="panel",
                label=SOURCE_LABELS["panel"],
                queryset=PanelHistoryReport.objects.select_related("panel").order_by("id"),
            ),
            "display": BackfillSource(
                key="display",
                label=SOURCE_LABELS["display"],
                queryset=DisplayHistoryReport.objects.select_related("display", "slot").order_by("id"),
            ),
            "application": BackfillSource(
                key="application",
                label=SOURCE_LABELS["application"],
                queryset=ApplicationHistoryReport.objects.order_by("id"),
            ),
            "departure": BackfillSource(
                key="departure",
                label=SOURCE_LABELS["departure"],
                queryset=DepartureHistoryReport.objects.select_related("user").order_by("id"),
            ),
            "daily": BackfillSource(
                key="daily",
                label=SOURCE_LABELS["daily"],
                queryset=DailyTaskHistoryReport.objects.select_related("task").order_by("id"),
            ),
        }
        if source == "all":
            return list(source_map.values())
        return [source_map[source]]

    def _migrate_source(self, source: BackfillSource, *, batch_size: int, dry_run: bool) -> None:
        total = source.queryset.count()
        self.stdout.write(f"{source.label}: processing {total} rows")

        batch: list[ActivityLog] = []
        processed = 0

        for row in source.queryset.iterator(chunk_size=batch_size):
            entry = self._build_entry(source.key, source.label, row)
            if entry is not None:
                batch.append(entry)
            processed += 1

            if len(batch) >= batch_size:
                self._flush(batch, dry_run=dry_run)
                batch = []
                self.stdout.write(f"{source.label}: processed {processed}/{total}")

        if batch:
            self._flush(batch, dry_run=dry_run)

        suffix = "DRY RUN" if dry_run else "DONE"
        self.stdout.write(self.style.SUCCESS(f"{source.label}: processed {processed}/{total} [{suffix}]"))

    def _flush(self, batch: list[ActivityLog], *, dry_run: bool) -> None:
        if dry_run or not batch:
            return
        ActivityLog.objects.bulk_create(batch, ignore_conflicts=True)

    def _build_entry(self, source_key: str, source_label: str, row) -> ActivityLog | None:
        if source_key == "panel":
            return self._build_panel_entry(source_label, row)
        if source_key == "display":
            return self._build_display_entry(source_label, row)
        if source_key == "application":
            return self._build_application_entry(source_label, row)
        if source_key == "departure":
            return self._build_departure_entry(source_label, row)
        if source_key == "daily":
            return self._build_daily_entry(source_label, row)
        return None

    def _build_panel_entry(self, source_label: str, row: PanelHistoryReport) -> ActivityLog:
        target_ct = None
        target_id = None
        payload = {
            "legacy_type_report": row.type_report,
            "legacy_panel_name": getattr(row.panel, "name", None),
        }

        if row.panel_id:
            panel = LegacyPanel.objects.filter(name=row.panel_id).first()
            if panel is not None:
                target_ct = ContentType.objects.get_for_model(panel)
                target_id = panel.pk

        return self._make_entry(
            source_label=source_label,
            legacy_id=row.id,
            event_type=PANEL_EVENT_TYPE_MAP.get(row.type_report, "panel.comment_added"),
            target_ct=target_ct,
            target_id=target_id,
            actor_value=row.user,
            occurred_at=row.time,
            description=row.description,
            comment=row.comment,
            payload=payload,
        )

    def _build_display_entry(self, source_label: str, row: DisplayHistoryReport) -> ActivityLog:
        target_ct = None
        target_id = None
        payload = {
            "legacy_type_event": row.type_event,
            "legacy_slot_id": row.slot_id,
            "legacy_display_name": getattr(row.display, "name", None),
        }
        if row.slot_id:
            payload["cell_id"] = row.slot_id
            payload["cell_position"] = getattr(row.slot, "position", None)

        if row.display_id:
            display = LegacyDisplay.objects.filter(name=row.display_id).first()
            if display is not None:
                target_ct = ContentType.objects.get_for_model(display)
                target_id = display.pk

        return self._make_entry(
            source_label=source_label,
            legacy_id=row.id,
            event_type="display.panel_installed" if row.type_event == "moving" else "display.note",
            target_ct=target_ct,
            target_id=target_id,
            actor_value=row.user,
            occurred_at=row.time,
            description=row.description,
            comment=row.comment,
            payload=payload,
        )

    def _build_application_entry(self, source_label: str, row: ApplicationHistoryReport) -> ActivityLog:
        target_ct = None
        target_id = None
        payload = {"legacy_application_id": row.application_id}

        if row.application_id and str(row.application_id).isdigit():
            target_ct = self._get_content_type(Application)
            target_id = int(row.application_id)

        return self._make_entry(
            source_label=source_label,
            legacy_id=row.id,
            event_type=self._infer_application_event_type(row.description or ""),
            target_ct=target_ct,
            target_id=target_id,
            actor_value=row.user,
            occurred_at=row.time,
            description=row.description,
            comment=row.comment,
            payload=payload,
        )

    def _build_departure_entry(self, source_label: str, row: DepartureHistoryReport) -> ActivityLog:
        target_ct = None
        target_id = None
        payload = {"legacy_description": row.description or ""}

        if row.departure_id:
            target_ct = self._get_content_type(Departure)
            target_id = row.departure_id

        return self._make_entry(
            source_label=source_label,
            legacy_id=row.id,
            event_type=self._infer_departure_event_type(row.description or ""),
            target_ct=target_ct,
            target_id=target_id,
            actor_value=row.user,
            occurred_at=row.time,
            description=row.description,
            comment=row.comment,
            payload=payload,
        )

    def _build_daily_entry(self, source_label: str, row: DailyTaskHistoryReport) -> ActivityLog:
        target_ct = None
        target_id = None
        payload = {"legacy_result": row.result}

        if row.task_id:
            task = DailyTask.objects.filter(name=row.task_id).first()
            if task is not None:
                target_ct = ContentType.objects.get_for_model(task)
                target_id = task.pk

        event_type = "daily_task.reset" if self._looks_like_reset(row.result or "") else "daily_task.completed"
        return self._make_entry(
            source_label=source_label,
            legacy_id=row.id,
            event_type=event_type,
            target_ct=target_ct,
            target_id=target_id,
            actor_value=row.user,
            occurred_at=row.time,
            description=f"Результат daily task: {row.result or ''}".strip(),
            comment="",
            payload=payload,
        )

    def _make_entry(
        self,
        *,
        source_label: str,
        legacy_id: int,
        event_type: str,
        target_ct: ContentType | None,
        target_id: int | None,
        actor_value,
        occurred_at,
        description,
        comment,
        payload: dict,
    ) -> ActivityLog:
        actor, actor_name = self._resolve_actor(actor_value)
        return ActivityLog(
            actor=actor,
            actor_name=actor_name,
            target_type=target_ct,
            target_id=target_id,
            event_type=event_type,
            description=description or "",
            comment=comment or "",
            payload=payload,
            occurred_at=occurred_at or timezone.now(),
            legacy_source=source_label,
            legacy_id=legacy_id,
        )

    def _resolve_actor(self, actor_value) -> tuple[MsUser | None, str]:
        if actor_value is None:
            return None, "system"
        if isinstance(actor_value, MsUser):
            actor_name = f"{actor_value.first_name} {actor_value.last_name}".strip() or actor_value.username
            return actor_value, actor_name

        actor_name = str(actor_value).strip()
        if not actor_name:
            return None, "system"

        actor = MsUser.objects.filter(username=actor_name).first()
        return actor, actor_name

    def _get_content_type(self, model_class: type[object]) -> ContentType:
        cached = self._content_type_cache.get(model_class)
        if cached is None:
            cached = ContentType.objects.get_for_model(model_class)
            self._content_type_cache[model_class] = cached
        return cached

    def _infer_application_event_type(self, description: str) -> str:
        normalized = description.lower()
        if "создани" in normalized:
            return "application.created"
        if "удален" in normalized:
            return "application.deleted"
        if "исполнитель" in normalized:
            return "application.executor_changed"
        return "application.transitioned"

    def _infer_departure_event_type(self, description: str) -> str:
        normalized = description.lower()
        if "создан" in normalized:
            return "departure.created"
        if "соверш" in normalized or "выполн" in normalized:
            return "departure.completed"
        return "departure.archived"

    def _looks_like_reset(self, result: str) -> bool:
        normalized = result.lower()
        return "\u0441\u0431\u0440\u043e\u0441" in normalized or "reset" in normalized
