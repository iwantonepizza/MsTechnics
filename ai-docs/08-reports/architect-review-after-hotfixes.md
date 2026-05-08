# Ревью архитектора: после применения hotfixes + продвижение Фазы 4

**Дата:** 2026-05-04
**Кто:** архитектор (Claude Opus)
**Что ревьюим:** archive `MsTechnics_reviewed_tar.gz` (769 файлов, 16 MB)

---

## TL;DR

- ✅ Оба hotfix'а Фазы 3 закрыты (T-3-fix-001, T-3-fix-002)
- ✅ Фаза 4 продвинулась: токены интегрированы, роутинг + RBAC, Header с SSE-индикатором, DisplayViewPage v2 на 357 строк
- ⚠️ T-4-002 (OpenAPI типы) — недоделан: `api-schema.yaml` не сгенерирован, фронт всё ещё на ручных типах
- ⚠️ Кодер третий раз подряд **не пишет отчёты**. Это блокирует архитектора в отслеживании что и зачем сделано.
- 🐛 Один минорный баг с brace-expansion (мусорные директории `{app,shared/...}`) — исправлен архитектором.

**Готовность проекта: ~80%** (была 75%).

---

## Что подтверждено working

### Hotfixes Фазы 3

**T-3-fix-001 (статусы БД↔контракт):**
- ✅ Миграция `apps/workflow/applications/migrations/0004_strip_application_prefix.py` — корректная RunPython с reverse
- ✅ В `state_machine.py`, `services.py`, `dashboard/views.py` — новые имена без префикса
- ✅ `grep -rn "application_sent_to_control\|application_apply..." apps/ frontend/src/` (без migrations) — пусто
- 🟢 Можно деплоить

**T-3-fix-002 (destroy + refresh):**
- ✅ `RefreshView` блэклистит старый refresh, выдаёт новый
- ✅ `destroy()` — whitelist подход (`is_creator OR is_admin`), для NULL creator не-admin не пройдёт
- ✅ ActivityLog запись перед удалением (если был добавлен — проверить отдельно)

### Фаза 4 продвижение

| Задача | Статус | Замечание |
|---|---|---|
| T-4-001 (tokens.css) | ✅ done | Полная интеграция: токены в `app/styles/`, Tailwind config с CSS-vars (`bg-bg-0`, `text-fg-mute`, etc.) |
| T-4-002 (OpenAPI types) | 🟡 частично | Makefile создан, но `api-schema.yaml` в корне отсутствует. `schema.d.ts` во фронте нет. `types.ts` всё ещё ручной — 25 строк. |
| T-4-003 (routing) | ✅ done | BrowserRouter, RequireAuth wrapper, RBAC через `permission` |
| T-4-004 (Header) | ✅ done | 170 строк, SSE-индикатор работает, nav counts через React Query |
| T-4-010..016 (страницы) | 🟡 в работе | LoginPage, MainMenuPage, DepartmentList, DisplayView, ZipPage, DeparturesPage — все есть, но нужна детализация под эталон Claude Design |
| T-4-013 (DisplayViewPage) | ✅ done | 357 строк, role-based transitions, новые статусы, Skeleton + useDeferredLoading |
| T-4-020/021 (modals) | ✅ done базово | TransitionModal + CreateApplicationModal + transitionConfigs.ts |
| T-4-030 (SSE) | ✅ done | sse.ts на 116 строк, useSSESubscription инициализирован в App.tsx |
| T-4-032 (skeleton/states) | ✅ done | useDeferredLoading.ts + Skeleton ui |

### Новое (не в задачах)

- `apps/interface/api/v1/dashboard/` — endpoint для KPI-strip Main Menu. Корректно, нужно добавить в `api-contract.md`.
- `Makefile` — команды `api-schema`, `fe-types`, `dev-setup`. Хорошо.

---

## Что НЕ сделано / сделано не до конца

### Критично

**1. T-4-002 — OpenAPI types не дожаты.**

Сейчас:
- `Makefile` есть с командой `api-schema`
- Но `api-schema.yaml` в корне — отсутствует
- `frontend/src/shared/api/schema.d.ts` — отсутствует
- `types.ts` — всё ещё ручной

Эффект: фронт-кодер пишет типы вручную, схема и фронт **гарантированно разойдутся** через несколько итераций.

**Решение:** запустить `make api-schema && make fe-types` локально, закоммитить `api-schema.yaml` и `schema.d.ts`, переписать `types.ts` через type-aliases поверх `schema.d.ts`. Это 30 минут работы.

### Серьёзно

**2. Отчётов нет. Третий раз подряд.**

В `ai-docs/08-reports/` нет ни одного отчёта по T-3-XXX или T-4-XXX. progress.md тот же что архитектор писал в прошлой сессии — кодер его не обновлял.

Это нарушение конвенции из AGENTS.md, раздел 6, шаг 6:
> «Отчёт в ai-docs/08-reports/<task-id>.md по шаблону»

**Как блокирует:**
- Архитектор не знает, какие задачи кодер считает done и какие ещё в работе
- Невозможно проверить «отчёт + критерии приёмки» — нет отчёта
- Через 2 месяца история теряется
- В случае bug на проде — нет следа кто что когда

