import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.directory.displays.models import PhotoDisplay
from apps.workflow.departures.models import Contact
from tests.factories import (
    ApplicationFactory,
    CellFactory,
    CityFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
)

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


def test_display_detail_does_not_expose_missing_media_urls() -> None:
    city = CityFactory(name="city-missing-media", slug="city-missing-media")
    display = DisplayFactory(
        name="display-missing-media",
        slug="display-missing-media",
        city=city,
        file="files/missing-schematic.pdf",
        project_photo="files/missing-project.pdf",
    )
    photo = PhotoDisplay.objects.create(display=display, image="photos/display_photos/missing.jpg")
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(f"/api/v1/displays/{display.slug}/")

    assert response.status_code == 200
    assert response.data["file_url"] is None
    assert response.data["project_photo_url"] is None
    assert len(response.data["photos"]) == 1
    assert response.data["photos"][0]["id"] == photo.id
    assert response.data["photos"][0]["url"] is None


def test_display_list_includes_application_count() -> None:
    city = CityFactory(name="city-app-count", slug="city-app-count")
    display = DisplayFactory(name="display-app-count", slug="display-app-count", city=city)
    panel = PanelFactory(name="display-app-count-panel", display=display)
    cell = CellFactory(display=display, panel=panel, row=1, col=1)
    ApplicationFactory(display=display, panel=panel, cell=cell)
    ApplicationFactory(display=display, panel=panel, cell=cell)
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/displays/")

    assert response.status_code == 200
    assert response.data["results"][0]["application_count"] == 2


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


def test_service_can_upload_display_asset() -> None:
    city = CityFactory(name="city-asset-upload", slug="city-asset-upload")
    display = DisplayFactory(name="display-asset-upload", slug="display-asset-upload", city=city)
    user = MsUserFactory(permission="service", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/displays/{display.slug}/assets/schematic/",
        {
            "file": SimpleUploadedFile(
                "schematic.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            )
        },
        format="multipart",
    )

    assert response.status_code == 200
    display.refresh_from_db()
    assert display.file.name.startswith("files/schematic")
    assert display.file.name.endswith(".pdf")
    assert response.data["url"].endswith(".pdf")


def test_monitoring_cannot_upload_display_asset() -> None:
    city = CityFactory(name="city-asset-forbidden", slug="city-asset-forbidden")
    display = DisplayFactory(
        name="display-asset-forbidden", slug="display-asset-forbidden", city=city
    )
    user = MsUserFactory(permission="monitoring", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/displays/{display.slug}/assets/project/",
        {
            "file": SimpleUploadedFile(
                "project.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            )
        },
        format="multipart",
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("case_id", "name", "content", "content_type"),
    [
        ("pdf", "fake.pdf", b"not a pdf", "application/pdf"),
        ("image", "fake.png", b"not an image", "image/png"),
    ],
)
def test_display_asset_upload_rejects_invalid_file_content(
    case_id: str,
    name: str,
    content: bytes,
    content_type: str,
) -> None:
    city = CityFactory(name=f"city-invalid-{case_id}", slug=f"city-invalid-{case_id}")
    display = DisplayFactory(
        name=f"display-invalid-{case_id}",
        slug=f"display-invalid-{case_id}",
        city=city,
    )
    user = MsUserFactory(permission="service", allowed_cities=[city])
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/displays/{display.slug}/assets/project/",
        {"file": SimpleUploadedFile(name, content, content_type=content_type)},
        format="multipart",
    )

    assert response.status_code == 422
    assert not display.project_photo


def test_display_photo_create_forbidden_for_monitoring() -> None:
    city = CityFactory(name="city-photo-forbidden", slug="city-photo-forbidden")
    display = DisplayFactory(
        name="display-photo-forbidden", slug="display-photo-forbidden", city=city
    )
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
