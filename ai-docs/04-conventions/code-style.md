# Code Style

## Python

### Версия
Python 3.12. Никаких `typing.Dict` (используй `dict`), никаких `typing.Optional` (используй `X | None`), никаких `List` (используй `list`).

### Окружение разработки
- После установки runtime-зависимостей ставь dev/test extras: `pip install -e ".[dev,test]"`.
- Для повторяемой базовой среды используй `make dev-setup` или `pip install -r requirements.lock`.

### Форматирование
- **black** line-length 100
- **ruff** с правилами: E, F, W, I, B, C4, DJ, N, UP, ANN, TCH, RET, ARG, SIM, ERA, PL, RUF
- **mypy** strict на `apps/` и `shared/`, менее строго на `tests/`, выключено на `migrations/`

### Названия
- Модули, пакеты, функции, переменные — `snake_case`
- Классы — `CamelCase`
- Константы — `UPPER_SNAKE_CASE`
- Приватные — `_underscore_prefix`
- Protected-но-реально-приватные — НЕ используем `__dunder__` имена (это Python-магия)

### Длина
- Функция — **до 30 строк тела**, максимум 50. Если больше — выделяй вложенные функции / классы.
- Класс — **до 200 строк**. Больше — декомпозируй.
- Файл — **до 400 строк**. Больше — разбей на модули.

Эти лимиты — предупреждение, а не запрет. Но превысил — аргументируй в PR.

### Импорты
```python
# 1. стандартная библиотека
import logging
from datetime import datetime

# 2. third-party
import httpx
from django.db import models
from rest_framework import serializers

# 3. первая сторона (наш код)
from apps.core.models import MsUser
from apps.directory.repositories import PanelRepository
```

- ruff --select I сортирует автоматически, НЕ пиши `from X import *`
- не пиши `import module as m` за исключением общепринятых сокращений (`np`, `pd`, `plt`)

### Типы
```python
def apply_application(
    application_id: int,
    comment: str,
    user: MsUser,
    *,
    file: UploadedFile | None = None,
) -> Application:
    ...
```

- **Все публичные функции должны иметь типы.** `mypy --strict` это проверит.
- Private-функции могут быть без типов, но лучше с ними.
- `Any` — только с комментарием почему.
- `TYPE_CHECKING` для циклических импортов.

### Docstrings
Для публичных классов и функций — Google style:
```python
def apply_application(application_id: int, comment: str) -> Application:
    """Переводит заявку в состояние apply_in_control.

    Args:
        application_id: ID существующей заявки в состоянии sent_to_control.
        comment: Комментарий контролёра.

    Returns:
        Обновлённая заявка.

    Raises:
        InvalidStateTransition: если заявка не в состоянии sent_to_control.
        PermissionDenied: если user.permission не подходит.
    """
```

Для private-функций — короткий однострочник, если нужен.

**НЕ пиши очевидное.**
```python
# плохо
def get_user_name(user):
    """Returns user name."""

# лучше — вообще без docstring для тривиального метода
def get_user_name(user):
    return user.name
```

### Комментарии

- Пиши комментарий **зачем**, а не **что**. «Что» — видно из кода.
- На русском — для бизнес-логики. На английском — для технических деталей.
- `# TODO(архитектор):` — с автором. Перед мёржем все TODO должны быть либо закрыты, либо превращены в задачу в `03-tasks/`.

### Исключения
- Свои исключения — в `apps/<app>/exceptions.py`. Наследуются от `shared.exceptions.DomainError`.
- `except Exception:` — ЗАПРЕЩЕНО без конкретной причины.
- `except Exception as e: logger.exception(...); raise` — ОК, если надо добавить контекст.

### Логирование
```python
import structlog
logger = structlog.get_logger(__name__)

logger.info("application_transition",
            application_id=app.id,
            from_state=app.status.name,
            to_state=target_state,
            user_id=user.id)
```

- **Запрещён** `print(...)`, кроме debug'а (должен быть удалён перед PR).
- Логируем структурно (keyword args), не плоский format-string.
- Уровни:
  - `debug` — для разработки, в проде фильтруется
  - `info` — ключевые события (transition, login)
  - `warning` — что-то подозрительное (rate limit hit, fallback activated)
  - `error` — ошибка с контекстом (exception + state)
  - `critical` — катастрофа (потеряны данные, сломан инвариант)

### Транзакции
```python
from django.db import transaction

@transaction.atomic
def transition_application(application_id, target_state, user):
    ...
```

- Мутации нескольких записей → **всегда транзакция**.
- Внутри транзакции — минимум I/O (никаких HTTP-запросов, отправки писем).
- Для долгих операций — `on_commit(callback)`.

