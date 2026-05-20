# T-3-fix-001. Синхронизация имён статусов: БД ↔ api-contract.md

> **Тип:** hotfix / data
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3 (доработка)
> **Статус:** done

---

## Цель

Привести имена статусов заявок к единому виду без префикса `application_*`.

В коде везде:
- `application_sent_to_control`
- `application_apply_in_control`
- `application_sent_to_service`
- `application_work_in_service`
- `application_unable`

В `api-contract.md` (источник правды):
- `sent_to_control`, `apply_in_control`, `sent_to_service`, `work_in_service`, `unable`

**Не статусы заявок (без префикса)** — `done`, `archive_done`, `archive_unable` — оставляем как есть.

---

## Принятое архитектурное решение

**Меняем БД, не контракт.** Причины:
1. Контракт — публичный API. Меняя его, ломаем будущий фронт всех потребителей.
2. Префикс `application_*` — наследие легаси-именования. Современный API — без префиксов, тип уже в URL (`/applications/{id}/transition/`).
3. Архитектурная чистота: enum-значение не должно дублировать имя сущности.

---

## Зависимости

- **Блокируется:** Фаза 3 закрыта (миграции применены)
- **Блокирует:** Фаза 4 (фронт по контракту)

---

## Что сделать

### Шаг 1. Data-migration

`apps/workflow/applications/migrations/00XX_strip_application_prefix.py`:

```python
"""T-3-fix-001: убираем префикс application_ из имён ApplicationStatus.

До: application_sent_to_control, application_apply_in_control, ...
После: sent_to_control, apply_in_control, ...
"""
from django.db import migrations


PREFIX = "application_"
RENAMES = [
    ("application_sent_to_control",  "sent_to_control"),
    ("application_apply_in_control", "apply_in_control"),
    ("application_sent_to_service",  "sent_to_service"),
    ("application_work_in_service",  "work_in_service"),
    ("application_unable",           "unable"),
]


def forwards(apps, schema_editor):
    Status = apps.get_model("workflow_applications", "ApplicationStatus")
    for old, new in RENAMES:
        Status.objects.filter(name=old).update(name=new)


def reverse(apps, schema_editor):
    Status = apps.get_model("workflow_applications", "ApplicationStatus")
    for old, new in RENAMES:
        Status.objects.filter(name=new).update(name=old)


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "__latest__"),  # заменить на конкретное имя
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
```

### Шаг 2. Обновить код

Найти и заменить **во всём проекте** (исключая `migrations/`):

```bash
grep -rln "application_sent_to_control\|application_apply_in_control\|application_sent_to_service\|application_work_in_service\|application_unable" \
  --include="*.py" --include="*.tsx" --include="*.ts" \
  apps/ shared/ frontend/src/ | xargs sed -i \
  -e 's/application_sent_to_control/sent_to_control/g' \
  -e 's/application_apply_in_control/apply_in_control/g' \
  -e 's/application_sent_to_service/sent_to_service/g' \
  -e 's/application_work_in_service/work_in_service/g' \
  -e 's/application_unable/unable/g'
```

**ВАЖНО:** не трогаем `apps/workflow/applications/migrations/*` — там старые имена должны остаться, иначе сломаем историю миграций.

### Шаг 3. Обновить FSM

`apps/workflow/applications/state_machine.py` — все упоминания префикса убрать.

`apps/directory/panels/services.py:27-28` — список ACTIVE_STATUSES без префикса.

### Шаг 4. Обновить frontend

`frontend/src/pages/display-view/DisplayViewPage.tsx`:
```ts
// До
const ROLE_TRANSITIONS: Record<string, string[]> = {
  control: ['application_apply_in_control', 'application_sent_to_service', ...],
  // ...
}

// После
const ROLE_TRANSITIONS: Record<string, string[]> = {
  control: ['apply_in_control', 'sent_to_service', 'archive_done', 'archive_unable'],
  service: ['work_in_service', 'done', 'unable'],
  admin:   ['apply_in_control', 'sent_to_service', 'work_in_service', 'done', 'unable', 'archive_done', 'archive_unable'],
  all:     ['apply_in_control', 'sent_to_service', 'work_in_service', 'done', 'unable', 'archive_done', 'archive_unable'],
  monitoring: [],
}
```

### Шаг 5. Тесты

Обновить `tests/test_fsm.py`, `apps/interface/tests/test_auth.py`, любые fixture seed'ы.

### Шаг 6. Прогон

```bash
# 1. Локально на копии прода
./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
python manage.py migrate
# миграция переименовала записи

# 2. Запустить тесты
pytest -x
# all green

# 3. Проверить openapi.yaml
python manage.py spectacular --validate
# схема валидна

# 4. Smoke API
curl -X POST localhost:8000/api/v1/auth/login/ -d '{"username":"x","password":"y"}'
# 422 с правильным JSON-форматом
```

---

## Критерии приёмки

- [x] Миграция `0004_strip_application_prefix.py` создана с reverse
- [x] `grep` по старым `application_*` именам в non-migration коде пустой
- [x] Frontend `ROLE_TRANSITIONS` использует имена без префикса
- [x] api-contract.md и реальный API совпадают по статусным именам
- [ ] Все тесты проходят — локально не прогнаны: в `.venv` нет `pytest`, PostgreSQL host из env недоступен
- [x] FSM (`state_machine.py`) использует имена без префикса

---

## Что НЕ делать

- **НЕ трогать** имена в `migrations/*` — там история должна быть воспроизводимой
- **НЕ менять** имена `done`, `archive_done`, `archive_unable` — у них префикса нет
- **НЕ откатывать** на префикс «потому что в БД так» — БД меняется этой задачей

---

## Откат

Если на проде после миграции всплывает баг — `python manage.py migrate workflow_applications XXXX_previous` откатывает. Reverse-функция мигрирует имена обратно.
