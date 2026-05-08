"""
tests/factories.py — factory_boy фабрики для всех основных моделей.

T-2-002: единый файл фабрик (упрощённый вариант — один файл vs разбивка по apps).
Для более крупного проекта разбить по apps/<app>/tests/factories.py.
"""
import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from factory.django import DjangoModelFactory


# ─── Core ─────────────────────────────────────────────────────────────────────

class ColorFactory(DjangoModelFactory):
    class Meta:
        model = "core_references.Color"
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"color_{n}")
    hex_color = factory.Sequence(lambda n: f"#{n:06x}"[:7])


class SmileFactory(DjangoModelFactory):
    class Meta:
        model = "core_references.Smile"
        django_get_or_create = ("smile_icon",)

    smile_icon = factory.Iterator(["🟢", "⚠️", "❌", "💀", "🔧", "🧰", "✋", "📟", "💥", "🚚"])


class CityFactory(DjangoModelFactory):
    class Meta:
        model = "core_references.Cities"
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"city-{n}")
    slug = factory.LazyAttribute(lambda o: o.name.lower())


class ConditionFactory(DjangoModelFactory):
    class Meta:
        model = "core_references.Condition"
        django_get_or_create = ("name",)

    name = factory.Iterator(["work", "error", "unrecoverable", "default"])
    description = factory.LazyAttribute(lambda o: o.name.title())
    color = factory.SubFactory(ColorFactory, name="white")
    color_text = factory.SubFactory(ColorFactory, name="black")
    icon = factory.SubFactory(SmileFactory, smile_icon="🟢")


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = "core_references.Department"
        django_get_or_create = ("name",)

    name = factory.Iterator(["monitor", "service", "zip", "hand", "control"])
    description = factory.LazyAttribute(lambda o: f"Отдел {o.name}")
    color = factory.SubFactory(ColorFactory, name="blue")
    color_text = factory.SubFactory(ColorFactory, name="white")
    icon = factory.SubFactory(SmileFactory, smile_icon="🔧")


class MsUserFactory(DjangoModelFactory):
    class Meta:
        model = "user.MsUser"
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.test")
    password = factory.LazyFunction(lambda: make_password("testpassword"))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    permission = "service"

    @factory.post_generation
    def allowed_cities(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.allowed_city.set(extracted)


# ─── Directory ────────────────────────────────────────────────────────────────

class ApplicationStatusFactory(DjangoModelFactory):
    class Meta:
        model = "workflow_applications.ApplicationStatus"
        django_get_or_create = ("name",)

    name = factory.Iterator([
        "sent_to_control",
        "apply_in_control",
        "sent_to_service",
        "work_in_service",
        "done",
        "unable",
        "archive_done",
        "archive_unable",
        "default",
    ])
    description = factory.LazyAttribute(lambda o: o.name.replace("_", " ").title())
    color = factory.SubFactory(ColorFactory, name="gray")
    color_text = factory.SubFactory(ColorFactory, name="dark")
    icon = factory.SubFactory(SmileFactory, smile_icon="📟")


class DisplayFactory(DjangoModelFactory):
    """Display без автосоздания ячеек/панелей (rows=0, cols=0 → save() не создаёт cells)."""

    class Meta:
        model = "directory_displays.Display"
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"display-{n}")
    city = factory.SubFactory(CityFactory)
    description = factory.LazyAttribute(lambda o: f"Экран {o.name}")
    rows = 0
    cols = 0
    slug = factory.LazyAttribute(lambda o: o.name.lower())


class PanelFactory(DjangoModelFactory):
    class Meta:
        model = "directory_panels.Panel"
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"P-{n:05d}")
    display = factory.SubFactory(DisplayFactory)
    condition = factory.SubFactory(ConditionFactory, name="work")
    department = factory.SubFactory(DepartmentFactory, name="zip")
    comment = ""


class CellFactory(DjangoModelFactory):
    class Meta:
        model = "directory_displays.Cell"

    display = factory.SubFactory(DisplayFactory)
    row = factory.Sequence(lambda n: (n % 3) + 1)
    col = factory.Sequence(lambda n: (n % 3) + 1)
    panel = factory.SubFactory(PanelFactory)


# ─── Workflow ─────────────────────────────────────────────────────────────────

class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = "workflow_applications.Application"

    display = factory.SubFactory(DisplayFactory)
    panel = factory.SubFactory(PanelFactory)
    cell = factory.SubFactory(CellFactory)
    status = factory.SubFactory(ApplicationStatusFactory, name="sent_to_control")
    comment_monitoring = "Моргает верхний ряд"
    time_monitoring = factory.LazyFunction(timezone.now)
    user_monitoring = "test_user"
    last_update_date_time = factory.LazyFunction(timezone.now)


class ExecutorFactory(DjangoModelFactory):
    class Meta:
        model = "workflow_departures.Executor"

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    executor_role = "Техник"
    phone_number = factory.Sequence(lambda n: f"+7900{n:07d}")



class DepartureStatusFactory(DjangoModelFactory):
    class Meta:
        model = "workflow_departures.DepartureStatus"
        django_get_or_create = ("name",)

    name = factory.Iterator(["created", "completed", "archived", "deleted"])
    description = factory.LazyAttribute(lambda o: {
        "created": "Создан", "completed": "Выполнен",
        "archived": "В архиве", "deleted": "Удалён"
    }.get(o.name, o.name))
    order = factory.Sequence(lambda n: n)
    is_terminal = factory.LazyAttribute(lambda o: o.name in ("archived", "deleted"))

class DepartureFactory(DjangoModelFactory):
    class Meta:
        model = "workflow_departures.Departure"

    description = factory.Faker("sentence")
    user_create = factory.Sequence(lambda n: f"user{n}")
    executor = factory.SubFactory(ExecutorFactory)
    status = factory.SubFactory(DepartureStatusFactory, name='created')


# ─── T-2-027: DisplayWithLayoutFactory ───────────────────────────────────────

class DisplayWithLayoutFactory:
    """
    Не DjangoModelFactory — wrapper над DisplayService.
    Создаёт Display с ячейками и панелями (полный layout).

    Использование:
        display = DisplayWithLayoutFactory.create(rows=3, cols=3, city=city)
    """

    @staticmethod
    def create(*, rows: int = 3, cols: int = 3, city=None, extra_panels: int = 2, **kwargs):
        from apps.directory.displays.services import DisplayService, DisplayLayoutSpec
        import uuid
        city = city or CityFactory()
        name = kwargs.get("name", f"layout-display-{uuid.uuid4().hex[:6]}")
        spec = DisplayLayoutSpec(
            name=name,
            city_name=city.name,
            rows=rows,
            cols=cols,
            extra_panels=extra_panels,
        )
        return DisplayService().create_with_layout(spec)
