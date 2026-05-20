from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.activity.models import ActivityLog
from apps.workflow.applications.models import ApplicationHistoryReport
from apps.workflow.daily_tasks.models import DailyTask
from apps.workflow.departures.models import DepartureHistoryReport
from main_menu.models import DailyTaskHistoryReport, DisplayHistoryReport, PanelHistoryReport
from tests.factories import (
    ApplicationFactory,
    CellFactory,
    CityFactory,
    DepartureFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
)
from zip.models import DailyTask as LegacyDailyTask
from zip.models import Display as LegacyDisplay
from zip.models import Panels as LegacyPanel

pytestmark = pytest.mark.django_db


@pytest.fixture
def legacy_history_rows():
    actor = MsUserFactory(username="legacy-user", permission="admin")
    display = DisplayFactory(name="LEGACY-DISPLAY")
    panel = PanelFactory(name="LEGACY-PANEL", display=display)
    cell = CellFactory(display=display, panel=panel, row=1, col=1)
    application = ApplicationFactory(display=display, panel=panel, cell=cell)
    departure = DepartureFactory()
    city = CityFactory(name="legacy-city")
    task = DailyTask.objects.create(
        name="legacy-task",
        description="daily legacy task",
        city=city,
        status="done",
        link="https://example.test/daily",
    )

    legacy_display = LegacyDisplay.objects.get(pk=display.pk)
    legacy_panel = LegacyPanel.objects.get(pk=panel.pk)
    legacy_task = LegacyDailyTask.objects.get(pk=task.pk)

    panel_history = PanelHistoryReport.objects.create(
        panel=legacy_panel,
        description="legacy panel move",
        comment="legacy panel comment",
        type_report="moving",
        time=timezone.now(),
        user=actor.username,
    )
    DisplayHistoryReport.objects.create(
        display=legacy_display,
        slot=cell,
        description="Панель установлена",
        comment="legacy display comment",
        type_event="moving",
        time=timezone.now(),
        user=actor.username,
    )
    application_history = ApplicationHistoryReport.objects.create(
        application_id=str(application.id),
        description="Создание заявки",
        comment="legacy app comment",
        time=timezone.now(),
        user=actor.username,
    )
    departure_history = DepartureHistoryReport.objects.create(
        departure=departure,
        description="Выезд создан",
        comment="legacy departure comment",
        time=timezone.now(),
        user=actor,
    )
    daily_history = DailyTaskHistoryReport.objects.create(
        task=legacy_task,
        user=actor.username,
        result="Выполнено",
        time=timezone.now(),
    )

    return {
        "actor": actor,
        "panel": panel,
        "application": application,
        "departure": departure,
        "task": task,
        "panel_history": panel_history,
        "application_history": application_history,
        "departure_history": departure_history,
        "daily_history": daily_history,
    }


def test_backfill_activity_log_creates_entries_for_all_legacy_sources(legacy_history_rows):
    call_command("backfill_activity_log")

    assert ActivityLog.objects.filter(legacy_source="panel_history").count() == 1
    assert ActivityLog.objects.filter(legacy_source="display_history").count() == 1
    assert ActivityLog.objects.filter(legacy_source="application_history").count() == 1
    assert ActivityLog.objects.filter(legacy_source="departure_history").count() == 1
    assert ActivityLog.objects.filter(legacy_source="daily_history").count() == 1

    panel_entry = ActivityLog.objects.get(legacy_source="panel_history")
    assert panel_entry.event_type == "panel.moved"
    assert panel_entry.target_id == legacy_history_rows["panel"].id
    assert panel_entry.actor_name == legacy_history_rows["actor"].username

    application_entry = ActivityLog.objects.get(legacy_source="application_history")
    assert application_entry.event_type == "application.created"
    assert application_entry.target_id == legacy_history_rows["application"].id

    departure_entry = ActivityLog.objects.get(legacy_source="departure_history")
    assert departure_entry.event_type == "departure.created"
    assert departure_entry.target_id == legacy_history_rows["departure"].id

    daily_entry = ActivityLog.objects.get(legacy_source="daily_history")
    assert daily_entry.event_type == "daily_task.completed"
    assert daily_entry.target_id == legacy_history_rows["task"].id


def test_backfill_activity_log_is_idempotent(legacy_history_rows):
    call_command("backfill_activity_log")
    first_count = ActivityLog.objects.count()

    call_command("backfill_activity_log")

    assert ActivityLog.objects.count() == first_count


def test_backfill_activity_log_dry_run_does_not_create_entries(legacy_history_rows):
    call_command("backfill_activity_log", dry_run=True)

    assert ActivityLog.objects.count() == 0


def test_backfill_activity_log_can_limit_source(legacy_history_rows):
    call_command("backfill_activity_log", source="application")

    assert ActivityLog.objects.count() == 1
    assert ActivityLog.objects.get().legacy_source == "application_history"


def test_verify_activity_log_reports_ok_after_backfill(legacy_history_rows):
    call_command("backfill_activity_log")
    stdout = StringIO()

    call_command("verify_activity_log", stdout=stdout)

    output = stdout.getvalue()
    assert "panel_history: src=1 dst=1 [OK]" in output
    assert "display_history: src=1 dst=1 [OK]" in output
    assert "application_history: src=1 dst=1 [OK]" in output
    assert "departure_history: src=1 dst=1 [OK]" in output
    assert "daily_history: src=1 dst=1 [OK]" in output
