# T-2-011. Создать скелет `apps/` по целевой архитектуре

> **Тип:** refactor
> **Приоритет:** P1
> **Оценка:** 1.5 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Создать пустую структуру пакетов из `ai-docs/00-architecture/target-architecture.md`, но **без переноса кода**. Перенос — следующими задачами (T-2-012 .. T-2-014). Сейчас — каркас.

---

## Зависимости

- **Блокируется:** T-2-010 (config/)
- **Блокирует:** T-2-012, T-2-013, T-2-014

---

## Что нужно сделать

### Шаг 1. Создать директории

```
apps/
├── __init__.py
├── core/                        # users, cities, colors, icons
│   ├── __init__.py
│   ├── apps.py
│   ├── users/
│   │   ├── __init__.py
│   │   └── apps.py
│   ├── cities/
│   │   ├── __init__.py
│   │   └── apps.py
│   └── references/              # colors, icons, conditions справочники
│       ├── __init__.py
│       └── apps.py
│
├── directory/                    # displays, panels, cells, zip
│   ├── __init__.py
│   ├── apps.py
│   ├── displays/
│   ├── panels/
│   ├── cells/
│   └── storage/                  # Wires, Hubs, Lamels
│
├── workflow/                     # applications, departures
│   ├── __init__.py
│   ├── apps.py
│   ├── applications/
│   └── departures/
│
├── activity/                     # ActivityLog (единый журнал)
│   ├── __init__.py
│   └── apps.py
│
├── notifications/                # каналы, правила, диспетчер
│   ├── __init__.py
│   └── apps.py
│
├── integrations/                 # Gmail, Telegram, MAX
│   ├── __init__.py
│   └── apps.py
│
└── interface/                    # REST API (Фаза 3)
    ├── __init__.py
    └── apps.py
```

```
shared/
├── __init__.py
├── exceptions.py           # DomainError, InvalidStateTransition, etc.
├── logging.py              # structlog helpers (если есть общие)
├── time.py                 # перенести get_time.py сюда
└── http.py                 # safe_redirect (из T-1-009)
```

### Шаг 2. apps.py для каждого нового пакета

Пример `apps/core/apps.py`:
```python
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"
```

Аналогично для остальных:
- `apps.directory` → label `directory`
- `apps.workflow` → label `workflow`
- `apps.activity` → label `activity`
- `apps.notifications` → label `notifications`
- `apps.integrations` → label `integrations`
- `apps.interface` → label `interface`

**Важно:** пока что эти приложения **пустые** — ни моделей, ни views. Они нужны как "landing zones" для следующих задач.

### Шаг 3. Зарегистрировать в `INSTALLED_APPS`

`config/settings/base.py`:
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Наши (новая структура)
    "apps.core",
    "apps.directory",
    "apps.workflow",
    "apps.activity",
    "apps.notifications",
    "apps.integrations",
    # "apps.interface",  # закомментирован — добавим в Фазе 3
    
    # Legacy (пока оставляем — постепенно удалим)
    "application",
    "control",
    "departure",
    "mail",
    "main",
    "main_menu",
    "monitoring",
    "service",
    "user",
    "zip",
]
```

### Шаг 4. `shared/` как пакет

1. Перенести `get_time.py` → `shared/time.py`:
   ```bash
   git mv get_time.py shared/time.py
   grep -rln "from get_time" .
   # заменить на: from shared.time
   ```

2. `shared/http.py` — пустой пока (наполнится в T-1-009). Если T-1-009 уже сделан, просто убедиться что файл там.

3. `shared/exceptions.py`:
   ```python
   """Базовые доменные исключения."""
   
   class DomainError(Exception):
       """Базовая ошибка доменной логики."""
       code: str = "domain_error"
       
       def __init__(self, message: str | None = None, **kwargs):
           self.message = message or self.__class__.__doc__
           self.context = kwargs
           super().__init__(self.message)
   
   class InvalidStateTransition(DomainError):
       """Запрошенный переход состояния недопустим."""
       code = "invalid_state_transition"
   
   class PanelHasActiveApplication(DomainError):
       """Нельзя выполнить действие — у панели активная заявка."""
       code = "panel_has_active_application"
   
   class PermissionDeniedForCity(DomainError):
       """Нет доступа к этому городу."""
       code = "forbidden_for_city"
   
   class PermissionDeniedForDepartment(DomainError):
       """Нет доступа к этому отделу."""
       code = "forbidden_for_department"
   ```

### Шаг 5. Проверить

```bash
python manage.py check
python manage.py showmigrations  # все существующие должны остаться
pytest
```

Новые apps не должны генерить миграций — моделей в них нет.

---

## Критерии приёмки

- [ ] Все директории и `__init__.py` / `apps.py` созданы
- [ ] `INSTALLED_APPS` расширен
- [ ] `python manage.py check` — чисто
- [ ] `python manage.py makemigrations` — **не создаёт** новых миграций (apps пустые)
- [ ] `shared/time.py` существует, `get_time.py` удалён, импорты обновлены
- [ ] `shared/exceptions.py` содержит классы ошибок
- [ ] Legacy-приложения остались в `INSTALLED_APPS` и работают

---

## Что НЕ делать

- **НЕ переноси** ни одну модель в этой задаче (это T-2-012..014)
- **НЕ меняй** существующие legacy-apps
- **НЕ добавляй** `app_label` в legacy-моделях — миграции из-за этого переедут и сломают историю

---

## Frequent pitfalls

- **`CoreConfig` label conflicts**. Django по дефолту берёт label из последнего компонента имени. `apps.core` → label=`core`. Если в legacy есть app с label=`core` — конфликт. Исправить: явно указать `label = "core_new"` или переименовать legacy app. Проверь до коммита.

- **Двойное имя в INSTALLED_APPS.** Не должно быть одновременно `apps.core.users` и просто `user` — Django может спутать миграции. Пока `apps.core.users` пустой — ОК.
