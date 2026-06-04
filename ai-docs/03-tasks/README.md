# 03-tasks — задачи для кодеров

## Как работать

1. Открой `README.md` (этот файл), найди задачу со статусом `ready`
2. Убедись, что **все зависимости (блокеры) в статусе `done`**
3. Замени в файле задачи `Статус: ready` → `Статус: in-progress`, впиши свой никнейм/модель в `Исполнитель:`
4. Читай ВСЮ задачу, включая разделы «Что НЕ нужно делать» и «Вопросы для архитектора»
5. Если что-то непонятно — **задай вопрос в секции «Вопросы для архитектора» и не начинай работу**. Архитектор ответит и обновит задачу.
6. Реализуй по чеклисту «Критерии приёмки»
7. Заполни раздел «Отчёт по выполнению»
8. Переведи статус в `review`
9. Открой PR, ссылайся на файл задачи
10. После мержа архитектор переводит статус в `done` и обновляет `../02-roadmap/progress.md`

---

## Реестр задач

Формат записи: `T-<фаза>-<номер>. <название>` — `статус` — `оценка`

### Фаза 1. Фундамент

| ID                                                | Название                                    | Статус | Часов |
|---------------------------------------------------|---------------------------------------------|--------|-------|
| [T-1-001](phase-1-foundation/T-1-001-pyproject-toml.md)   | pyproject.toml + requirements.lock          | done   | 1.5   |
| [T-1-002](phase-1-foundation/T-1-002-docker-compose.md)   | Починить docker-compose                     | done   | 2     |
| [T-1-003](phase-1-foundation/T-1-003-pre-commit.md)       | Pre-commit hooks                            | done   | 1.5   |
| [T-1-004](phase-1-foundation/T-1-004-structlog.md)        | Заменить print на structlog                 | done   | 2     |
| [T-1-005](phase-1-foundation/T-1-005-ci.md)               | GitHub Actions: lint + test                 | blocked | 2     |
| [T-1-006](phase-1-foundation/T-1-006-critical-bugfixes.md)| Критические багфиксы (signal, if Panels)    | done   | 2     |
| [T-1-007](phase-1-foundation/T-1-007-env-secrets.md)      | django-environ, секреты из git, отзыв OAuth | done   | 2     |
| [T-1-008](phase-1-foundation/T-1-008-prod-logging.md)     | Prod logging: JSON stdout + Sentry          | done   | 1.5   |
| [T-1-009](phase-1-foundation/T-1-009-safe-redirect.md)    | safe_redirect вместо redirect(HTTP_REFERER) | done   | 1     |
| [T-1-010](phase-1-foundation/T-1-010-limit-querysets.md)  | Ограничить querysets в views                | done   | 0.5   |
| [T-1-011](phase-1-foundation/T-1-011-hide-archived.md)    | Скрыть архивные заявки в панели (от владельца) | done | 1     |

**Итого фаза 1:** ~17 часов

### Фаза 2. Модели и миграции

**Итого: ~27 часов, 17 задач**

#### 2.1. Подготовка

| ID                                                           | Название                                       | Статус  | Часов |
|--------------------------------------------------------------|------------------------------------------------|---------|-------|
| [T-2-001](phase-2-models/T-2-001-prod-dump-baseline.md)      | Дамп прод-БД, импорт в dev, PII scrubber       | done    | 2     |
| [T-2-002](phase-2-models/T-2-002-factories.md)               | factory_boy фабрики для всех моделей           | done    | 3     |
| [T-2-003](phase-2-models/T-2-003-regression-tests.md)        | Regression-тесты (FSM, create/delete, panels)  | done    | 4     |

#### 2.2. Реорганизация

