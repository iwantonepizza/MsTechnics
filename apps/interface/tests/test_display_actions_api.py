import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.directory.displays.models import PhotoDisplay
from apps.workflow.departures.models import Contact
from tests.factories import CityFactory, DisplayFactory, MsUserFactory

pytestmark = pytest.mark.django_db


GIF_1X1 = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def test_display_actions_accept_router_slug_kwarg() -> None:
    city = CityFactory(name="city-contacts", slug="city-contacts")
    display = DisplayFactory(name="display-contacts", slug="display-contacts", city=city)
    contact = Contact.objects.create(
        first_name="Ivan",
        last_name="Petrov",
        description="Electrician",
        phone_number="+70000000001",
        telegram_id="123456",
    )
    contact.displays.add(display)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    contacts_response = client.get(f"/api/v1/displays/{display.slug}/contacts/")
    alarms_response = client.get(f"/api/v1/displays/{display.slug}/alarms/")
    photos_response = client.get(f"/api/v1/displays/{display.slug}/photos/")

    assert contacts_response.status_code == 200
    assert contacts_response.data[0]["id"] == contact.id
    assert alarms_response.status_code == 200
    assert alarms_response.data["results"] == []
    assert photos_response.status_code == 200
    assert photos_response.data == []


def test_display_detail_contains_contacts_photos_and_camera_link() -> None:
    city = CityFactory(name="city-detail", slug="city-detail")
    display = DisplayFactory(
        name="display-detail",
        slug="display-detail",
        city=city,
        camera_link="https://camera.example.test/embed",
    )
    contact = Contact.objects.create(
        first_name="Anna",
        last_name="Sidorova",
        description="Guard",
        phone_number="+70000000002",
        telegram_id="987654",
    )
    contact.displays.add(display)
    photo = PhotoDisplay.objects.create(
        display=display,
        image=SimpleUploadedFile("display.gif", GIF_1X1, content_type="image/gif"),
    )
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(f"/api/v1/displays/{display.slug}/")

    assert response.status_code == 200
    assert response.data["camera_link"] == "https://camera.example.test/embed"
    assert response.data["contacts"] == [
        {
            "id": contact.id,
            "full_name": "Anna Sidorova",
            "description": "Guard",
            "phone": "+70000000002",
            "telegram_id": "987654",
        }
    ]
    assert len(response.data["photos"]) == 1
    assert response.data["photos"][0]["id"] == photo.id
    assert response.data["photos"][0]["url"].endswith(".gif")


def test_display_photo_crud_uses_task_routes() -> None:
    city = CityFactory(name="city-photo-crud", slug="city-photo-crud")
    display = DisplayFactory(name="display-photo-crud", slug="display-photo-crud", city=city)
    user = MsUserFactory(permission="service", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    create_response = client.post(
        f"/api/v1/displays/{display.slug}/photos/",
        {"file": SimpleUploadedFile("upload.gif", GIF_1X1, content_type="image/gif")},
        format="multipart",
    )

    assert create_response.status_code == 201
    photo_id = create_response.data["id"]

    list_response = client.get(f"/api/v1/displays/{display.slug}/photos/")

    assert list_response.status_code == 200
    assert [photo["id"] for photo in list_response.data] == [photo_id]

    delete_response = client.delete(f"/api/v1/displays/{display.slug}/photos/{photo_id}/")

    assert delete_response.status_code == 204
    assert not PhotoDisplay.objects.filter(id=photo_id).exists()


def test_display_photo_create_forbidden_for_monitoring() -> None:
    city = CityFactory(name="city-photo-forbidden", slug="city-photo-forbidden")
    display = DisplayFactory(name="display-photo-forbidden", slug="display-photo-forbidden", city=city)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/displays/{display.slug}/photos/",
        {"file": SimpleUploadedFile("forbidden.gif", GIF_1X1, content_type="image/gif")},
        format="multipart",
    )

    assert response.status_code == 403
    assert not PhotoDisplay.objects.filter(display=display).exists()
