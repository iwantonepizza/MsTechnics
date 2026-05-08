"""
tests/test_models_phase2b.py — тесты T-2-027..T-2-030.
"""
import pytest

pytestmark = pytest.mark.django_db


# ─── Общие фикстуры ────────────────────────────────────────────────────────────

@pytest.fixture
def base_refs(db):
    """Создаём минимальный набор справочников."""
    from tests.factories import (
        ColorFactory, SmileFactory, ConditionFactory, DepartmentFactory,
        ApplicationStatusFactory, CityFactory,
    )
    ColorFactory(name="gray",  hex_color="#888888")
    ColorFactory(name="dark",  hex_color="#222222")
    ColorFactory(name="white", hex_color="#ffffff")
    ColorFactory(name="black", hex_color="#000000")
    ColorFactory(name="blue",  hex_color="#0000ff")
    SmileFactory(smile_icon="🟢")
    SmileFactory(smile_icon="📟")
    SmileFactory(smile_icon="🔧")

    city = CityFactory(name="ekb")
    ConditionFactory(name="work")
    ConditionFactory(name="error")
    DepartmentFactory(name="monitor")
    DepartmentFactory(name="service")
    DepartmentFactory(name="zip")
    ApplicationStatusFactory(name="default")
    ApplicationStatusFactory(name="sent_to_control")
    ApplicationStatusFactory(name="archive_done")
    ApplicationStatusFactory(name="archive_unable")
    return {"city": city}


# ─── T-2-027: DisplayService ───────────────────────────────────────────────────

class TestDisplayService:
    def test_create_with_layout_creates_cells(self, base_refs):
        """DisplayService создаёт ровно rows×cols ячеек."""
        from apps.directory.displays.services import DisplayService, DisplayLayoutSpec
        from apps.directory.displays.models import Cell

        spec = DisplayLayoutSpec(
            name="test-display-3x4",
            city_name=base_refs["city"].name,
            rows=3,
            cols=4,
            extra_panels=0,
        )
        svc = DisplayService()
        display = svc.create_with_layout(spec)

        assert Cell.objects.filter(display=display).count() == 12  # 3×4

    def test_create_with_layout_creates_panels(self, base_refs):
        """DisplayService создаёт cells + extra_panels панелей."""
        from apps.directory.displays.services import DisplayService, DisplayLayoutSpec
        from apps.directory.panels.models import Panel

        spec = DisplayLayoutSpec(
            name="test-display-2x2",
            city_name=base_refs["city"].name,
            rows=2,
            cols=2,
            extra_panels=5,
        )
        svc = DisplayService()
        display = svc.create_with_layout(spec)

        # 4 cells + 5 extra = 9 panels
        assert Panel.objects.filter(display=display).count() == 9

    def test_create_with_layout_assigns_panels_to_cells(self, base_refs):
        """Все ячейки получают панели после create_with_layout."""
        from apps.directory.displays.services import DisplayService, DisplayLayoutSpec
        from apps.directory.displays.models import Cell

        spec = DisplayLayoutSpec(
            name="test-display-assign",
            city_name=base_refs["city"].name,
            rows=2,
            cols=3,
            extra_panels=0,
        )
        svc = DisplayService()
        display = svc.create_with_layout(spec)

        cells_without_panel = Cell.objects.filter(display=display, panel__isnull=True).count()
        assert cells_without_panel == 0

    def test_create_with_layout_raises_for_zero_rows(self, base_refs):
        """rows=0 должен вызвать ValueError."""
        from apps.directory.displays.services import DisplayService, DisplayLayoutSpec

        spec = DisplayLayoutSpec(
            name="bad-display",
            city_name=base_refs["city"].name,
            rows=0,
            cols=3,
        )
        with pytest.raises(ValueError, match="rows и cols"):
            DisplayService().create_with_layout(spec)

    def test_display_save_no_side_effects(self, base_refs):
        """Display.save() больше НЕ создаёт ячейки — T-2-027."""
        from apps.directory.displays.models import Display, Cell

        display = Display(
            name="plain-display",
            rows=3,
            cols=3,
            slug="plain-display",
        )
        display.city = base_refs["city"]
        display.save()

        assert Cell.objects.filter(display=display).count() == 0


# ─── T-2-028: Panel.application_status property ────────────────────────────────

