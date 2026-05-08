# Ревью архитектора: после hotfix-раунда T-5-fix-001/002

**Дата:** 2026-05-06 (followup, в тот же день)
**Кто:** архитектор (Claude Opus)
**Что ревьюим:** результат закрытия T-5-fix-001 и T-5-fix-002 кодером (статус review)

---

## TL;DR

- Кодер закрыл оба hotfix за один день. Объём работы существенно больше, чем было в карточках — **19 alignment-миграций** дополнительно к ожидаемым shim+DeleteModel.
- Архитектурно решение хорошее: legacy `zip` сделан **через proxy-models** (наследование от `apps.directory.*` моделей с `proxy=True, app_label='zip'`), а не голые re-export — это лучше моего исходного предложения, потому что сохраняет работоспособность string-FK `to='zip.Display'` в существующих миграциях.
- `manage.py check` зелёный, `makemigrations --check --dry-run` → `No changes detected`, `pytest --collect-only` собирает 79, точечный smoke 9/9 зелёных. Главное скрытое требование задачи закрыто.
- Остаётся **один P0 gate**: 19 alignment-миграций ещё ни разу не сравнивались с реальной prod-схемой. Без этого staging cutover невозможен. Создал `T-5-fix-003-live-db-verification.md`.

**Готовность реальная: ~92%** (была 88% перед hotfix, 90% по самооценке кодера). Поднятие связано с разблокировкой migration graph и dev-tooling — два настоящих блокера сняты.

---

## 1. Что подтверждено лично

### legacy models.py → shim/proxy

Прочитал все 7 legacy `models.py`:

| File | Размер | Что внутри |
|---|---|---|
| `main/models.py` | 5 строк | пустой (но в shape `from django.db import models`-only — норм) |
| `user/models.py` | 7 строк | re-export `MsUser` из `apps.core.users` |
| `application/models.py` | 15 строк | re-export `Application*` |
| `departure/models.py` | 19 строк | re-export `Departure/Executor/Contact*` |
| `zip/models.py` | 100 строк | **proxy-models** (наследование от `apps.directory.*` + `apps.workflow.daily_tasks`) с `app_label='zip'` |
| `mail/models.py` | 36 строк | concrete `GmailMessage` + `Alarm` — **не тронуто**, кодер обосновал в отчёте |
| `main_menu/models.py` | 91 строка | concrete `*HistoryReport` — **не тронуто**, ждёт T-2-023 |

Решение по `mail` и `main_menu` — корректное. Они не создавали duplicate-model collision, и трогать их в этом hotfix'е значило бы выйти за scope. Зафиксировал в `T-5-fix-003`, что T-5-050 должен явно решить судьбу `mail_alarm`/`mail_gmailmessage` после prod stable.

### `INSTALLED_APPS`

Подтверждено: `monitoring`, `control`, `service` убраны. Остались `main`, `main_menu`, `zip`, `departure`, `application`, `mail` — все с миграциями.

### Pattern proxy-models в zip/migrations/0003

Прочитал `zip/migrations/0003_remove_models_from_state.py` — корректно: сначала `DeleteModel` (убирает concrete из state), затем `CreateModel(proxy=True, bases=…)` для каждой. Симметрично коду в `zip/models.py`. **Сохраняет работоспособность** legacy импорт-путей и string-FK `"zip.Display"`, `"zip.Panels"` в старых миграциях `application/0002_initial.py` и т.д.

### 19 alignment-миграций

Прочитал `apps/directory/displays/migrations/0004_alter_*.py` — это как раз пример накопленного state-drift. Содержит `AlterModelOptions` (`ordering`, `verbose_name`) и `AlterField` для `Cell.id → BigAutoField`, `Cell.display → FK без to_field='name'`, `Display.camera_link/description/cols/city`. Все обёрнуты в `SeparateDatabaseAndState(database_operations=[])`. Это означает:
- Django state теперь утверждает, что эти поля имеют **нынешние** определения.
- Физически в БД поля **должны быть в таком же виде уже сейчас** (применено через T-2-025/T-2-027/T-2-028 в Phase-2).
- Если в реальной prod-БД поле всё ещё в старом виде — следующая нормальная миграция найдёт inconsistency.

Это и есть содержание T-5-fix-003.

### dev/test deps + UTF-8 requirements

Проверил, что:
- `T-5-fix-002-followup-ruff.md` создан и в `blocked` (правильно — после cutover).
- В отчёте кодер явно перечислил: `pip install -e ".[dev,test]"` → ok, `requirements.txt` UTF-8, `pytest --collect-only` → 79, `bootstrap_dev.sh`+`Makefile dev-setup` ставят extras.

Из отклонений: пришлось дописать `setuptools.find` в `pyproject.toml` для editable install и переехать с `--cov-omit` CLI-флага на `.coveragerc` (pytest-cov 7 убрал поддержку флага). Оба отклонения — мелкие, корректные.

---

## 2. Архитектурные решения кодера, которые стоит отметить

### 2.1. Proxy-models в `zip` вместо чистого re-export

В моей карточке T-5-fix-001 я написал «голый re-export shim» с прямым `from apps.directory.displays.models import Display`. Кодер сделал лучше: `class Display(DirectoryDisplay): class Meta: proxy = True; app_label='zip'`.

