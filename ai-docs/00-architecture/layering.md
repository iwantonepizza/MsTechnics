# Слоистость приложений

Правила, которые ревью не прощает.

---

## Правило № 1. Одностороннее направление зависимостей

```
      interface/
          ↓
      workflow/  ─────►  activity/
          ↓                  ↓
      directory/  ──────► notifications/
          ↓                  ↓
           core/  ◄────── integrations/
```

Стрелка идёт в сторону «я могу импортировать». Обратно — запрещено.

### Что можно:

- `workflow.applications` → `directory.models.Panel` ✅
- `directory.services.PanelMover` → `activity.services.log_event` ✅
- `interface.api.views` → `workflow.services.*` ✅

### Что нельзя:

- `core.models.User` → `workflow.models.Application` ❌
- `directory.models.Panel` → `workflow.models.Application` ❌
- `activity` → `directory` ❌ (activity работает через ContentType, не конкретные модели)

### Почему это важно

- Круговые импорты → `AppRegistryNotReady`
- Тесты модуля нельзя запустить изолированно → замедление CI
- Невозможно вынести приложение в отдельный сервис, если понадобится
- Один неверный импорт тянет за собой половину проекта (в текущем коде `zip.models` тянет `user.models` и `main_menu.models` и `sorting_message.py`)

---

## Правило № 2. Public interface приложения

Каждое приложение определяет **что именно** оно экспортирует в `apps/<app>/__init__.py` или через явные импорты из внешних модулей только через `apps/<app>/public.py`.

Пример:

**apps/directory/public.py**:

```python
from apps.directory.models.display import Display
from apps.directory.models.panel import Panel
from apps.directory.models.cell import Cell
from apps.directory.services.display_factory import DisplayFactory
from apps.directory.services.panel_mover import PanelMover, CannotMovePanelError

__all__ = [
    'Display', 'Panel', 'Cell',
    'DisplayFactory', 'PanelMover',
    'CannotMovePanelError',
]
```

Внешний код:

```python
# правильно
from apps.directory.public import Panel, PanelMover

# неправильно
from apps.directory.models.panel import Panel   # ❌ лезет во внутреннюю структуру
from apps.directory.services.panel_mover import PanelMover  # ❌
```

Внутри самого приложения (`apps/directory/*`) — ходить куда угодно можно.

---

## Правило № 3. Сервисы — stateless

Все сервисы — это классы/функции **без стейта** (за исключением инъектируемых зависимостей).

```python
# плохо
class PanelMover:
    def __init__(self):
        self.moved_panels = []  # ❌ локальный стейт

    def move(self, panel, to_department):
        ...
        self.moved_panels.append(panel)

# хорошо
class PanelMover:
    def __init__(self, activity_logger: ActivityLogger, notifier: Notifier):
        self.activity_logger = activity_logger  # ✅ injectable dependency
        self.notifier = notifier

    def move(self, panel: Panel, to_department: Department, actor: User, comment: str = '') -> Panel:
        ...
```

---

## Правило № 4. Модели Django — thin

В модели:

- ✅ Поля
- ✅ `Meta` (ordering, constraints, indexes, db_table)
- ✅ `__str__`
- ✅ `clean()` и валидация уровня одной записи
- ✅ Простые `@property` без побочных эффектов и без SQL (или с одним `.first()`)
- ✅ Managers и QuerySets (но без бизнес-логики)

Чего в модели **быть не должно**:

- ❌ `.save()` с автоматическим созданием связанных объектов (как сейчас `Display.save`)
- ❌ Вызовы внешних сервисов (notifications, emails)
- ❌ Бизнес-workflow (смена статуса заявки → побочные эффекты)
- ❌ Методы типа `apply()`, `send_to_service()`, `archive()` — это сервисы

---

## Правило № 5. Кого куда класть

