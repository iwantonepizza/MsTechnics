# HANDOFF.md — что делать дальше

> Шпаргалка для владельца. Состояние: Phases 1-5 закрыты, T-5-fix-003 апрувлен. **Phase 7 готов:** дизайнерский Round 4 закрыт (T-7-100), multi-role permissions (T-7-003 Wave 1+2) закрыты, 3 backend follow-up закрыты. Все coder-side задачи Phase 6 (T-6-001..006) закрыты. **Архитектор довёл репо до прод-готовности.**

**Дата:** 2026-05-20

---

## 0. TL;DR — что делать прямо сейчас (≤30 минут)

1. **На сервере `git pull origin main`** — всё уже в main, никаких merge'ей открывать не нужно. Ветка `feature/phase-7-prod-readiness` уже смержена fast-forward и удалена.
2. **Выполнить T-6-005 secret rotation** (~30 мин ваших действий, см. раздел ниже).
3. **Прогнать prod cutover по `ai-docs/06-integrations/production-cutover-runbook.md`** в maintenance окно 22:00–08:00 МСК.
4. После cutover включить systemd-таймер бэкапов (`ai-docs/06-integrations/backup-runbook.md`) и поднять Prometheus+Grafana (`ai-docs/06-integrations/observability-runbook.md`).

**Проверки перед прод-деплоем уже выполнены:**
- ✅ **Полный prod-copy smoke 2026-05-20** (`db_dumps/mstechnics.dump` → `pg_restore` → `migrate` → `check` → HTTP smoke на 24 endpoints). Все миграции (включая T-7-003 backfill ролей) отработали на реальных данных. Полный отчёт: [`ai-docs/08-reports/smoke-2026-05-20-prod-copy.md`](ai-docs/08-reports/smoke-2026-05-20-prod-copy.md).
- ✅ Data-integrity post-migration: **7 users, 8 displays, 2333 panels, 10 applications** — точно как ожидалось.
- ✅ **T-7-003 multi-role backfill безопасен:** все 7 user-ов получили роли (`permission='all'` корректно разворачивается в 3 роли monitoring+control+service).
- ✅ `/api/v1/health/live` → 200, `/api/v1/health/ready` → 200 (DB+Redis OK), `/metrics` → 200 (Prometheus), `/api/schema/?format=json` → 200 (OpenAPI 3.0.3, 64+ маршрутов), `/api/v1/auth/login/` → 200 (JWT с `permission`+`roles`+`extra_permissions`).
- ✅ Backend pytest: **114/114 passed**.
- ✅ Frontend vitest: **16 files / 60 tests passed**.
- ✅ Frontend typecheck: **clean**.
- ✅ Git: всё в `main`, working tree clean, никаких feature-веток.

---

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

✅ **T-6-004 done.** `.gitignore` обновлён, история переписана через `git filter-repo`, `git push --force --all/--tags origin` выполнен. Кодер обнаружил в утечке **больше**, чем думали: помимо `db_dumps/mstechnics.dump` и `logs/`, в git-tracked были `Config/.env` и `Config/client_secret.json` — это полноценный security incident.

