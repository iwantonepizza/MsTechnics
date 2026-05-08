# Ревью архитектора: Фазы 3 + старт Фазы 4

**Дата:** 2026-04-29
**Кто:** архитектор (Claude Opus)
**Что ревьюим:** archive `MsTechnics_phase4_tar.gz` (1338 файлов, 30 MB)

---

## Что заявлено кодером

В `progress.md`: **92% готовности**, Фаза 3 закрыта на 100% (20 задач + T-2-fix-001), Фаза 4 «100% — все экраны реализованы».

---

## Что реально (verified)

### Фаза 1 — закрыта (95%)

10 отчётов (T-1-001..011 без T-1-005/008). Кодер подтянул хвосты Фазы 1, что не было сделано в первом раунде. ✅

### Фаза 2 — закрыта согласно плану (95%)

T-2-021/023/024 ждут пауз — это правильно. T-2-fix-001 (Contact) — закрыт ✅.

### Фаза 3 — реализована, но БЕЗ ОТЧЁТОВ

Все 11 модулей в `apps/interface/api/v1/` существуют:
- auth, me, refs (cities/colors/conditions/smiles/departments/statuses), displays, panels, cells, storage, applications (CRUD + transition + events), departures, activity, events (SSE), health.

**Качество кода (выборка):**

- **SSE стрим (`events/views.py`)** — отлично. Redis Streams xread, heartbeat 15s, query-token для EventSource, no-buffering header, last-event-id resume.
- **Applications transition view** — корректно использует `application_service.transition()` через FSM, `CanTransitionApplication` permission, `TransitionRateThrottle`.
- **Settings** — DRF + JWT + CORS — на месте (15 мин access, 7 дней refresh, ROTATE_REFRESH_TOKENS, BLACKLIST_AFTER_ROTATION).
- **shared/** — `exceptions.py` (119), `permissions.py` (109), `pagination.py` (44), `throttling.py` (22) — содержательно.
- **Tests** — `tests/test_api_e2e.py` (144 строки) + `test_fsm.py` (371) + `test_auth.py` (68). Покрытие критичных путей реальное.

**Проблема №1 — отчёты Фазы 3 не написаны.** Конвенция «каждая задача = отчёт в `08-reports/`» нарушена для всех 20 задач.

### Фаза 4 — каркас и 6 страниц, но не «100% реализована»

В `frontend/`:
- `package.json` — стек по плану (React 18 + Vite + TS + TanStack Query + Zustand + Tailwind + Radix + RHF + zod + sonner + lucide + openapi-typescript).
- 6 страниц: login, menu, department, display-view, zip, departures.
- Архитектура FSD: `app/`, `pages/`, `widgets/` (3), `features/` (auth, applications), `entities/` (application, panel, display), `shared/` (api, lib, ui).
- DisplayViewPage — 300 строк, реальная: useParams, RBAC через `department` prop, role-based transitions, modal stack.

**Проблемы Фазы 4:**

- **Не интегрировано с дизайном**: `frontend-design/` (эталоны Claude Design v2 с tokens.css OKLCH, Inter+JetBrains Mono, плотность Linear) не использован. Файлы существуют, но фронт-кодер сделал свой Tailwind без них.
- **Типы API руками** (`shared/api/types.ts`, 25 строк), не из OpenAPI через `pnpm generate:api-types`. Гарантированно отстанут.
- **Нет роутинга в App.tsx** проверить (надо ли).
- **Нет Storybook** (мелкое замечание).

---

## КРИТИЧНЫЕ БАГИ (нашёл и исправил)

### B1. Синтаксические ошибки в двух services (исправлено)

**Файлы:**
- `apps/workflow/applications/services.py:209` — метод `create_from_ids` оказался **снаружи класса** (после `application_service = ApplicationService()`).
- `apps/directory/panels/services.py:200` — три метода (`change_condition`, `move_to_cell`, `remove_from_cell`) оказались **снаружи класса** `PanelMover`.

Без фикса проект **не запускался**. Исправлено архитектором в этой ревью-сессии — перенёс методы в класс до инстанцирования singleton.

### B2. Рассинхрон имён статусов: БД vs api-contract.md

В коде везде имена с префиксом `application_*`:
- `application_sent_to_control`
- `application_apply_in_control`
- `application_sent_to_service`
- `application_work_in_service`
- `application_unable`

В `api-contract.md`:
- `sent_to_control`, `apply_in_control`, `sent_to_service`, `work_in_service`, `unable`

**Эффект:** фронтенд, написанный по контракту, не работает с этим API. Сейчас фронт-кодер поскрёб БД и подстроил типы под префиксы — но это нарушает контракт и связывает frontend с легаси-именами навсегда.

**Решение** — задача **T-3-fix-001** (см. ниже).

### B3. `destroy()` уязвимость

В `applications/views.py:97-99`:
```python
creator = getattr(app, "user_monitoring", None)
if creator and creator != request.user.username and request.user.permission not in ("admin", "all"):
    raise DomainError(...)
```

Если `creator is None` (старая заявка без поля), ветка пропускается → **любой авторизованный** может удалить заявку. Уязвимость низкого риска (старых заявок мало в окне 5 мин), но ведёт к security-баг-репорту.

**Решение** — задача **T-3-fix-002** (см. ниже).

---

## Главный итог

- Кодер сделал огромный объём — **в основном правильно**.
- 2 синтаксические ошибки на критичных сервисах — исправил архитектор.
- Расхождение имён БД↔контракт нужно фиксить в Фазе 4.
- Отчёты Фазы 3 — kodeрское обязательство, написать постфактум.
- **Готовность реальная: ~75%**, не 92%. Фаза 4 далеко не закрыта (есть скелет + 6 страниц без интеграции дизайна).

---

## Что дальше

Создаются:
- **T-3-fix-001** — синхронизация имён статусов с api-contract
- **T-3-fix-002** — фикс уязвимости destroy()
- **Phase-4 SPA** — задачи: интеграция дизайна, OpenAPI типы, роутинг, оставшиеся экраны
- **Phase-5 Integrations** — TG-прокси, MAX-бот, gmail-парсер, notifications-redesign
