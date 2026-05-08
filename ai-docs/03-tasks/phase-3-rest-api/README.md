# Фаза 3 — REST API на DRF

> **Цель фазы:** превратить Django-проект в API-first. Убрать всю бизнес-логику из views, добавить JSON-эндпоинты по `ai-docs/07-frontend/api-contract.md`, OpenAPI-схему, JWT-аутентификацию.
>
> Параллельно legacy-templates продолжают работать (компаты, не трогаем). После Фазы 4 (SPA готов) — legacy убираем.

**Длительность:** ~25 часов работы кодера + ревью.
**Кодер:** GPT-кодер (backend) или Claude Sonnet — по выбору владельца.
**Архитектор:** Claude Opus.

---

## Список задач (порядок выполнения важен!)

### 3.0. Подготовка (всё блокирует)

| ID | Задача | Оценка | Блокирует |
|----|--------|--------|-----------|
| T-3-001 | DRF setup + JWT auth | 2ч | всё ниже |
| T-3-002 | OpenAPI schema (drf-spectacular) | 1ч | T-3-014 |
| T-3-003 | Permissions + допуск по городам | 2ч | все CRUD |
| T-3-004 | Pagination, error format, throttling | 1.5ч | все CRUD |
| T-3-005 | Перенести admin'ки в `apps/` | 1.5ч | независимо |

### 3.1. CRUD справочников (можно параллельно после 3.0)

| ID | Задача | Оценка | Зависимости |
|----|--------|--------|-------------|
| T-3-010 | `/api/v1/me`, login, refresh, logout | 2ч | T-3-001..3-004 |
| T-3-011 | Cities, Colors, Conditions, Smiles, Departments — CRUD | 1.5ч | T-3-001..3-004 |
| T-3-012 | ApplicationStatus + DepartureStatus CRUD | 0.5ч | T-3-011 |

### 3.2. Основные ресурсы

| ID | Задача | Оценка | Зависимости |
|----|--------|--------|-------------|
| T-3-020 | Displays (list/detail/photos) | 2.5ч | T-3-011 |
| T-3-021 | Panels (list/detail/move/replace) | 3ч | T-3-020 + T-2-041 |
| T-3-022 | Cells endpoint + сетка | 1ч | T-3-020 |
| T-3-023 | ZIP storage (Wires/Hubs/Lamels) | 1ч | T-3-020 |

### 3.3. Workflow

| ID | Задача | Оценка | Зависимости |
|----|--------|--------|-------------|
| T-3-030 | Applications list + detail + filters | 2.5ч | T-3-021 |
| T-3-031 | Application transitions (FSM endpoint) | 2ч | T-3-030 + T-2-040 |
| T-3-032 | ApplicationEvents read-only | 0.5ч | T-3-030 |
| T-3-033 | Departures + transitions | 2ч | T-3-021 |

### 3.4. Лог и реалтайм

| ID | Задача | Оценка | Зависимости |
|----|--------|--------|-------------|
| T-3-040 | ActivityLog read endpoint + фильтры | 1ч | T-2-022 |
| T-3-041 | SSE stream для real-time | 2ч | T-3-040 |

### 3.5. Полировка

| ID | Задача | Оценка | Зависимости |
|----|--------|--------|-------------|
| T-3-050 | Health-check endpoints | 0.5ч | независимо |
| T-3-051 | API tests на критичных путях | 2ч | все |

---

## Граф зависимостей

```
T-3-001 (DRF + JWT) ──┬──► T-3-003 (permissions) ──┬──► T-3-010 (auth views)
                      │                            │
                      ├──► T-3-004 (pagination)    │
                      │                            │
                      └──► T-3-002 (OpenAPI)       │
                                                   │
T-3-005 (admin) ─── independent                    │
                                                   ▼
T-3-011 (refs) ──► T-3-012 (statuses) ──► T-3-020 (Displays) ──┬──► T-3-021 (Panels)
                                                                │            │
                                                                ├──► T-3-022 (Cells)
                                                                │            │
                                                                └──► T-3-023 (ZIP)
                                                                             │
T-3-030 (Apps) ──► T-3-031 (transitions) ──► T-3-032 (events)                │
              \                                                              │
               └──► T-3-033 (departures)                                     │
                                                                             ▼
T-3-040 (log) ──► T-3-041 (SSE) ──────────────────────────► T-3-051 (e2e tests)
```

---

## Что должно получиться по итогам Фазы 3

- **`/api/v1/...`** работает на всех ключевых ресурсах (`api-contract.md` — единственный источник правды)
- **JWT-аутентификация:** access (15 мин), refresh в httpOnly cookie (7 дней)
- **Permissions:** строгие, по департаменту + по городу
- **OpenAPI schema:** автогенерируется, доступна `/api/schema/`, Swagger UI на `/api/docs/`
- **TS-типы для фронта:** генерируются из OpenAPI командой `pnpm generate:api-types`
- **SSE:** работает, фронт подписывается на `/api/v1/events/stream`
- **Legacy templates:** **продолжают работать** через старые views (не трогаем — Фаза 4 их уберёт)
- **Coverage:** ≥ 70% на новом коде, на критичных путях (transitions, auth) — 90%+

---

## Что **не** делается в Фазе 3

- ❌ React SPA (это Фаза 4)
- ❌ Удаление legacy templates (Фаза 4 после готовности SPA)
- ❌ Notification redesign (Фаза 5)
- ❌ MAX-бот, gmail-парсер (Фаза 5)
- ❌ Удаление 28 полей Application (T-2-021 — отдельная очередь)
- ❌ Удаление history-таблиц (T-2-024)

---

## API-контракт = источник правды

`ai-docs/07-frontend/api-contract.md` — это **то, что обязан реализовать кодер**. Любое расхождение между кодом и контрактом = баг.

При необходимости изменить контракт — **сначала PR в `api-contract.md` с обоснованием**, потом код. Не наоборот.

---

## Тестирование

Каждая задача содержит свои критерии приёмки. Общие правила:

- **Минимум 3 теста на endpoint:** happy, 403, 422
- **Schema-тест:** `test_openapi_schema_is_valid`
- **Contract-тест:** для critical (login, transition) — snapshot структуры response

---

## После закрытия Фазы 3

- Архитектор делает review-pass + smoke-test API через curl
- Деплоится на staging
- Claude Design / frontend-кодер начинает Фазу 4 (SPA) — у него уже готовый OpenAPI и эталоны экранов