| ID                                                           | Название                                       | Статус  | Часов |
|--------------------------------------------------------------|------------------------------------------------|---------|-------|
| [T-2-010](phase-2-models/T-2-010-rename-msservicecontrol.md) | MsServiceControl → config                      | done    | 1     |
| [T-2-011](phase-2-models/T-2-011-apps-skeleton.md)           | Скелет apps/ по целевой архитектуре            | done    | 1.5   |
| [T-2-012](phase-2-models/T-2-012-move-main-user-to-core.md)  | Перенос main + user → apps/core                | done    | 3     |
| [T-2-013](phase-2-models/T-2-013-move-zip-to-directory.md)   | zip → apps/directory + Panels → Panel          | done    | 3     |
| [T-2-014](phase-2-models/T-2-014-move-application-departure.md) | application + departure → apps/workflow    | done    | 2.5   |

#### 2.3. Нормализация моделей

| ID                                                           | Название                                       | Статус  | Часов |
|--------------------------------------------------------------|------------------------------------------------|---------|-------|
| [T-2-020](phase-2-models/T-2-020-application-event-model.md) | Создать ApplicationEvent + backfill 28 полей   | done    | 3     |
| [T-2-021](phase-2-models/T-2-021-drop-denormalized-fields.md)| Удалить 28 старых полей (после T-2-020 на проде) | ready  | 1     |
| [T-2-022](phase-2-models/T-2-022-activity-log-model.md)      | Создать ActivityLog с GenericForeignKey        | done    | 2     |
| [T-2-023](phase-2-models/T-2-023-backfill-activity-log.md)   | Миграция данных: 5 History → ActivityLog (нужен прод-дамп) | review | 3     |
| [T-2-024](phase-2-models/T-2-024-drop-legacy-history.md)     | Удалить 5 старых History-таблиц (после T-2-023) | ready  | 1     |
| [T-2-025](phase-2-models/T-2-025-fk-to-id.md)                | FK to_field='name' → to_field='id'             | done    | 4     |
| [T-2-026](phase-2-models/T-2-026-remove-concretemsuser.md)   | Удалить ConcreteMsUser                         | done    | 0.5   |
| [T-2-027](phase-2-models/T-2-027-display-service.md)         | Display.save → DisplayService.create_with_layout | done | 2     |
| [T-2-028](phase-2-models/T-2-028-panel-application-status-computed.md) | Panel.application_status → computed  | done    | 2     |
| [T-2-029](phase-2-models/T-2-029-dailytask-notified-stages.md)| DailyTask.*_notification_sent → JSONField     | done    | 1.5   |
| [T-2-030](phase-2-models/T-2-030-departure-status-fk.md)     | Departure.status: CharField → FK               | done    | 1.5   |

#### 2.4. Сервисы и FSM

