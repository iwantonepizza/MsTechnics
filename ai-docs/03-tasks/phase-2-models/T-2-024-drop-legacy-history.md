# T-2-024. Удалить 5 старых History-моделей

> **Тип:** migration
> **Приоритет:** P2
> **Оценка:** 1 час
> **Фаза:** 2
> **Статус:** blocked (ждёт паузы 2 недели после T-2-023)

---

## Цель

После 2 недель работы на `ActivityLog` без инцидентов — удалить legacy-таблицы истории.

---

## Зависимости

- **Блокируется:** T-2-023 + 2-недельная пауза
- **Блокируется:** переход всего кода на `activity_logger` (внутри T-2-040, T-2-041)

---

## Предусловия

1. `python manage.py verify_activity_log` — все OK
2. `grep -rln "PanelHistoryReport\|DisplayHistoryReport\|ApplicationHistoryReport" --include="*.py" . | grep -v migrations | grep -v compat` — только через compat-shim, прод-код не пишет напрямую
3. Все views / services переписаны на `activity_logger.log(...)` (будет в рамках T-2-040, T-2-041)

---

## Что нужно сделать

### Шаг 1. Архив

```bash
pg_dump "$PROD_DATABASE_URL" -t history_panel -t history_display -t history_application \
  -f legacy_history_before_T-2-024.sql
gzip legacy_history_before_T-2-024.sql
# хранить в защищённом месте, вне git
```

### Шаг 2. Миграция

```python
# apps/activity/migrations/00XX_drop_legacy_history.py
# ВАЖНО: физически таблицы в разных app_label — нужна миграция в каждом,
# но проще — один RunSQL в activity

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('activity', 'XXXX_previous'),
    ]
    atomic = False
    operations = [
        # Удаляем из state моделей, которые в compat-shim
        migrations.RunSQL(
            sql=[
                'DROP TABLE IF EXISTS history_panel CASCADE;',
                'DROP TABLE IF EXISTS history_display CASCADE;',
                'DROP TABLE IF EXISTS history_application CASCADE;',
            ],
            reverse_sql=[
                # Необратимая миграция — вернуть нельзя без recovery из дампа
                'SELECT 1',  # noop
            ],
        ),
    ]
```

Плюс по отдельной миграции в старых apps для удаления моделей из state:

```python
# main_menu/migrations/00XX_delete_history_models.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [('main_menu', 'XXXX_previous')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # таблицы уже удалены предыдущей миграцией activity
            state_operations=[
                migrations.DeleteModel(name='PanelHistoryReport'),
                migrations.DeleteModel(name='DisplayHistoryReport'),
            ],
        ),
    ]

# application/migrations/00XX_delete_history_application.py — аналогично для ApplicationHistoryReport
```

### Шаг 3. Удалить Python-модели и compat-shim

- `main_menu/models.py` — удалить `PanelHistoryReport`, `DisplayHistoryReport` (оставить остальное)
- `application/models.py` — удалить `ApplicationHistoryReport`
- `main/templatetags/`, `main/Db/orm_query.py` — убрать импорты, использовать `ActivityLog`

### Шаг 4. Обновить admin

Удалить регистрации в старых admin.py. Админка `ActivityLog` уже показывает всё.

### Шаг 5. Тест

```bash
# Dry-run:
python manage.py migrate --plan

# На dev-копии прода:
python manage.py migrate
python manage.py check

# Ручной тест: админка /admin/activity/activitylog/ — показывает данные
# Старых ссылок в меню admin быть не должно
```

---

## Критерии приёмки

- [ ] 3 таблицы (`history_panel`, `history_display`, `history_application`) удалены физически
- [ ] Python-модели `PanelHistoryReport`, `DisplayHistoryReport`, `ApplicationHistoryReport` удалены
- [ ] Архив-дамп создан перед удалением (хранить год минимум)
- [ ] `python manage.py check` — чисто
- [ ] `grep -rln "PanelHistoryReport\|DisplayHistoryReport\|ApplicationHistoryReport" --include="*.py" .` — только в migrations
- [ ] Admin: `/admin/main_menu/panelhistoryreport/` — 404, `/admin/activity/activitylog/` — работает

---

## Что НЕ делать

- **НЕ запускай** до верификации T-2-023 (verify OK)
- **НЕ запускай** если в коде ещё есть прямые writes в старые модели
- **НЕ используй** `CASCADE DROP` без уверенности что нет FK извне
- **НЕ откатывай** миграцию без восстановления из архив-дампа

---

## Откат

Если после удаления выяснилось что данные нужны:
1. Создать таблицы из архивного дампа: `psql < legacy_history_before_T-2-024.sql`
2. Миграцию `drop_legacy_history` — `python manage.py migrate activity XXXX_previous` (откат)
3. Python-модели восстановить из git history

Это сложно. Потому и пауза 2 недели — чтобы за это время всплыли баги.