### Инварианты моделей
- Все бизнес-правила — в service layer, не в models.
- Модель содержит данные + простые computed properties + валидацию (clean).
- FK `on_delete` указан всегда явно. Default — `PROTECT`.
- `default=`, `null`, `blank` указаны явно.
- `db_index=True` — всюду, где есть ORDER BY / filter.

---

## Django

### Views
- Все view — class-based (APIView или ViewSet).
- Функциональные view только для совсем тривиальных (health, ping).
- Во views — **только**: десериализация, вызов сервиса, сериализация. Никакой бизнес-логики.

### Services
- Сервисы в `apps/<app>/services/`.
- Чистые Python-классы, без Django-специфики в сигнатурах где можно.
- Принимают зависимости через конструктор (пусть через DI), не через глобальные импорты.

### Repositories
- Все `Model.objects.filter(...)` — в `apps/<app>/repositories/`.
- Сервис зовёт репозиторий, не ORM напрямую.
- Это делает сервисы тестируемыми без БД.

Да, это немного больше кода. Нет, это не over-engineering — это то, что отличает «рабочий прототип» от «поддерживаемый проект».

### Serializers
- DRF Serializer'ы — в `apps/<app>/serializers/`.
- НЕ тащи бизнес-логику в `.create()` / `.update()` — вызови сервис.
- `read_only_fields` — явно перечислены.

### URLs
- `path('...', View.as_view(), name='...')` — всегда с именем.
- Группировка: `include('apps.<app>.urls', namespace='<app>')`.

### Settings
- Нет `settings.py` — есть `settings/base.py`, `settings/dev.py`, `settings/prod.py`, `settings/test.py`.
- Секреты — `django-environ`, из `.env`. Default — fail-fast.

---

## Тесты

### Структура
```
apps/<app>/tests/
  test_models.py
  test_services.py
  test_views.py
  test_integration.py  — тесты через HTTP
  factories.py         — factory_boy
  conftest.py
```

### Именование
```python
def test_apply_application_changes_status_from_sent_to_control_to_apply_in_control(...):
    # Arrange
    ...
    # Act
    result = service.apply(...)
    # Assert
    assert result.status.name == "apply_in_control"
```

- **Длинные говорящие имена** — ОК, это тесты.
- Arrange / Act / Assert явно разделены пустой строкой.

### Параметризация
```python
@pytest.mark.parametrize("target_state,requires_comment", [
    ("apply_in_control", False),
    ("sent_to_service", False),
    ("unable", True),
])
def test_transition_validation(...):
    ...
```

### Фабрики
```python
@register
class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
    status = factory.SubFactory(ApplicationStatusFactory)
    panel = factory.SubFactory(PanelFactory)
```

### Coverage
- **Новый код — минимум 80% coverage.**
- Пропущенные строки — с комментарием почему.
- Игнорируются только: migrations, settings.py, manage.py, admin.py (если тривиальный).

---

## TypeScript / React (для фронтенда)

### Строгость
- `strict: true` в tsconfig
- `noImplicitAny`, `strictNullChecks` — on
- `any` — запрещён, кроме `unknown` → type guard → нужный тип

### Структура
FSD-подобная:
```
src/
├── app/            — роутер, providers, theme
├── pages/
├── widgets/
├── features/
├── entities/
├── shared/
│   ├── ui/
│   ├── api/        — api-client, query-keys, типы из OpenAPI
│   ├── config/
│   ├── lib/
│   └── types/
```

### Компоненты
- **Function components**, не class
- **Default export** для страниц и widgets, **named export** для всего остального
- Один компонент — один файл (`Button.tsx` + `Button.stories.tsx` + `Button.test.tsx`)

### Хуки
- Используй query-hooks из TanStack: `useQuery`, `useMutation`
- Кастомные хуки — в `features/<name>/hooks/useXxx.ts`
- Префикс `use*` обязателен

### Стили
- Tailwind classes в `className`
- Общие паттерны — через `cva` (class-variance-authority)
- Нет inline `style={{...}}` кроме случаев с динамическими значениями (цвет из БД)

### Именование
- Компоненты — PascalCase (`ApplicationCard.tsx`)
- Хуки — camelCase (`useApplications.ts`)
- Типы — PascalCase (`type Application = ...`)
- Консты — UPPER_SNAKE_CASE (`const MAX_RETRIES = 3`)

### Imports
```ts
// 1. внешние
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";

// 2. алиасы проекта
import { api } from "@/shared/api";
import { Button } from "@/shared/ui";

// 3. относительные (редко)
import { useLocalState } from "./useLocalState";
```

### State
- **Server state → TanStack Query**
- **Client state → Zustand** (если нужен глобальный)
- **Форма → React Hook Form + zod**
- **URL state → useSearchParams**

Нельзя: useState для того что на сервере. Redux. Context с большими объектами.

---

## Git

- Подробно в `git-workflow.md` и `commit-format.md`.