| Что                                       | Где                                                 |
|-------------------------------------------|-----------------------------------------------------|
| Модели (поля, Meta)                       | `apps/<app>/models/*.py` или `models.py`             |
| Managers и QuerySets                      | `apps/<app>/managers.py` (или внутри модели, если маленькие) |
| Constants, choices, enums                 | `apps/<app>/constants.py`                           |
| Сериализаторы DRF                         | `apps/<app>/api/serializers.py`                    |
| ViewSets / Views DRF                      | `apps/<app>/api/views.py`                          |
| URL-роутер приложения                     | `apps/<app>/api/urls.py`                           |
| Permissions DRF                           | `apps/<app>/api/permissions.py`                    |
| Use-cases (однодельные классы)            | `apps/<app>/services/<name>.py`                    |
| Интеграции с БД, только чтение/запись     | `apps/<app>/repositories/<name>.py` (опционально)   |
| Тесты                                     | `apps/<app>/tests/test_*.py`                       |
| Тесты моделей                             | `tests/test_models.py`                             |
| Тесты сервисов                            | `tests/test_services.py`                           |
| Тесты API                                 | `tests/test_api.py`                                |
| E2E/integration                           | `backend/tests/e2e/`                               |
| Формы (если нужны для админки)            | `apps/<app>/forms.py`                              |
| Админка                                   | `apps/<app>/admin.py`                              |
| Сигналы                                   | `apps/<app>/signals.py` + регистрация в `apps.py`  |
| Management commands                       | `apps/<app>/management/commands/<name>.py`         |
| Задачи воркера (background)               | `apps/<app>/worker.py` или `tasks.py`               |

---

## Правило № 6. Транзакционная граница — сервис

Все операции, затрагивающие более одной таблицы, обёрнуты в `@transaction.atomic` на уровне **сервиса** (не view и не модели):

```python
class ApplicationService:
    @transaction.atomic
    def transition(self, application: Application, target_status: str, actor: User, ...) -> Application:
        # 1. Application.status = ...
        # 2. ApplicationEvent.objects.create(...)
        # 3. ActivityLog.objects.create(...)
        # 4. notification_queue.enqueue(...)  ← вне транзакции через on_commit
        ...
```

Внешние эффекты (отправка в очередь, http-запросы) — **через `transaction.on_commit(callable)`**, иначе при откате транзакции уведомление всё равно уйдёт, а заявка не изменится.

---

## Правило № 7. Константы

Любая строка, которая используется в двух местах и имеет бизнес-смысл — **константа**.

```python
# apps/workflow/applications/constants.py

class ApplicationStatusCode:
    SENT_TO_CONTROL = 'application_sent_to_control'
    APPLY_IN_CONTROL = 'application_apply_in_control'
    SENT_TO_SERVICE = 'application_sent_to_service'
    WORK_IN_SERVICE = 'application_work_in_service'
    DONE = 'done'
    UNABLE = 'application_unable'
    ARCHIVE_DONE = 'archive_done'
    ARCHIVE_UNABLE = 'archive_unable'

    ACTIVE = {SENT_TO_CONTROL, APPLY_IN_CONTROL, SENT_TO_SERVICE, WORK_IN_SERVICE}
    TERMINAL = {ARCHIVE_DONE, ARCHIVE_UNABLE}
```

Сравнения, filter'ы, choices — все через эти константы. Магические строки в коде = блокер PR.

---

## Правило № 8. ContentType только в activity

`django.contrib.contenttypes` используется **только** в приложении `activity` (ActivityLog). Если кажется, что где-то ещё нужна Generic-связь — скорее всего, нужен нормальный FK.

---

## Правило № 9. `select_related` / `prefetch_related`

Любой QuerySet, который идёт в шаблон/сериалайзер и содержит FK/M2M обращения — с явным `.select_related()` / `.prefetch_related()`. Линтер проверяет через `django-silk` в dev — запрос дольше 50ms = warning.

В сериализатора список полей для prefetch выносится в атрибут класса:

```python
class PanelSerializer(serializers.ModelSerializer):
    PREFETCH_RELATED = ['condition__icon', 'department', 'display']

    class Meta:
        model = Panel
        fields = [...]
```

ViewSet использует:

```python
class PanelViewSet(viewsets.ModelViewSet):
    serializer_class = PanelSerializer

    def get_queryset(self):
        return Panel.objects.all().select_related(
            *self.serializer_class.PREFETCH_RELATED
        )
```

---

## Правило № 10. Нет циклических импортов — точка

Если получил `ImportError: cannot import ... partially initialized`:

1. Не лепи `from X import Y` внутрь функции.
2. Не ставь `apps.get_model()`.
3. **Переосмысли зависимость.** Скорее всего, у тебя слоение сломано.

---

## Валидация правил

В CI (фаза 1 задача «lint-deps»):

- Скрипт `scripts/check_layering.py` парсит импорты и падает, если `core` импортит `workflow`.
- Запускается в pre-commit и в CI.

Это ставит **забор**, а не полагается на добрую волю.
