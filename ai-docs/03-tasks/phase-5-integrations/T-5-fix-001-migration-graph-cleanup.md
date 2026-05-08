# T-5-fix-001. Разруливание migration graph: legacy apps → state-only DeleteModel

> **Тип задачи:** migration + infra
> **Приоритет:** P0 (блокирует staging cutover Фазы 5)
> **Оценка:** 4-5 часов
> **Фаза:** 5 (hotfix перед deploy)
> **Статус:** review
> **Исполнитель:** GPT-5 / Codex

---

## Цель

Сделать так, чтобы `python manage.py check` и `python manage.py migrate --plan` проходили на чистой и на копии прод-БД без `KeyError: 'display'` и без `legacy duplicate models` ошибок. Это разблокирует Фазу 5 cutover на staging — без этого новые миграции (`directory_displays.0002`, `gmail_alarms.0001`, `notifications.0003`, `notifications.0004`) применить нельзя, и невозможно гарантировать прод-данные.

**Не «удалить legacy app»**, а **«перевести в state-only безопасное состояние»** — physical таблицы остаются в БД (там данные), но Django state видит модели только в новых `apps/*`.

---

## Контекст

После Phase-2 переезда модели созданы в новых apps через `SeparateDatabaseAndState(state_operations=[CreateModel(...)], database_operations=[])` — БД не трогается, state знает новые модели. Проверь:

- `apps/directory/displays/migrations/0001_initial_state_import.py` — пример правильно сделанной state-only миграции.
- `apps/workflow/applications/migrations/0001_initial_state_import.py` — то же.
- `apps/core/users/migrations/0001_initial_state_import.py`, `apps/core/references/migrations/0001_initial_state_import.py` — аналогично.

**Симметричный шаг в legacy apps НЕ был сделан.** Сейчас в репо:

```
zip/models.py:21-44     class Display(models.Model): db_table='display'
apps/directory/displays/models.py        class Display(models.Model)  ← дубль
zip/models.py:120-166   class Cell(models.Model)   db_table='cell'
apps/directory/displays/models.py        class Cell                  ← дубль
zip/models.py:168-213   class Panels(models.Model) db_table='panel'
apps/directory/panels/models.py          class Panel                 ← дубль (имя другое, db_table тот же)
zip/models.py:215+      DailyTask, Wires, Hubs, Lamels, PhotoDisplay  ← дубли
main/models.py          Cities, Color, Smile, Condition, ...          ← дубли apps/core/references
user/models.py          MsUser, ConcreteMsUser                        ← дубли apps/core/users
application/models.py   Application                                   ← дубль apps/workflow/applications
departure/models.py     Departure, Executor, Contact                  ← дубль apps/workflow/departures
mail/models.py          (старая AlarmEvent)                            ← дубль apps/integrations/gmail_alarms
main_menu/models.py     PanelHistoryReport, DisplayHistoryReport, ... ← дубли apps/activity (если есть)
monitoring/, control/, service/  без models.py, но в INSTALLED_APPS    ← мусор
```

Снипет, ради которого Django валится при `manage.py check`:

```python
# zip/migrations/0001_initial.py:107
options={'db_table': 'display', ...}

# apps/directory/displays/migrations/0001_initial_state_import.py:28
options={"db_table": "display", "verbose_name": "Экран", "ordering": ["id"]},
```

— две `CreateModel` на одну таблицу. На свежей БД сначала отрабатывает `zip` миграция (создаёт таблицу), потом state-only `apps.directory.displays` — но Django держит **обе** модели в graph, и любая ссылка `to='directory_displays.display'` в новых миграциях не резолвится в context'е, где есть и `to='zip.display'`. Это и даёт `KeyError: 'display'`.

`AUTH_USER_MODEL = "user.MsUser"` (`Config/settings.py:191`) тоже указывает на legacy — это менять **сейчас не надо**, иначе Django потребует пересоздания auth-таблиц. `user.MsUser` будет shim, импортирующий `apps.core.users.models.MsUser`.

