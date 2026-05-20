import pytest
from rest_framework.test import APIClient

from apps.workflow.departures.models import Contact
from tests.factories import CityFactory, DisplayFactory, MsUserFactory

pytestmark = pytest.mark.django_db


def test_display_actions_accept_router_slug_kwarg() -> None:
    city = CityFactory(name="Пермь", slug="perm")
    display = DisplayFactory(name="PRM-1", slug="prm-1", city=city)
    contact = Contact.objects.create(
        first_name="Иван",
        last_name="Петров",
        description="Электрик",
        phone_number="+79001234567",
    )
    contact.displays.add(display)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    contacts_response = client.get(f"/api/v1/displays/{display.slug}/contacts/")
    alarms_response = client.get(
        f"/api/v1/displays/{display.slug}/alarms/",
        {"resolved": "false", "limit": 50},
    )
    photos_response = client.get(f"/api/v1/displays/{display.slug}/photos/")

    assert contacts_response.status_code == 200
    assert contacts_response.data == [
        {
            "id": contact.id,
            "first_name": "Иван",
            "last_name": "Петров",
            "description": "Электрик",
            "phone_number": "+79001234567",
            "telegram_id": None,
        }
    ]
    assert alarms_response.status_code == 200
    assert alarms_response.data["results"] == []
    assert alarms_response.data["has_more"] is False
    assert photos_response.status_code == 200
    assert photos_response.data == []
