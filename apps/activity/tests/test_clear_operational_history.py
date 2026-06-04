from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.activity.models import ActivityLog
from apps.workflow.applications.models import ApplicationEvent, ApplicationHistoryReport
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
from zip.models import Display as LegacyDisplay
from zip.models import Panels as LegacyPanel

pytestmark = pytest.mark.django_db


def _create_history_rows():
    creator = MsUserFactory(username="thecreator", permission="admin")
    other_user = MsUserFactory(username="history-user", permission="service")
    city = CityFactory(name="history-clear-city")
    display = DisplayFactory(name="HISTORY-CLEAR", city=city)
    panel = PanelFactory(name="HISTORY-CLEAR-PANEL", display=display)
    cell = CellFactory(display=display, panel=panel, row=1, col=1)
    application = ApplicationFactory(display=display, panel=panel, cell=cell)
    departure = DepartureFactory()
    legacy_display = LegacyDisplay.objects.get(pk=display.pk)
    legacy_panel = LegacyPanel.objects.get(pk=panel.pk)
    task = DailyTask.objects.create(
        name="history-clear-task",
        description="history cleanup",
        city=city,
        link="https://example.test/history-clear",
    )

    ActivityLog.objects.create(actor=creator, actor_name=creator.username, event_type="system")
    ApplicationEvent.objects.create(
        application=application,
        stage="monitoring_create",
        actor=creator,
        actor_name=creator.username,
    )
    ApplicationHistoryReport.objects.create(
        application_id=str(application.pk),
        description="legacy app",
        comment="legacy",
        time=timezone.now(),
        user=creator.username,
    )
    DepartureHistoryReport.objects.create(
        departure=departure,
        description="legacy departure",
        comment="legacy",
        time=timezone.now(),
        user=creator,
    )
    PanelHistoryReport.objects.create(
        panel=legacy_panel,
        description="legacy panel",
        time=timezone.now(),
        user=creator.username,
    )
    DisplayHistoryReport.objects.create(
        display=legacy_display,
        slot=cell,
        description="legacy display",
        time=timezone.now(),
        user=creator.username,
    )
    DailyTaskHistoryReport.objects.create(
        task=task,
        user=creator.username,
        result="done",
        time=timezone.now(),
    )
    return creator, other_user, application, departure


def test_clear_operational_history_is_dry_run_by_default() -> None:
    _create_history_rows()
    stdout = StringIO()

    call_command("clear_operational_history", stdout=stdout)

    assert ActivityLog.objects.count() == 1
    assert ApplicationEvent.objects.count() == 1
    assert "DRY RUN" in stdout.getvalue()


def test_clear_operational_history_preserves_users_and_current_entities() -> None:
    creator, other_user, application, departure = _create_history_rows()

    call_command("clear_operational_history", apply=True)

    for model in (
        ActivityLog,
        ApplicationEvent,
        ApplicationHistoryReport,
        DepartureHistoryReport,
        PanelHistoryReport,
        DisplayHistoryReport,
        DailyTaskHistoryReport,
    ):
        assert model.objects.count() == 0
    assert type(creator).objects.filter(pk=creator.pk, username="thecreator").exists()
    assert type(other_user).objects.filter(pk=other_user.pk).exists()
    assert type(application).objects.filter(pk=application.pk).exists()
    assert type(departure).objects.filter(pk=departure.pk).exists()


def test_clear_operational_history_refuses_apply_without_preserved_user() -> None:
    ActivityLog.objects.create(actor_name="system", event_type="system")

    with pytest.raises(CommandError, match="does not exist"):
        call_command("clear_operational_history", apply=True)

    assert ActivityLog.objects.count() == 1