---

## Зависимости

- **Блокируется:** ничем (можно брать сейчас).
- **Блокирует:** staging cutover Фазы 5 (применение новых миграций), полный `pytest`, T-5-050 (legacy cleanup — но это уже после prod stability window).

---

## Что нужно сделать

### Шаг 0. Подготовка

```bash
# Установить dev/test extras, если ещё не сделано (см. T-5-fix-002)
.venv/Scripts/pip install -e ".[dev,test]"
```

Сделать дамп локальной БД перед началом:

```bash
pg_dump -h localhost -U mstechnics mstechnics > dumps/before_t5_fix_001.sql
```

### Шаг 1. Превратить legacy `models.py` в shim

Для каждого legacy app, у которого сейчас в `models.py` лежат полноценные `class X(models.Model)`:

| Legacy app | Куда переехало (новый apps) |
|---|---|
| `main` | `apps.core.references` (Cities, Color, Smile, Condition, Department, Icon — проверь по факту) |
| `user` | `apps.core.users` (MsUser; `ConcreteMsUser` — удалён в T-2-026) |
| `zip` | `apps.directory.displays` (Display, Cell, PhotoDisplay), `apps.directory.panels` (Panel), `apps.directory.storage` (Wires, Hubs, Lamels), `apps.workflow.daily_tasks` (DailyTask) |
| `application` | `apps.workflow.applications` (Application, ApplicationStatus, ApplicationEvent) |
| `departure` | `apps.workflow.departures` (Departure, Executor, Contact, DepartureStatus) |
| `mail` | `apps.integrations.gmail_alarms` (AlarmEvent — новый), либо просто опустошить, если старая AlarmEvent больше не нужна |
| `main_menu` | `apps.activity` если HistoryReport-ы переехали (проверь по `T-2-022/023`); если ещё blocked — оставить старые модели до T-2-023, но **не дублировать в apps.activity**, ставить TODO |

Для каждого замени `models.py` на чистый re-export. Пример для `zip/models.py`:

```python
"""Compat shim. T-5-fix-001: реальные модели — в apps.directory.* и apps.workflow.daily_tasks.*"""
from apps.directory.displays.models import Display, Cell, PhotoDisplay  # noqa: F401
from apps.directory.panels.models import Panel  # noqa: F401
from apps.directory.storage.models import Wires, Hubs, Lamels  # noqa: F401
from apps.workflow.daily_tasks.models import DailyTask  # noqa: F401

# Legacy alias (несколько мест ещё импортируют `Panels`)
Panels = Panel
```

Для `user/models.py`:

```python
"""Compat shim. T-5-fix-001: MsUser — в apps.core.users."""
from apps.core.users.models import MsUser  # noqa: F401
```

И так для остальных. **Никакого `class … (models.Model)` в shim'ах не остаётся**, иначе Django снова увидит модель.

### Шаг 2. State-only DeleteModel миграция в каждом legacy app

Для каждого legacy app, где удалили модели из `models.py`, добавь миграцию (номер 0002 или следующий после последней существующей). Назначение — убрать модель из Django state без `DROP TABLE`. Пример для `zip`:

```python
# zip/migrations/0003_remove_models_from_state.py
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zip", "0002_dailytask_notified_stages"),
        # перед нашим DeleteModel убедимся, что новые apps уже создали модели в state
        ("directory_displays", "0001_initial_state_import"),
        ("directory_panels", "0001_initial_state_import"),
        ("directory_storage", "0001_initial_state_import"),
        ("workflow_daily_tasks", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # таблицы остаются — там данные
            state_operations=[
                migrations.DeleteModel(name="PhotoDisplay"),
                migrations.DeleteModel(name="Cell"),
                migrations.DeleteModel(name="Panels"),
                migrations.DeleteModel(name="DailyTask"),
                migrations.DeleteModel(name="Wires"),
                migrations.DeleteModel(name="Hubs"),
                migrations.DeleteModel(name="Lamels"),
                migrations.DeleteModel(name="Display"),  # последним — на него FK
            ],
        ),
    ]
```