**Почему это лучше:**
- String-FK ссылки `to="zip.Display"` в старых миграциях продолжают резолвиться корректно (через registered `zip.Display` proxy-model).
- Re-export без proxy сделал бы `zip.Display` алиасом `directory_displays.Display` — для python-кода работает, но Django app-registry знает только `directory_displays.Display`, и любая string-FK на `zip.Display` упала бы.
- При миграциях legacy app `zip` остаётся валидным app в Django state — миграции `zip/migrations/0001_initial.py..0003_remove_models_from_state.py` непрерывны.

**Это решение, которое архитектор должен отметить как pattern для будущих legacy-app migration.** Записываю в `adr/`-задачу: после cutover написать ADR «proxy-models для legacy compat при переезде apps».

### 2.2. Alignment через новые миграции, а не правкой существующих

Кодер сам себе предупреждение в отчёте:

> «Остаточный drift гасился не через переписывание старых `0001_initial_state_import`, а через новые выравнивающие миграции. Это сохраняет историю и делает change set явным.»

Это правильный подход для прода: переписывать применённые миграции — это перезапись `django_migrations` истории, а это всегда плохо в долгом проекте. Лучше +N alignment-миграций, чем mutated state.

### 2.3. Минимальные отклонения от плана

В обоих отчётах кодер чётко перечислил отклонения с обоснованием:
- В T-5-fix-002: пришлось править `pyproject.toml` для package discovery (без этого editable install не работает) — корректно.
- В T-5-fix-001: `mail`/`main_menu` не трогались — корректно (вне scope).
- В T-5-fix-001: live-DB прогон не сделан — честно зафиксировано как known issue.

Конвенция «PR без отчёта не мерджится» работает.

---

## 3. Что не доделано — для T-5-fix-003

### Критично (блокирует staging)

**Live-DB verification не сделан.** Все 19 alignment-миграций — state-only. Никто не подтвердил, что физическая схема в prod совпадает с тем, что Django state теперь утверждает. Это разрулит T-5-fix-003.

### Серьёзно

- Полный `pytest -x` не прогнан (зависит от живой БД). 9/9 точечных тестов прошли — приятно, но 79 collected ≠ 9 passed.
- Schema diff `clean DB ↔ prod-после-migrate` не построен.

### В followup-задачах (P3, после cutover)

- `T-5-fix-002-followup-ruff` — 291 ruff / 96 black / 16 mypy. Blocked до cutover, корректно.
- `T-5-050` — финальный legacy cleanup, blocked до 2 недель prod stable.
- Backlog (P3): `Executor → MsUser` явный FK, чтобы trigger assignee не зависел от совпадения `telegram_id`. После prod stable.
- Backlog (P3): `AUTH_USER_MODEL='user.MsUser'` → `apps.core.users.MsUser`. Отдельная итерация после prod stable, требует пересоздания auth-таблиц с data-migration. Не P0.

---

## 4. Что архитектор сделал в этой followup-сессии

- Прочитал отчёты T-5-fix-001 и T-5-fix-002.
- Лично проверил: legacy `models.py` (все 7), `Config/settings.py:INSTALLED_APPS`, `zip/migrations/0003_remove_models_from_state.py`, `apps/directory/displays/migrations/0004_alter_*.py`.
- Создал `T-5-fix-003-live-db-verification.md` — финальный gate перед cutover, P0, 2-3 часа.
- Этот followup-отчёт `08-reports/architect-review-2026-05-06-followup.md`.
- Обновил `03-tasks/README.md` (новый ряд T-5-fix-003) и `02-roadmap/progress.md`.

### Что архитектор НЕ делал

- Не переводил T-3-fix-001/002, T-4-*, T-5-001..040 из review в done. Делаю это **одной волной** после T-5-fix-003, потому что live-DB прогон может выявить регрессии в любой из этих задач.
- Не правил миграции — это работа кодера в T-5-fix-003.
- Не писал ADR про proxy-models pattern — отдельной заметкой в backlog после cutover.

---

## 5. Что делать дальше

1. **Кодер** берёт `T-5-fix-003`. Поднимает локальный PostgreSQL (docker compose), прогоняет migrate на чистой БД и (если есть дамп от владельца) на копии прод-БД. Сравнивает схемы. Прогоняет `pytest -x`. Локальный smoke. Решает по `mail`/`main_menu`. Пишет отчёт.
2. **Владелец** выдаёт прод-БД дамп (если ещё не выдан) — без него Шаг 3 в T-5-fix-003 пропускается, но архитектор не закроет задачу `done` без этого шага.
3. **Архитектор** ревьюит результат. Если schema diff чистый и pytest зелёный — переводит T-3-fix-001/002 + T-4-* + T-5-001..040 + T-5-fix-001/002/003 в `done`, обновляет progress до 95%+.
4. **Владелец** запускает staging cutover по `phase-5-rollout-runbook.md`. Заполняет реальные env, прогоняет smoke (Telegram proxy, MAX webhook, VNNOX), включает systemd timers.
5. **2 недели стабильной работы SPA в проде** → разблокирует `T-5-050` legacy cleanup.

---

## 6. Если коротко

Хорошо: оба hotfix закрыты грамотно, proxy-models pattern в `zip` лучше моего исходного плана, отчёты содержательные.
Плохо: 19 state-only миграций ни разу не верифицированы на живой БД — пока это слепая зона.
Действие: одна задача `T-5-fix-003` (~2-3 часа кодера) разблокирует staging cutover.

Готовность 92%, осталось ровно одно фактическое препятствие — `migrate` на dump прод-БД.
