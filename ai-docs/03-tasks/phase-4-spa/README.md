# Фаза 4 — React SPA

> **Что есть на старте:** базовый каркас фронта (FSD-структура, 6 страниц, виджеты, Tailwind).
> **Что нужно сделать:** интегрировать дизайн (Claude Design v2 эталоны), генерить TS типы из OpenAPI, доделать недостающие экраны/модалки, тесты, e2e Playwright.

**Длительность:** ~30 часов работы кодера + ревью.
**Кодер:** фронтенд-кодер (Claude Sonnet или другой агент)
**Архитектор:** Claude Opus
**Дизайнер:** Claude Design (эталоны уже готовы)

---

## Что есть из коробки

```
frontend/
├── package.json         (стек по плану)
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── app/App.tsx
    ├── main.tsx
    ├── pages/
    │   ├── login/        ✅ есть
    │   ├── menu/         ✅ есть
    │   ├── department/   ✅ есть
    │   ├── display-view/ ✅ есть (RBAC по department-prop)
    │   ├── zip/          ✅ есть
    │   └── departures/   ✅ есть
    ├── widgets/
    │   ├── display-grid/    ✅ есть
    │   ├── applications-panel/ ✅ есть
    │   └── navigation/AppLayout ✅ есть
    ├── features/
    │   ├── auth/         ✅ hooks + zustand store
    │   └── applications/ ✅ CreateApplicationModal + TransitionModal
    ├── entities/
    │   ├── application/  ✅ ApplicationCard + EventTimeline + hooks
    │   ├── panel/        ✅ CellSlot + hooks
    │   └── display/      ✅ hooks
    └── shared/
        ├── api/client.ts    ✅
        ├── api/types.ts     ⚠ ВРУЧНУЮ — задача T-4-002
        ├── lib/queryClient  ✅
        ├── lib/sse.ts       ✅ (соединение есть, реакция на события — задача T-4-008)
        └── ui/              ✅ Button/Modal/Tabs/Spinner/Badge/EmptyState
```

---

## Список задач

### 4.0. Подготовка

| ID | Задача | Оценка |
|----|--------|--------|
| T-4-001 | Интеграция дизайн-токенов из `frontend-design/tokens.css` (OKLCH + плотности) | 2ч |
| T-4-002 | Генерация TS-типов из OpenAPI (`pnpm generate:api-types`) + замена `types.ts` | 1.5ч |
| T-4-003 | Роутинг: React Router v6 + protected routes + RBAC | 2ч |
| T-4-004 | Layout с Header (адаптация `frontend-design/header.jsx`) + crumbs + SSE-индикатор | 2ч |

### 4.1. Страницы — переработка под дизайн

| ID | Задача | Оценка |
|----|--------|--------|
| T-4-010 | LoginPage — финальный вид | 1.5ч |
| T-4-011 | MainMenuPage — переработать под Main Menu v2 (4 KPI, 4 колонки отделов) | 3ч |
| T-4-012 | DepartmentListPage (Department List от Claude Design) | 3ч |
| T-4-013 | DisplayView / Сервис — финальный вид по эталону v2 | 3ч |
| T-4-014 | DisplayView / Мониторинг — вариация (T-3-fix-001 обязательна) | 2ч |
| T-4-015 | DisplayView / Контроль — вариация | 2ч |
| T-4-016 | ZipPage — Storage + расходники + history rail | 3ч |

### 4.2. Модалки и потоки

| ID | Задача | Оценка |
|----|--------|--------|
| T-4-020 | TransitionModal — все 12 типов (с zod-валидацией, optimistic + rollback) | 3ч |
| T-4-021 | CreateApplicationModal — финальный вид | 1.5ч |
| T-4-022 | RemoveFromCellModal, MoveToCellModal | 1.5ч |
| T-4-023 | ChangeConditionModal, ChangeDepartmentModal (с предупреждением о активной заявке) | 1ч |

### 4.3. Real-time + UX-полировка

| ID | Задача | Оценка |
|----|--------|--------|
| T-4-030 | SSE интеграция: `useEventSource` + invalidation queries по событию | 2ч |
| T-4-031 | Optimistic mutations + rollback по ошибке | 1.5ч |
| T-4-032 | Skeleton/Empty/Error states на всех страницах | 1ч |
| T-4-033 | Keyboard shortcuts (`/` поиск, R/D/A/S/V для transitions) | 1ч |

### 4.4. Тесты

| ID | Задача | Оценка |
|----|--------|--------|
| T-4-040 | Vitest unit-тесты на utils + entities hooks | 1ч |
| T-4-041 | Playwright e2e: login → main menu → display-view → transition | 2ч |

---

## Граф зависимостей

```
T-4-001 (tokens)  ──┐
T-4-002 (types)   ──┼──► T-4-003 (router) ──► T-4-004 (layout) ──► T-4-010..016 (pages)
                    │                                                     │
                    └──► T-4-008 SSE base ──► T-4-030 (real-time) ◄────┐
                                                                         │
T-4-020..023 (modals) ───────────────────────────────────────────────────┤
                                                                         ▼
                                                            T-4-031 (optimistic)
                                                                         │
                                                                         ▼
                                                          T-4-032 (states), T-4-033 (kbd)
                                                                         │
                                                                         ▼
                                                          T-4-040 (unit), T-4-041 (e2e)
```

---

## Что НЕ делать в Фазе 4

- ❌ Удалять Django templates / legacy views — это после деплоя SPA на staging (Фаза 4.5 «cleanup»)
- ❌ Мобильная версия < 768px (показываем «откройте с планшета или компа»)
- ❌ Светлая тема
- ❌ Storybook — на следующий цикл
- ❌ SSR / Next.js — не нужен внутреннему ops-tool

---

## Критерии завершения Фазы 4

- [ ] T-3-fix-001/002 применены (без них фронт не дружит с API)
- [ ] Все 7 страниц (login, menu, dept-list, 3× display-view, zip) работают на эталонных tokens.css v2
- [ ] OpenAPI types генерятся из схемы (не вручную)
- [ ] SSE работает: тестовое событие на сервере → invalidate query → UI обновился
- [ ] Все 12 transition-модалок реализованы
- [ ] Lighthouse Performance ≥ 80 (для desktop 1920×1080)
- [ ] Сборка прода: `pnpm build` успешна
- [ ] e2e: 3+ сценария (login, create application, transition)
