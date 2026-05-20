import pytest
from rest_framework.test import APIClient

from apps.activity.models import ActivityLog
from apps.directory.panels.services import panel_mover
from tests.factories import (
    ApplicationFactory,
    ApplicationStatusFactory,
    CellFactory,
    CityFactory,
    ColorFactory,
    ConditionFactory,
    DepartmentFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
    SmileFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_refs():
    ColorFactory(name="gray", hex_color="#888888")
    ColorFactory(name="dark", hex_color="#222222")
    ColorFactory(name="white", hex_color="#ffffff")
    ColorFactory(name="black", hex_color="#000000")
    ColorFactory(name="blue", hex_color="#0000ff")
    SmileFactory(smile_icon="🟢")
    SmileFactory(smile_icon="📟")
    SmileFactory(smile_icon="🔧")

    city = CityFactory(name="remove-city")
    work = ConditionFactory(name="work")
    error = ConditionFactory(name="error")
    DepartmentFactory(name="monitor")
    DepartmentFactory(name="service")
    DepartmentFactory(name="zip")
    DepartmentFactory(name="hand")
    ApplicationStatusFactory(name="work_in_service")
    ApplicationStatusFactory(name="sent_to_control")
    ApplicationStatusFactory(name="default")

    return {
        "city": city,
        "work": work,
        "error": error,
    }


@pytest.fixture
def installed_panel(base_refs):
    display = DisplayFactory(name="remove-display", city=base_refs["city"])
    panel = PanelFactory(name="REMOVE-PANEL-1", display=display, condition=base_refs["work"])
    cell = CellFactory(display=display, row=1, col=1, panel=panel)
    return panel, cell


def test_remove_from_cell_updates_condition_when_application_context_present(
    base_refs, installed_panel
):
    panel, cell = installed_panel
    actor = MsUserFactory(username="svc-remove", permission="service")
    application = ApplicationFactory(
        display=cell.display,
        panel=panel,
        cell=cell,
        status=ApplicationStatusFactory(name="work_in_service"),
    )

    panel_mover.remove_from_cell(
        panel=panel,
        actor=actor,
        new_condition=base_refs["error"],
        comment="Сильное мерцание",
        application=application,
    )

    panel.refresh_from_db()
    cell.refresh_from_db()
    activity = ActivityLog.objects.filter(event_type="panel.removed", target_id=panel.id).latest(
        "id"
    )

    assert cell.panel_id is None
    assert panel.department.name == "service"
    assert panel.condition.name == "error"
    assert activity.payload["via_application_id"] == application.id
    assert activity.payload["new_condition"] == "error"


def test_remove_from_cell_keeps_condition_without_application_context(base_refs, installed_panel):
    panel, cell = installed_panel
    actor = MsUserFactory(username="svc-remove-2", permission="service")

    panel_mover.remove_from_cell(
        panel=panel,
        actor=actor,
        comment="Плановое снятие",
    )

    panel.refresh_from_db()
    cell.refresh_from_db()
    activity = ActivityLog.objects.filter(event_type="panel.removed", target_id=panel.id).latest(
        "id"
    )

    assert cell.panel_id is None
    assert panel.department.name == "service"
    assert panel.condition.name == "work"
    assert activity.payload["via_application_id"] is None
    assert activity.payload["new_condition"] is None


def test_remove_endpoint_returns_400_for_unknown_condition(base_refs, installed_panel):
    panel, _cell = installed_panel
    actor = MsUserFactory(username="svc-remove-api", permission="service")
    client = APIClient()
    client.force_authenticate(actor)

    response = client.post(
        f"/api/v1/panels/{panel.id}/remove/",
        {"new_condition": "missing-condition", "comment": "bad"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "invalid_condition"
