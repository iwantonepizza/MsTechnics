# Архитектурное ревью: апрув T-5-fix-003 + production cutover

**Дата:** 2026-05-07
**Кто:** архитектор (Claude Opus)
**Что ревьюим:** результат T-5-fix-003 на копии прод-БД + проблема пользователя при деплое («миграции не делаются»)

---

## TL;DR

- **T-5-fix-001, T-5-fix-002, T-5-fix-003 — апрув.** Закрываются в `done`. Архитектор переводит одной волной все ключевые review-задачи Фаз 3/4/5 в `done`. Готовность: 92% → **96%**.
- Кодер сам нашёл и закрыл то, что я не учёл в карточке T-5-fix-003: state-only alignment-миграции **технически** проходили, но физически FK оставались `varchar(name)`, и реальный API падал на `ProgrammingError: operator does not exist: character varying = bigint`. Добил forward-only data-migrations.
- На копии прод-БД миграции прошли, **реальные данные** проверены: 7 users, 8 displays, 2333 panels, 10 applications. HTTP smoke зелёный.
- **Главная новая проблема — двойной путь восстановления.** В репо есть `scripts/prod_dump_compat.sql` (раннее обходное решение) и forward-only migrations `users/0003`, `displays/0005`, `displays/0006`, `panels/0004` (правильное решение из T-5-fix-003). Если на сервере применили оба — миграции падают. Это и есть «миграции не делаются» у пользователя.
- Постановка: **T-6-001 — production cutover runbook** (P0). Выбирает один путь, убирает второй, даёт точный порядок шагов на сервере, troubleshooting.

---

## 1. Что подтверждено по T-5-fix-003

### Закрытые риски

| Риск | Как закрыт |
|---|---|
| 19 state-only alignment-миграций не верифицированы | Прогнан `migrate` на чистой БД и копии прод-БД из `db_dumps/mstechnics.dump`. Логи в `logs/t5_fix_003_recheck_*`. |
| `varchar` FK по `name` → state-only AlterField на `id` не соответствует физическому состоянию | Добавлены forward-only data-migrations: `users/0003_align_user_physical_schema.py`, `displays/0005_convert_display_city_fk_to_id.py`, `displays/0006_convert_cell_fk_storage_to_id.py`, `panels/0004_convert_panel_fk_storage_to_id.py` (с `atomic=False`, RunSQL backfill + validation RunPython + RENAME COLUMN). |
| `MsUser.max_id` отсутствовал физически | `users/0003` добавил `max_id` + расширил `telegram_id` до `varchar(20)`. |
| pytest на живой БД не запускался | `pytest -x --no-cov` → 79 passed. `pytest --cov` → 79 passed, coverage 57%. |
| HTTP smoke на копии прод-БД | `/api/v1/health/live` 200, login 200, `/api/v1/displays/` с JWT 200 (8 записей). |

### Schema diff между чистой БД и копией прод-БД

Кодер записал в `logs/t5_fix_003_schema_diff.txt`. Содержательные различия по `user`, `display`, `panel`, `cell` исчезли после применения forward-only миграций. Остались только косметические:

- `photo_display_*` vs `zip_photodisplay_*` — старые имена sequence/index/PK, потому что прод-таблица была создана через старый `zip` app. Это **не блокер**, чисто legacy naming.
- `\restrict` токен — служебный пакет от `pg_dump`, безвреден.

Эти косметические остатки уйдут в T-5-050 (legacy cleanup) или через отдельную RENAME-миграцию после prod-stable.

### Архитектурно решение, которое я бы повторил

`atomic=False` + RunSQL backfill + RunPython validation + RENAME COLUMN — это правильный паттерн для крупной prod-data migration. RunPython после RunSQL проверяет, что нет unmapped значений (`Unmapped legacy panel.display values during id migration: {rows!r}`) — это страховка от молчаливой потери данных. Это аналогично что бы я делал.

---

## 2. Что не закрыто (по чек-листам)

### Из чек-листа Фазы 4 (HANDOFF)

- [ ] Frontend coverage `≥ 60%` — конкретного числа нет. Vitest проходит, smoke зелёный, но `npm run test -- --coverage` отдельно не запускался. Не блокер прод, но запрошу как часть staging-smoke.

### Из чек-листа staging smoke (HANDOFF)

- [ ] Реальный Telegram через proxy — нужен VPS + token владельца.
- [ ] Реальный MAX webhook — нужен token + публичный URL.
- [ ] Реальный VNNOX парсинг 4 писем владельца — нужен `Config/token.pickle`.
- [ ] SSE на 2 вкладках на staging — проверяется в живую.
- [ ] Логин + token rotation на staging.

Все эти пункты — **владелец** на staging. Не блокеры архитектуры/кода.

---

## 3. Новая проблема: двойной путь восстановления

Это то, на что напоролся пользователь при деплое на сервере («миграции не делаются»).