| ID                                                           | Название                                       | Статус  | Часов |
|--------------------------------------------------------------|------------------------------------------------|---------|-------|
| [T-2-040](phase-2-models/T-2-040-application-state-machine.md)| ApplicationStateMachine + Transition          | done    | 3     |
| [T-2-041](phase-2-models/T-2-041-panel-mover.md)             | PanelMover сервис (задача владельца #8)        | done    | 2     |

**Итого фаза 2:** ~27 часов активной работы + 2 недели пауз для миграций T-2-021 и T-2-024.

### Фаза 3. REST API

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-3-001](phase-3-rest-api/T-3-001-drf-jwt-setup.md) | DRF + SimpleJWT setup | done | 2 |
| [T-3-002](phase-3-rest-api/T-3-002-openapi-schema.md) | drf-spectacular schema | done | 1 |
| [T-3-003](phase-3-rest-api/T-3-003-permissions.md) | Permissions + city access | done | 2 |
| [T-3-004](phase-3-rest-api/T-3-004-pagination-errors-throttling.md) | Pagination, errors, throttling | done | 1.5 |
| [T-3-005](phase-3-rest-api/T-3-005-admin-refactor.md) | Перенести admin в apps/ | done | 1.5 |
| [T-3-010](phase-3-rest-api/T-3-010-auth-me.md) | /auth, /me | done | 2 |
| [T-3-011](phase-3-rest-api/T-3-011-references-crud.md) | Refs CRUD | done | 1.5 |
| [T-3-012](phase-3-rest-api/T-3-012-statuses.md) | Statuses ViewSet | done | 0.5 |
| [T-3-020](phase-3-rest-api/T-3-020-displays.md) | Displays | done | 2.5 |
| [T-3-021](phase-3-rest-api/T-3-021-panels.md) | Panels + transitions | done | 3 |
| [T-3-022](phase-3-rest-api/T-3-022-cells.md) | Cells | done | 1 |
| [T-3-023](phase-3-rest-api/T-3-023-storage.md) | ZIP storage | done | 1 |
| [T-3-030](phase-3-rest-api/T-3-030-applications.md) | Applications CRUD + filters | done | 2.5 |
| [T-3-031](phase-3-rest-api/T-3-031-application-transitions.md) | Application FSM endpoint | done | 2 |
| [T-3-032](phase-3-rest-api/T-3-032-events.md) | ApplicationEvents readonly | done | 0.5 |
| [T-3-033](phase-3-rest-api/T-3-033-departures.md) | Departures + transitions | done | 2 |
| [T-3-040](phase-3-rest-api/T-3-040-activity-log.md) | ActivityLog endpoint | done | 1 |
| [T-3-041](phase-3-rest-api/T-3-041-sse-stream.md) | SSE через Redis Streams | done | 2 |
| [T-3-050](phase-3-rest-api/T-3-050-health-checks.md) | Health checks | done | 0.5 |
| [T-3-051](phase-3-rest-api/T-3-051-e2e-tests.md) | E2E API tests | done | 2 |
| [T-3-fix-001](phase-3-rest-api/T-3-fix-001-status-names-sync.md) | **HOTFIX:** sync статусов БД↔контракт | done | 2 |
| [T-3-fix-002](phase-3-rest-api/T-3-fix-002-destroy-and-refresh.md) | **HOTFIX:** destroy() + refresh rotation | done | 1 |

**Итого фаза 3:** ~32 часа (29 done + 3 hotfix). Hotfix-ы критичны до старта Фазы 4.

### Фаза 4. React SPA

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-4-001](phase-4-spa/T-4-001-design-tokens.md) | tokens.css + Tailwind config | done | 2 |
| [T-4-002](phase-4-spa/T-4-002-openapi-types.md) | Generate TS types from schema | done | 1.5 |
| [T-4-003](phase-4-spa/T-4-003-routing.md) | React Router + ProtectedRoute | done | 2 |
| [T-4-004](phase-4-spa/T-4-004-app-layout.md) | AppLayout + Header + crumbs | done | 2 |
| [T-4-010](phase-4-spa/T-4-010-login-page.md) | LoginPage | done | 1.5 |
| [T-4-011](phase-4-spa/T-4-011-main-menu-page.md) | MainMenu v2 | done | 3 |
| [T-4-012](phase-4-spa/T-4-012-department-list.md) | DepartmentList | done | 3 |
| [T-4-013](phase-4-spa/T-4-013-display-view-pages.md) | DisplayView 3 ролей | done | 7 |
| [T-4-016](phase-4-spa/T-4-016-zip-page.md) | ZipPage | done | 3 |
| [T-4-020](phase-4-spa/T-4-020-transition-modals.md) | TransitionModal universal | done | 3 |
| [T-4-021](phase-4-spa/T-4-021-specialized-modals.md) | Specialized modals (5 шт.) | done | 4 |
| [T-4-030](phase-4-spa/T-4-030-sse-optimistic.md) | SSE + Optimistic mutations | done | 3.5 |
| [T-4-032](phase-4-spa/T-4-032-states-shortcuts-tests.md) | States + shortcuts + tests | done | 5 |

**Итого фаза 4:** ~40 часов. Параллелится: 4-001..4-004 (база) → 4-010..4-016 (страницы) + 4-020..4-021 (модалки) → 4-030 (SSE) → 4-032 (полировка).