🔴 **T-6-005 (новая P0 security).** Force-push НЕ инвалидирует уже утёкшие секреты. Любая копия истории до push содержит их в открытом виде. Перед prod cutover обязательно ротировать: Google OAuth credentials (`client_secret.json` + новый `token.pickle`), `SECRET_KEY` Django, `DATABASE_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `SENTRY_DSN`. Карточка [T-6-005](ai-docs/03-tasks/phase-5-integrations/T-6-005-rotate-leaked-secrets.md) — это **владелец** делает большую часть (доступ к Google Cloud Console, BotFather, dev.max.ru, прод-БД).

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

### Шаг 2 — владелец доделывает T-6-005 owner-side (~30 мин)

Coder-side готова (`check_gmail_oauth.py` + helper + обезличенный `.env.example` + incident report). Полная карточка: [`ai-docs/03-tasks/phase-5-integrations/T-6-005-rotate-leaked-secrets.md`](ai-docs/03-tasks/phase-5-integrations/T-6-005-rotate-leaked-secrets.md).

Минимум — что делает владелец:

- Google Cloud Console → **удалить** старый OAuth Client ID, выпустить новый, скачать `client_secret.json`, удалить старый `token.pickle` на сервере, перевыполнить OAuth flow, прогнать `python scripts/check_gmail_oauth.py` для проверки.
- Django `SECRET_KEY` → новый `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- `DATABASE_PASSWORD` → `ALTER USER mstechnics WITH PASSWORD '...'` + обновить `Config/.env`.
- `@BotFather` → `/revoke` старый TG token, новый в `Config/.env`.
- https://dev.max.ru → reset MAX token + перегенерить `MAX_WEBHOOK_SECRET` + перерегистрировать webhook.
- Обновить `08-reports/security-incident-2026-05-13.md` фактическими датами ротации.

### Шаг 3 — старые клоны репо: чистка

Filter-repo переписал SHA коммитов. Любая существующая копия репо (на других машинах разработчиков, на прод-сервере, форки на GitHub) содержит **старую** историю с утёкшими файлами. См. раздел «Про старые клоны» ниже — что с ними делать.

### Шаг 3 — владелец проходит runbook на сервере

После T-6-001 done. По созданному `production-cutover-runbook.md`:

