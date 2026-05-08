# Ревью архитектора: Фаза 5 в review, готовность к staging

**Дата:** 2026-05-06
**Кто:** архитектор (Claude Opus)
**Что ревьюим:** актуальное дерево репозитория после раунда T-3 hotfix + T-4 polish + T-5 integrations
**Источник:** `progress.md`, `HANDOFF.md`, `ai-docs/08-reports/T-5-*`, фактическое состояние `apps/`, `Config/`, legacy apps, `frontend/`.

---

## TL;DR

- Кодер закрыл Фазу 5 на уровне «review» (notifications, channels, triggers, TG proxy healthcheck, MAX webhook + binding, VNNOX gmail-парсер + AlarmEvent + UI tab, systemd timers). Отчёты на этот раз есть — конвенция соблюдена.
- Фаза 4 SPA: тоже review, OpenAPI types сгенерированы, `api-schema.yaml` (80 KB) и `frontend/src/shared/api/schema.d.ts` (95 KB) лежат в репо синхронно.
- **НО есть критичный архитектурный долг, который блокирует staging cutover**: в repo сосуществуют **дубли моделей** в новых `apps/*` и в legacy `main`, `user`, `zip`, `application`, `departure`, `mail`, `main_menu`. `manage.py check` падает на `legacy-дубли моделей и таблиц`, `manage.py migrate --plan` падает на `KeyError: 'display'`. Все T-5 отчёты явно отмечают этот блокер.
- Этот долг был неявно отнесён к T-5-050 (legacy cleanup, blocked до 2 недель в проде) — но он не cleanup, он **prerequisite миграций**. Без него ни локально, ни на копии прод-БД новые миграции применить нельзя.
- Параллельно `pytest`, `ruff`, `factory-boy` отсутствуют в `.venv` — `[project.optional-dependencies]` объявлены, но никто не выполнил `pip install -e ".[dev,test]"`. В итоге кодер не прогоняет полный pytest, а ревьюер не видит coverage.

**Итого готовность реальная: ~88%** (была заявлена 90%). Минус 2% за migration graph и dev-deps gap, которые пока скрывают неизвестные регрессии.

---

## 1. Что подтверждено working

### Фаза 5 — реализована по карточкам

| Задача | Статус | Подтверждение |
|---|---|---|
| T-5-001 (notifications infra) | review | `apps/notifications/` с `models.py`, `channels/`, `triggers/`, `dispatcher.py`, dispatcher fallback `tg → max → email`, unit-тесты dispatcher (success/fallback/skip/all-failed/missing). |
| T-5-002 (TG/MAX/Email channels) | review | `httpx`+`socks` в `pyproject.toml`, `socksio==1.0.0` в `requirements.lock`. `MaxChannel` использует `https://platform-api.max.ru/messages`. Шаблоны seed'ятся миграцией. |
| T-5-006 (triggers) | review | 6 шаблонов в `0002_seed_templates.py`, triggers подключены через `NotificationsConfig.ready()`. `ApplicationService.create/transition/set_executor` и `DepartureViewSet.create` шлют. |
| T-5-010 (TG proxy) | review | `scripts/check_telegram_proxy.py` с маскированием creds. `sender_tg_message.py`/`tg_sender` удалены. `sorting_message.py` оставлен как compat-shim, отправляющий через `NotificationDispatcher` (legacy import path до T-5-050). |
| T-5-020 (MAX bot) | review | webhook `POST /api/v1/integrations/max/webhook` + `X-MAX-Secret`, `/start <username>` → `MsUser.max_id`, callback `application_done:<id>` → `ApplicationService.transition`. |
| T-5-030..033 (VNNOX) | review | `apps/integrations/gmail_alarms/`, `AlarmEvent` с idempotency по `gmail_message_id`, `Display.vnnox_device_id` + миграция. UI вкладка VNNOX в DisplayView, без автосоздания заявок (по карточке). `pull_vnnox_alarms` + `check_unresolved_alarms` + systemd timers. |
| T-5-040/041 (worker rewrite) | review | `daily_checker.py` + `ManageControl.py` удалены, `check_daily_tasks` через management command + systemd timer. |

### Артефакты, которые я лично проверил

- `api-schema.yaml` — 80 KB, дата 2026-05-05.
- `frontend/src/shared/api/schema.d.ts` — 95 KB, дата 2026-05-05. Соответствует `api-schema.yaml`.
- `.env.example` — обновлён, есть все новые переменные TG/MAX/Email/Sentry/VNNOX.
- `Makefile` есть, `infra/systemd/` содержит 6 unit-файлов (3 пары service+timer).
- `frontend/`: vitest, playwright настроены, e2e tests лежат, `npm run build` зелёный по отчёту T-5-030.

### Отчёты

В этом раунде кодер написал отчёты по T-5-001, T-5-002, T-5-006, T-5-010, T-5-020, T-5-030..033, T-5-040, плюс T-1-008, T-3-fix-001, T-3-fix-002, и большинство ключевых T-4. Конвенция «PR без отчёта не мерджится» теперь соблюдается.

---

## 2. Что блокирует staging — приоритет P0