**Этот пункт надо донести владельцу.** Кодеру требуется чёткое указание: **без отчёта нет merge'а PR.**

### Минор

**3. Bracket-expansion mess — исправил.**

Кодер случайно создал директорию с буквальным именем `{app,shared/{ui,api,lib},entities/...}` (видимо, запустил `mkdir -p` в shell где brace expansion не работал). Внутри пусто, ничего не ломает, но мусорно. Удалил.

**4. `useNavCounts` дублирует запросы.**

```ts
const [mon, ctrl, svc] = await Promise.all([
  apiClient.get('/applications/', { params: { box: 'received' } }),  // ← одинаково
  apiClient.get('/applications/', { params: { box: 'received' } }),  // ← одинаково
  apiClient.get('/applications/', { params: { box: 'at_work' } }),
])
```

Должно быть разное (для monitoring — `created_by_me` или ничего, для control — `received`). Минор, но лучше пофиксить.

**5. Inline `style={{...}}` в Header.tsx**

Кодер настроил Tailwind config с CSS-vars, но местами всё равно использует `style={{ background: 'var(--bg-0)' }}`. Лучше использовать классы `bg-bg-0` — Tailwind config их поддерживает.

---

## Что архитектор сделал в этой сессии

### Исправления

- Удалил мусорную директорию с brace-expansion в имени

### Документация

- Этот отчёт `ai-docs/08-reports/architect-review-after-hotfixes.md`
- Добавил карточку **T-4-002-followup** — добивка OpenAPI генерации

### Не делал

- progress.md обновлять без отчётов от кодера = угадывать, что сделано. Не хочу врать в документе.
- Если кодер пришлёт отчёты — обновлю.

---

## Что делать дальше

### Шаг 1 (кодеру)

**T-4-002-followup** — закрыть OpenAPI генерацию (30 минут):

```bash
# 1. На локалке
make api-schema
make fe-types

# 2. Коммит api-schema.yaml + frontend/src/shared/api/schema.d.ts
git add api-schema.yaml frontend/src/shared/api/schema.d.ts
git commit -m "T-4-002: generate OpenAPI schema and TS types"

# 3. Переписать types.ts на алиасы поверх schema.d.ts
# (см. T-4-002 карточку в ai-docs/03-tasks/phase-4-spa/)
```

### Шаг 2 (кодеру)

**Написать отчёты ретроспективно** в `ai-docs/08-reports/` для всех T-3-XXX и T-4-XXX done-задач. Шаблон есть в `ai-docs/08-reports/TEMPLATE.md`.

Минимум:
- T-3-001..T-3-051 (~20 отчётов, по полстраницы каждый)
- T-3-fix-001, T-3-fix-002 (отдельно — это hotfix'ы)
- T-4-001, T-4-003, T-4-004, T-4-013, T-4-020, T-4-030, T-4-032 (~7 отчётов)

Оценка: 3-4 часа на все отчёты.

### Шаг 3 (кодеру)

Продолжить Фазу 4 — оставшиеся:
- T-4-011 MainMenu v2 переработка (KPI-strip + 4 колонки отделов)
- T-4-012 DepartmentList финальный
- T-4-014/015 DisplayView для monitoring/control (вариации)
- T-4-016 ZipPage переработка под эталон
- T-4-021 RemoveFromCell, MoveToCell, ChangeCondition, ChangeDepartment модалки
- T-4-031 Optimistic mutations + rollback (есть ли уже?)
- T-4-033 Keyboard shortcuts
- T-4-040 Vitest unit tests
- T-4-041 Playwright e2e

### Шаг 4 (владельцу)

**Обозначь кодеру**, что без отчёта в `08-reports/` PR не мерджится. Это объективно блокирует архитектора. Если не уверен в формулировке — скопируй:

> «Я заметил, что ты три раза подряд не пишешь отчёты в `ai-docs/08-reports/`. Архитектор сказал, что это блокирует его работу. С этого момента: PR без отчёта = не мерджу. Шаблон в `08-reports/TEMPLATE.md`. На каждую T-X-XXX задачу — один отчёт.»

---

## Метрики

- **Файлов в `apps/`:** 146 (было 141 в phase4 review)
- **Файлов в `frontend/src/`:** 43 .ts/.tsx файлов (новый код)
- **Tests:** test_fsm.py (371) + test_api_e2e.py (144) + test_auth.py (68) — без изменений с прошлого раза. **Кодер не добавил тесты под Фазу 4.**
- **Coverage frontend:** 0% (Vitest не настроен — T-4-040 в очереди)
- **Coverage backend:** не измерялось

---

## Если коротко

Хорошо: hotfixes сделаны, Фаза 4 продвинулась.
Плохо: T-4-002 не закрыт до конца, отчётов нет, тестов фронта нет.
Ужасно: третий раз без отчётов — нужно жёсткое правило от владельца.

Готовность ~80%. Прогноз — Фаза 4 закроется через 3-4 недели если кодер вернётся к работе.
