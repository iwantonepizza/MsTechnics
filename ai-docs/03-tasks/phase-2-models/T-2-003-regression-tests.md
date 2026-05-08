# T-2-003. Regression-тесты на ключевую бизнес-логику

> **Тип:** tests
> **Приоритет:** P0 (blocker для миграций моделей)
> **Оценка:** 4 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Зафиксировать текущее поведение ключевой бизнес-логики **до** рефакторинга. Любое изменение, которое случайно сломает логику — упадёт тест.

**Принцип:** тесты черного ящика. Мы тестируем **что делает** функция, а не **как**. При рефакторинге реализация меняется — тесты остаются.

---

## Зависимости

- **Блокируется:** T-2-002 (фабрики)
- **Блокирует:** все T-2-020..T-2-041 (миграции и FSM — не делать без этих тестов)

---

## Что покрыть

### 1. Application FSM (в `application/utils.py::apply_application`)

Это 150 строк ветвлений — сейчас неизвестно, правильно ли они работают во всех случаях. Покрываем каждый переход.

`application/tests/test_fsm_legacy.py`:
```python
import pytest
from application.utils import apply_application

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx(display_factory, ms_user_factory, application_status_factory):
    """Базовые справочники + экран 3×3"""
    display = display_factory(rows=3, cols=3)
    user = ms_user_factory(permission='admin')
    # убедимся что все статусы созданы
    for name in ['sent_to_control','apply_in_control','sent_to_service',
                 'work_in_service','done','unable','archive_done','archive_unable']:
        application_status_factory(name=name)
    return display, user


@pytest.mark.parametrize("from_status,target_status,expected_time_field", [
    ('sent_to_control',  'apply_in_control', 'time_control_apply'),
    ('apply_in_control', 'sent_to_service',  'time_control_send'),
    ('sent_to_service',  'work_in_service',  'time_service_apply'),
    ('work_in_service',  'done',             'time_control_at_work'),
    ('work_in_service',  'unable',           'time_control_unable'),
    ('done',             'archive_done',     'time_control_archive'),
    ('unable',           'archive_unable',   'time_control_archive'),
])
def test_apply_application_legal_transition(ctx, application_factory, from_status, target_status, expected_time_field):
    display, user = ctx
    cell = display.cells.first()
    app = application_factory(
        display=display, panel=cell.panel, cell=cell, status__name=from_status,
    )
    
    # act
    result = apply_application(
        application_id=app.id,
        target_status=target_status,
        user=user,
        comment='test transition',
    )
    
    # assert
    app.refresh_from_db()
    assert app.status.name == target_status
    assert getattr(app, expected_time_field) is not None


@pytest.mark.parametrize("from_status,invalid_target", [
    ('sent_to_control', 'done'),           # не может прыгнуть через 2 статуса
    ('apply_in_control', 'unable'),         # unable только из work_in_service
    ('done', 'work_in_service'),            # нельзя назад
    ('archive_done', 'apply_in_control'),   # архивная неизменяема
])
def test_apply_application_illegal_transition_raises(ctx, application_factory, from_status, invalid_target):
    display, user = ctx
    cell = display.cells.first()
    app = application_factory(
        display=display, panel=cell.panel, cell=cell, status__name=from_status,
    )
    
    with pytest.raises(Exception):  # TODO: тип исключения после T-2-040
        apply_application(application_id=app.id, target_status=invalid_target, user=user, comment='')
```

### 2. Create application

```python
def test_create_application_links_panel_cell_display(ctx, panels_factory):
    display, user = ctx
    cell = display.cells.first()
    panel = cell.panel
    
    from application.utils import create_application
    app = create_application(
        display_id=display.id,
        panel_id=panel.name,
        cell_id=cell.id,
        comment='Moргает',
        user=user,
    )
    
    assert app.display == display
    assert app.panel == panel
    assert app.cell == cell
    assert app.status.name == 'sent_to_control'
    assert app.comment_monitoring == 'Моргает'
    assert app.time_monitoring is not None
    assert app.user_monitoring == user.username
```

### 3. Delete application

```python
def test_delete_application_in_sent_to_control_succeeds(ctx, application_factory):
    display, user = ctx
    cell = display.cells.first()
    app = application_factory(display=display, panel=cell.panel, cell=cell, status__name='sent_to_control')
    
    from application.utils import delete_application
    delete_application(application_id=app.id, user=user)
    
    from application.models import Application
    assert not Application.objects.filter(id=app.id).exists()


def test_delete_application_in_later_status_fails(ctx, application_factory):
    display, user = ctx
    cell = display.cells.first()
    app = application_factory(display=display, panel=cell.panel, cell=cell, status__name='apply_in_control')
    
    from application.utils import delete_application
    with pytest.raises(Exception):
        delete_application(application_id=app.id, user=user)
```

### 4. Panel condition change