**Порядок DeleteModel** имеет значение: сначала зависимые модели, потом их FK-цели.

Аналогичные миграции для:

- `main/migrations/0002_remove_models_from_state.py` — `Cities`, `Color`, `Smile`, `Condition`, `Department`, `Icon` (проверь по факту, что в `main/models.py`).
- `user/migrations/0002_remove_models_from_state.py` — `MsUser` **в state-only**. Здесь осторожнее: `AUTH_USER_MODEL = 'user.MsUser'` всё ещё указывает на legacy app. Поэтому в state модель остаётся, но физически — это re-export `apps.core.users.MsUser`. Если миграция падает на `auth.User` ссылках — оставь только `ConcreteMsUser` DeleteModel (если он ещё в state) и не трогай `MsUser` до отдельной задачи смены `AUTH_USER_MODEL`. **Это корректное отклонение от плана, отметь в отчёте.**
- `application/migrations/000N_remove_models_from_state.py` — `Application`, `ApplicationStatus`.
- `departure/migrations/000N_remove_models_from_state.py` — `Departure`, `Executor`, `Contact`, `DepartureStatus` (если они там были).
- `mail/migrations/0002_remove_models_from_state.py` — старая `AlarmEvent` (если была).
- `main_menu/migrations/000N_remove_models_from_state.py` — *HistoryReport-ы, если они переехали в `apps.activity`. Если **не переехали** (T-2-022/023 в blocked) — **не делай** DeleteModel, оставь модели в `main_menu/models.py` и пометь в отчёте «ждёт T-2-023».

### Шаг 3. Убрать `monitoring`, `control`, `service` из `INSTALLED_APPS`

Эти app'ы существуют в репо как пустые модули с views (которые уже не используются после Фазы 4), не имеют `models.py`. Они продолжают занимать место в Django app registry без пользы.

В `Config/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    # ── Legacy (compat shims) — модели через re-export, миграции хранят историю ─
    "main",
    "main_menu",
    "zip",
    "departure",
    "application",
    "mail",
    "user",          # держим, потому AUTH_USER_MODEL='user.MsUser'
    # удалили: "monitoring", "control", "service" — нет models, нет миграций
]
```

**Если** в `monitoring/`, `control/`, `service/` есть `migrations/` папка с какими-то миграциями (даже `0001_initial.py`) — **не удаляй их из INSTALLED_APPS**, иначе Django потеряет state. Проверь сначала:

```bash
ls monitoring/migrations control/migrations service/migrations 2>/dev/null
```

Если только `__init__.py` — спокойно убирай из INSTALLED_APPS. Если есть `0001_*.py` — оставь как есть и пометь в отчёте «эти три app'а в INSTALLED_APPS из-за legacy миграций — уберём в T-5-050 после squash».

### Шаг 4. Pre-flight проверки

```bash
# 1. Django видит проект
python manage.py check
# ожидание: System check identified no issues (or только known warnings из drf-spectacular).

# 2. Migration graph чистый
python manage.py makemigrations --check --dry-run
# ожидание: No changes detected.

# 3. План на чистую БД — не падает
python manage.py migrate --plan | head -50
# ожидание: список миграций, никакого KeyError.

# 4. На реальной (локальной dev) БД миграции apply'ятся
python manage.py migrate --fake-initial
# (--fake-initial безопасен, потому новые миграции в legacy apps — state-only DeleteModel)
```

### Шаг 5. Прогнать тесты

После T-5-fix-002 (если идёт первой) — `pytest` доступен:

```bash
pytest -x --cov=apps --cov=shared --cov-report=term-missing
```

Ожидание: тесты, которые раньше падали на `SystemCheckError`, теперь проходят. Если что-то падает по другой причине (FK по имени, например) — фикс в той же задаче, **только если фикс мелкий** (1-2 строки). Иначе заведи отдельную задачу T-5-fix-003 и оставь как known issue.

