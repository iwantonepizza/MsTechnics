# Production-copy smoke (2026-05-20)

> **Дата:** 2026-05-20
> **Автор:** архитектор
> **Цель:** убедиться, что текущий main (`9aa0341`) разворачивается на копии прод-БД без ручного вмешательства, чтобы реальный prod cutover прошёл максимально гладко.

---

## Что прогнал

Полностью воспроизвёл прод-сценарий в локальном docker compose:

```bash
docker compose down -v                                    # чистый старт
docker compose up -d db redis                             # postgres 16 + redis
docker cp db_dumps/mstechnics.dump mstechnics-db-1:/tmp/  # копия прода (1.1 MB custom format)
docker compose exec db pg_restore -U msadmin -d ms_db \
  --clean --if-exists --no-owner --no-privileges /tmp/mstechnics.dump
docker compose run --rm web python manage.py showmigrations
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py check
docker compose up -d web
```

`pg_restore` + `migrate` отработали **без ошибок**: 60+ миграций по 20 приложениям прокатились, включая:

- `apps.core.users.0001_initial_state_import` — replaces `user.0001_initial`, заменён без ручных `--fake`.
- 4 forward-only FK конверсии (varchar(name) → bigint(id)) из T-5-fix-003: `users/0003`, `displays/0005/0006`, `panels/0004`, `core_references/0003`.
- `application.0004_strip_application_prefix` — переименовал legacy `application_*` → новые имена в `application_status`.
- `workflow_departures.0005_align_departure_status_legacy_column_state` из T-7-100 PR-13.
- **`apps.core.users.0004_role_and_user_roles`** — создал таблицу `role` с 5 ролями (фикстура), backfill `permission → roles` отработал на реальных данных:

```
 username   | permission | roles
------------+------------+----------------------------------
 alexey     | all        | {control, monitoring, service}
 izhevsk11  | service    | {service}
 roman      | monitoring | {monitoring}
 senya      | admin      | {admin}
 sergey     | all        | {control, monitoring, service}
 thecreator | admin      | {admin}
```

`manage.py check`: **System check identified no issues (0 silenced)**.

## Целостность данных после миграций

| Сущность | Count |
|---|---|
| users | 7 |
| roles (fixture) | 5 (monitoring, control, service, admin, technical) |
| users с >=1 role | 7 |
| admins по роли | 2 |
| displays | 8 |
| panels | 2333 |
| applications | 10 (9 archive_done + 1 done) |
| cities | 3 |
| application_statuses | 9 |
| departure_statuses | 4 |
| notification_templates | 8 |

Полностью соответствует ожиданиям из `T-5-fix-003`: 7 users, 8 displays, 2333 panels, 10 applications.

## HTTP smoke (через docker `localhost:8000`)

### Без авторизации

| Endpoint | Status | Size |
|---|---|---|
| `/api/v1/health/live` | 200 | 18 B |
| `/api/v1/health/ready` (DB + Redis) | 200 | 72 B |
| `/api/schema/` (OpenAPI 3.0.3, 64+ paths) | 200 | 237 KB |
| `/metrics` (Prometheus) | 200 | 16 KB |
| `/admin/login/` | 200 | 4 KB |

### С авторизацией (`thecreator` / `admin` role)

JWT-токен содержит **и legacy `permission`, и новые `roles`/`extra_permissions`**:

```json
{"permission":"admin","roles":["admin"],"extra_permissions":[]}
```

| Endpoint | Status | Size | Notes |
|---|---|---|---|
| `/api/v1/auth/login/` (POST) | 200 | 349 B | JWT issued |
| `/api/v1/me` | 200 | 319 B | возвращает `roles`+`extra_permissions`+`allowed_cities` |
| `/api/v1/displays/` | 200 | 2.8 KB | 8 displays |
| `/api/v1/displays/liner/` | 200 | 216 KB | detail с cells+panels |
| `/api/v1/displays/liner/contacts/` | 200 | 2 B | empty |
| `/api/v1/displays/liner/alarms/?resolved=false&limit=5` | 200 | 69 B | empty (T-7-100 PR-13 fix отработал) |
| `/api/v1/panels/?display=1` | 200 | 16 KB | 50 panels (page 1 of 2333) |
| `/api/v1/panels/?department=zip` | 200 | — | 3 ZIP panels |
| `/api/v1/cells/?display=1` | 200 | 19 KB | layout cells |
| `/api/v1/applications/?box=received` | 200 | 69 B | 0 active |
| `/api/v1/applications/?box=archive` | 200 | — | 9 archived |
| `/api/v1/applications/1/` | 200 | 563 B | detail |
| `/api/v1/applications/1/events/` | 200 | 14 B | events list |
| `/api/v1/cities/`, `/colors/`, `/conditions/`, `/smiles/`, `/departments/`, `/application-statuses/`, `/departure-statuses/` | 200 | 0.3..2.7 KB | все refs |
| `/api/v1/activity-log/` | 200 | 69 B | empty (T-2-023 backfill ещё не прогонялся) |
| `/api/v1/notifications/inbox/` | 200 | 24 B | empty |
| `/api/v1/dashboard/` | 200 | 202 B | counts + queues |
| `/api/v1/search/?q=display` | 200 | 85 B | global search |

### Статика SPA

| Endpoint | Status | Size |
|---|---|---|
| `/static/spa/index.html` | 200 | 2.8 KB |
| `/static/spa/assets/index-*.js` | 200 | 619 KB |
| `/static/spa/logo-supersymmetria.svg` | 200 | brand asset |
| `/static/spa/favicon.ico`, `icon-192.png`, `icon-512.png` | 200 | brand assets |

SPA shell + brand assets есть в собранном Docker image (`ms-service:1.0.1`).

## Что подтверждено для прода

1. **Cutover-runbook** (`ai-docs/06-integrations/production-cutover-runbook.md`) — рабочий end-to-end. Никаких ручных `--fake-initial`/`--fake` команд не нужно.
2. **T-7-003 multi-role backfill безопасен на реальных данных.** Все 7 user-ов получили роли, `permission='all'` корректно разворачивается в 3 роли.
3. **FK-конверсии** (varchar→bigint) из T-5-fix-003 не ломают существующие данные.
4. **Schema regen** (`/api/schema/?format=json`) валиден, OpenAPI 3.0.3, 64+ маршрутов.
5. **Prometheus `/metrics`** активен.
6. **JWT-токен совместим со старым FE** (имеет `permission`) и поддерживает новый (`roles`, `extra_permissions`).

## Что не закрыто в этом smoke (требует владельца)

- `T-6-005` ротация секретов — не моя зона. До prod cutover обязательно.
- Реальный prod cutover на Linux-сервере по `production-cutover-runbook.md`.
- Включение systemd-таймера бэкапов (`mstechnics-db-backup.timer`) после cutover.
- Поднять Prometheus+Grafana docker сервисы по `observability-runbook.md`.
- `T-2-023 backfill ActivityLog` отдельной командой `python manage.py backfill_activity_log` — опционально, не блокирует прод.

## Команды для повтора smoke перед prod cutover

Если хочешь ещё раз убедиться перед самим cutover'ом — `docker compose down -v && docker compose up -d db redis && docker cp db_dumps/mstechnics.dump mstechnics-db-1:/tmp/ && docker compose exec db pg_restore -U msadmin -d ms_db --clean --if-exists --no-owner --no-privileges /tmp/mstechnics.dump && docker compose run --rm web python manage.py migrate --noinput && docker compose up -d web`. Smoke `/api/v1/health/ready` должен возвращать 200 с `{"checks":{"database":{"ok":true},"redis":{"ok":true}}}`.
