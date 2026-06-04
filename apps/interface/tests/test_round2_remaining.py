"""Tests for Round 2 remaining tasks: T-8-003, T-8-004, T-8-020, T-8-035, T-8-062, T-8-063."""

import pytest
from rest_framework.test import APIClient

from apps.activity.models import ActivityLog
from apps.directory.displays.models import DisplayNote
from apps.workflow.daily_tasks.models import DailyTask
from tests.factories import (
    ApplicationFactory,
    CellFactory,
    CityFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
)

pytestmark = pytest.mark.django_db


# --- T-8-003: display notes -------------------------------------------------


def test_display_notes_post_and_list() -> None:
    city = CityFactory(name="notes-city", slug="notes-city")
    display = DisplayFactory(name="notes-display", slug="notes-display", city=city)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    create = client.post(
        f"/api/v1/displays/{display.slug}/notes/",
        {"text": "Проверить блок питания"},
        format="json",
    )
    assert create.status_code == 201
    assert create.data["text"] == "Проверить блок питания"
    assert create.data["department"] == "monitoring"
    assert create.data["author_name"]

    listing = client.get(f"/api/v1/displays/{display.slug}/notes/")
    assert listing.status_code == 200
    assert len(listing.data) == 1
    assert DisplayNote.objects.filter(display=display).count() == 1
    assert ActivityLog.objects.filter(event_type="display.note_added").exists()


# ─── T-8-004: история панели / места ────────────────────────────────────────


def test_activity_panel_filter_returns_panel_and_application_events() -> None:
    city = CityFactory(name="hist-city", slug="hist-city")
    display = DisplayFactory(name="hist-display", slug="hist-display", city=city)
    panel = PanelFactory(name="HIST-PANEL", display=display)
    application = ApplicationFactory(display=display, panel=panel)
    admin = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(admin)

    ActivityLog.objects.create(
        target=panel, event_type="panel.condition_changed", description="cond"
    )
    ActivityLog.objects.create(
        target=application, event_type="application_transition", description="trans"
    )
    other_panel = PanelFactory(name="OTHER-PANEL", display=display)
    ActivityLog.objects.create(
        target=other_panel, event_type="panel.condition_changed", description="other"
    )

    res = client.get(f"/api/v1/activity-log/?panel={panel.id}")
    assert res.status_code == 200
    descriptions = {row["description"] for row in res.data["results"]}
    assert descriptions == {"cond", "trans"}


def test_activity_cell_filter_returns_place_events() -> None:
    city = CityFactory(name="place-city", slug="place-city")
    display = DisplayFactory(name="place-display", slug="place-display", city=city)
    cell = CellFactory(display=display)
    panel = cell.panel
    admin = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(admin)

    ActivityLog.objects.create(
        target=panel,
        event_type="panel.removed",
        description="removed-from-place",
        payload={"from_cell_id": cell.id},
    )
    ActivityLog.objects.create(
        target=panel, event_type="panel.condition_changed", description="not-place"
    )

    res = client.get(f"/api/v1/activity-log/?cell={cell.id}")
    assert res.status_code == 200
    descriptions = {row["description"] for row in res.data["results"]}
    assert descriptions == {"removed-from-place"}


# ─── T-8-062: набор типов событий ───────────────────────────────────────────


def test_activity_event_types_filter() -> None:
    city = CityFactory(name="types-city", slug="types-city")
    display = DisplayFactory(name="types-display", slug="types-display", city=city)
    panel = PanelFactory(name="TYPES-PANEL", display=display)
    admin = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(admin)

    ActivityLog.objects.create(target=panel, event_type="panel_move", description="move")
    ActivityLog.objects.create(
        target=panel, event_type="panel.condition_changed", description="cond"
    )

    res = client.get(f"/api/v1/activity-log/?panel={panel.id}&event_types=panel_move")
    assert res.status_code == 200
    descriptions = {row["description"] for row in res.data["results"]}
    assert descriptions == {"move"}


# ─── T-8-020: лента на главной / тумблер ────────────────────────────────────


