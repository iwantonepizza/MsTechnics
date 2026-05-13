# HANDOFF.md — что делать дальше

> Шпаргалка для владельца. Состояние: Phases 1-5 закрыты, T-5-fix-003 апрувлен. На сервере при деплое — ошибка миграций из-за конфликта старого `prod_dump_compat.sql` и новых forward-only migrations. Разруливает `T-6-001`.

**Дата:** 2026-05-07 (обновлено архитектором)

---

## 1. Что произошло

### Кодер закрыл (с прошлого HANDOFF)

- ✅ **T-5-fix-003 done.** На копии прод-БД (`db_dumps/mstechnics.dump`) полный цикл `restore → migrate → smoke` отработал. Реальные данные: 7 users, 8 displays, 2333 panels, 10 applications. HTTP smoke зелёный. pytest 79/79, coverage 57%.
- ✅ Добил то, чего не было в моей карточке: 4 forward-only data-migrations для физической конверсии `varchar(name)` FK → `bigint(id)` (`users/0003`, `displays/0005/0006`, `panels/0004`). С `atomic=False`, backfill + validation + RENAME COLUMN.
- ✅ Schema diff между чистой БД и копией прод-after-migrate: содержательных различий нет, остатки косметические (`zip_photodisplay_*` имена индексов от legacy).

### Архитектор закрыл

- ✅ **Апрув T-5-fix-001/002/003.** Все три hotfix переведены review → done.
- ✅ **Массовый review → done:** T-1-008, T-3-fix-001/002, T-4-001..T-4-032, T-5-001..T-5-040. Все ключевые работы Фаз 3/4/5 теперь done. Готовность 92% → **96%**.

### Архитектор нашёл новое (критичный блокер cutover)

🔴 **Двойной путь восстановления.** В репо есть и `scripts/prod_dump_compat.sql` (старый костыль), и forward-only migrations T-5-fix-003. На сервере применение **обоих** приводит к `ProgrammingError: operator does not exist: bigint = character varying` — именно это видит владелец как «миграции не делаются». См. подробный разбор в `08-reports/architect-review-2026-05-07-prod-cutover.md`, раздел 3.

🔴 **Прод-дамп в git.** `db_dumps/mstechnics.dump` и `mstechnics.dump` в корне могут быть закоммичены. Это PII (имена пользователей, заявки, координаты камер). Закрыть `.gitignore`, при необходимости — почистить историю через `git filter-repo`.

---

## 2. Что делать прямо сейчас

### Шаг 1 — кодер берёт T-6-001 (3-4 часа)

Полная карточка: [`ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md`](ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md).

Главное:

1. Запросить у владельца параметры сервера + текущий вывод `python manage.py showmigrations` с прод-сервера. Это центральный диагностический артефакт.
2. **Удалить `scripts/prod_dump_compat.sql`.** Убрать его вызов из `restore_dump.ps1`.
3. **Переписать `scripts/restore_to_dev.sh`** под актуальный формат (`pg_restore` + `migrate`).
4. Прогнать на staging-копии БД целиком, без compat — миграции должны пройти.
5. Если на проде уже частично применены миграции — `showmigrations` покажет, до какой точки. Дальше `migrate` точечно + при необходимости `--fake` (с обоснованием в отчёте).
6. Написать `ai-docs/06-integrations/production-cutover-runbook.md` — это документ для владельца, не для кодера. Со step-by-step Linux-командами, backup strategy перед cutover и rollback plan.

### Шаг 2 — кодер берёт T-6-004 (P0 security, 30 мин — 2 часа)

Полная карточка: [`ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md`](ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md).

```bash
# Сначала проверить, был ли push в публичный remote
git log --all --full-history -- "*.dump" "db_dumps/*" "logs/*"
```

Если push был — согласовать с владельцем `git filter-repo` + force push (это ломает все клоны). Если только локально — просто закрыть `.gitignore` и удалить из tracked.

### Шаг 3 — владелец проходит runbook на сервере

После T-6-001 done. По созданному `production-cutover-runbook.md`:

