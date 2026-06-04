import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APIClient

from apps.activity.models import ActivityLog
from apps.activity.services import activity_logger
from apps.workflow.applications.models import ApplicationEvent, ApplicationHistoryReport
from main_menu.models import PanelHistoryReport
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
def panel_delete_refs():
    ColorFactory(name="gray", hex_color="#888888")
    ColorFactory(name="dark", hex_color="#222222")
    ColorFactory(name="white", hex_color="#ffffff")
    ColorFactory(name="black", hex_color="#000000")
    ColorFactory(name="blue", hex_color="#0000ff")
    SmileFactory(smile_icon="🟢")
    SmileFactory(smile_icon="📟")

    city = CityFactory(name="panel-delete-city")
    work = ConditionFactory(name="work")
    DepartmentFactory(name="monitor")
    DepartmentFactory(name="service")
    DepartmentFactory(name="zip")
    ApplicationStatusFactory(name="archive_done")
    ApplicationStatusFactory(name="sent_to_control")
    ApplicationStatusFactory(name="default")

    return {"city": city, "work": work}


def test_admin_delete_panel_cascades_archived_relations(panel_delete_refs):
    from apps.directory.panels.models import Panel
    from apps.workflow.applications.models import Application

    admin = MsUserFactory(username="panel-admin", permission="admin")
    display = DisplayFactory(name="panel-delete-display", city=panel_delete_refs["city"])
    panel = PanelFactory(
        name="P-DELETE-001",
        display=display,
        condition=panel_delete_refs["work"],
    )
    cell = CellFactory(display=display, row=1, col=1, panel=panel)
    application = ApplicationFactory(
        display=display,
        panel=panel,
        cell=cell,
        status=ApplicationStatusFactory(name="archive_done"),
    )
    ApplicationEvent.objects.create(
        application=application,
        stage="archive_done",
        comment="Архивная заявка",
        actor=admin,
        actor_name=admin.username,
        occurred_at=timezone.now(),
    )
    activity_logger.log(
        event_type="panel.comment_added",
        target=panel,
        actor=admin,
        description="Комментарий по панели",
    )
    activity_logger.log(
        event_type="application.transitioned",
        target=application,
        actor=admin,
        description="Архивная заявка завершена",
    )
    PanelHistoryReport.objects.create(
        panel_id=panel.name,
        description="legacy panel history",
        comment="legacy panel comment",
        type_report="service",
        time=timezone.now(),
        user=admin.username,
    )
    ApplicationHistoryReport.objects.create(
        application_id=str(application.id),
        description="legacy application history",
        comment="legacy application comment",
        time=timezone.now(),
        user=admin.username,
    )

    client = APIClient()
    client.force_authenticate(admin)

    response = client.delete(f"/api/v1/panels/{panel.id}/")

    panel_content_type = ContentType.objects.get_for_model(Panel)
    application_content_type = ContentType.objects.get_for_model(Application)

    assert response.status_code == 204
    assert not Panel.objects.filter(id=panel.id).exists()
    cell.refresh_from_db()
    assert cell.panel_id is None
    assert not Application.objects.filter(id=application.id).exists()
    assert not ApplicationEvent.objects.filter(application_id=application.id).exists()
    assert not PanelHistoryReport.objects.filter(panel_id=panel.name).exists()
    assert not ApplicationHistoryReport.objects.filter(application_id=str(application.id)).exists()
    assert not ActivityLog.objects.filter(
        target_type=panel_content_type,
        target_id=panel.id,
    ).exists()
    assert not ActivityLog.objects.filter(
        target_type=application_content_type,
        target_id=application.id,
    ).exists()
    assert ActivityLog.objects.filter(
        event_type="panel.deleted",
        target_id__isnull=True,
        description__contains=panel.name,
    ).exists()


def test_admin_delete_panel_is_blocked_when_active_application_exists(panel_delete_refs):
    from apps.directory.panels.models import Panel
    from apps.workflow.applications.models import Application

    admin = MsUserFactory(username="panel-admin-blocked", permission="admin")
    display = DisplayFactory(name="panel-delete-display-blocked", city=panel_delete_refs["city"])
    panel = PanelFactory(
        name="P-DELETE-002",
        display=display,
        condition=panel_delete_refs["work"],
    )
    cell = CellFactory(display=display, row=1, col=1, panel=panel)
    application = ApplicationFactory(
        display=display,
        panel=panel,
        cell=cell,
        status=ApplicationStatusFactory(name="sent_to_control"),
    )

    client = APIClient()
    client.force_authenticate(admin)

    response = client.delete(f"/api/v1/panels/{panel.id}/")

    assert response.status_code == 409
    assert response.data["code"] == "panel_has_active_application"
    assert Panel.objects.filter(id=panel.id).exists()
    assert Application.objects.filter(id=application.id).exists()
    cell.refresh_from_db()
    assert cell.panel_id == panel.id


def test_multi_role_admin_can_delete_panel(panel_delete_refs):
    from apps.core.users.models import Role
    from apps.directory.panels.models import Panel

    user = MsUserFactory(username="panel-delete-multi-role-admin", permission="service")
    user.roles.add(Role.objects.create(name="admin", description="Администратор"))
    display = DisplayFactory(
        name="panel-delete-display-multi-role-admin",
        city=panel_delete_refs["city"],
    )
    panel = PanelFactory(
        name="P-DEL-MRA",
        display=display,
        condition=panel_delete_refs["work"],
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.delete(f"/api/v1/panels/{panel.id}/")

    assert response.status_code == 204
    assert not Panel.objects.filter(id=panel.id).exists()


@pytest.mark.parametrize("permission", ["service", "all"])
def test_non_admin_cannot_delete_panel(panel_delete_refs, permission):
    from apps.directory.panels.models import Panel

    user = MsUserFactory(username=f"panel-delete-{permission}", permission=permission)
    display = DisplayFactory(
        name=f"panel-delete-display-{permission}",
        city=panel_delete_refs["city"],
    )
    panel = PanelFactory(
        name=f"P-DEL-{permission[:3].upper()}",
        display=display,
        condition=panel_delete_refs["work"],
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.delete(f"/api/v1/panels/{panel.id}/")

    assert response.status_code == 403
    assert Panel.objects.filter(id=panel.id).exists()
