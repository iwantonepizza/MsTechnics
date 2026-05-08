# T-2-002. factory_boy фабрики для всех моделей

> **Тип:** tests / infra
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Любой тест в Фазе 2 должен создавать данные через фабрики, не прямыми `Model.objects.create(...)`. Иначе regression-тесты будут копипастой с десятками полей, и их невозможно поддерживать.

---

## Зависимости

- **Блокируется:** T-1-001 (factory-boy в deps)
- **Блокирует:** T-2-003 (regression-тесты)

---

## Что нужно сделать

Создать `apps/<каждое приложение>/tests/factories.py` (на этапе, когда реорганизация ещё не сделана — в `<app>/tests/factories.py`).

### Структура файлов

```
<app>/tests/
  __init__.py
  factories.py
  conftest.py    # register-ит фабрики
```

### Фабрики (минимум)

`main/tests/factories.py`:
```python
import factory
from factory.django import DjangoModelFactory
from main.models import Cities, Color, Smile, Condition

class ColorFactory(DjangoModelFactory):
    class Meta:
        model = Color
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'color_{n}')
    description = factory.Faker('color_name')
    hex_color = factory.Faker('hex_color')


class SmileFactory(DjangoModelFactory):
    class Meta:
        model = Smile
        django_get_or_create = ('smile_icon',)
    
    smile_icon = factory.Iterator(['🟢', '⚠️', '❌', '💀', '🔧', '🧰', '✋'])


class CityFactory(DjangoModelFactory):
    class Meta:
        model = Cities
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'city-{n}')
    slug = factory.LazyAttribute(lambda o: o.name)


class ConditionFactory(DjangoModelFactory):
    class Meta:
        model = Condition
        django_get_or_create = ('name',)
    
    name = factory.Iterator(['work', 'problem', 'unrecoverable', 'default'])
    description = factory.LazyAttribute(lambda o: o.name.title())
    color = factory.SubFactory(ColorFactory)
    color_text = factory.SubFactory(ColorFactory)
    icon = factory.SubFactory(SmileFactory)
```

`user/tests/factories.py`:
```python
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.hashers import make_password
from user.models import MsUser
from main.tests.factories import CityFactory

class MsUserFactory(DjangoModelFactory):
    class Meta:
        model = MsUser
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.test')
    password = factory.LazyFunction(lambda: make_password('test_password'))
    permission = 'service'
    
    @factory.post_generation
    def allowed_cities(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.allowed_city.set(extracted)
```

`zip/tests/factories.py`:
```python
import factory
from factory.django import DjangoModelFactory
from zip.models import Display, Cell, Panels, Department
from main.tests.factories import CityFactory, ConditionFactory

class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department
        django_get_or_create = ('name',)
    name = factory.Iterator(['monitor', 'service', 'zip', 'hand'])


class DisplayFactory(DjangoModelFactory):
    class Meta:
        model = Display
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'display-{n}')
    city = factory.SubFactory(CityFactory)
    description = factory.LazyAttribute(lambda o: f'Описание {o.name}')
    rows = 3
    cols = 3
    slug = factory.LazyAttribute(lambda o: o.name)
    
    # ВАЖНО: Display.save() создаёт Cells/Panels автоматически.
    # Для тестов часто это не нужно — используй DisplayFactory.build()
    # или отдельную DisplayWithoutCellsFactory (ниже).


class DisplayEmptyFactory(DjangoModelFactory):
    """Display без авто-создания Cells/Panels (обходит Display.save())"""
    class Meta:
        model = Display
    
    name = factory.Sequence(lambda n: f'display-empty-{n}')
    city = factory.SubFactory(CityFactory)
    rows = 0
    cols = 0
    slug = factory.LazyAttribute(lambda o: o.name)


class PanelsFactory(DjangoModelFactory):
    class Meta:
        model = Panels
    
    name = factory.Sequence(lambda n: f'P-{n:05d}')
    display = factory.SubFactory(DisplayEmptyFactory)
    department = factory.SubFactory(DepartmentFactory, name='zip')
    condition = factory.SubFactory(ConditionFactory, name='work')
    comment = ''
```

`application/tests/factories.py`:
```python
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from application.models import Application, ApplicationStatus
from main.tests.factories import ColorFactory, SmileFactory

class ApplicationStatusFactory(DjangoModelFactory):
    class Meta:
        model = ApplicationStatus
        django_get_or_create = ('name',)
    
    name = factory.Iterator([
        'sent_to_control', 'apply_in_control', 'sent_to_service',
        'work_in_service', 'done', 'unable', 'archive_done', 'archive_unable'
    ])
    description = factory.LazyAttribute(lambda o: o.name.replace('_', ' ').title())
    color = factory.SubFactory(ColorFactory)
    color_text = factory.SubFactory(ColorFactory)
    icon = factory.SubFactory(SmileFactory)


class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = Application
    
    status = factory.SubFactory(ApplicationStatusFactory, name='sent_to_control')
    display = None  # override
    panel = None
    cell = None
    comment_monitoring = 'Моргает верхний ряд'
    time_monitoring = factory.LazyFunction(timezone.now)
    user_monitoring = 'test_user'
    last_update_date_time = factory.LazyFunction(timezone.now)
```

`departure/tests/factories.py`, `main_menu/tests/factories.py` и т.д. — по тому же шаблону.

### conftest.py

Создать в `<app>/tests/conftest.py`:
```python
import pytest
from pytest_factoryboy import register
from .factories import DisplayFactory, PanelsFactory, ApplicationFactory
# ...

register(DisplayFactory)
register(PanelsFactory)
register(ApplicationFactory)
```

И в корневом `conftest.py`:
```python
import pytest

@pytest.fixture
def db(db):
    """pytest-django db fixture by default wraps test in transaction"""
    return db

@pytest.fixture
def authenticated_client(client, ms_user_factory):
    user = ms_user_factory(permission='admin')
    client.force_login(user)
    return client, user
```

### Смоук-тесты

`tests/test_factories.py`:
```python
import pytest

pytestmark = pytest.mark.django_db

def test_panel_factory_creates_panel(panels_factory):
    panel = panels_factory()
    assert panel.pk
    assert panel.name.startswith('P-')
    assert panel.condition.name == 'work'

def test_application_factory_with_relations(application_factory, display_factory, panels_factory):
    display = display_factory(rows=2, cols=2)  # auto-creates 4 cells + 14 panels
    cell = display.cells.first()
    panel = cell.panel
    app = application_factory(display=display, panel=panel, cell=cell)
    assert app.status.name == 'sent_to_control'
    assert app.display == display
```

---

## Критерии приёмки

- [ ] Фабрики существуют для всех основных моделей: Cities, Color, Smile, Condition, MsUser, Executor, Display, Cell, Panels, Department, Application, ApplicationStatus, Departure
- [ ] `django_get_or_create` используется для справочников, иначе тесты падают на дублях
- [ ] `DisplayEmptyFactory` — отдельная, минует `Display.save()` с side effects
- [ ] `conftest.py` регистрирует фабрики через `pytest-factoryboy`
- [ ] `test_factories.py` — смоук-тесты проходят
- [ ] В зависимостях: `factory-boy>=3.3`, `pytest-factoryboy>=2.7`
- [ ] Coverage на новых файлах ≥ 70%

---

## Что НЕ делать

- **НЕ используй** глобальный state между фабриками (`Sequence` — ок, module-level — нет)
- **НЕ добавляй** post_save signals в фабриках — тестируем изолированно
- **НЕ копируй** фабрики между файлами — импортируй через relative/absolute

---

## Вопросы

- [ ]