1. **Обязательно сначала `pg_dump` текущей прод-БД** в `/var/backups/pre_cutover_YYYYMMDD.dump`.
2. Pull новую ветку.
3. `pip install -e ".[dev,test]"` + `pip install -r requirements.txt`.
4. Прогон `restore_to_dev.sh` или нативный `pg_restore` + `migrate`.
5. Smoke `/api/v1/health/live`, `/admin/`, реальный login через SPA, открыть страницу `Displays` — должно быть 8 экранов.
6. Включить systemd timers (`mstechnics-daily-tasks.timer`, `mstechnics-vnnox-pull.timer`, `mstechnics-vnnox-unresolved.timer`).
7. Заполнить env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PROXY_URL`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `Config/token.pickle`.

### Шаг 4 — кодер берёт T-6-002 (backup) и T-6-003 (observability)

Параллельно с наблюдением. Без backup'а первый же сбой = потеря данных. Без мониторинга падение прода обнаружится по жалобе пользователя.

Полные карточки:
- [`T-6-002-backup-strategy.md`](ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md)
- [`T-6-003-observability.md`](ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md)

### Шаг 5 — 2 недели наблюдения, потом cleanup

- T-5-050 (templates/views/shims cleanup) разблокируется через 2 недели prod-stable.
- T-2-021/023/024 — параллельно по своим паузам.
- T-5-fix-002-followup-ruff — после cutover (lint baseline 291/96/16).

---

## 3. Чек-лист перед prod cutover

### Подготовка (Phase 5 hotfix)

- [x] T-5-fix-001 done — migration graph cleaned.
- [x] T-5-fix-002 done — dev/test extras в `.venv`.
- [x] T-5-fix-003 done — live-DB verify + 4 forward-only data-migrations.
- [x] Все review → done одной волной.
- [ ] **T-6-001 done** — runbook + удалён `prod_dump_compat.sql`.
- [ ] **T-6-004 done** — `.gitignore` + проверка утечки дампа.

### На сервере (владелец)

- [ ] `pg_dump` текущей прод-БД до cutover.
- [ ] `migrate` отработал на прод-БД без ошибок.
- [ ] `/api/v1/health/live` 200.
- [ ] Реальный login + token rotation работает.
- [ ] DisplayView видит 8 реальных экранов.
- [ ] SSE на 2 вкладках обновляется.
- [ ] Создание заявки end-to-end.
- [ ] Transition (apply/send/work/done) проходит.
- [ ] Telegram через proxy доставляет (нужен VPS).
- [ ] MAX fallback на закрытом TG.
- [ ] VNNOX парсит 4 реальных письма.
- [ ] systemd timers активны.

### После cutover (post-stable)

- [ ] T-6-002 done — backup strategy.
- [ ] T-6-003 done — observability + alerts.
- [ ] 2 недели prod-stable.
- [ ] T-5-050 (legacy cleanup) — после 2 недель.
- [ ] T-2-021/023/024 — после своих пауз.
- [ ] T-5-fix-002-followup-ruff — lint baseline.

---

## 4. Если что-то пошло не так

- **Миграции на сервере падают сейчас (текущий блокер)** → это T-6-001. Не пытайся обойти через `--fake-initial` или ручные SQL. Подожди закрытия T-6-001, кодер опишет точный путь с `showmigrations` matrix.
- **Прод-БД сломалась после `migrate`** → откатить из `/var/backups/pre_cutover_*.dump`. У forward-only миграций есть `reverse_sql = noop`, поэтому Django сам откатить не может — только из backup.
- **Не работает Telegram** → это ожидаемо в РФ. Должен сработать MAX fallback (если конфиг есть). Проверить `scripts/check_telegram_proxy.py`.
- **Прод упал** → откати миграцию из backup, потом разбираться.

---

## 5. Полные ссылки

- **Свежий апрув + новые задачи:** [`ai-docs/08-reports/architect-review-2026-05-07-prod-cutover.md`](ai-docs/08-reports/architect-review-2026-05-07-prod-cutover.md)
- **T-6-001 (P0 текущий блокер):** [`ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md`](ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md)
- **T-6-002 (P1 backup):** [`ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md`](ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md)
- **T-6-003 (P1 observability):** [`ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md`](ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md)
- **T-6-004 (P0 security):** [`ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md`](ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md)
- **Отчёт T-5-fix-003:** [`ai-docs/08-reports/T-5-fix-003.md`](ai-docs/08-reports/T-5-fix-003.md)
- **Прогресс:** [`ai-docs/02-roadmap/progress.md`](ai-docs/02-roadmap/progress.md)
- **Reestr задач:** [`ai-docs/03-tasks/README.md`](ai-docs/03-tasks/README.md)

---

**Готовность: 96%. До prod-релиза — 1 неделя на cutover runbook + 2 недели наблюдения.**