```python
def test_change_panel_condition_updates_condition(ctx, panels_factory, condition_factory):
    display, user = ctx
    panel = panels_factory(display=display)
    new_condition = condition_factory(name='problem')
    
    from zip.utils import change_panel_condition  # уточнить путь в проекте
    change_panel_condition(panel_id=panel.id, new_condition_name='problem', user=user, comment='гудит')
    
    panel.refresh_from_db()
    assert panel.condition.name == 'problem'


def test_change_panel_condition_with_active_application_blocks(ctx, panels_factory, application_factory):
    display, user = ctx
    cell = display.cells.first()
    panel = cell.panel
    application_factory(display=display, panel=panel, cell=cell, status__name='sent_to_service')
    
    from zip.utils import change_panel_condition
    with pytest.raises(Exception):
        change_panel_condition(panel_id=panel.id, new_condition_name='unrecoverable', user=user, comment='')
```

### 5. Panel replace in cell

```python
def test_replace_panel_in_cell_updates_cell(ctx, panels_factory):
    display, user = ctx
    cell = display.cells.first()
    old_panel = cell.panel
    new_panel = panels_factory(display=display, department__name='zip')
    
    from main.Db.orm_query import replace_panel_in_cell
    replace_panel_in_cell(cell_id=cell.id, new_panel_id=new_panel.name, user=user, comment='замена')
    
    cell.refresh_from_db()
    new_panel.refresh_from_db()
    old_panel.refresh_from_db()
    
    assert cell.panel == new_panel
    assert new_panel.department.name == 'monitor'  # теперь в экране
    # old_panel должна быть либо в service, либо в zip — зависит от логики
```

### 6. Display.save() side effects

Этот метод создаёт Cells, Panels и History records. Зафиксируем поведение.

```python
def test_display_save_creates_cells_equal_rows_times_cols(city_factory):
    from zip.models import Display
    city = city_factory()
    
    d = Display(name='test-3x2', city=city, rows=3, cols=2, slug='test-3x2')
    d.save()
    
    assert d.cells.count() == 6


def test_display_save_creates_panels_with_extras(city_factory):
    from zip.models import Display
    city = city_factory()
    
    d = Display(name='test-2x2', city=city, rows=2, cols=2, slug='test-2x2')
    d._extra_panels = 5
    d.save()
    
    from zip.models import Panels
    assert Panels.objects.filter(display=d).count() == 4 + 5  # cells + extras


def test_display_save_creates_history_entries(city_factory):
    from zip.models import Display
    from main_menu.models import PanelHistoryReport, DisplayHistoryReport
    city = city_factory()
    
    d = Display(name='test-1x1', city=city, rows=1, cols=1, slug='test-1x1')
    d.save()
    
    assert PanelHistoryReport.objects.filter(panel__display=d).count() >= 1
    assert DisplayHistoryReport.objects.filter(display=d).count() >= 1
```

### 7. current_condition property

```python
def test_display_current_condition_reflects_worst_panel_condition(display_factory, condition_factory):
    d = display_factory(rows=2, cols=2)
    # по дефолту все панели work
    assert d.current_condition.name == 'work'
    
    # сломаем одну
    panel = d.cells.first().panel
    panel.condition = condition_factory(name='unrecoverable')
    panel.save()
    
    d.refresh_from_db()
    assert d.current_condition.name == 'unrecoverable'
```

---

## Что если функция устарела или работает через side effect в view

Некоторые операции в legacy-проекте размазаны между views, utils и models. Пример: `apply_application` принимает `request` в старом коде.

**Решение:** не тести view напрямую. Если нужно — вызови вью через `client.post(...)` как integration-test, но **минимально**. Основной вес тестов — unit, на публичных функциях domain-слоя.

Если логика размазана — **временно** в тесте дублируй то, что делают view. Это уродливо, но это baseline, который потом заменим.

---

## Критерии приёмки

- [ ] Все 7 блоков тестов написаны, pytest проходит
- [ ] Coverage на `application/utils.py`, `zip/utils.py` (если есть), `main/Db/orm_query.py` ≥ 60%
- [ ] Параметризованные тесты для всех 7 валидных FSM-переходов + 4 невалидных (минимум)
- [ ] Тест на Display.save() — минимум 3 варианта (cells count, panels count, history records)
- [ ] CI зелёный

---

## Что НЕ делать

- **НЕ исправляй** баги, найденные этими тестами, в этой задаче — заведи отдельный тикет
- **НЕ тести** UI / templates / форматирование в этих тестах
- **НЕ используй** `mock` для БД — используй настоящую через `@pytest.mark.django_db`
- **НЕ покрывай** helper-функции ради покрытия — покрывай бизнес-логику

---

## Ожидаемые побочные эффекты

Обнаружатся баги. Например:
- Невалидные FSM-переходы могут НЕ падать — сейчас. Логика неполная.
- `Display.save()` может упасть при `rows=0` или `cols=0`.
- `change_panel_condition` может НЕ проверять активную заявку.

**В отчёте** перечисли найденные баги в раздел «побочные эффекты» с номерами issue. Заведи их в `ai-docs/01-current-state/audit-report.md` — пусть будут зафиксированы.
