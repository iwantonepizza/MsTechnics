# HANDOFF.md — что делать дальше

> Шпаргалка для владельца. Состояние: Фаза 5 и оба hotfix в review; перед staging cutover осталась живая DB/env проверка.

**Дата:** 2026-05-06 (обновлено кодером)

---

## 1. Что произошло

### Кодер сделал (с прошлого HANDOFF)

- ✅ Фаза 5 в review целиком: notifications infra/channels/triggers, Telegram proxy healthcheck, MAX webhook + binding, VNNOX Gmail парсер + AlarmEvent + UI tab, systemd timers для daily tasks/VNNOX, удаление `sender_tg_message.py`/`daily_checker.py`/`ManageControl.py`.
- ✅ Все ключевые T-3 hotfix и T-4 polish задачи закрыты на уровне review с отчётами.
- ✅ `api-schema.yaml` (80 KB) и `frontend/src/shared/api/schema.d.ts` (95 KB) сгенерированы и синхронны.
- ✅ Конвенция «PR без отчёта не мерджится» теперь соблюдается — кодер пишет отчёты в `ai-docs/08-reports/`.

### Что архитектор нашёл и обозначил (новое)

🟡 **Что уже снято по T-5-fix-001.**
- `python manage.py check` теперь зелёный;
- legacy duplicate models в `main/user/zip/application/departure` вычищены через shim/proxy и state-only миграции;
- пустые `monitoring/control/service` убраны из `INSTALLED_APPS`.
- `python manage.py makemigrations --check --dry-run` теперь даёт `No changes detected`.

🔴 **Что всё ещё блокирует staging cutover.**
- `python manage.py migrate --plan` локально нельзя добить из-за недоступного PostgreSQL host из env (`getaddrinfo failed`);
- `python manage.py migrate` не проверен на живой dev/staging БД;
- нужен smoke runbook с реальными env после поднятия PostgreSQL/секретов.

🟢 **Инфра-блокер (T-5-fix-002) закрыт на review.**
- `.venv` теперь поднимает `pytest`, `ruff`, `black`, `mypy`, `factory-boy`, `freezegun`;
- `requirements.txt` переведён в UTF-8 без BOM;
- `pytest --collect-only` собирает 79 тестов, точечный backend smoke даёт 9/9 зелёных;
- `ruff/black/mypy` запускаются, но показывают накопленный baseline (`291/96/16`) — это вынесено в follow-up, а не в cutover hotfix.

🟢 **Хорошие новости.** Фаза 5 функционально на месте, `Makefile`, `infra/systemd/*`, `phase-5-rollout-runbook.md` готовы.

---

## 2. Что делать прямо сейчас

### Шаг 1 — поднять живой DB/env и добить verification

Превратить legacy `main/user/zip/application/departure/mail/main_menu/models.py` в re-export shim'ы (модели импортируются из `apps/*`), добавить миграции `SeparateDatabaseAndState(state_operations=[DeleteModel(...)], database_operations=[])` в каждый legacy app, убрать `monitoring/control/service` из INSTALLED_APPS если у них нет миграций.

Что уже сделано:

```bash
python manage.py check                  # уже чисто
pytest --collect-only -q                # уже собирает 79 тестов
python manage.py makemigrations --check --dry-run   # уже No changes detected
```

Что осталось:

```bash
python manage.py migrate --plan
python manage.py migrate
pytest -x
```

См. полную карточку: `ai-docs/03-tasks/phase-5-integrations/T-5-fix-001-migration-graph-cleanup.md`.

### Шаг 2 — staging cutover по runbook

После закрытия T-5-fix-001 разблокирован шаг 2 в `ai-docs/06-integrations/phase-5-rollout-runbook.md`. Дальше — env, smoke по разделам runbook'а (Telegram proxy, MAX webhook, VNNOX, timers).

### Шаг 3 — заполнить env (как и раньше)

Без коммита секретов:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_PROXY_URL`
- `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`
- `Config/token.pickle` для Gmail OAuth

### Шаг 4 — дизайнер polish (если ещё актуально)

Если ещё нет эскизов от Claude Design на оставшиеся 5 экранов — запросить по `ai-docs/07-frontend/design-brief-round-3.md`:
1. Display View / Мониторинг
2. Display View / Контроль
3. Department List
4. ZIP Overview
5. 12 модалок transition

### Шаг 5 — T-5-050 не трогать пока

Legacy cleanup `T-5-050` остаётся blocked до SPA в prod/staging + 2 недели без откатов.

---

## 3. Чек-лист «когда закроется Фаза 5 / можно катить prod»

### Перед staging cutover

- [x] **T-5-fix-001 review** — migration graph/state drift дочищен в коде
- [x] **T-5-fix-002 review** — pytest и ruff запускаются
- [ ] `pytest -x` зелёный (или внятный список known failures)
- [ ] `python manage.py migrate` на копии прод-БД успешно применил все новые миграции

### Staging smoke (по runbook)

- [ ] Логин + token rotation
- [ ] DisplayView показывает реальные данные
- [ ] SSE: открыл 2 вкладки, изменил статус — обновляется
- [ ] Создание заявки end-to-end
- [ ] Transition (apply, send-to-service, work, done)
- [ ] Telegram через proxy доставляет
- [ ] MAX fallback срабатывает при недоступном TG
- [ ] VNNOX парсит реальные 4 письма владельца
- [ ] Coverage frontend ≥ 60% (на критичных hooks) — задокументировано в отчёте

### Перевод задач в done (архитектор)

- [ ] T-3-fix-001/T-3-fix-002 в `03-tasks/README.md` переведены review → done
- [ ] T-4-001..T-4-032 переведены review → done
- [ ] T-5-001..T-5-040 переведены review → done
- [ ] `02-roadmap/progress.md` обновлён до 100% по Фазе 5

---

## 4. Если что-то пошло не так

- **Кодер не понимает, как делать SeparateDatabaseAndState DeleteModel** → есть пример в `apps/directory/displays/migrations/0001_initial_state_import.py` (правильный SeparateDatabaseAndState с пустыми database_operations). В карточке T-5-fix-001 есть готовый снипет миграции для `zip`.
- **Прод-БД сломалась после migrate** → откатить commit, восстановить дамп, пересмотреть план миграций. T-5-fix-001 — state-only, физических изменений в таблицах быть не должно. Если что-то изменилось — в коде есть `database_operations`, не должно быть.
- **Дизайнер делает не то** → скинуть эскиз, архитектор ревью.
- **Прод упал** → откатить миграцию, потом разобраться.

---

## 5. Полные ссылки

- **Архитектурное ревью (свежее):** `ai-docs/08-reports/architect-review-2026-05-06.md`
- **Hotfix задача P0:** `ai-docs/03-tasks/phase-5-integrations/T-5-fix-001-migration-graph-cleanup.md`
- **Hotfix задача P1:** `ai-docs/03-tasks/phase-5-integrations/T-5-fix-002-dev-test-deps.md`
- **Follow-up lint baseline:** `ai-docs/03-tasks/phase-5-integrations/T-5-fix-002-followup-ruff.md`
- **Runbook staging:** `ai-docs/06-integrations/phase-5-rollout-runbook.md`
- **Прогресс:** `ai-docs/02-roadmap/progress.md`

---

**Текущая ветка содержит:**
- Фазу 5 в review;
- отчёты по T-3 hotfix, T-4 polish, T-5 integrations;
- свежее архитектурное ревью + два hotfix-задачи (T-5-fix-001/002) перед staging.
