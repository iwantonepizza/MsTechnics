"""T-3-051: E2E тесты критичных путей API."""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _make_statuses():
    from tests.factories import ApplicationStatusFactory, ColorFactory, SmileFactory
    ColorFactory(name="gray", hex_color="#888888")
    ColorFactory(name="dark", hex_color="#222222")
    SmileFactory(smile_icon="📟")
    for n in ["sent_to_control", "apply_in_control",
              "sent_to_service", "work_in_service",
              "done", "archive_done", "archive_unable", "unable", "default"]:
        ApplicationStatusFactory(name=n)


def test_e2e_application_full_lifecycle():
    """Полный путь заявки: создание → переходы → архив."""
    from tests.factories import (
        MsUserFactory, ColorFactory, SmileFactory,
        CityFactory, ConditionFactory, DepartmentFactory,
        DisplayFactory, PanelFactory, CellFactory, ApplicationStatusFactory,
    )

    ColorFactory(name="white", hex_color="#ffffff")
    ColorFactory(name="black", hex_color="#000000")
    ColorFactory(name="blue",  hex_color="#0000ff")
    SmileFactory(smile_icon="🟢")
    SmileFactory(smile_icon="🔧")
    _make_statuses()

    city = CityFactory(name="e2e-city")
    ConditionFactory(name="work")
    ConditionFactory(name="error")
    DepartmentFactory(name="monitor")
    DepartmentFactory(name="service")
    DepartmentFactory(name="zip")

    display = DisplayFactory(name="e2e-display", city=city)
    panel = PanelFactory(name="P-E2E-01", display=display)
    cell = CellFactory(display=display, row=1, col=1, panel=panel)

    monitor = MsUserFactory(username="e2e_monitor", permission="monitoring")
    monitor.allowed_city.add(city)
    control = MsUserFactory(username="e2e_control", permission="control")
    control.allowed_city.add(city)
    service = MsUserFactory(username="e2e_service", permission="service")
    service.allowed_city.add(city)

    client = APIClient()

    # 1. Monitor создаёт заявку
    client.force_authenticate(user=monitor)
    resp = client.post("/api/v1/applications/", {
        "display_id": display.id, "panel_id": panel.id,
        "cell_id": cell.id, "comment": "Моргает E2E",
    }, format="json")
    assert resp.status_code == 201, resp.data
    app_id = resp.data["id"]
    assert resp.data["status"]["name"] == "sent_to_control"

    # 2. Control видит в received box
    client.force_authenticate(user=control)
    resp = client.get(f"/api/v1/applications/?display={display.slug}&box=received")
    assert resp.status_code == 200
    assert any(r["id"] == app_id for r in resp.data["results"])

    # 3. Control: sent_to_control → apply_in_control
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "apply_in_control", "comment": "принято"},
                       format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"]["name"] == "apply_in_control"

    # 4. Control → sent_to_service
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "sent_to_service", "comment": "в сервис"},
                       format="json")
    assert resp.status_code == 200

    # 5. Service берёт в работу
    client.force_authenticate(user=service)
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "work_in_service"}, format="json")
    assert resp.status_code == 200

    # 6. Service завершает
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "done", "comment": "починил"}, format="json")
    assert resp.status_code == 200

    # 7. Control архивирует
    client.force_authenticate(user=control)
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "archive_done"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"]["name"] == "archive_done"

    # 8. Events timeline
    resp = client.get(f"/api/v1/applications/{app_id}/events")
    assert resp.status_code == 200
    assert len(resp.data["results"]) >= 6


def test_e2e_invalid_transition_returns_409():
    from tests.factories import (
        MsUserFactory, ColorFactory, SmileFactory,
        CityFactory, ConditionFactory, DepartmentFactory,
        DisplayFactory, PanelFactory, CellFactory, ApplicationStatusFactory,
    )
    ColorFactory(name="gray2", hex_color="#777777")
    ColorFactory(name="dark2", hex_color="#333333")
    SmileFactory(smile_icon="⚠️")
    _make_statuses()
    city = CityFactory(name="city-409")
    ConditionFactory(name="work")
    DepartmentFactory(name="monitor")
    display = DisplayFactory(name="disp-409", city=city)
    panel = PanelFactory(name="P-409", display=display)
    cell = CellFactory(display=display, row=1, col=1, panel=panel)
    monitor = MsUserFactory(permission="monitoring")
    monitor.allowed_city.add(city)
    control = MsUserFactory(permission="control")
    control.allowed_city.add(city)
    client = APIClient()
    client.force_authenticate(user=monitor)
    resp = client.post("/api/v1/applications/", {
        "display_id": display.id, "panel_id": panel.id,
        "cell_id": cell.id, "comment": "test 409",
    }, format="json")
    assert resp.status_code == 201
    app_id = resp.data["id"]
    # sent_to_control → done НЕЛЬЗЯ
    client.force_authenticate(user=control)
    resp = client.post(f"/api/v1/applications/{app_id}/transition/",
                       {"target_state": "done", "comment": ""}, format="json")
    assert resp.status_code == 409
    assert resp.data["code"] == "invalid_state_transition"


def test_e2e_openapi_schema_valid():
    """OpenAPI schema должна быть валидной."""
    client = APIClient()
    response = client.get("/api/schema/")
    assert response.status_code == 200
