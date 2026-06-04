import pytest
from rest_framework.test import APIClient

from tests.factories import CityFactory, DepartureFactory, MsUserFactory

pytestmark = pytest.mark.django_db


def test_departures_list_returns_results_for_authenticated_user() -> None:
    DepartureFactory()
    user = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/departures/")

    assert response.status_code == 200
    assert response.data["results"]


def test_departures_list_does_not_crash_for_city_restricted_user() -> None:
    DepartureFactory()
    city = CityFactory(name="departure-city")
    user = MsUserFactory(permission="service", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/departures/")

    assert response.status_code == 200
    assert response.data["results"]
