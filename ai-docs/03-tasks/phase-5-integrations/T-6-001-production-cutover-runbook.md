# T-6-001. Production cutover runbook (на сервере)

> **Тип задачи:** infra + migration + docs
> **Приоритет:** P0 (текущий блокер — пользователь не может задеплоить)
> **Оценка:** 3-4 часа (1ч исследование сервера + 1.5ч runbook + 1ч прогон на staging-копии + 0.5ч документация)
> **Фаза:** 6 (production)
> **Статус:** review
> **Исполнитель:** GPT-5 Codex

---

## Цель

Снять текущий блокер деплоя («миграции не делаются»). Удалить дублирующий путь восстановления (`scripts/prod_dump_compat.sql`). Описать один и единственный production cutover runbook, который реально работает на Linux-сервере владельца. Прогнать его на копии прод-БД ещё раз — теперь без compat-патча.

---

## Контекст

После закрытия T-5-fix-003 в репозитории сосуществуют **два пути** перевода legacy prod-схемы на новые id-based FK:

### Путь A — `scripts/prod_dump_compat.sql` (старый, костыль)

Применяется ПОСЛЕ `pg_restore` и ДО `migrate`. Делает:

1. `UPDATE django_migrations SET name='0001_initial_state_import' WHERE app='user' AND name='0001_initial'` — переименование записи в django_migrations, чтобы Django думал, что state-import уже applied.
2. `INSERT INTO django_migrations` для `core_references.0001_initial_state_import`.
3. **Физически** дропает legacy `_fk_<table>_name` constraints + `_id_<hash>_like` индексы.
4. **Физически** конвертит `display.city_id`, `panel.{display,condition,department,application_status}_id`, `cell.{display,panel}_id`, `application.status_id`, color/icon ссылки в `bigint` через `UPDATE … SET col = id::text … ALTER COLUMN col TYPE bigint`.

### Путь B — forward-only migrations (новое, правильное)

з T-5-fix-003:
- `apps/core/users/migrations/0003_align_user_physical_schema.py`
- `apps/directory/displays/migrations/0005_convert_display_city_fk_to_id.py`
- `apps/directory/displays/migrations/0006_convert_cell_fk_storage_to_id.py`
- `apps/directory/panels/migrations/0004_convert_panel_fk_storage_to_id.py`

Делают ту же физическую конверсию, но идиоматично через Django (`atomic=False`, RunSQL backfill + RunPython validation + RENAME COLUMN + новый FK на id).

### Что ломается на сервере

Сценарий, который, скорее всего, происходит у пользователя:

1. `pg_restore` дампа → legacy схема с `varchar(name)` FK + legacy `django_migrations` записями (`zip.0001_initial`, `application.0001_initial`, …).
2. Либо применён `prod_dump_compat.sql`, либо нет.

**Если compat применён + потом `migrate`:**
- compat уже перевёл `panel.display_id` в `bigint`.
- миграция `panels/0004_convert_panel_fk_storage_to_id.py` запускается; внутри:
  ```sql
  UPDATE public.panel AS p
  SET display_new_id = d.id
  FROM public.display AS d
  WHERE p.display_id = d.name;
  ```
- `p.display_id` — уже `bigint` (compat сделал), `d.name` — `varchar`. Postgres: `operator does not exist: bigint = character varying`. **Падает.**

**Если compat НЕ применён + потом `migrate`:**
- Django видит, что в `django_migrations` стоит `user.0001_initial` (старое имя), а в коде есть `apps.core.users.0001_initial_state_import` (новое). Это считается **не applied**.
- Django пытается применить `core_references.0001_initial_state_import` — state-only, проходит.
- Дальше Django применяет `users.0001_initial_state_import` — state-only, проходит.
- Но потом Phase-2 миграции (T-2-020 ApplicationEvent, T-2-022 ActivityLog, T-2-025 FK to_id, …) ожидают, что таблицы уже существуют в правильной форме. На live legacy схеме — `application_event` таблицы нет, **миграция её создаёт**. Должно пройти. Дальше `panels/0004` снова падает, потому что в БД physical FK varchar, а Django state их уже считает bigint (после 0003_alter_panel_options_alter_panel_condition_and_more.py state-only).

