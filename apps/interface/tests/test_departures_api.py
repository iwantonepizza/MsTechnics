import pytest
from rest_framework.test import APIClient

from tests.factories import DepartureFactory, MsUserFactory

pytestmark = pytest.mark.django_db


def test_departures_list_returns_results_for_authenticated_user() -> None:
    DepartureFactory()
    user = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/departures/")

    assert response.status_code == 200
    assert response.data["results"]