def test_me_exposes_show_activity_feed() -> None:
    user = MsUserFactory(permission="monitoring", show_activity_feed=True)
    client = APIClient()
    client.force_authenticate(user)
    res = client.get("/api/v1/me")
    assert res.status_code == 200
    assert res.data["show_activity_feed"] is True


def test_activity_feed_requires_flag_for_non_admin() -> None:
    city = CityFactory(name="feed-city", slug="feed-city")
    display = DisplayFactory(name="feed-display", slug="feed-display", city=city)
    panel = PanelFactory(name="FEED-PANEL", display=display)
    ActivityLog.objects.create(target=panel, event_type="panel.condition_changed", description="x")

    no_flag = MsUserFactory(
        permission="monitoring", allowed_cities=[city], show_activity_feed=False
    )
    client = APIClient()
    client.force_authenticate(no_flag)
    assert client.get("/api/v1/activity-log/").data["results"] == []

    with_flag = MsUserFactory(
        username="feeduser", permission="monitoring", allowed_cities=[city], show_activity_feed=True
    )
    client.force_authenticate(with_flag)
    res = client.get("/api/v1/activity-log/")
    assert len(res.data["results"]) == 1


# ─── T-8-035: ежедневные задачи ─────────────────────────────────────────────


def _make_task(city, status="ready", name="task-1"):
    return DailyTask.objects.create(
        name=name, city=city, link="https://example.test/task", status=status
    )


def test_daily_tasks_list_filtered_by_city() -> None:
    city_a = CityFactory(name="dt-a", slug="dt-a")
    city_b = CityFactory(name="dt-b", slug="dt-b")
    _make_task(city_a, name="task-a")
    _make_task(city_b, name="task-b")
    user = MsUserFactory(permission="monitoring", allowed_cities=[city_a])
    client = APIClient()
    client.force_authenticate(user)

    res = client.get("/api/v1/daily-tasks/")
    assert res.status_code == 200
    names = {row["name"] for row in res.data["results"]}
    assert names == {"task-a"}


def test_daily_tasks_city_filter_cannot_bypass_allowed_cities() -> None:
    city_a = CityFactory(name="dt-allowed", slug="dt-allowed")
    city_b = CityFactory(name="dt-forbidden", slug="dt-forbidden")
    _make_task(city_a, name="task-allowed")
    _make_task(city_b, name="task-forbidden")
    user = MsUserFactory(permission="monitoring", allowed_cities=[city_a])
    client = APIClient()
    client.force_authenticate(user)

    res = client.get(f"/api/v1/daily-tasks/?city={city_b.id}")

    assert res.status_code == 200
    assert res.data["results"] == []


def test_daily_tasks_reject_invalid_city_filter() -> None:
    user = MsUserFactory(permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    res = client.get("/api/v1/daily-tasks/?city=not-a-number")

    assert res.status_code == 422
    assert "city" in res.data["errors"]


def test_daily_task_complete_by_monitoring() -> None:
    city = CityFactory(name="dt-complete", slug="dt-complete")
    task = _make_task(city, status="ready", name="task-c")
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    res = client.post(f"/api/v1/daily-tasks/{task.id}/complete/")
    assert res.status_code == 200
    assert res.data["status"] == "done"
    task.refresh_from_db()
    assert task.status == "done"
    assert ActivityLog.objects.filter(event_type="daily_task_complete").exists()


def test_daily_task_complete_forbidden_for_control() -> None:
    city = CityFactory(name="dt-control", slug="dt-control")
    task = _make_task(city, status="ready", name="task-d")
    user = MsUserFactory(permission="control", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    res = client.post(f"/api/v1/daily-tasks/{task.id}/complete/")
    assert res.status_code == 403
    task.refresh_from_db()
    assert task.status == "ready"


def test_daily_task_complete_rejected_when_not_available() -> None:
    city = CityFactory(name="dt-na", slug="dt-na")
    task = _make_task(city, status="not_ready", name="task-e")
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    res = client.post(f"/api/v1/daily-tasks/{task.id}/complete/")
    assert res.status_code == 422  # ValidationError → 422 в этом проекте
    task.refresh_from_db()
    assert task.status == "not_ready"
