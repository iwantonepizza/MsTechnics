"""
tests/test_fsm.py — regression-тесты FSM заявок.

T-2-003: фиксируем текущее поведение до рефакторинга.
Все переходы через ApplicationStateMachine (T-2-040).
"""
import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ─── Фикстуры ─────────────────────────────────────────────────────────────────

@pytest.fixture
def all_statuses(db):
    """Создаём все необходимые статусы заявок."""
    from tests.factories import ApplicationStatusFactory, ColorFactory, SmileFactory

    ColorFactory(name="gray", hex_color="#888888")
    ColorFactory(name="dark", hex_color="#222222")
    SmileFactory(smile_icon="📟")

    statuses = [
        "sent_to_control",
        "apply_in_control",
        "sent_to_service",
        "work_in_service",
        "done",
        "unable",
        "archive_done",
        "archive_unable",
        "default",
    ]
    return {name: ApplicationStatusFactory(name=name) for name in statuses}


@pytest.fixture
def base_objects(db, all_statuses):
    """Базовый экран, панель, ячейка и пользователь."""
    from tests.factories import (
        CityFactory, ColorFactory, SmileFactory, ConditionFactory,
        DepartmentFactory, DisplayFactory, PanelFactory, CellFactory, MsUserFactory,
    )
    ColorFactory(name="white", hex_color="#ffffff")
    ColorFactory(name="black", hex_color="#000000")
    ColorFactory(name="blue", hex_color="#0000ff")
    SmileFactory(smile_icon="🟢")
    SmileFactory(smile_icon="🔧")

    city = CityFactory(name="test-city")
    condition_work = ConditionFactory(name="work")
    ConditionFactory(name="error")
    ConditionFactory(name="unrecoverable")
    dept_monitor = DepartmentFactory(name="monitor")
    DepartmentFactory(name="service")
    DepartmentFactory(name="zip")

    display = DisplayFactory(name="test-display", city=city, rows=0, cols=0)
    panel = PanelFactory(
        name="P-TEST-01",
        display=display,
        condition=condition_work,
        department=dept_monitor,
    )
    cell = CellFactory(display=display, row=1, col=1, panel=panel)
    user_admin = MsUserFactory(username="admin_user", permission="admin")
    user_control = MsUserFactory(username="control_user", permission="control")
    user_service = MsUserFactory(username="service_user", permission="service")

    return {
        "display": display,
        "panel": panel,
        "cell": cell,
        "admin": user_admin,
        "control": user_control,
        "service": user_service,
        "statuses": all_statuses,
    }


@pytest.fixture
def app_in_status(base_objects):
    """Фабрика заявок в нужном статусе."""
    from tests.factories import ApplicationFactory

    def _make(status_name: str):
        ctx = base_objects
        return ApplicationFactory(
            display=ctx["display"],
            panel=ctx["panel"],
            cell=ctx["cell"],
            status=ctx["statuses"][status_name],
        )
    return _make


# ─── Тесты допустимых переходов ───────────────────────────────────────────────

@pytest.mark.parametrize("from_status,to_status,actor_key", [
    ("sent_to_control",   "apply_in_control", "control"),
    ("apply_in_control",  "sent_to_service",  "control"),
    ("sent_to_service",   "work_in_service",  "service"),
    ("work_in_service",   "done",                          "service"),
    ("work_in_service",   "unable",            "service"),
    ("done",                          "archive_done",                  "control"),
    ("unable",            "archive_unable",                "control"),
])
def test_valid_transition(app_in_status, base_objects, from_status, to_status, actor_key):
    """Все 7 допустимых переходов FSM должны выполняться без ошибок."""
    from apps.workflow.applications.state_machine import application_fsm
    from apps.workflow.applications.models import ApplicationEvent

    app = app_in_status(from_status)
    actor = base_objects[actor_key]

    application_fsm.transition(
        application=app,
        target_status=to_status,
        actor=actor,
        comment="test transition",
    )

    app.refresh_from_db()
    assert app.status.name == to_status

    # Должно создаться событие
    assert ApplicationEvent.objects.filter(application=app).exists()


# ─── Тесты недопустимых переходов ─────────────────────────────────────────────

