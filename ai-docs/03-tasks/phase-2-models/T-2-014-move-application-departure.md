# T-2-014. `application/` + `departure/` → `apps/workflow/`

> **Тип:** refactor / migration
> **Приоритет:** P1
> **Оценка:** 2.5 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Перенести заявки и выезды в `apps/workflow/` по той же методике, что T-2-012 и T-2-013. Одновременно **обновить string-FK** на новые пути моделей из `apps/directory/`.

---

## Зависимости

- **Блокируется:** T-2-013 (Panel в новом месте)
- **Блокирует:** T-2-020 (ApplicationEvent), T-2-040 (FSM)

---

## Что нужно сделать

### Шаг 1. Структура

```
apps/workflow/
├── __init__.py
├── apps.py
├── applications/
│   ├── __init__.py
│   ├── apps.py                 # ApplicationsConfig(label='workflow_applications')
│   ├── models.py               # Application, ApplicationStatus
│   ├── admin.py
│   └── managers.py             # ApplicationManager с all_new()
└── departures/
    ├── __init__.py
    ├── apps.py                 # DeparturesConfig(label='workflow_departures')
    ├── models.py               # Departure, Executor
    └── admin.py
```

### Шаг 2. Миграции по схеме из T-2-012/013

1. Копируем модели в новые файлы, `db_table` оставляем прежние (`'application'`, `'application_status'`, `'departure'`, `'executor'`)
2. Генерируем миграцию с `SeparateDatabaseAndState` + `state_operations=[CreateModel...]`
3. В старых `application/migrations/` / `departure/migrations/` — финальная миграция с `DeleteModel` в state_operations

### Шаг 3. Обновление string-FK

**ДО (в `application/models.py` старом):**
```python
display = models.ForeignKey("zip.Display", to_field='name', ...)
panel = models.ForeignKey("zip.Panels", to_field='name', ...)
cell = models.ForeignKey("zip.Cell", to_field='id', ...)
executor = models.ForeignKey("departure.Executor", ...)
status = models.ForeignKey("ApplicationStatus", to_field='name', ...)
```

**ПОСЛЕ (в `apps/workflow/applications/models.py`):**
```python
display = models.ForeignKey("directory_displays.Display", to_field='name', ...)
panel = models.ForeignKey("directory_panels.Panel", to_field='name', ...)
cell = models.ForeignKey("directory_displays.Cell", to_field='id', ...)
executor = models.ForeignKey("workflow_departures.Executor", ...)
status = models.ForeignKey("workflow_applications.ApplicationStatus", to_field='name', ...)
```

**КРИТИЧЕСКИ ВАЖНО:** 
- Меняем ТОЛЬКО в новых моделях (`apps/workflow/...`)
- В СТАРЫХ миграциях (`application/migrations/*.py`) — **не трогаем** строки FK
- Старые миграции должны остаться воспроизводимыми на чистой БД

Django **сохранит FK связи**, потому что `db_table` и колонки не меняются — меняется только Python-модель. Django резолвит `"directory_panels.Panel"` → находит модель с тем же `db_table='panels'` → связь жива.

### Шаг 4. Compat-shim

`application/models.py`:
```python
"""Compat shim — модели переехали в apps.workflow.applications."""
from apps.workflow.applications.models import (  # noqa: F401
    Application, ApplicationStatus, ApplicationHistoryReport,
)
```

`departure/models.py`:
```python
"""Compat shim — модели переехали в apps.workflow.departures."""
from apps.workflow.departures.models import Departure, Executor  # noqa: F401
```

### Шаг 5. ApplicationManager

В `application/models.py` сейчас есть `ApplicationManager` с методами `all_new`, `all`, и т.п. Его переносим в:
```
apps/workflow/applications/managers.py
```

И в `models.py`:
```python
from apps.workflow.applications.managers import ApplicationManager

class Application(models.Model):
    # ... поля ...
    objects = ApplicationManager()
```

### Шаг 6. FSM utils

`application/utils.py` содержит `apply_application`, `create_application`, `delete_application` — 150 строк бизнес-логики. **В этой задаче НЕ рефакторим**, только переносим:
```
apps/workflow/applications/utils.py
```

И compat-shim:
```python
# application/utils.py
from apps.workflow.applications.utils import (  # noqa: F401
    apply_application, create_application, delete_application,
)
```

FSM-рефакторинг — отдельная задача T-2-040.

---

## Критерии приёмки

- [ ] Модели в `apps/workflow/applications/` и `apps/workflow/departures/`
- [ ] String-FK обновлены в новых моделях (но не в migrations!)
- [ ] Compat-shim в `application/models.py`, `application/utils.py`, `departure/models.py`
- [ ] ApplicationManager перенесён в `managers.py`
- [ ] Миграции применяются на копии прода без потерь данных
- [ ] Regression-тесты T-2-003 — проходят
- [ ] `python manage.py check` — чисто
- [ ] `python manage.py makemigrations --dry-run` — пусто

---

## Что НЕ делать

- **НЕ рефактори FSM** (`apply_application`) — это T-2-040
- **НЕ трогай** 28 денормализованных полей (comment_*, time_*, ...) — это T-2-020..21
- **НЕ меняй** `db_table`
- **НЕ трогай** string-FK в старых миграциях

---

## Риски

- **Циклическая зависимость.** `applications` ссылается на `departures.Executor`. Если AppConfig.ready() в `applications` пытается импортнуть `Executor` до того как `departures` зарегистрирован — `AppRegistryNotReady`. Митигация: использовать string-FK (`"workflow_departures.Executor"`), не прямой импорт.
- **Legacy import paths в шаблонах.** Django templates могут использовать `{% url 'application:index' %}` — имена URL меняются редко, но проверить. В Фазе 3 URLs всё равно перепишем.