class TestPanelApplicationStatusProperty:
    def test_returns_default_when_no_application(self, base_refs):
        """Без заявок — application_status == default."""
        from tests.factories import PanelFactory, DisplayFactory

        display = DisplayFactory(name="disp-prop-01", city=base_refs["city"])
        panel = PanelFactory(name="P-PROP-01", display=display)

        status = panel.application_status
        assert status is not None
        assert status.name == "default"

    def test_returns_active_application_status(self, base_refs):
        """С активной заявкой — возвращает её статус."""
        from tests.factories import (
            PanelFactory, DisplayFactory, CellFactory, ApplicationFactory,
        )
        from apps.workflow.applications.models import ApplicationStatus

        display = DisplayFactory(name="disp-prop-02", city=base_refs["city"])
        panel = PanelFactory(name="P-PROP-02", display=display)
        cell = CellFactory(display=display, row=1, col=1, panel=panel)

        active_status = ApplicationStatus.objects.get(name="sent_to_control")
        ApplicationFactory(
            display=display, panel=panel, cell=cell,
            status=active_status,
        )

        assert panel.application_status.name == "sent_to_control"

    def test_ignores_archived_application(self, base_refs):
        """Архивная заявка не влияет — возвращает default."""
        from tests.factories import (
            PanelFactory, DisplayFactory, CellFactory, ApplicationFactory,
        )
        from apps.workflow.applications.models import ApplicationStatus

        display = DisplayFactory(name="disp-prop-03", city=base_refs["city"])
        panel = PanelFactory(name="P-PROP-03", display=display)
        cell = CellFactory(display=display, row=1, col=1, panel=panel)

        archive_status = ApplicationStatus.objects.get(name="archive_done")
        ApplicationFactory(
            display=display, panel=panel, cell=cell,
            status=archive_status,
        )

        assert panel.application_status.name == "default"

    def test_has_active_application_false_by_default(self, base_refs):
        from tests.factories import PanelFactory, DisplayFactory

        display = DisplayFactory(name="disp-prop-04", city=base_refs["city"])
        panel = PanelFactory(name="P-PROP-04", display=display)
        assert panel.has_active_application is False


# ─── T-2-029: DailyTask.notified_stages ────────────────────────────────────────

class TestDailyTaskNotifications:
    @pytest.fixture
    def daily_task(self, db, base_refs):
        from zip.models import DailyTask
        return DailyTask.objects.create(
            name="test-task-notif",
            city=base_refs["city"],
            link="http://example.com",
        )

    def test_has_notified_false_initially(self, daily_task):
        assert daily_task.has_notified("alert") is False

    def test_mark_notified_sets_flag(self, daily_task):
        daily_task.mark_notified("alert")
        daily_task.refresh_from_db()
        assert daily_task.has_notified("alert") is True

    def test_mark_notified_idempotent(self, daily_task):
        """Двойной вызов не создаёт дублей в списке."""
        daily_task.mark_notified("start")
        daily_task.mark_notified("start")
        daily_task.refresh_from_db()
        assert daily_task.notified_stages.count("start") == 1

    def test_reset_notifications_clears_all(self, daily_task):
        daily_task.mark_notified("alert")
        daily_task.mark_notified("deadline")
        daily_task.reset_notifications()
        daily_task.refresh_from_db()
        assert daily_task.notified_stages == []
        assert daily_task.alert_notification_sent is False

    def test_mark_notified_unknown_stage_raises(self, daily_task):
        with pytest.raises(ValueError, match="Неизвестная стадия"):
            daily_task.mark_notified("unknown_stage")


# ─── T-2-030: DepartureStatus FK ───────────────────────────────────────────────

class TestDepartureStatus:
    @pytest.fixture
    def statuses(self, db):
        from apps.workflow.departures.models import DepartureStatus
        rows = [
            ("created",   "Создан",   0, False),
            ("completed", "Выполнен", 1, False),
            ("archived",  "В архиве", 2, True),
            ("deleted",   "Удалён",   3, True),
        ]
        result = {}
        for name, desc, order, terminal in rows:
            s, _ = DepartureStatus.objects.get_or_create(
                name=name,
                defaults={"description": desc, "order": order, "is_terminal": terminal},
            )
            result[name] = s
        return result

    @pytest.fixture
    def departure(self, db, statuses):
        from apps.workflow.departures.models import Departure
        return Departure.objects.create(
            description="Тестовый выезд",
            user_create="test_user",
            status=statuses["created"],
        )

    def test_departure_is_created_property(self, departure):
        assert departure.is_created is True
        assert departure.is_archived is False

    def test_departure_is_archived_property(self, departure, statuses):
        departure.status = statuses["archived"]
        departure.save()
        assert departure.is_archived is True
        assert departure.is_terminal is True

    def test_departure_status_str(self, statuses):
        assert str(statuses["created"]) == "Создан"
        assert str(statuses["archived"]) == "В архиве"

    def test_filter_by_status_name(self, departure, statuses):
        from apps.workflow.departures.models import Departure
        qs = Departure.objects.filter(status__name="created")
        assert qs.filter(pk=departure.pk).exists()

    def test_terminal_statuses(self, statuses):
        from apps.workflow.departures.models import DepartureStatus
        terminal = DepartureStatus.objects.filter(is_terminal=True)
        names = set(terminal.values_list("name", flat=True))
        assert names == {"archived", "deleted"}