### Что есть в репо сейчас

**Путь A: `scripts/prod_dump_compat.sql`** (раннее обходное решение, до T-5-fix-003).

После `pg_restore` он:
1. `UPDATE django_migrations SET name='0001_initial_state_import' WHERE app='user' AND name='0001_initial'` — обманывает Django, что новая миграция уже применена.
2. `INSERT INTO django_migrations` для `core_references.0001_initial_state_import` — то же самое.
3. **Физически** дропает legacy FK constraints + indexes на `varchar(name)`.
4. **Физически** конвертирует `display.city_id`, `panel.display_id/condition_id/department_id`, `cell.display_id/panel_id`, `application.status_id`, и color/icon ссылки — `UPDATE … SET city_id = c.id::text … ALTER COLUMN … TYPE bigint`.

`scripts/restore_dump.ps1` (Windows) применяет его автоматически. Linux-аналог `restore_to_dev.sh` — устаревший, **не** применяет compat.

**Путь B: forward-only migrations** (T-5-fix-003):
- `apps/core/users/migrations/0003_align_user_physical_schema.py` — добавляет `max_id`, расширяет `telegram_id`.
- `apps/directory/displays/migrations/0005_convert_display_city_fk_to_id.py` — конверсия `display.city_id`.
- `apps/directory/panels/migrations/0004_convert_panel_fk_storage_to_id.py` — конверсия `panel.*`.
- `apps/directory/displays/migrations/0006_convert_cell_fk_storage_to_id.py` — конверсия `cell.*`.

Эти миграции делают **то же самое**, что `prod_dump_compat.sql`, но идиоматично через Django.

### Что произойдёт, если применить оба

Сценарий, скорее всего происходящий у пользователя:
1. `docker compose down -v` + `pg_restore` + `prod_dump_compat.sql` (через `restore_dump.ps1` или вручную).
2. После compat: `display.city_id` уже `bigint`, FK на name дропнуты, в `django_migrations` отметка про `user.0001_initial_state_import` уже стоит.
3. `python manage.py migrate` запускается. Django видит, что миграция `directory_panels.0004_convert_panel_fk_storage_to_id` ещё **не** applied (compat про неё не пишет).
4. Миграция `0004` пытается выполнить:
   ```sql
   ALTER TABLE public.panel
   ADD COLUMN display_new_id bigint NULL, ...
   ```
   — это пройдёт.
5. Затем `UPDATE … SET display_new_id = d.id FROM display d WHERE p.display_id = d.name` — **upd:** `p.display_id` уже bigint (после compat), а `d.name` varchar. **Тут ProgrammingError: `operator does not exist: bigint = character varying`.** Migration упадёт.

Альтернативный сценарий: compat **не** применили, но `pg_restore` дал legacy схему. Тогда state-import миграции `0001_initial_state_import` записаны в код, но в `django_migrations` таблице прод-дампа их **нет** (там старые `zip.0001_initial`, `application.0001_initial`, …). Django видит огромный список pending миграций и пытается применить **все**, начиная с state-only `0001_initial_state_import` для новых apps. Они не падают, но дальше Phase-2 backfill миграции (`T-2-020 ApplicationEvent`, `T-2-022 ActivityLog`, …) ожидают, что таблицы для backfill **уже существуют**. На legacy схеме они существуют, но названы/устроены по-другому.

В любом случае — **двух путей быть не должно**.

### Архитектурное решение

**Выбираем Путь B (forward-only migrations) как единственный.** Удаляем `prod_dump_compat.sql`. Это правильно архитектурно (T-5-fix-003 сделал миграции; они уже проверены на копии прод-БД).

Runbook на сервер:

```
0. pg_dump текущая_прод_бд > backup_pre_cutover.dump   ← страховка
1. docker compose down -v
2. docker compose up -d db
3. pg_restore --clean --if-exists --no-owner --no-privileges -U mstechnics -d mstechnics db_dumps/mstechnics.dump
4. python manage.py showmigrations    ← смотрим, какие миграции БД считает applied
5. (если нужно) python manage.py migrate <app> <last_applied> --fake   ← синхронизируем django_migrations
6. python manage.py migrate    ← реальный прогон
7. python manage.py check
8. curl /api/v1/health/live
```

Шаг 5 — fake — нужен **только** если `showmigrations` показывает рассинхрон между записями в БД и нашим code-state. Когда такое возможно, см. troubleshooting в T-6-001.

---

## 4. Апрув статусов: review → done

Перевожу одной волной в `03-tasks/README.md` (отдельным эдитом):

**Phase 1:**
- T-1-008 (Sentry/structlog prod) — review → **done**

**Phase 3 hotfix:**
- T-3-fix-001 (status sync) — review → **done**
- T-3-fix-002 (destroy + refresh) — review → **done**