В любом раскладе текущий двойной путь — это мина.

### Решение

**Удалить Путь A (`prod_dump_compat.sql`) полностью.** Сделать одну выверенную последовательность для Linux-сервера, которая прогоняется в один присест на копии прод-БД.

---

## Зависимости

- **Блокируется:** ничем (можно брать сейчас).
- **Блокирует:** реальный staging cutover владельца → 2-недельный stability window → T-5-050.

---

## Что нужно сделать

### Шаг 0. Запросить у владельца параметры сервера

В блоке «Вопросы для архитектора» в этой карточке (можно ответить кодеру самостоятельно, но указать в отчёте):

- Linux-дистрибутив сервера (Ubuntu/Debian/RHEL/…).
- Версия PostgreSQL на сервере.
- спользует ли владелец `docker compose` или нативный PostgreSQL.
- Путь к прод-дампу на сервере.
- Как сейчас запускается Django (gunicorn? supervisor? systemd?).
- Текущий вывод `python manage.py showmigrations | tail -100` с сервера — **ключевой артефакт**, который покажет, какие миграции сервер считает applied.

Это нужно ДО начала Шага 1.

### Шаг 1. Удалить `scripts/prod_dump_compat.sql`

```bash
git rm scripts/prod_dump_compat.sql
```

В `scripts/restore_dump.ps1` (Windows) — удалить блок `Get-Content -Raw $compatSqlPath | docker exec -i $dbContainer psql …`.

### Шаг 2. Переписать `scripts/restore_to_dev.sh` (Linux)

Сейчас `restore_to_dev.sh` использует `psql` для `.sql.gz` дампов и **не вызывает** ни compat, ни migrate. Это устарело. Переписать так:

```bash
#!/usr/bin/env bash
# restore_to_dev.sh — залить прод-дамп в dev/staging БД и прогнать миграции
# спользование: DATABASE_URL="postgres://..." ./scripts/restore_to_dev.sh db_dumps/mstechnics.dump
set -euo pipefail

DUMP_FILE="${1:?Укажи файл дампа: $0 <path/to/mstechnics.dump>}"
: "${DATABASE_URL:?Нужна переменная DATABASE_URL=postgres://user:pass@host/db}"

# Безопасность: не даём перезаписать прод
if [[ "$DATABASE_URL" == *"mstechnics.ru"* ]] || [[ "$DATABASE_URL" == *"185.251"* ]]; then
  echo "ОТКАЗАНО: DATABASE_URL выглядит как прод. Останавливаемся." >&2
  exit 1
fi

echo "[1/4] Очищаем dev/staging-БД..."
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" --quiet

echo "[2/4] Восстанавливаем из $DUMP_FILE..."
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$DATABASE_URL" "$DUMP_FILE"

echo "[3/4] Сверяем django_migrations с актуальным graph..."
python manage.py showmigrations | tail -60

echo "[4/4] Применяем миграции..."
python manage.py migrate

echo "Готово. Smoke:"
python manage.py check
```

Никакого compat, никаких костылей. Один `pg_restore` + один `migrate`. Если migrate падает — это диагностируется на этапе `showmigrations`, см. troubleshooting ниже.

### Шаг 3. Прогнать на чистой staging-копии (без compat)

```bash
# Локально (или на staging-host)
docker compose down -v
docker compose up -d db

# Восстановить прод-дамп
DATABASE_URL="postgres://mstechnics:dev@localhost:5432/mstechnics" \
  ./scripts/restore_to_dev.sh db_dumps/mstechnics.dump
```

Ожидание — `migrate` проходит до конца **без** ошибок `operator does not exist`, потому что compat НЕ применялся. forward-only миграции делают конверсию сами.

Если падает — **это и есть точка диагностики**. Скорее всего падает на `panels/0004` или `displays/0005`, и причина в том, что какие-то миграции в `django_migrations` дампа уже отмечены applied (но мы их применять собирались). Тогда нужен Шаг 4.

### Шаг 4. Troubleshooting через `showmigrations` + `--fake`

Запустить:

