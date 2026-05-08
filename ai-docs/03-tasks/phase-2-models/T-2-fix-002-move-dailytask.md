# T-2-fix-002. Перенести `DailyTask` в `apps/workflow/daily_tasks/`

> **Тип:** refactor / migration
> **Приоритет:** P2
> **Оценка:** 1 час
> **Фаза:** 2 (доработка)
> **Статус:** done

---

## Цель

`DailyTask` — последняя бизнес-модель, оставшаяся в legacy `zip/models.py`. Кодер в отчёте задал вопрос куда переносить. Архитектор решил: `apps/workflow/daily_tasks/` как отдельный sub-app параллельно с `applications` и `departures`.

Логика: DailyTask — это **рабочее задание**, такая же сущность как заявка или выезд, поэтому его место в `workflow`, а не в `directory` (где экраны/панели) и не в `notifications` (где только каналы доставки).

---

## Зависимости

- **Блокируется:** T-2-014 (workflow на месте)
- **Блокирует:** Фаза 5 — переписывание `daily_checker.py` worker'а на новый стек

---

## Что нужно сделать

### Шаг 1. Скелет sub-app

```
apps/workflow/daily_tasks/
├── __init__.py
├── apps.py             # DailyTasksConfig(label='workflow_daily_tasks')
├── models.py
├── managers.py
├── admin.py
├── tests/
│   └── __init__.py
└── migrations/
    ├── __init__.py
    ├── 0001_initial_state_import.py
    └── 0002_notified_stages.py        # T-2-029 — переход на JSON
```

### Шаг 2. `apps.py`

```python
from django.apps import AppConfig


class DailyTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow.daily_tasks'
    label = 'workflow_daily_tasks'
    verbose_name = 'Ежедневные задания'
```

Зарегистрировать в `config/settings.py` → `INSTALLED_APPS`.

### Шаг 3. `models.py`

Скопировать `class DailyTask` из текущего `zip/models.py:49+`. **Важно:**
- `db_table = 'dailytask'` — оставить (или какое сейчас в проде, проверить через `\d dailytask` в psql)
- FK на `Display`, `Executor`, `MsUser` — обновить на string-FK с новыми путями:
  - `display = models.ForeignKey('directory_displays.Display', ...)`
  - `executor = models.ForeignKey('workflow_departures.Executor', ...)` (если есть)
  - `user = models.ForeignKey('user.MsUser', ...)`

T-2-029 (`notified_stages: JSONField` вместо булевых полей) **закрывается в этой же задаче**, в миграции `0002_notified_stages.py`. См. карточку T-2-029.

### Шаг 4. State-only миграция `0001_initial_state_import.py`

```python
"""T-2-fix-002: импортируем существующую таблицу dailytask из legacy zip."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('directory_displays', '0001_initial_state_import'),
        ('user', '__latest__'),
        ('workflow_departures', '0002_departure_status_fk'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='DailyTask',
                    fields=[
                        # точная копия полей из legacy zip/models.py:49+
                        # — добавить через makemigrations и проверить
                    ],
                    options={
                        'db_table': 'dailytask',  # ИЛИ ТО ИМЯ ЧТО В ПРОДЕ
                        'verbose_name': 'Ежедневное задание',
                        'verbose_name_plural': 'Ежедневные задания',
                    },
                ),
            ],
        ),
    ]
```

**Важно:** перед тем как написать `state_operations` руками — сгенерировать через `makemigrations` (после переноса модели в новый файл и удаления из legacy) и взять `state_operations` из автогенерации. Это защита от опечаток в `field=models.CharField(...)`.

### Шаг 5. Снять модель из state legacy `zip`

`zip/migrations/00XX_remove_dailytask_from_state.py`:

```python
class Migration(migrations.Migration):
    dependencies = [
        ('zip', '__previous__'),
        ('workflow_daily_tasks', '0001_initial_state_import'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='DailyTask'),
            ],
        ),
    ]
```

### Шаг 6. Compat-shim в `zip/models.py`

```python
# в существующем zip/models.py добавить:
from apps.workflow.daily_tasks.models import DailyTask  # noqa: F401
```

### Шаг 7. T-2-029 миграция: notified_stages

Создать `0002_notified_stages.py`. Логика по карточке T-2-029:

1. Добавить поле `notified_stages = models.JSONField(default=list, blank=True)`
2. Backfill: пройти по всем `DailyTask`, собрать список из существующих булевых полей (`morning_notification_sent`, `afternoon_notification_sent`, и т.п.) → `notified_stages`
3. Удалить старые булевые поля

В этой задаче **только реализация** — пауза перед удалением старых полей в этой же задаче не нужна, т.к. булевые поля писали только worker'ы (`daily_checker.py`), а они будут переписаны в Фазе 5.

### Шаг 8. Admin

Перенести `DailyTaskAdmin` из `zip/admin.py` в `apps/workflow/daily_tasks/admin.py`. Удалить регистрацию в `zip/admin.py`.

### Шаг 9. Проверки

```bash
python manage.py check
python manage.py makemigrations --dry-run
# Должно быть пусто

# На dev копии:
./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
python manage.py migrate
# Все миграции применяются

# Смоук:
python manage.py shell -c "
from apps.workflow.daily_tasks.models import DailyTask
print(DailyTask.objects.count())
print(DailyTask.objects.first().notified_stages if DailyTask.objects.exists() else 'no rows')
"
```

---

## Критерии приёмки

- [ ] `apps/workflow/daily_tasks/` создан с моделями, миграциями, admin
- [ ] `DailyTask` доступен через `from apps.workflow.daily_tasks.models import DailyTask`
- [ ] Compat-shim `from zip.models import DailyTask` работает
- [ ] Миграции применяются на чистой и dev-копии прод-БД
- [ ] `notified_stages: JSONField` — реализован, старые булевые поля удалены
- [ ] `python manage.py check` — чисто
- [ ] Admin отображается в новом месте
- [ ] `daily_checker.py` worker не сломался (он использует через legacy импорты)

---

## Что НЕ делать

- **НЕ переписывай** `daily_checker.py` worker — это Фаза 5 (T-5-XXX)
- **НЕ меняй** API DailyTask (signatures методов) — worker зависит
- **НЕ удаляй** старые булевые поля если есть write'ы в коде, который ещё не переписан

---

## Что закрывается этой задачей

- ❌ ~~Вопрос кодера №2: «куда переносить DailyTask»~~ → ответ: `apps/workflow/daily_tasks/`
- ✅ T-2-029 (notified_stages) — реализуется в шаге 7

---

## Что НЕ закрывается

- `daily_checker.py` worker остаётся в legacy. Переписывание — Фаза 5 при работе с notification-стеком.
