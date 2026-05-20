# T-5-fix-003. Live-DB verification 19 alignment-миграций перед staging cutover

> **Тип задачи:** migration + infra
> **Приоритет:** P0 (блокирует staging cutover; финальный gate перед прод)
> **Оценка:** 2-3 часа
> **Фаза:** 5 (cutover gate)
> **Статус:** done
> **Исполнитель:** GPT-5 Codex

---

## Цель

Подтвердить, что 19 state-only миграций, сгенерированных в T-5-fix-001, действительно совпадают с физической схемой существующей БД. Прогнать `migrate --plan` и `migrate` на (а) чистой БД и (б) копии прод-БД. Прогнать полный `pytest -x` на живой БД. Это финальный gate: если он зелёный — staging cutover разблокирован.

---

## Контекст

T-5-fix-001 закрыт на review с пометкой:

> «`migrate --plan` и `migrate` локально не проверить без живого PostgreSQL host из env (`getaddrinfo failed`).»

И добавил **19 миграций**, все обёрнутые в `SeparateDatabaseAndState(database_operations=[], state_operations=[…])`. Это значит: Django state теперь синхронизирован с реальными моделями в коде, но физический SQL не выполняется. Если фактическая прод-схема **совпадает** с тем, что state теперь утверждает — отлично. Если нет — следующая после-cutover миграция, требующая `database_operations`, упадёт на несоответствии.

Конкретный пример риска. В `apps/directory/displays/migrations/0004_alter_cell_options_alter_display_options_and_more.py` есть:

```python
migrations.AlterField(
    model_name='cell',
    name='display',
    field=models.ForeignKey(..., to='directory_displays.display', verbose_name='экран'),  # to_field более не name
),
migrations.AlterField(
    model_name='cell',
    name='id',
    field=models.BigAutoField(...),
),
```

Эти AlterField обёрнуты в state-only. То есть Django теперь **думает**, что `cell.display` — это FK на id, а `cell.id` — BigAutoField. Если в реальной БД (применённой через Phase-2 миграции T-2-025) физически это уже так — всё хорошо. Если где-то осталось `cell.display` как FK на name — расходимся, и следующая нормальная миграция упадёт.

Полный список миграций, требующих перепроверки — в `08-reports/T-5-fix-001.md`, раздел «Список новых alignment-миграций» + cleanup/import.

---

## Зависимости

- **Блокируется:** T-5-fix-001 (done/review), T-5-fix-002 (done/review).
- **Блокирует:** staging cutover Фазы 5, прод-релиз.

---

## Что нужно сделать

### Шаг 1. Поднять локальный PostgreSQL

```bash
# В корне репо
docker compose up -d db
# или (если db service в compose ещё нет — настроить env правильно)
docker run --rm -d --name mst-pg \
  -e POSTGRES_DB=mstechnics -e POSTGRES_USER=mstechnics -e POSTGRES_PASSWORD=dev \
  -p 5432:5432 postgres:16

# Проверить, что DB доступна
psql -h localhost -U mstechnics -d mstechnics -c "SELECT 1"
```

В `.env` (локальный, не в git) — `DATABASE_HOST=localhost` или `127.0.0.1`.

### Шаг 2. Прогон на ЧИСТОЙ БД

```bash
.venv/Scripts/python manage.py migrate --plan | tee logs/t5_fix_003_plan_clean.log
```

Ожидание: список из ~всех миграций без ошибок, `KeyError` нет. Сохрани лог.

```bash
.venv/Scripts/python manage.py migrate
```

Ожидание: все миграции applied. Особое внимание на `apps.directory.displays.0004`, `apps.workflow.applications.0005`, `apps.core.users.0002` — это самые «толстые» alignment'ы. Если что-то упадёт — фиксы здесь, **только если они мелкие** (1-2 строки в миграции). Иначе заведи follow-up задачу.

После успеха проверь схему:

```bash
pg_dump --schema-only -h localhost -U mstechnics mstechnics > logs/t5_fix_003_schema_clean.sql
```

### Шаг 3. Прогон на КОПИИ ПРОД-БД

Если у владельца есть свежий дамп:

```bash
# Залить дамп в чистую БД (см. scripts/restore_to_dev.sh)
bash scripts/restore_to_dev.sh dumps/prod_2026-XX-XX.dump

# План миграций — должен показать ровно 19 alignment + 4 cleanup
.venv/Scripts/python manage.py migrate --plan | tee logs/t5_fix_003_plan_prod.log

# Применить
.venv/Scripts/python manage.py migrate | tee logs/t5_fix_003_apply_prod.log
```

После — снова `pg_dump --schema-only` и сравнение:

```bash
pg_dump --schema-only -h localhost -U mstechnics mstechnics > logs/t5_fix_003_schema_prod_after.sql
diff logs/t5_fix_003_schema_clean.sql logs/t5_fix_003_schema_prod_after.sql > logs/t5_fix_003_schema_diff.txt
```

**Что считается ОК:**
- Только различия в порядке `CREATE INDEX` строк или их именах (alignment 0002_rename_*_idx миграции).
- Различия в `OWNER`/`SET search_path` — это postgres-side, не наша проблема.

**Что считается ПРОБЛЕМОЙ:**
- Колонка существует в проде но не в чистой схеме (или наоборот).
- Тип колонки разный (`varchar(15)` vs `varchar(20)`, `integer` vs `bigint`).
- Constraint существует на одной стороне и не существует на другой.
- FK направлен на разные `to_field` (`name` vs `id`).

Любое такое расхождение — **stop**, не катить на staging, поднять архитектора.

### Шаг 4. Прогнать полный pytest

