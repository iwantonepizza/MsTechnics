import pytest
from rest_framework.test import APIClient

from apps.directory.storage.models import Wires
from tests.factories import (
    ApplicationFactory,
    ApplicationStatusFactory,
    CityFactory,
    DepartureFactory,
    DepartureStatusFactory,
    DisplayFactory,
    ExecutorFactory,
    MsUserFactory,
    PanelFactory,
)

pytestmark = pytest.mark.django_db


def test_search_requires_minimum_query_length() -> None:
    user = MsUserFactory(permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/search/", {"q": "a"})

    assert response.status_code == 400
    assert response.data["code"] == "search_query_too_short"


def test_search_returns_all_categories_with_matches() -> None:
    city = CityFactory(name="Ижевск", slug="izhevsk")
    display = DisplayFactory(name="RK-1", slug="rk-1", city=city, description="Экран RK-1")
    panel = PanelFactory(name="RK-1-PANEL", display=display, comment="Main rk panel")
    application_status = ApplicationStatusFactory(name="sent_to_service", description="В сервисе")
    application = ApplicationFactory(
        id=501,
        display=display,
        panel=panel,
        status=application_status,
        comment_monitoring="rk issue on top row",
    )
    departure_status = DepartureStatusFactory(name="created", description="Создан")
    departure = DepartureFactory(
        id=601,
        description="Trip for rk repair",
        status=departure_status,
        executor=ExecutorFactory(first_name="Ivan", last_name="Petrov"),
    )
    user_result = MsUserFactory(
        username="rk-admin",
        first_name="Rk",
        last_name="User",
        permission="admin",
    )
    Wires.objects.create(name="rk-wire", description="rk storage wire", count=2)
    admin = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get("/api/v1/search/", {"q": "rk", "limit": 5})

    assert response.status_code == 200
    assert response.data["displays"][0]["id"] == display.id
    assert response.data["panels"][0]["id"] == panel.id
    assert response.data["applications"][0]["id"] == application.id
    assert response.data["departures"][0]["id"] == departure.id
    assert response.data["users"][0]["id"] == user_result.id
    assert response.data["storage"][0]["name"] == "rk-wire"


def test_search_respects_allowed_cities_for_display_entities() -> None:
    allowed_city = CityFactory(name="Ижевск", slug="izhevsk")
    hidden_city = CityFactory(name="Казань", slug="kazan")
    visible_display = DisplayFactory(name="Visible RK", slug="visible-rk", city=allowed_city)
    hidden_display = DisplayFactory(name="Hidden RK", slug="hidden-rk", city=hidden_city)
    visible_panel = PanelFactory(name="VISIBLE-RK-PANEL", display=visible_display)
    hidden_panel = PanelFactory(name="HIDDEN-RK-PANEL", display=hidden_display)
    visible_status = ApplicationStatusFactory(name="apply_in_control", description="В контроле")
    hidden_status = ApplicationStatusFactory(name="work_in_service", description="В работе")
    visible_application = ApplicationFactory(
        display=visible_display,
        panel=visible_panel,
        status=visible_status,
        comment_monitoring="visible rk issue",
    )
    ApplicationFactory(
        display=hidden_display,
        panel=hidden_panel,
        status=hidden_status,
        comment_monitoring="hidden rk issue",
    )
    user = MsUserFactory(permission="monitoring", allowed_cities=[allowed_city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/search/", {"q": "rk"})

    assert response.status_code == 200
    assert {item["id"] for item in response.data["displays"]} == {visible_display.id}
    assert {item["id"] for item in response.data["panels"]} == {visible_panel.id}
    assert {item["id"] for item in response.data["applications"]} == {visible_application.id}


def test_search_hides_user_results_for_non_admin() -> None:
    MsUserFactory(username="visible-user", permission="service")
    user = MsUserFactory(permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/search/", {"q": "user"})

    assert response.status_code == 200
    assert response.data["users"] == []


def test_search_returns_empty_lists_when_no_matches() -> None:
    user = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/search/", {"q": "zz-no-match"})

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "displays",
        "panels",
        "applications",
        "departures",
        "users",
        "storage",
    }
    assert all(response.data[key] == [] for key in response.data)