1. **Обязательно сначала `pg_dump` текущей прод-БД** в `/var/backups/pre_cutover_YYYYMMDD.dump`.
2. Pull новую ветку.
3. `pip install -e ".[dev,test]"` + `pip install -r requirements.txt`.
4. Прогон `restore_to_dev.sh` или нативный `pg_restore` + `migrate`.
5. Smoke `/api/v1/health/live`, `/admin/`, реальный login через SPA, открыть страницу `Displays` — должно быть 8 экранов.
6. Включить systemd timers (`mstechnics-daily-tasks.timer`, `mstechnics-vnnox-pull.timer`, `mstechnics-vnnox-unresolved.timer`).
7. Заполнить env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PROXY_URL`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `Config/token.pickle`.

### Шаг 4 — T-6-006 ✅ done (апрув архитектора)

`.editorconfig` + `.gitattributes` + `scripts/check_encoding.py` + pre-commit hook `check-encoding`. Сканер зелёный по всему репо, **54 markdown task card с BOM** починены, `T-6-001-production-cutover-runbook.md` восстановлен из cp1251-mojibake. 7 тестов, coverage 92%. Карточка: [`T-6-006`](ai-docs/03-tasks/phase-5-integrations/T-6-006-encoding-hygiene.md).

### Шаг 4c — Design Round 4 СДАН дизайнером (2026-05-19 вечер) ★

Дизайнер прислал готовый пакет интеграции. Положено в репо:

- **5 ai-docs** в `ai-docs/07-frontend/`: `design-handoff-round-4.md`, `design-audit-2026-05-19.md` (43 пункта, 9 P0 / 24 P1 / 10 P2), `design-polish-round-3.md`, `microinteractions-a11y-fixes.md`, `mobile-adaptation-plan.md` (Phase 8).
- Исторический пакет из **17 файлов-патчей** (`_design-patches-round-4/frontend-patches/`) уже интегрирован и удалён cleanup-PR'ом. История выполнения разложена по `ai-docs/08-reports/T-7-100-pr-1.md` ... `T-7-100-pr-11.md`.
- **Карточка для кодера:** [`T-7-100`](ai-docs/03-tasks/phase-7-product/T-7-100-design-round-4-integration.md) — со ссылками на все диффы.
- **3 backend follow-up** для архитектора → кодеру:
  - [`T-7-followup-applications-display-city`](ai-docs/03-tasks/phase-7-product/T-7-followup-applications-display-city.md) — P1, нужно для PR-10.
  - [`T-7-followup-display-aggregated-condition`](ai-docs/03-tasks/phase-7-product/T-7-followup-display-aggregated-condition.md) — P2.
  - [`T-7-followup-bell-deeplink-resolve`](ai-docs/03-tasks/phase-7-product/T-7-followup-bell-deeplink-resolve.md) — P3 опционально.

**От тебя ждётся:** ничего — cleanup уже выполнен. Если нужен контекст по Round 4, смотри `ai-docs/07-frontend/design-handoff-round-4.md` и отчёты `T-7-100-pr-*`.

### Шаг 4b — Design Brief Round 4 готов (2026-05-19, утро)

[ai-docs/07-frontend/design-brief-round-4-2026-05-19.md](ai-docs/07-frontend/design-brief-round-4-2026-05-19.md) — **большое задание для Claude Design** на ~25 часов работы. 5 зон:

- **A. Comprehensive design audit** всех 9 экранов в обеих темах → баг-репорт ≥30 пунктов.
- **B. Полировка 5 экранов Round-3** (DepartmentList, 3 ролей DisplayView, ZIP, Departures, модалки).
- **C. Review 6+ новых компонентов** Phase 7 от Opus (ConfirmDialog, NotificationBell, PanelCreate/Delete, ThemeToggle, Profile-секции).
- **D. Mobile/Android adaptation** — новое требование A2. План breakpoints + JSX для Login/Menu/DepartmentList/DisplayView на phone.
- **E. Microinteractions + accessibility** — focus rings, skeletons единообразие, theme switch transition, ARIA labels.

Содержит готовый промпт для копипасты в Claude Design (Часть 1), контекст (Часть 2), 5 зон работы (Часть 3), выжимку owner-answers (Часть 4), open questions (Часть 5), deliverables-чеклист (Часть 6), список референсов (Часть 7).

**Что владелец делает:**
1. Прикрепляет к новому сообщению Claude Design свежий ZIP проекта.
2. Прикрепляет PDF брендбука + гайдбука (если у дизайнера их ещё нет — у владельца есть локально).
3. Копирует промпт из Части 1 и шлёт.

Дизайнер работает несколькими сессиями. Каждая зона — отдельный deliverable.

### Шаг 5 — старт Phase 7 (rebranding + dark mode, параллельно с post-cutover)

Владелец дал большой пакет продуктовых ответов 2026-05-13 + новый брендинг «Суперсимметрия» с конкретной палитрой и логотипом, требование dark mode.

Артефакты архитектора (обновлены 2026-05-16):
- [`07-frontend/owner-answers-2026-05-13.md`](ai-docs/07-frontend/owner-answers-2026-05-13.md) — все ответы как источник истины.
- [`07-frontend/brand-palette-supersymmetria.md`](ai-docs/07-frontend/brand-palette-supersymmetria.md) — палитра + готовый CSS-mapping (light + dark).
- [`07-frontend/brand-guidelines-supersymmetria.md`](ai-docs/07-frontend/brand-guidelines-supersymmetria.md) — **новое**: полный свод правил из брендбука Суперсимметрия (115 стр.) + гайдбука (50 стр.). Шрифты, логотип-правила, голос бренда, что НЕ делать.
- [`adr/ADR-002-rebranding-supersymmetria.md`](ai-docs/adr/ADR-002-rebranding-supersymmetria.md) — решение по rebranding (UI меняем, БД/код/домен — нет). Обогащён находкой: **msgroup → Суперсимметрия**, наша система — внутренний инструмент DOOH-агентства.
- [`03-tasks/phase-7-product/README.md`](ai-docs/03-tasks/phase-7-product/README.md) — полный трекер 36 задач Phase 7 с закрытыми open questions.

**Закрыто Phase 7 (на 2026-05-20):**
- ✅ T-7-001 Rebranding (done).
- ✅ T-7-002 Design tokens v2 + dark mode (done).
- ✅ T-7-005 Storage + low-stock (done).
- ✅ T-7-007 Panel removal (done).
- ✅ T-7-010 Global search (done).
- ✅ T-7-013 Print заявки (done).
- ✅ T-7-030/031 Sort + city filter (done).
- ✅ T-7-100 **Round 4 design integration → review.** PR-1..13 закрыты, automated acceptance (npm test, эмодзи-grep, hex-grep, mёртвые классы) зелёный. Остался manual visual sweep light/dark/focus rings.
- ✅ T-7-003 **Multi-role + fine-grained permissions → review.** Wave 1 (модель `Role` + `MsUser.roles` M2M + `extra_permissions` JSONField + миграция `0004_role_and_user_roles.py` + backfill `permission → roles`) + Wave 2 (30+ мест с `user.permission in (...)` переведены на `has_role/is_admin`; notification triggers через `role_membership_q` для BC-friendly работы; admin UI с checkbox-формой для `extra_permissions`). Backend suite 114/114 ✅.
- ✅ Три backend follow-up из Round 4 → review:
  - T-7-followup-applications-display-city (DisplayMini.city для PR-10).
  - T-7-followup-display-aggregated-condition (P2, для DL-003 status bullet).
  - T-7-followup-bell-deeplink-resolve (P3, `deep_link_path` в inbox-сериализаторе).
- 🟡 **T-7-008 ConfirmDialog (review).** Универсальный диалог + `useConfirmDialog`-хук. 6 тестов.
- 🟡 **T-7-014 История юзера в Profile (review).** Хук `useMyActivity` + секция в ProfilePage. 3 теста.
- 🟡 **T-7-012 Звук уведомлений (review).** `notificationSound.ts` Web Audio API + SSE триггер на `application.create` + секция в Profile. 6+3 тестов.
- 🟡 **T-7-035 Создание панели (review).** Backend `POST /panels/` + `PanelCreateButton` (service/admin). 5 тестов.
- 🟡 **T-7-036 Удаление панели admin-only (review).** Backend `DELETE /panels/{id}/` с защитами + `PanelDeleteButton` через `<ConfirmDialog>`. 5 тестов.

**2-недельный stability window отменён** (владелец 2026-05-18). Разблокированы T-7-003 (multi-role) — закрыта в Wave 1+2, T-7-004 (Departure M2M) — ready, T-2-021/023/024 (Phase-2 cleanup), T-5-050 (legacy cleanup).

**Phase 7 фронт-блок + Round 4 + multi-role закрыты.** Frontend vitest 16 файлов / 60 тестов, backend pytest 114 passed.

**Техдолг из ревью T-7-005/007/010** (заведены как T-7-040..043, низкоприоритетные):
- T-7-040 — прогнать миграцию storage на копии прод-БД (страховка перед cutover).
- T-7-041 — стабилизировать `api-schema.yaml` snapshot (drf-spectacular даёт большой unrelated diff).
- T-7-042 — починить глобальный `npm run typecheck` (pre-existing ошибки в react-hook-form / legacy типах).
- T-7-043 — surfaced search schema в `shared/api/schema.d.ts`.
- [T-7-003 (6-8 ч)](ai-docs/03-tasks/phase-7-product/T-7-003-multi-role-and-fine-grained-permissions.md) — multi-role + extra_permissions. **Закрыта Wave 1+2 → review.** Wave 3 (drop `MsUser.permission`) — отдельная итерация через 2-4 недели работы Wave 2.
- [T-7-005 (~4 ч)](ai-docs/03-tasks/phase-7-product/T-7-005-storage-extensions-and-low-stock.md) — Storage: PowerBlocks + Connectors + `low_stock_threshold=3` (Z3, Z4). **Ready** (раунд 2026-05-17 закрыл вопрос порога).
- [T-7-007 (1.5-2 ч)](ai-docs/03-tasks/phase-7-product/T-7-007-panel-removal-conditional-reason.md) — снятие панели: в заявке `condition` required, без заявки optional. **Ready** (раунд 2026-05-17 разъяснил).
- [T-7-010 (4-6 ч)](ai-docs/03-tasks/phase-7-product/T-7-010-global-search.md) — глобальный поиск через `/` по 6 категориям (X1). **Ready**.
- [T-7-013 (2-3 ч)](ai-docs/03-tasks/phase-7-product/T-7-013-print-application-card.md) — print-friendly карточка заявки (X4). **Ready**.

**Отменено:** T-7-020 (VK Workspace channel) — владелец 2026-05-17 не использует этот продукт, fallback chain упрощён до **MAX → Telegram → Email**. T-7-021 (VK Community Bot) остаётся **blocked** до того, как владелец заведёт community-группу (личный VK API не подходит для бота).

PDF брендбуков лежат в `dumps/brand-pdf/` — **не коммитим в git** (`/dumps/` уже в `.gitignore`). При работе над T-7-001/002 PDF открывать как референс, выжимка для разработки — в `brand-guidelines-supersymmetria.md`.

T-7-001/002 — frontend-only, можно делать параллельно с T-6-001/002/003.
T-7-003..036 — большая часть blocked до prod stable.

### Шаг 6 — кодер берёт T-6-002 (backup) и T-6-003 (observability)

Параллельно с наблюдением. Без backup'а первый же сбой = потеря данных. Без мониторинга падение прода обнаружится по жалобе пользователя.

Полные карточки:
- [`T-6-002-backup-strategy.md`](ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md)
- [`T-6-003-observability.md`](ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md)

### Шаг 7 — 2 недели наблюдения, потом cleanup

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
- [x] **T-6-004 done** — `.gitignore` + проверка утечки дампа.
- [ ] **T-6-006 review** — encoding guardrails в репо уже добавлены, нужен апрув ревьюера.

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

## 4. Про старые клоны репо

После T-6-004 в `origin/main` лежит **переписанная** история без `*.dump`, `Config/.env`, `Config/client_secret.json`, `logs/`. SHA коммитов сдвинулись. Любая копия, сделанная до этого момента, содержит **старые** SHA + утёкшие файлы.

**Что считается «старым клоном»:**
- Локальные репо на других машинах разработчиков (если кто-то ещё клонировал).
- Клон на прод-сервере (`/opt/mstechnics/.git` или где он лежит).
- Форки на GitHub (если есть).
- GitHub mirror / CI-cache (Actions, Jenkins).

**Что делать с каждым:**

### Самый чистый вариант — fresh clone

```bash
# На той машине, где есть старый клон
cd ~
mv mstechnics mstechnics.old   # сохранили
git clone <repo_url> mstechnics  # свежий клон с переписанной историей
# Если в .old были uncommitted локальные правки — перенести руками через diff
diff -r mstechnics.old/<file> mstechnics/<file>
# После проверки можно удалить
rm -rf mstechnics.old
```

### Альтернатива — жёсткий resync (если жаль удалять)

```bash
cd <old_clone>