@pytest.mark.parametrize("from_status,invalid_target", [
    ("sent_to_control",  "done"),
    ("sent_to_control",  "archive_done"),
    ("apply_in_control", "unable"),
    ("done",                         "work_in_service"),
    ("archive_done",                 "sent_to_control"),
])
def test_invalid_transition_raises(app_in_status, base_objects, from_status, invalid_target):
    """Недопустимые переходы должны вызывать InvalidTransition."""
    from apps.workflow.applications.exceptions import InvalidTransition
    from apps.workflow.applications.state_machine import application_fsm

    app = app_in_status(from_status)

    with pytest.raises(InvalidTransition):
        application_fsm.transition(
            application=app,
            target_status=invalid_target,
            actor=base_objects["admin"],
            comment="",
        )


def test_transition_wrong_role_raises(app_in_status, base_objects):
    """Сервисник не может выполнить control-переход."""
    from apps.workflow.applications.exceptions import TransitionPermissionDenied
    from apps.workflow.applications.state_machine import application_fsm

    app = app_in_status("sent_to_control")

    with pytest.raises(TransitionPermissionDenied):
        application_fsm.transition(
            application=app,
            target_status="apply_in_control",
            actor=base_objects["service"],  # service не может делать control-переходы
            comment="",
        )


# ─── Тесты ApplicationService ─────────────────────────────────────────────────

def test_application_service_delete_from_sent_to_control(base_objects, app_in_status):
    """Удаление заявки из статуса sent_to_control — разрешено."""
    from apps.workflow.applications.models import Application
    from apps.workflow.applications.services import application_service

    app = app_in_status("sent_to_control")
    app_id = app.id

    application_service.delete(application=app, actor=base_objects["admin"], comment="test")

    assert not Application.objects.filter(id=app_id).exists()


def test_application_service_delete_from_later_status_raises(base_objects, app_in_status):
    """Удаление из более позднего статуса — запрещено."""
    from apps.workflow.applications.services import application_service
    from shared.exceptions import DomainError

    app = app_in_status("apply_in_control")

    with pytest.raises(DomainError):
        application_service.delete(application=app, actor=base_objects["admin"])


# ─── Тесты PanelMover ─────────────────────────────────────────────────────────

def test_panel_mover_moves_panel(base_objects):
    """PanelMover перемещает панель в другой отдел."""
    from apps.directory.panels.services import panel_mover

    panel = base_objects["panel"]
    actor = base_objects["admin"]

    panel_mover.move(panel=panel, to_department="service", actor=actor, comment="тест")

    panel.refresh_from_db()
    assert panel.department.name == "service"


def test_panel_mover_blocks_move_with_active_application(base_objects, app_in_status):
    """PanelMover запрещает перемещение панели с активной заявкой."""
    from apps.directory.panels.services import panel_mover
    from shared.exceptions import PanelHasActiveApplication

    app_in_status("sent_to_control")
    panel = base_objects["panel"]

    with pytest.raises(PanelHasActiveApplication):
        panel_mover.move(panel=panel, to_department="zip", actor=base_objects["admin"])


# ─── Тесты ActivityLog ────────────────────────────────────────────────────────

def test_activity_logger_creates_entry(base_objects, app_in_status):
    """После FSM-перехода в ActivityLog появляется запись."""
    from apps.activity.models import ActivityLog
    from apps.workflow.applications.state_machine import application_fsm

    app = app_in_status("sent_to_control")
    count_before = ActivityLog.objects.count()

    application_fsm.transition(
        application=app,
        target_status="apply_in_control",
        actor=base_objects["control"],
        comment="принял",
    )

    assert ActivityLog.objects.count() > count_before


def test_available_transitions_returns_correct_list(base_objects, app_in_status):
    """available_transitions() возвращает только допустимые переходы из текущего статуса."""
    from apps.workflow.applications.state_machine import application_fsm

    app = app_in_status("work_in_service")
    transitions = application_fsm.available_transitions(app)
    target_statuses = {t.to_status for t in transitions}

    assert "done" in target_statuses
    assert "unable" in target_statuses
    # Нельзя вернуться назад
    assert "sent_to_control" not in target_statuses