```bash
python manage.py showmigrations 2>&1 | tee logs/t6_001_showmigrations_before.log
```

Вывод покажет матрицу:
- `[X]` — миграция applied
- `[ ]` — не applied

**Случай A: legacy миграции есть, новые state-import нет.**

Это нормально на свежем restore прод-дампа. Просто запускаем `migrate`. Forward-only миграции (T-2-025, T-5-fix-003 series) сделают конверсию.

**Случай B: новые state-import уже applied (например, после ручных экспериментов).**

```bash
# Посмотреть конкретно user app
psql $DATABASE_URL -c "SELECT app, name, applied FROM django_migrations WHERE app IN ('user', 'core_users', 'core_references', 'directory_displays', 'directory_panels') ORDER BY applied;"
```

Если видишь `core_users.0001_initial_state_import [X]` + `user.0001_initial [X]` (старое имя сохранилось от raw legacy дампа) — нужен ручной `--fake`:

```bash
# Зафиксировать, что в state эта миграция типа применена, но физически SQL не выполнять
python manage.py migrate --fake <app> <migration_name>
```

Какие миграции `--fake`'ать, решает кодер по факту diff'а между `showmigrations` и code.

**Случай C: миграция падает на конкретном SQL** (`column does not exist`, `operator does not exist`).

Этого быть не должно после удаления compat — но если случилось:
1. Дамп логи: `python manage.py migrate --verbosity=3 2>&1 | tee logs/t6_001_migrate_error.log`.
2. Внутри ошибки — точное имя миграции и SQL. Привязываем к конкретной миграции в коде.
3. Если миграция предполагает старую схему, а реально дамп имеет более новую (после compat был применён к дампу ранее) — нужно `--fake` именно эту миграцию.

### Шаг 5. Финальный прогон на копии прод-БД

После того как Шаг 4 разрешён:

```bash
DATABASE_URL="..." ./scripts/restore_to_dev.sh db_dumps/mstechnics.dump 2>&1 | tee logs/t6_001_final_run.log
python manage.py check
python manage.py showmigrations 2>&1 | tee logs/t6_001_showmigrations_after.log
```

Smoke:

```bash
python manage.py runserver 0.0.0.0:8000 &
curl -sf http://localhost:8000/api/v1/health/live
curl -sX POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"...","password":"..."}'
curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/displays/
```

Все три должны вернуть 200 + валидный JSON.

### Шаг 6. Написать `ai-docs/06-integrations/production-cutover-runbook.md`

Финальный документ для владельца. Содержит:

1. **Pre-flight checklist** — что должно быть готово на сервере (Postgres 16, Python 3.12, .venv, .env, dump).
2. **Backup current prod** — `pg_dump текущая_прод_бд > backup_pre_cutover.dump` **обязательно** перед чем-либо.
3. **Maintenance window** — **подтверждено владельцем 2026-05-17**: пользователи работают **08:00–22:00 МСК**, ночью никогда. Cutover планировать **после 22:00**, окно до 6 часов гарантированно без пользователей. Простой режим: downtime, не нужен blue/green. Что показать пользователям утром (если упало) — «сервис на профилактике», но это не должно случиться, потому что прогон на копии прод-БД (T-5-fix-003) уже зелёный.
4. **Step-by-step shell-commands** для Linux:
   ```bash
   # 1. Остановить старый прод
   sudo systemctl stop mstechnics-old
   # 2. Backup current DB
   pg_dump -h localhost -U mstechnics mstechnics > /var/backups/pre_cutover_$(date +%Y%m%d_%H%M).dump
   # 3. Развернуть новую ветку
   cd /opt/mstechnics && git pull origin main
   .venv/bin/pip install -e ".[dev,test]" -r requirements.txt
   # 4. Восстановить (если ставим с нуля) или просто migrate (если поверх той же БД)
   DATABASE_URL=... ./scripts/restore_to_dev.sh db_dumps/mstechnics.dump
   # 5. Smoke
   .venv/bin/python manage.py check
   curl -sf http://localhost:8000/api/v1/health/live
   # 6. Systemd
   sudo cp infra/systemd/*.service /etc/systemd/system/
   sudo cp infra/systemd/*.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now mstechnics-web mstechnics-daily-tasks.timer ...
   # 7. Включить nginx upstream на новый порт / новый contianer
   sudo nginx -s reload
   ```