# 1. Сохранить локальные правки если есть
git stash

# 2. Обнулить все ветки до origin
git fetch --all
git reset --hard origin/main
git for-each-ref --format='%(refname)' refs/heads | while read ref; do
  git update-ref -d "$ref"
done
git fetch origin

# 3. Очистить reflog (там ссылки на старые объекты)
git reflog expire --expire=now --all

# 4. Garbage collect старые blob'ы из .git/objects
git gc --prune=now --aggressive

# 5. Проверить, что чувствительные файлы вычищены
git log --all --full-history -- "*.dump" "Config/.env" "Config/client_secret.json"
# Если ничего не выводит — чисто.
```

**Внимание:** жёсткий resync **не гарантирует** удаление, если:
- Старые объекты есть в `git stash`.
- Старые объекты есть в reflog других веток (поэтому удаляем все локальные refs).
- Какой-то процесс держит файл из старого commit (закрыть редактор/IDE).

После resync — рекомендую `du -sh .git/` — если размер не сильно сократился, значит остатки есть, fresh clone надёжнее.

### Что на проде

На прод-сервере репо тоже клон. После T-6-001 (когда будет deploy) кодер обновит сервер. Безопаснее **тоже сделать fresh clone**, не `git pull --force`:

```bash
sudo systemctl stop mstechnics-web
cd /opt
sudo mv mstechnics mstechnics.old
sudo git clone <repo_url> mstechnics
sudo chown -R mstechnics-user:mstechnics-user mstechnics
# Скопировать обратно .env, client_secret.json — это локальные файлы НА СЕРВЕРЕ, в git их нет
sudo cp /opt/mstechnics.old/Config/.env /opt/mstechnics/Config/.env       # ← НОВЫЕ значения после T-6-005
sudo cp /opt/mstechnics.old/Config/client_secret.json /opt/mstechnics/Config/  # ← НОВЫЙ файл
# .venv можно переиспользовать или пересоздать
sudo systemctl start mstechnics-web
```

После того как уверены, что новый клон работает — `rm -rf /opt/mstechnics.old`.

### Что с форками / GitHub mirror

Если на GitHub были форки (включая случайные клики «Fork») — старая история **в форках остаётся** независимо от force-push в `origin`. Если форки внутренние — попросить владельца их удалить. Если внешние — связаться с GitHub Support через https://github.com/contact и запросить removal of sensitive data (DMCA-like процедура).

---

## 5. Если что-то пошло не так

- **Миграции на сервере падают сейчас (текущий блокер)** → это T-6-001. Не пытайся обойти через `--fake-initial` или ручные SQL. Подожди закрытия T-6-001, кодер опишет точный путь с `showmigrations` matrix.
- **Прод-БД сломалась после `migrate`** → откатить из `/var/backups/pre_cutover_*.dump`. У forward-only миграций есть `reverse_sql = noop`, поэтому Django сам откатить не может — только из backup.
- **Не работает Telegram** → это ожидаемо в РФ. Должен сработать MAX fallback (если конфиг есть). Проверить `scripts/check_telegram_proxy.py`.
- **Прод упал** → откати миграцию из backup, потом разбираться.

---

## 6. Полные ссылки

- **Свежий апрув + новые задачи:** [`ai-docs/08-reports/architect-review-2026-05-07-prod-cutover.md`](ai-docs/08-reports/architect-review-2026-05-07-prod-cutover.md)
- **T-6-001 (P0 текущий блокер):** [`ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md`](ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md)
- **T-6-002 (P1 backup):** [`ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md`](ai-docs/03-tasks/phase-5-integrations/T-6-002-backup-strategy.md)
- **T-6-003 (P1 observability):** [`ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md`](ai-docs/03-tasks/phase-5-integrations/T-6-003-observability.md)
- **T-6-004 (P0 security, done):** [`ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md`](ai-docs/03-tasks/phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md)
- **T-6-005 (P0 security, ротация секретов, владелец):** [`ai-docs/03-tasks/phase-5-integrations/T-6-005-rotate-leaked-secrets.md`](ai-docs/03-tasks/phase-5-integrations/T-6-005-rotate-leaked-secrets.md)
- **Security conventions:** [`ai-docs/04-conventions/security-conventions.md`](ai-docs/04-conventions/security-conventions.md)
- **Отчёт T-5-fix-003:** [`ai-docs/08-reports/T-5-fix-003.md`](ai-docs/08-reports/T-5-fix-003.md)
- **Прогресс:** [`ai-docs/02-roadmap/progress.md`](ai-docs/02-roadmap/progress.md)
- **Reestr задач:** [`ai-docs/03-tasks/README.md`](ai-docs/03-tasks/README.md)

---

**Готовность: 96%. До prod-релиза — 1 неделя на cutover runbook + 2 недели наблюдения.**