# ─── T-2-027: DisplayService ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_display_service_creates_with_layout(base_objects):
    """DisplayService.create_with_layout() создаёт display + cells + panels."""
    from apps.directory.displays.services import DisplayService, DisplayLayoutSpec

    city = base_objects["display"].city
    svc = DisplayService()
    spec = DisplayLayoutSpec(name="test-svc-display", city_name=city.name, rows=2, cols=3)
    display = svc.create_with_layout(spec, actor=base_objects["admin"])

    from apps.directory.displays.models import Cell, Display
    from apps.directory.panels.models import Panel

    assert Display.objects.filter(name="test-svc-display").exists()
    assert Cell.objects.filter(display=display).count() == 6   # 2×3
    assert Panel.objects.filter(display=display).count() == 6 + spec.extra_panels


@pytest.mark.django_db
def test_display_service_raises_on_zero_rows():
    """DisplayService падает при rows=0."""
    from apps.directory.displays.services import DisplayService, DisplayLayoutSpec

    svc = DisplayService()
    with pytest.raises(ValueError, match="rows и cols должны быть >= 1"):
        svc.create_with_layout(DisplayLayoutSpec(name="bad", city_name="city", rows=0, cols=3))


@pytest.mark.django_db
def test_display_save_no_side_effects(base_objects):
    """Display.save() больше НЕ создаёт cells/panels — side effects убраны."""
    from apps.directory.displays.models import Cell, Display
    from apps.directory.panels.models import Panel

    city = base_objects["display"].city
    d = Display(name="plain-display", rows=2, cols=2, slug="plain-display")
    d.city = city
    d.save()

    assert Cell.objects.filter(display=d).count() == 0
    assert Panel.objects.filter(display=d).count() == 0


# ─── T-2-028: Panel.application_status property ───────────────────────────────

@pytest.mark.django_db
def test_panel_application_status_returns_active(base_objects, app_in_status):
    """Panel.application_status возвращает статус активной заявки."""
    app_in_status("sent_to_control")
    panel = base_objects["panel"]
    assert panel.application_status.name == "sent_to_control"


@pytest.mark.django_db
def test_panel_application_status_returns_default_when_no_app(base_objects):
    """Без активной заявки Panel.application_status возвращает 'default'."""
    from tests.factories import ApplicationStatusFactory
    ApplicationStatusFactory(name="default")
    panel = base_objects["panel"]
    assert panel.application_status.name == "default"


@pytest.mark.django_db
def test_panel_with_application_status_annotation(base_objects, app_in_status):
    """QuerySet.with_application_status() аннотирует панели без N+1."""
    from apps.directory.panels.models import Panel

    app_in_status("sent_to_service")
    panel = base_objects["panel"]

    panels = list(Panel.objects.with_application_status().filter(pk=panel.pk))
    assert panels[0]._active_application_status_name == "sent_to_service"


# ─── T-2-030: DepartureStatus ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_departure_status_properties(db):
    """Departure.is_created/is_archived работают через FK."""
    from tests.factories import DepartureFactory
    from apps.workflow.departures.models import DepartureStatus

    created_status = DepartureStatus.objects.create(
        name="created", description="Создан", order=0, is_terminal=False
    )
    DepartureStatus.objects.create(name="archived", description="В архиве", order=2, is_terminal=True)

    dep = DepartureFactory(status=created_status)
    assert dep.is_created is True
    assert dep.is_archived is False
    assert dep.is_terminal is False


@pytest.mark.django_db
def test_departure_filter_by_status_name(db):
    """Фильтр по FK статусу работает без русских строк."""
    from tests.factories import DepartureFactory
    from apps.workflow.departures.models import Departure, DepartureStatus

    archived = DepartureStatus.objects.create(
        name="archived", description="В архиве", order=2, is_terminal=True
    )
    created = DepartureStatus.objects.create(
        name="created", description="Создан", order=0, is_terminal=False
    )
    DepartureFactory(status=created)
    DepartureFactory(status=archived)

    active = Departure.objects.exclude(status__name="archived")
    assert active.count() == 1