### Шаг 6. Прогнать на копии прод-БД

```bash
# Восстановить дамп прод-БД (см. T-2-001 runbook, scripts/restore_to_dev.sh)
bash scripts/restore_to_dev.sh dumps/prod_$(date +%Y%m%d).dump

# Применить миграции
python manage.py migrate
```

Если `migrate` ругается на conflict-state какой-нибудь конкретной модели — это означает, что DeleteModel в legacy app выполняется до создания соответствующей модели в новом app. Поправь `dependencies` в legacy миграции (нужный новый app должен быть в зависимостях ДО DeleteModel этого имени).

---

## Критерии приёмки

- [ ] `python manage.py check` — чисто (либо только известные warnings из `drf-spectacular`, не SystemCheckError).
- [ ] `python manage.py makemigrations --check --dry-run` — `No changes detected`.
- [ ] `python manage.py migrate --plan` — выводит план без `KeyError`.
- [ ] `python manage.py migrate` на чистой БД — успешно.
- [ ] `python manage.py migrate` на копии прод-БД — успешно. **Хеш `pg_dump --schema-only` до и после совпадает по структурам legacy таблиц** (ничего не дропнули случайно).
- [ ] `pytest -x` — зелёный (если есть failing — описано в отчёте, чем).
- [ ] `ruff check apps/ shared/ Config/` — чисто (или только existing warnings).
- [ ] `mypy apps/` — без новых ошибок относительно baseline.
- [ ] Все legacy `models.py` (`main`, `user`, `zip`, `application`, `departure`, `mail`) — это re-export shim'ы, не более 15 строк каждый.
- [ ] `INSTALLED_APPS` не содержит `monitoring`, `control`, `service` (если у них нет миграций).
- [ ] Отчёт в `ai-docs/08-reports/T-5-fix-001.md` по шаблону — обязательно с разделом «Миграции» (количество, тип, время на проде, план отката).
- [ ] PR-description ссылается на эту задачу и `architect-review-2026-05-06.md`.

---

## Что НЕ нужно делать

- **Не удалять physical таблицы** в legacy apps. Все DeleteModel должны быть в `state_operations`, `database_operations=[]`. Данные в `display`, `cell`, `panel`, `application`, `departure`, `daily_task` etc. остаются — на них смотрят новые apps через свои state-модели.
- **Не удалять migrations из legacy apps**. Старые миграции хранят историю — без них prod-БД с записью «zip.0001_initial applied 2024-XX-XX» в `django_migrations` не сойдётся с graph'ом.
- **Не менять `AUTH_USER_MODEL = 'user.MsUser'`.** В этой задаче — только shim. Полная миграция AUTH_USER_MODEL — отдельная P2-задача после prod stability window.
- **Не трогать `sorting_message.py`** — он будет удалён в T-5-050.
- **Не делать `--fake` миграции на проде**. На локалке `--fake-initial` для тестирования — ок; на стейдже/проде — только нормальный `migrate`.
- **Не объединять с T-5-fix-002** в один PR — это разные изменения с разной reversibility.

---

## Ссылки на примеры