### 2.1. Миграционный граф: дубли моделей в legacy apps

**Симптом** (фигурирует в каждом T-5-* отчёте):
- `manage.py makemigrations --check --dry-run --skip-checks` → `KeyError: 'display'`.
- `manage.py check` → `SystemCheckError: legacy-дубли моделей и таблиц` (`application`, `zip`, `departure`, …).
- `manage.py test` блокируется тем же check'ом.

**Корень**.

В `INSTALLED_APPS` сосуществуют:

```
apps.core.references          + legacy: main          # дублирует Cities/Color/Smile/Condition/Department/Icon
apps.core.users               + legacy: user          # дублирует MsUser
apps.directory.displays       + legacy: zip           # дублирует Display, Cell, PhotoDisplay (db_table='display')
apps.directory.panels         + legacy: zip           # дублирует Panels (db_table='panel')
apps.directory.storage        + legacy: zip           # дублирует Wires/Hubs/Lamels (wires_zip/hubs_zip/lamels_storage)
apps.workflow.applications    + legacy: application   # дублирует Application + ApplicationStatus
apps.workflow.departures      + legacy: departure     # дублирует Departure/Executor/Contact
apps.workflow.daily_tasks     + legacy: zip           # дублирует DailyTask (db_table='daily_task')
                                + legacy: main_menu   # *HistoryReport
                                + legacy: mail        # AlarmEvent (старый)
                                + legacy: monitoring/control/service  # без моделей, но в INSTALLED_APPS
```

Я лично прочитал `zip/models.py`, `main/models.py`, `user/models.py`, `application/models.py` — там **полные `class X(models.Model)`**, а не shim'ы. То есть Phase-2 переезд через `SeparateDatabaseAndState(state_operations=…)` в новых apps был сделан правильно, **но симметричный шаг в старых apps не сделан**: модели не превращены в re-export shim, миграции `…/legacy/migrations/0001_initial.py` всё ещё активно создают/держат модели в state.

Django видит две `Display` (одна в `zip`, одна в `apps.directory.displays`), обе указывают на `db_table='display'`. На fresh DB одна из них первой создаст таблицу — вторая упадёт. На существующей prod-БД (где таблицы уже есть) check всё равно ругается на model-name collision, и любая попытка `makemigrations` ломает граф ссылками вида `to='zip.display'` vs `to='directory_displays.display'`.

**Эффект:**
- Невозможно прогнать `migrate --plan` на копии прод-БД → невозможно безопасно катить новые миграции (`directory_displays.0002_display_vnnox_device_id`, `gmail_alarms.0001_initial`, `notifications.0003`, `notifications.0004`, и любые будущие).
- Невозможно прогнать `pytest` целиком — system check падает на старте.
- Невозможно перейти на staging, не потеряв способность откатить.

**Решение** — задача **T-5-fix-001** (см. карточку, P0).

### 2.2. Backend dev/test deps не установлены

**Симптом** (тоже в каждом T-5-* отчёте):
- `pytest` не установлен в `.venv`, тесты прогоняются через `python -m unittest` точечно.
- `ruff` не установлен, lint вообще не выполняется.
- `factory-boy`, `freezegun`, `pytest-django`, `pytest-cov` тоже не установлены — все factories из Phase-2 простаивают.

**Корень.** В `pyproject.toml` зависимости `pytest`/`ruff`/`black`/`mypy` лежат в `[project.optional-dependencies] dev` и `test`. Базовый `pip install -r requirements.txt` (или `pip install .`) их не подтягивает. Никто не выполнил `pip install -e ".[dev,test]"` после реструктуризации зависимостей в Phase-1.

**Эффект:**
- Coverage backend нулевой к измерению — ни в одном T-5-* отчёте нет.
- Регрессии видны только тогда, когда продпортит — ровно то, чего избегали в Phase-1.
- Pre-commit hooks (`ruff`, `black`, `mypy`) тоже не выполняются — и вряд ли уже месяцы.

**Решение** — задача **T-5-fix-002** (см. карточку, P1).

---

## 3. Что не доделано, но не блокирует — P1/P2

### 3.1. Executor → MsUser явный binding (T-5-006 отметил)

В trigger `application_assigned_to_executor` мы ищем пользователя по совпадению `Executor.telegram_id` ↔ `MsUser.telegram_id`. Если binding не найден — уведомление молча пропускается. Это работает, но хрупко (исполнитель может менять telegram_id без обновления Executor). **Заводим в backlog: добавить `Executor.user_fk = ForeignKey(MsUser, null=True)` после T-5-fix-001.**

### 3.2. `sorting_message.py` всё ещё импортируется legacy кодом

После T-5-010 он работает через `NotificationDispatcher`, но импорт остался. Его нельзя удалить до полного выноса legacy `application/zip/main` views — это часть T-5-050 (legacy cleanup, blocked корректно).

### 3.3. Frontend coverage ≥ 60% (чек-лист Фазы 4)

Vitest и Playwright настроены, smoke зелёные, но численный coverage в отчётах не указан. После T-5-fix-001 — попросить кодера явно прогнать `npm run test -- --coverage` и записать число.