5. **Rollback plan** — если что-то пошло не так:
   ```bash
   sudo systemctl stop mstechnics-web
   pg_restore --clean --no-owner -d mstechnics /var/backups/pre_cutover_*.dump
   git checkout <prev_tag>
   sudo systemctl start mstechnics-web-old   # старая версия
   ```
6. **Post-cutover monitoring** — что мониторить первые 24h (sentry, error rate, notifications delivery).

---

## Критерии приёмки

- [ ] `scripts/prod_dump_compat.sql` удалён.
- [ ] `scripts/restore_to_dev.sh` переписан под текущий формат дампа (.dump через pg_restore) и сам прогоняет migrate.
- [ ] `scripts/restore_dump.ps1` чист от вызова compat'а.
- [ ] На копии прод-БД (локально) прогнан `restore_to_dev.sh` целиком, без compat'а — migrate проходит до конца, check зелёный, smoke `/api/v1/displays/` зелёный. Логи в `logs/t6_001_*`.
- [ ] Шаги troubleshooting (`showmigrations` matrix, `--fake` cases) задокументированы.
- [ ] `ai-docs/06-integrations/production-cutover-runbook.md` написан — это документ для владельца, не для кодера.
- [ ] Отчёт `ai-docs/08-reports/T-6-001.md`.

---

## Что НЕ нужно делать

- **Не запускать ничего на реальном prod-сервере владельца** без участия владельца. Кодер прогоняет на staging-копии и пишет runbook. Финальный прод-cutover — владелец вручную по этому runbook'у, с заранее снятым `pg_dump` страховкой.
- **Не добавлять `--fake-initial`** в `restore_to_dev.sh` как «универсальное лекарство». Это маскирует проблему. `--fake` — точечно, через troubleshooting блок.
- **Не править существующие миграции** Phase-2/Phase-5-fix. Они работают, протестированы в T-5-fix-003. Если что-то падает — это конфликт с compat-патчем, который мы удаляем.
- **Не создавать data-migration «backfill из старых полей в ApplicationEvent»** (T-2-020 backfill) сейчас. T-2-021 (drop 28 fields) специально blocked до 2-недельного prod-stable window — это решение остаётся.
- **Не запускать legacy cleanup (T-5-050)** в этой задаче. Это после prod + 2 недели.

---

## Ссылки

- `08-reports/T-5-fix-003.md` — пруф, что миграции работают на копии прод-БД БЕЗ compat.
- `08-reports/architect-review-2026-05-07-prod-cutover.md` — архитектурный апрув.
- `apps/directory/panels/migrations/0004_convert_panel_fk_storage_to_id.py` — эталон data-migration.
- `06-integrations/phase-5-rollout-runbook.md` — устаревший runbook (заменим на новый).

---

## Вопросы для архитектора

- [ ] У владельца есть отдельный staging-сервер или сразу прод? — **Ответ:** скорее всего сразу прод, отдельного staging нет. Тогда первое тестирование — на копии прод-БД локально/у кодера. На сервере владельца — один прогон по runbook с backup'ом.
- [ ] Что делать, если на проде уже частично применены новые миграции (например, кто-то запускал `migrate` без compat и часть прошла)? — **Ответ:** `showmigrations` покажет точку, до которой дошло. Дальше — `migrate <app> <next_migration>` пошагово до полного зелёного.
- [ ] Удалять ли `scripts/restore_dump.ps1` целиком? — **Ответ:** нет. Это локальный dev-инструмент Windows. Просто чистим от вызова compat-скрипта.

---

## Отчёт по выполнению

(Заполняет кодер при переводе в review/done.)

### Что сделано
- ...

### Что нашёл в `showmigrations` копии прод-БД
- ...

### Какие миграции потребовали `--fake` (если потребовали)
- ...

### Финальный smoke
- `migrate` exit code: ...
- `check` exit code: ...
- `/api/v1/health/live`: ...
- `/api/v1/displays/` (JWT): ...

### Дальнейшие шаги
- ...