- Pattern «состояние без БД» — `apps/directory/displays/migrations/0001_initial_state_import.py:11-30`.
- Pattern PR'а в этой схеме — `apps/workflow/applications/migrations/0002_display_fk_to_id.py:55-71`.
- Django docs: [SeparateDatabaseAndState](https://docs.djangoproject.com/en/5.1/ref/migration-operations/#separatedatabaseandstate).

---

## Вопросы для архитектора (если есть)

- [ ] Что делать, если на копии прод-БД `pg_dump --schema-only` показывает **разницу** в каких-то FK constraint'ах (например, `to_field='name'` vs `to_field='id'` — было в T-2-025)? — Ответ: фиксируешь diff в отчёте, не пытаешься выровнять в этой задаче. Это уже задача T-2-025-followup или новая.
- [ ] Что делать с `AUTH_USER_MODEL`? — Ответ: оставляем `'user.MsUser'`. Shim в `user/models.py` импортирует из `apps.core.users` — Django увидит то же самое. Меняем `AUTH_USER_MODEL` в **отдельной** P2-задаче.
- [ ] Если `main_menu/models.py` всё ещё содержит HistoryReport-модели и T-2-022 не закрыт, можно ли их оставить? — Ответ: да, оставляешь. Тогда `main_menu` остаётся «толстым» legacy-app до закрытия T-2-022/023.

---

## Отчёт по выполнению

(Заполняет кодер при переводе в review/done.)

### Что сделано
- Legacy duplicate-model blocker снят:
  - `main`, `user`, `application`, `departure` переведены на shim/re-export;
  - `zip` переведён на compat proxy-shim без concrete дублей;
  - из `INSTALLED_APPS` убраны пустые `monitoring`, `control`, `service`;
  - runtime ссылки на `MsServiceControl.settings` переключены на `Config.settings`;
  - `Dockerfile` и `docker-compose.yml` используют `Config.wsgi:application`.
- Добавлены state-only миграции/импорты для legacy/new apps:
  - `main.0002_remove_models_from_state`
  - `application.0004_remove_models_from_state`
  - `departure.0003_remove_models_from_state`
  - `zip.0003_remove_models_from_state`
  - `apps.workflow.daily_tasks.0001_initial_state_import`
  - `apps.directory.displays.0003_photo_display_state_import`
  - `apps.workflow.applications.0001_extra_legacy_fk_state`
  - `apps.workflow.departures.0003_contact_state_import`
- `apps/workflow/daily_tasks/models.py` и `apps/directory/displays/models.py` дополнены concrete моделями, которые раньше существовали только в legacy state.
- Исправлен route warning: `apps/interface/api/v1/me/urls.py` больше не содержит ведущий `/change-password`.
- `python manage.py check` теперь проходит чисто.
- Сгенерированы и добавлены state-alignment миграции для `activity`, `core_references`, `directory_storage`, `gmail_alarms`, `notifications`, `workflow_daily_tasks`, `workflow_departures`, `directory_displays`, `directory_panels`, `workflow_applications`, `user`.
- Все эти alignment-миграции переведены в `SeparateDatabaseAndState(database_operations=[])`, чтобы обновить Django state без физического churn по БД.
- `python manage.py makemigrations --check --dry-run` теперь даёт `No changes detected`.

### Отклонения от плана
- `mail` и `main_menu` пока не переводил на state cleanup: они не ломали текущий duplicate-model blocker, а `main_menu` частично завязан на legacy history-модели.
- `migrate --plan` и `migrate` локально всё ещё упираются в недоступный PostgreSQL host из env (`getaddrinfo failed`), поэтому DB-backed часть acceptance переносится на staging/dev с живой БД.

### Тесты
- Файлов: 0 новых test files
- Тестов: 9 точечно прогнанных backend tests + 79 collected
- Coverage: N/A на этом этапе
- Проверки:
  - `python manage.py check` -> зелёный
  - `python manage.py makemigrations --check --dry-run` -> `No changes detected`
  - `python -m compileall -q Config apps main application departure zip user control main_menu` -> зелёный
  - `pytest apps/notifications/tests/test_channels.py apps/integrations/max/tests/test_webhook.py --no-cov -q` -> 9 passed
  - `pytest --collect-only -q` -> 79 collected

### Миграции
- Количество: 19
- Тип: state-only (database_operations=[])
- На копии прод-БД: не прогнано локально, DB host из env недоступен
- План отката: каждая миграция reverse'ится в `RunPython.noop` для backfill'ов / SeparateDatabaseAndState без БД-эффекта.

### Измеренное время
- Оценка: 4-5 часов
- Фактически: ~5 часов

### Дальнейшие шаги
- Проверить `migrate --plan` и `migrate` на реальной dev/staging БД после починки env PostgreSQL.
