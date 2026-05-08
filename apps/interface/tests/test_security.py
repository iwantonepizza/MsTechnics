"""T-3-fix-002: security regression tests."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_refs(db):
    from tests.factories import (
        ColorFactory, SmileFactory, CityFactory,
        ConditionFactory, DepartmentFactory, ApplicationStatusFactory,
    )
    ColorFactory(name="gray", hex_color="#888888")
    ColorFactory(name="dark", hex_color="#222222")
    SmileFactory(smile_icon="📟")
    CityFactory(name="sec-city")
    ConditionFactory(name="work")
    DepartmentFactory(name="monitor")
    for n in ["sent_to_control", "apply_in_control", "done", "archive_done",
              "unable", "default", "sent_to_service", "work_in_service", "archive_unable"]:
        ApplicationStatusFactory(name=n)


@pytest.fixture
def make_app(db, base_refs):
    def _make(status_name="sent_to_control", user_monitoring=None, minutes_ago=0):
        from tests.factories import (
            DisplayFactory, PanelFactory, CellFactory, ApplicationFactory,
            ApplicationStatusFactory, CityFactory,
        )
        from django.utils import timezone as tz
        from datetime import timedelta
        city = CityFactory(name=f"city-{status_name[:5]}")
        display = DisplayFactory(name=f"d-{id(status_name)}", city=city)
        panel = PanelFactory(name=f"P-SEC-{id(user_monitoring)}", display=display)
        cell = CellFactory(display=display, row=1, col=1, panel=panel)
        status = ApplicationStatusFactory(name=status_name) if False else \
            __import__("apps.workflow.applications.models", fromlist=["ApplicationStatus"]).ApplicationStatus.objects.get(name=status_name)
        from apps.workflow.applications.models import Application
        return Application.objects.create(
            display=display, panel=panel, cell=cell,
            status=status,
            user_monitoring=user_monitoring,
            time_monitoring=tz.now() - timedelta(minutes=minutes_ago),
            last_update_date_time=tz.now() - timedelta(minutes=minutes_ago),
        )
    return _make


# ── B3: destroy() whitelist ──────────────────────────────────────────────────

def test_destroy_blocked_when_creator_none_and_not_admin(db, base_refs, make_app):
    """Regression B3: creator=None + non-admin → 403, заявка НЕ удаляется."""
    from tests.factories import MsUserFactory
    from apps.workflow.applications.models import Application

    app = make_app(user_monitoring=None)
    user = MsUserFactory(username="mon_user", permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    resp = client.delete(f"/api/v1/applications/{app.id}/")

    assert resp.status_code in (403, 409), f"Expected 403 or 409, got {resp.status_code}"
    assert Application.objects.filter(id=app.id).exists(), "Заявка была удалена — это баг!"


def test_destroy_allowed_for_admin_when_creator_none(db, base_refs, make_app):
    """Admin может удалить даже когда creator=None."""
    from tests.factories import MsUserFactory
    from apps.workflow.applications.models import Application

    app = make_app(user_monitoring=None)
    admin = MsUserFactory(username="admin_sec", permission="admin")
    client = APIClient()
    client.force_authenticate(admin)

    resp = client.delete(f"/api/v1/applications/{app.id}/")

    assert resp.status_code == 204
    assert not Application.objects.filter(id=app.id).exists()


def test_destroy_allowed_for_creator(db, base_refs, make_app):
    """Создатель может удалить свою заявку в окне 5 минут."""
    from tests.factories import MsUserFactory
    from apps.workflow.applications.models import Application

    user = MsUserFactory(username="creator_user", permission="monitoring")
    app = make_app(user_monitoring="creator_user", minutes_ago=0)
    client = APIClient()
    client.force_authenticate(user)

    resp = client.delete(f"/api/v1/applications/{app.id}/")

    assert resp.status_code == 204
    assert not Application.objects.filter(id=app.id).exists()


def test_destroy_blocked_after_5_minutes(db, base_refs, make_app):
    """Окно 5 минут истекло → 409."""
    from tests.factories import MsUserFactory

    user = MsUserFactory(username="late_user", permission="monitoring")
    app = make_app(user_monitoring="late_user", minutes_ago=10)
    client = APIClient()
    client.force_authenticate(user)

    resp = client.delete(f"/api/v1/applications/{app.id}/")

    assert resp.status_code in (409, 400), f"Expected 409, got {resp.status_code}"
    assert resp.data["code"] == "delete_window_expired"


def test_destroy_blocked_wrong_status(db, base_refs, make_app):
    """Нельзя удалить заявку не в sent_to_control."""
    from tests.factories import MsUserFactory

    user = MsUserFactory(username="ctrl_user", permission="control")
    app = make_app(status_name="apply_in_control", user_monitoring="ctrl_user", minutes_ago=0)
    client = APIClient()
    client.force_authenticate(user)

    resp = client.delete(f"/api/v1/applications/{app.id}/")

    assert resp.status_code in (409, 400), f"Expected 409, got {resp.status_code}"
    assert resp.data["code"] == "delete_status_invalid"


def test_destroy_writes_activity_log(db, base_refs, make_app):
    """После удаления в ActivityLog должна быть запись."""
    from tests.factories import MsUserFactory
    from apps.activity.models import ActivityLog

    admin = MsUserFactory(permission="admin")
    app = make_app(user_monitoring=None)
    app_id = app.id
    client = APIClient()
    client.force_authenticate(admin)

    client.delete(f"/api/v1/applications/{app.id}/")

    # Запись в лог должна остаться даже после delete()
    assert ActivityLog.objects.filter(
        event_type="application.deleted",
    ).exists(), "ActivityLog запись не создана"


# ── B4: RefreshView rotation ─────────────────────────────────────────────────

def test_refresh_returns_new_access(db):
    """RefreshView возвращает новый access token."""
    from tests.factories import MsUserFactory

    user = MsUserFactory(username="refresh_test")
    user.set_password("testpass123")
    user.save()

    client = APIClient()
    login_resp = client.post(
        "/api/v1/auth/login/",
        {"username": "refresh_test", "password": "testpass123"},
        format="json",
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.data}"
    first_access = login_resp.data["access"]

    refresh_resp = client.post("/api/v1/auth/refresh/")
    assert refresh_resp.status_code == 200
    assert "access" in refresh_resp.data
    assert refresh_resp.data["access"] != first_access, "Access token не изменился"
