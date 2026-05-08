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
| [T-1-008](phase-1-foundation/T-1-008-prod-logging.md)     | Prod logging: JSON stdout + Sentry          | review | 1.5   |
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
| [T-2-021](phase-2-models/T-2-021-drop-denormalized-fields.md)| Удалить 28 старых полей (после паузы)          | blocked | 1     |
| [T-2-022](phase-2-models/T-2-022-activity-log-model.md)      | Создать ActivityLog с GenericForeignKey        | done    | 2     |
| [T-2-023](phase-2-models/T-2-023-backfill-activity-log.md)   | Миграция данных: 5 History → ActivityLog       | blocked | 3     |
| [T-2-024](phase-2-models/T-2-024-drop-legacy-history.md)     | Удалить 5 старых History-таблиц                | blocked | 1     |
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
| [T-3-fix-001](phase-3-rest-api/T-3-fix-001-status-names-sync.md) | **HOTFIX:** sync статусов БД↔контракт | review | 2 |
| [T-3-fix-002](phase-3-rest-api/T-3-fix-002-destroy-and-refresh.md) | **HOTFIX:** destroy() + refresh rotation | review | 1 |

**Итого фаза 3:** ~32 часа (29 done + 3 hotfix). Hotfix-ы критичны до старта Фазы 4.

### Фаза 4. React SPA

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-4-001](phase-4-spa/T-4-001-design-tokens.md) | tokens.css + Tailwind config | review | 2 |
| [T-4-002](phase-4-spa/T-4-002-openapi-types.md) | Generate TS types from schema | review | 1.5 |
| [T-4-003](phase-4-spa/T-4-003-routing.md) | React Router + ProtectedRoute | review | 2 |
| [T-4-004](phase-4-spa/T-4-004-app-layout.md) | AppLayout + Header + crumbs | review | 2 |
| [T-4-010](phase-4-spa/T-4-010-login-page.md) | LoginPage | review | 1.5 |
| [T-4-011](phase-4-spa/T-4-011-main-menu-page.md) | MainMenu v2 | review | 3 |
| [T-4-012](phase-4-spa/T-4-012-department-list.md) | DepartmentList | review | 3 |
| [T-4-013](phase-4-spa/T-4-013-display-view-pages.md) | DisplayView 3 ролей | review | 7 |
| [T-4-016](phase-4-spa/T-4-016-zip-page.md) | ZipPage | review | 3 |
| [T-4-020](phase-4-spa/T-4-020-transition-modals.md) | TransitionModal universal | review | 3 |
| [T-4-021](phase-4-spa/T-4-021-specialized-modals.md) | Specialized modals (5 шт.) | review | 4 |
| [T-4-030](phase-4-spa/T-4-030-sse-optimistic.md) | SSE + Optimistic mutations | review | 3.5 |
| [T-4-032](phase-4-spa/T-4-032-states-shortcuts-tests.md) | States + shortcuts + tests | review | 5 |

**Итого фаза 4:** ~40 часов. Параллелится: 4-001..4-004 (база) → 4-010..4-016 (страницы) + 4-020..4-021 (модалки) → 4-030 (SSE) → 4-032 (полировка).

### Фаза 5. Integrations + cleanup

| ID | Название | Статус | Часов |
|----|----------|--------|-------|
| [T-5-001](phase-5-integrations/T-5-001-notification-architecture.md) | apps/notifications/ infra | review | 3 |
| [T-5-002](phase-5-integrations/T-5-002-channels.md) | Telegram + MAX + Email channels | review | 4.5 |
| [T-5-006](phase-5-integrations/T-5-006-triggers.md) | 6 правил уведомлений | review | 2 |
| [T-5-010](phase-5-integrations/T-5-010-tg-proxy-worker.md) | TG SOCKS5 + replace sender_tg_message | review | 2.5 |
| [T-5-020](phase-5-integrations/T-5-020-max-bot.md) | MAX bot (setup + integration + webhook + binding) | review | 5 |
| [T-5-030](phase-5-integrations/T-5-030-gmail-alarms.md) | VNNOX gmail-парсер + AlarmEvent | review | 6 |
| [T-5-040](phase-5-integrations/T-5-040-worker-rewrite.md) | daily_checker rewrite + ManageControl + structlog | review | 4 |
| [T-5-050](phase-5-integrations/T-5-050-legacy-cleanup.md) | Legacy cleanup (templates/views/shims/MsServiceControl) | blocked | 4.5 |
| [T-5-fix-001](phase-5-integrations/T-5-fix-001-migration-graph-cleanup.md) | **HOTFIX (P0):** legacy models → shim + state-only DeleteModel | review | 4-5 |
| [T-5-fix-002](phase-5-integrations/T-5-fix-002-dev-test-deps.md) | **HOTFIX (P1):** dev/test extras в .venv + UTF-8 requirements.txt | review | 1 |
| [T-5-fix-002-followup](phase-5-integrations/T-5-fix-002-followup-ruff.md) | Follow-up: ruff/black/mypy baseline cleanup (291/96/16) | blocked | 2-3 |
| [T-5-fix-003](phase-5-integrations/T-5-fix-003-live-db-verification.md) | **HOTFIX (P0):** live-DB verify 19 alignment-миграций + полный pytest | ready | 2-3 |

**Итого фаза 5:** ~31 час + 7-9 часов hotfix перед staging cutover (T-5-fix-001/002/003). T-5-050 и T-5-fix-002-followup — после деплоя SPA + 2 недели стабильной работы.

---

## Total

- Фаза 1 (foundation): ~17ч → **done**
- Фаза 2 (models): ~27ч → **done** (3 задачи в паузах)
- Фаза 3 (API): ~32ч → **30ч done, 3ч hotfix**
- Фаза 4 (SPA): ~40ч → **review / staging polish**
- Фаза 5 (integrations): ~31ч → **review, T-5-050 blocked**

**Полный объём проекта:** ~150 часов кодинга

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