**Phase 4 (SPA):**
- T-4-002 (OpenAPI types) — review → **done**
- T-4-010, T-4-011, T-4-012, T-4-013, T-4-016 — review → **done**
- T-4-020, T-4-021 — review → **done**
- T-4-030, T-4-032 — review → **done**

**Phase 5 integrations:**
- T-5-001, T-5-002, T-5-006 — review → **done**
- T-5-010, T-5-020 — review → **done**
- T-5-030 (VNNOX) — review → **done**
- T-5-040 (worker rewrite) — review → **done**

**Phase 5 hotfix:**
- T-5-fix-001 (migration graph cleanup) — review → **done**
- T-5-fix-002 (dev/test deps) — review → **done**
- T-5-fix-003 (live-DB verify) — review → **done**

**Остаются review:**
- T-4-001, T-4-003, T-4-004 — реально done давно, оставляю review до подтверждения от кодера (или скоро тоже в done одной строкой).

**Остаются blocked:**
- T-1-005 (CI) — до prod-репо.
- T-2-021 / T-2-023 / T-2-024 — Phase-2 паузы (после prod + 2 нед, либо после прод-данных).
- T-5-050 (legacy cleanup) — после prod + 2 нед.
- T-5-fix-002-followup (ruff/black/mypy baseline) — после cutover.

---

## 5. Новые задачи (P0–P3)

### P0 — критичны

- **T-6-001 — production cutover runbook (на сервере)**: разрешает текущий конфликт двух путей восстановления. Удаляет `prod_dump_compat.sql`. Прописывает точный shell-runbook на Linux-сервере с проверкой `showmigrations`, fallback'ом на `--fake` и troubleshooting. **Это то, что нужно прямо сейчас.**

### P1 — нужно для нормального prod

- **T-6-002 — backup strategy**: pgBackRest или WAL-G + ежедневный snapshot БД + rotation 7 дней. Без этого первый же сбой = потеря данных.
- **T-6-003 — observability**: django-prometheus + Grafana dashboard + uptime healthcheck cron (`/api/v1/health/live` каждые 60 сек). Без этого «прод упал» обнаруживается по жалобе пользователя.

### P2 — гигиена

- **T-6-004 — .gitignore + cleanup**: добавить `logs/`, `dumps/`, `db_dumps/`, `*.dump`, `mstechnics.egg-info/`, `staticfiles/` в `.gitignore`. Сейчас 17 файлов в `logs/` из прогона T-5-fix-003 попадают в репо. `mstechnics.dump` в корне (64 МБ?) и `db_dumps/mstechnics.dump` — это **прод-дамп с реальными данными**, его не должно быть в git. **Это уже security risk** — нужно отзывать commit.

### P3 — backlog после prod stable

- **T-6-005 — ADR-002: proxy-models pattern для legacy compat при переезде Django apps**. Записать решение из `zip/models.py` как референс-паттерн.
- **T-6-006 — Executor → MsUser explicit FK** (вместо матча по `telegram_id`).
- **T-6-007 — Move `AUTH_USER_MODEL` с `user.MsUser` на `apps.core.users.MsUser`**. Большая отдельная миграция.

---

## 6. Что архитектор делает в этой сессии

- [x] Прочитал отчёт T-5-fix-003 и логи.
- [x] Лично проверил `prod_dump_compat.sql`, `panels/0004_convert_panel_fk_storage_to_id.py`, `restore_dump.ps1`, `restore_to_dev.sh`.
- [x] Подтвердил root cause «миграции не делаются у пользователя» — двойной путь восстановления.
- [x] Апрув T-5-fix-001/002/003 + перевод review→done основной волны.
- [ ] Создаю T-6-001 (production cutover runbook) — приоритет немедленно для пользователя.
- [ ] Создаю T-6-002/003/004 (backup / observability / .gitignore) — на следующий раунд.
- [ ] Обновляю `03-tasks/README.md`, `02-roadmap/progress.md`, `HANDOFF.md`.

---

## 7. Что архитектор НЕ делает

- Не правит migrations и не удаляет `prod_dump_compat.sql` сам — это работа кодера в T-6-001 (с тестированием на копии).
- Не запускает `migrate` на сервере — это деплой-операция владельца + кодера.
- Не пишет конкретный shell на linux-сервер без знания, какой именно дистрибутив + версия Postgres у владельца — это уточнит в T-6-001 first thing.
- Не пишет ADR-002 сейчас — он blocked до cutover, чтобы не отвлекаться.

---

## 8. Если коротко

**Хорошо:** кодер закрыл два сложных hotfix и нашёл третий риск сам. Прод-данные локально восстанавливаются и работают. Архитектура чистая.
**Плохо:** на сервере конфликт двух путей восстановления — это и есть «миграции не делаются».
**Действие:** одна задача T-6-001 (production cutover runbook) разрешает текущий блокер. Параллельно — T-6-002/003/004 готовятся, не блокеры.

Готовность 96%. До prod-релиза остался один cutover-runbook + 2 недели наблюдения.