```bash
.venv/Scripts/pytest -x --no-cov 2>&1 | tee logs/t5_fix_003_pytest.log
```

Ожидание: 79 collected, все или почти все зелёные. Если падает 5-10 — фикс в этой задаче, если адресные. Если падает 30+ — заведи отдельную follow-up задачу `T-5-fix-003-pytest-failures` с разбивкой по причинам.

После успеха — прогон с coverage и фиксация числа:

```bash
.venv/Scripts/pytest --cov=apps --cov=shared --cov-report=term-missing 2>&1 | tee logs/t5_fix_003_coverage.log
```

В отчёт записать общее число coverage и список модулей с coverage < 50%.

### Шаг 5. Smoke по `phase-5-rollout-runbook.md` локально

После того как миграции применились на локальной prod-копии:

```bash
.venv/Scripts/python manage.py runserver
# в другой терминалке:
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/admin/   # 302 на login — ок
```

Проверь:
- `/admin/` открывается, видно справочники (Cities, Conditions, Departments, …).
- `/api/v1/displays/` (с JWT-токеном) возвращает данные.
- `/api/v1/applications/` возвращает данные.

Это локальная проверка работы; настоящий staging smoke — отдельным раундом по runbook'у.

### Шаг 6. Решение по mail/main_menu

В T-5-fix-001 кодер не трогал `mail/models.py` (concrete `GmailMessage`, `Alarm`) и `main_menu/models.py` (concrete `*HistoryReport`). Это корректно — они не блокировали duplicate-model coalition.

В отчёте этой задачи (T-5-fix-003) **зафиксировать**:
- Используется ли таблица `mail_alarm` где-либо в текущем коде кроме legacy import'ов? (`grep -rn "mail.Alarm\|mail.GmailMessage" --include='*.py' apps/ shared/`).
- Если **используется** — оставить как есть, дописать в `T-5-050` task.
- Если **не используется** — добавить в `T-5-050` пункт «дропнуть `mail_alarm`/`mail_gmailmessage` после прод stable».

Не реализовывать, **только зафиксировать в карточке T-5-050**.

---

## Критерии приёмки

- [ ] `migrate --plan` на чистой БД — без ошибок, лог в `logs/t5_fix_003_plan_clean.log`.
- [ ] `migrate` на чистой БД — все миграции applied.
- [ ] `migrate --plan` на копии прод-БД — без ошибок, ровно ожидаемый список миграций.
- [ ] `migrate` на копии прод-БД — все миграции applied; **schema diff** (clean ↔ prod-after) приведён в отчёте, расхождения объяснены.
- [ ] `pytest -x` — зелёный или известные failures документированы (с причиной + follow-up задачей).
- [ ] `pytest --cov` — общее число coverage задокументировано.
- [ ] Локальный smoke (`/admin/`, `/api/v1/health/`, `/api/v1/displays/` через JWT) работает.
- [ ] `mail`/`main_menu` cleanup-decision записан в `T-5-050` карточке.
- [ ] Отчёт в `ai-docs/08-reports/T-5-fix-003.md`.

---

## Что НЕ нужно делать

- **Не править существующие 19 alignment-миграций**, если они применяются. Их специально сделали state-only, чтобы не трогать БД. Если что-то падает — это **симптом**, не причина; разбираемся с причиной.
- **Не делать `--fake-initial`** на копии прод-БД. На чистой БД для тестирования допустимо. На прод-копии — только нормальный `migrate`.
- **Не закрывать review-задачи (T-3-fix, T-4, T-5-001..040) в done** до тех пор, пока эта задача не пройдёт. Архитектор закроет их одной волной после T-5-fix-003.
- **Не разбираться с lint baseline** (291 ruff / 96 black / 16 mypy). Это `T-5-fix-002-followup-ruff`, blocked до cutover.
- **Не переходить к staging cutover** в этой же задаче. Это последовательно: T-5-fix-003 → staging cutover (по runbook) → 2 недели stable → T-5-050.

---

## Ссылки на примеры

- `08-reports/T-5-fix-001.md`, раздел «Миграции» — список 19 alignment-миграций.
- `06-integrations/phase-5-rollout-runbook.md` — checklist для следующего шага.
- Pattern «как сравнивать схемы» — `pg_dump --schema-only` + `diff` достаточно для нашего масштаба.

---

## Вопросы для архитектора

- [ ] Если на копии прод-БД находится колонка, которую в коде уже нет (legacy `time_*`, `comment_*` из T-2-020) — это блокер этой задачи или нет? — **Ответ:** не блокер. T-2-021 явно blocked до 2-недельной паузы; колонки существуют по плану. Зафиксируй в schema diff и пропусти.
- [ ] Если pytest падает на не-DB причинах (импорты, fixture) — фиксить в этой задаче? — **Ответ:** да, если фиксы мелкие (≤ 30 минут на причину). Иначе follow-up.
- [ ] Прод-БД дамп — кто запрашивает у владельца? — **Ответ:** ты, кодер. Без дампа — этот шаг (Шаг 3) пропускается, но в отчёте чётко: «прод-копия не проверена, ждём дамп от владельца». Архитектор не закроет задачу `done` без этого шага, но `review` без живого дампа — допустимо как промежуточный статус.

---

## Отчёт по выполнению

(Заполняет кодер при переводе в review/done.)

### Что сделано
- ...

### Schema diff (clean ↔ prod-after)
- ...

### Pytest результаты
- Collected: N
- Passed: M
- Failed: K (причины: ...)
- Coverage: X% (apps/), Y% (shared/)

### Местные smoke результаты
- ...

### Решение по mail/main_menu
- ...

### Дальнейшие шаги
- ...