### 3.4. T-3-fix-001/T-3-fix-002 ещё в `review`, не `done`

В `03-tasks/README.md` они до сих пор `review`. По коду я подтвердил, что мердж сделан и работает. **Архитектор должен переключить статусы в `done`** — но я этого не делаю, пока кодер не подтвердит, что это его финальный merge. Зафиксировал в HANDOFF.

### 3.5. INSTALLED_APPS содержит `monitoring`, `control`, `service` без моделей

Эти три legacy app не имеют `models.py` (или там пусто), но в INSTALLED_APPS живут. Можно убрать сразу, но это часть T-5-fix-001 — там удобнее одной волной.

### 3.6. `requirements.txt` в UTF-16 BOM

При `Read` файл выглядит с null-bytes между символами — характерный признак UTF-16. Это не блокер (`requirements.lock` отдельно), но `pip install -r requirements.txt` на linux-host выдаст gibberish. **Перезаписать в UTF-8** — добавлено в T-5-fix-002.

---

## 4. Метрики готовности

| Срез | Реально |
|---|---|
| Фаза 1 (foundation) | done (95%, T-1-005 CI отложен до prod-репо) |
| Фаза 2 (models) | done **в новых apps**; legacy apps ещё не «опустошены» — это закрывает T-5-fix-001 |
| Фаза 3 (REST API) | done + 2 hotfix готовы к закрытию |
| Фаза 4 (SPA) | review, артефакты на месте; нужен staging smoke |
| Фаза 5 (integrations) | review; зависит от T-5-fix-001 для применения миграций |
| Фаза 5 cleanup (T-5-050) | blocked до SPA в проде + 2 недели — оставляем как было |

**Реальная готовность: ~88%.** Чтобы выйти на staging с нашими новыми миграциями — нужно ~6-8 часов работы кодера на T-5-fix-001 + T-5-fix-002 и прогон pytest.

---

## 5. Что архитектор сделал в этой сессии

- Прочитал AGENTS.md, ai-docs/README.md, roadmap, progress, HANDOFF, все T-5-* отчёты, ключевые legacy `models.py`, `INSTALLED_APPS`, миграции `apps.directory.displays`, `apps.workflow.applications`, `zip`.
- Подтвердил root cause `KeyError: 'display'` — двойная регистрация моделей в old + new apps.
- Создал две новые задачи:
  - **T-5-fix-001** (P0, ~4-5 часов) — migration graph cleanup, превратить legacy `main/user/zip/application/departure/mail/main_menu` в shim'ы + state-only DeleteModel миграции, убрать пустые `monitoring/control/service` из INSTALLED_APPS.
  - **T-5-fix-002** (P1, ~1 час) — установить `dev,test` extras в `.venv`, перезаписать `requirements.txt` в UTF-8, прогнать pytest и ruff, починить, что найдут.
- Обновил `02-roadmap/progress.md` и `HANDOFF.md` с новыми блокерами и приоритетами.
- Этот файл `08-reports/architect-review-2026-05-06.md`.

### Что архитектор НЕ делал

- Не правил legacy models.py — это работа кодера по T-5-fix-001 (см. раздел AGENTS.md о невмешательстве архитектора в прод-код).
- Не запускал `pip install -e ".[dev,test]"` локально — это шаг кодера в T-5-fix-002.
- Не обновлял статусы T-3-fix-001/T-3-fix-002 в `03-tasks/README.md` с review на done — жду явного подтверждения от кодера.

---

## 6. Что делать дальше — порядок

1. **Кодер** берёт `T-5-fix-002` (1 час): ставит `dev,test` extras, чинит `requirements.txt`, прогоняет `ruff check apps/ shared/` и `pytest -x` — фиксит, что ruff подсветил (но не реструктурирует масштабно).
2. **Кодер** берёт `T-5-fix-001` (4-5 часов): legacy models → shim, миграции state-only DeleteModel, INSTALLED_APPS чистый. После этого `python manage.py check` зелёный, `python manage.py migrate --plan` показывает разумный список миграций.
3. **Кодер** прогоняет `pytest` целиком (теперь должно работать) и сообщает реальный backend coverage. Frontend coverage отдельным сабшагом.
4. **Архитектор** ревьюит оба PR'а, переводит T-3-fix-001/T-3-fix-002 в done, T-5-fix-* в done, обновляет progress.
5. **Владелец** проводит staging cutover по `06-integrations/phase-5-rollout-runbook.md` — теперь шаг 2 (миграции) разблокирован.
6. После 2 недель стабильной работы SPA в проде — **снимаем блок с T-5-050** и закрываем legacy cleanup.

---

## 7. Если коротко

Хорошо: Фаза 5 функционально на месте, отчёты пишутся, схема и типы синхронны.
Плохо: миграционный граф не применим — два набора моделей конкурируют за одни таблицы.
Действие: одна задача (T-5-fix-001) кодеру решает 80% проблемы — staging разблокирован. Вторая (T-5-fix-002) приводит dev-окружение в нормальное состояние, чтобы регрессии ловились.
