import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationTemplate
from tests.factories import (
    ApplicationFactory,
    CellFactory,
    CityFactory,
    DepartureFactory,
    DisplayFactory,
    MsUserFactory,
    PanelFactory,
)

pytestmark = pytest.mark.django_db


def test_notifications_inbox_includes_deep_links_for_supported_targets() -> None:
    user = MsUserFactory(permission="service")
    city = CityFactory(name="Казань", slug="kazan")
    display = DisplayFactory(name="KZN-1", slug="kzn-1", city=city)
    panel = PanelFactory(name="KZN-PANEL-1", display=display)
    cell = CellFactory(display=display, panel=panel, row=1, col=1)
    application = ApplicationFactory(display=display, panel=panel, cell=cell)
    departure = DepartureFactory()
    template = NotificationTemplate.objects.create(name="bell-link", text="Bell {id}")

    Notification.objects.create(
        template=template,
        recipient=user,
        rendered_text="Application",
        related_target_ct=ContentType.objects.get_for_model(application),
        related_target_id=str(application.id),
        status=Notification.Status.SENT,
        delivered_via="tg",
    )
    Notification.objects.create(
        template=template,
        recipient=user,
        rendered_text="Departure",
        related_target_ct=ContentType.objects.get_for_model(departure),
        related_target_id=str(departure.id),
        status=Notification.Status.SENT,
        delivered_via="max",
    )
    Notification.objects.create(
        template=template,
        recipient=user,
        rendered_text="Panel",
        related_target_ct=ContentType.objects.get_for_model(panel),
        related_target_id=str(panel.id),
        status=Notification.Status.PENDING,
        delivered_via="tg",
    )

    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/notifications/inbox/", {"limit": 10})

    assert response.status_code == 200
    by_kind = {item["target_kind"]: item for item in response.data["results"]}
    assert (
        by_kind["application"]["deep_link_path"] == f"/service/kazan/kzn-1?app_id={application.id}"
    )
    assert by_kind["departure"]["deep_link_path"] == f"/departures?departure_id={departure.id}"
    assert by_kind["panel"]["deep_link_path"] == f"/zip/kzn-1?panel_id={panel.id}"