### Фаза 5. Integrations + cleanup

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-5-001](phase-5-integrations/T-5-001-notification-architecture.md) | apps/notifications/ infra | done | 3 |
| [T-5-002](phase-5-integrations/T-5-002-channels.md) | Telegram + MAX + Email channels | done | 4.5 |
| [T-5-006](phase-5-integrations/T-5-006-triggers.md) | 6 правил уведомлений | done | 2 |
| [T-5-010](phase-5-integrations/T-5-010-tg-proxy-worker.md) | TG SOCKS5 + replace sender_tg_message | done | 2.5 |
| [T-5-020](phase-5-integrations/T-5-020-max-bot.md) | MAX bot (setup + integration + webhook + binding) | done | 5 |
| [T-5-030](phase-5-integrations/T-5-030-gmail-alarms.md) | VNNOX gmail-парсер + AlarmEvent | done | 6 |
| [T-5-040](phase-5-integrations/T-5-040-worker-rewrite.md) | daily_checker rewrite + ManageControl + structlog | done | 4 |
| [T-5-050](phase-5-integrations/T-5-050-legacy-cleanup.md) | Legacy cleanup (templates/views/shims/MsServiceControl) | ready | 4.5 |
| [T-5-fix-001](phase-5-integrations/T-5-fix-001-migration-graph-cleanup.md) | **HOTFIX (P0):** legacy models → shim/proxy + state-only DeleteModel + 19 alignment миграций | done | 4-5 |
| [T-5-fix-002](phase-5-integrations/T-5-fix-002-dev-test-deps.md) | **HOTFIX (P1):** dev/test extras в .venv + UTF-8 requirements.txt | done | 1 |
| [T-5-fix-002-followup](phase-5-integrations/T-5-fix-002-followup-ruff.md) | Follow-up: ruff/black/mypy baseline cleanup (291/96/16) | blocked | 2-3 |
| [T-5-fix-003](phase-5-integrations/T-5-fix-003-live-db-verification.md) | **HOTFIX (P0):** live-DB verify + 4 forward-only data-migrations (users/displays/panels FK) | done | 2-3 |

**Итого фаза 5:** ~31 час + ~9 часов hotfix (T-5-fix-001/002/003). T-5-050 и T-5-fix-002-followup — после деплоя + 2 недели стабильной работы.

### Фаза 6. Production cutover + post-cutover

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-6-001](phase-5-integrations/T-6-001-production-cutover-runbook.md) | **P0:** prod cutover runbook + удаление `prod_dump_compat.sql` + переписать `restore_to_dev.sh` | review | 3-4 |
| [T-6-002](phase-5-integrations/T-6-002-backup-strategy.md) | **P1:** pgBackRest или pg_dump cron + off-host копия + тест восстановления | review | 2-3 |
| [T-6-003](phase-5-integrations/T-6-003-observability.md) | **P1:** django-prometheus + Grafana + uptime monitor + 4 alerts | review | 3-4 |
| [T-6-004](phase-5-integrations/T-6-004-gitignore-and-dump-leakage.md) | **P0 security:** .gitignore + filter-repo + force-push (history переписана) | done | 0.5-2 |
| [T-6-005](phase-5-integrations/T-6-005-rotate-leaked-secrets.md) | **P0 security:** ротация утёкших секретов (Google OAuth + `SECRET_KEY` + БД + TG/MAX токены) | review | 1-2 |
| [T-6-006](phase-5-integrations/T-6-006-encoding-hygiene.md) | **P1 hygiene:** UTF-8 без BOM + pre-commit hook + восстановление 54 markdown + T-6-001 cp1251-mojibake | done | 1-2 |

**Итого фаза 6:** ~11-17 часов перед prod-релизом + наблюдение.

### Фаза 7. Продуктовые требования + редизайн (раунд 2026-05-13)

