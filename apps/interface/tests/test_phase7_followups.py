import pytest
from rest_framework.test import APIClient

from tests.factories import (
    ApplicationFactory,
    ApplicationStatusFactory,
    CellFactory,
    CityFactory,
    ConditionFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
)

pytestmark = pytest.mark.django_db


def test_dashboard_recent_application_includes_display_city() -> None:
    city = CityFactory(name="Казань", slug="kazan")
    display = DisplayFactory(name="KZN-1", slug="kzn-1", city=city)
    panel = PanelFactory(name="KZN-PANEL-1", display=display)
    cell = CellFactory(display=display, panel=panel, row=1, col=1)
    status = ApplicationStatusFactory(name="sent_to_control", description="Отправлена в контроль")
    application = ApplicationFactory(
        display=display,
        panel=panel,
        cell=cell,
        status=status,
    )
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/dashboard/")

    assert response.status_code == 200
    recent_item = response.data["monitoring"]["recent"][0]
    assert recent_item["id"] == application.id
    assert recent_item["display"]["city"] == {"slug": "kazan", "name": "Казань"}


def test_display_list_includes_aggregated_condition() -> None:
    city = CityFactory(name="Ижевск", slug="izhevsk")
    display = DisplayFactory(name="IZH-1", slug="izh-1", city=city)
    work = ConditionFactory(name="work", description="Работает")
    error = ConditionFactory(name="error", description="Ошибка")
    healthy_panel = PanelFactory(name="IZH-PANEL-WORK", display=display, condition=work)
    broken_panel = PanelFactory(name="IZH-PANEL-ERROR", display=display, condition=error)
    CellFactory(display=display, panel=healthy_panel, row=1, col=1)
    CellFactory(display=display, panel=broken_panel, row=1, col=2)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/displays/", {"city": city.slug})

    assert response.status_code == 200
    display_payload = response.data["results"][0]
    assert display_payload["id"] == display.id
    assert display_payload["aggregated_condition"] is not None
    assert display_payload["aggregated_condition"]["id"] == error.id
    assert display_payload["aggregated_condition"]["name"] == error.name


def test_display_list_uses_condition_severity_not_condition_id() -> None:
    city = CityFactory(name="Пермь", slug="perm")
    display = DisplayFactory(name="PRM-1", slug="prm-1", city=city)
    unrecoverable = ConditionFactory(name="unrecoverable", description="Неремонтопригодна")
    work = ConditionFactory(name="work", description="Работает")
    severe_panel = PanelFactory(name="PRM-PANEL-BROKEN", display=display, condition=unrecoverable)
    healthy_panel = PanelFactory(name="PRM-PANEL-WORK", display=display, condition=work)
    CellFactory(display=display, panel=severe_panel, row=1, col=1)
    CellFactory(display=display, panel=healthy_panel, row=1, col=2)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/displays/", {"city": city.slug})

    assert response.status_code == 200
    display_payload = response.data["results"][0]
    assert display_payload["aggregated_condition"] is not None
    assert display_payload["aggregated_condition"]["id"] == unrecoverable.id
    assert display_payload["aggregated_condition"]["name"] == unrecoverable.name