Полное оглавление — [`phase-7-product/README.md`](phase-7-product/README.md). Здесь только top-level карточки с детальной разверткой.

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-7-001](phase-7-product/T-7-001-rebranding-supersymmetria.md) | Rebranding: имя «Суперсимметрия» + новый логотип в UI | done | 1.5-2 |
| [T-7-002](phase-7-product/T-7-002-design-tokens-v2-dark-mode.md) | Design tokens v2 + dark mode + theme toggle | done | 3-4 |
| [T-7-003](phase-7-product/T-7-003-multi-role-and-fine-grained-permissions.md) | Multi-role + fine-grained permissions (A5, Z5) | review (Wave 1+2) | 6-8 |
| T-7-004 | Departure ↔ Application FK → ManyToMany (DE5) | ready | 4-5 |
| [T-7-005](phase-7-product/T-7-005-storage-extensions-and-low-stock.md) | Storage: PowerBlocks/Connectors + `low_stock_threshold=3` | done | 2-3 + 1.5 |
| [T-7-007](phase-7-product/T-7-007-panel-removal-conditional-reason.md) | Снятие панели: 2 сценария (DV-S6) | done | 1.5-2 |
| T-7-008 | ConfirmDialog для опасных действий (Md5) | review | 1 |
| T-7-012 | Звук при новой заявке + opt-in в Profile (A8) | review | 1-2 |
| T-7-035 | Создание панели (Z7) — backend + UI | review | 1.5 |
| T-7-036 | Удаление панели (Z8, admin-only) — backend + UI с ConfirmDialog | review | 1 |
| [T-7-010](phase-7-product/T-7-010-global-search.md) | Глобальный поиск `/` по 6 категориям (X1) | done | 4-6 |
| [T-7-013](phase-7-product/T-7-013-print-application-card.md) | Print-friendly карточка заявки (X4) | done | 2-3 |
| T-7-014 | История юзера в Profile (P2) | review | 1.5 |
| T-7-030 / T-7-031 | Sort экранов + city filter в DepartmentPage | done | 1 + 1 |
| [T-7-100](phase-7-product/T-7-100-design-round-4-integration.md) | **Design Round 4 integration (10 PR'ов)** — полировка UI под брендгайд | review | 25-30 |
| T-7-followup-applications-display-city / display-aggregated-condition / bell-deeplink-resolve | Backend следствия Round 4 | review | ~2 |
| T-7-004..T-7-036 | См. полный реестр в `phase-7-product/README.md` | mixed | ~30-40 |

**Итого фаза 7:** ~50-65 часов продуктовой разработки + дизайн-итерации.

---

### Фаза 8. Owner feedback + prod stabilization

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-8-107](phase-8-owner-feedback/T-8-107-prod-ui-stability.md) | **P0:** Activity request-loop/429, mobile camera, SSE native runtime | review | 2-3 |
| [T-8-108](phase-8-owner-feedback/T-8-108-prod-media-reconciliation.md) | **P1:** Сверка отсутствующих prod media-файлов | done | 1-2 + owner data |
| [T-8-111](phase-8-owner-feedback/T-8-111-owner-prod-ux-and-data-reset.md) | **P0/P1:** owner prod UX, media reconciliation, history reset | done | 4-6 |

---

## Total

- Фаза 1 (foundation): ~17ч → **done**
- Фаза 2 (models): ~27ч → **done** (3 задачи в паузах)
- Фаза 3 (API): ~32ч → **done** (20 + 2 hotfix)
- Фаза 4 (SPA): ~40ч → **done**
- Фаза 5 (integrations): ~31ч + ~9ч hotfix → **done** (T-5-050 blocked)
- Фаза 6 (production): ~11-17ч → **в работе**, T-6-004/006 done
- Фаза 7 (product/redesign): ~50-65ч → **starts after prod stable** (часть rebranding можно параллельно)

**Полный объём проекта:** ~150 часов рефакторинга + ~15 часов production + ~55 часов продуктовой Phase 7.

---

## Нумерация

- **T-1-XXX** — фаза 1
- **T-2-XXX** — фаза 2
- ...

Внутри фазы номера **идут подряд**. Если задача была отменена — её номер НЕ используется повторно (чтобы ссылки в истории оставались валидными).

---

## Что делать, если нашёл баг / идею, не входящую в задачи

1. Проверь `../01-current-state/audit-report.md` — возможно, уже учтено
2. Если новое — заведи задачу-кандидата в отдельный файл `XXX-candidate-<short>.md` в этой же папке
3. Не начинай работу над ним самостоятельно. Архитектор оценит и присвоит номер.

Задачи без номера в работу не берутся.
