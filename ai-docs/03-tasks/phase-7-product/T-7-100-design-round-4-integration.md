# T-7-100. Интеграция Design Round 4 в проект (10 PR'ов)

> **Тип задачи:** frontend integration + точечный backend
> **Приоритет:** P0 (есть несколько P0-багов: D5/D6/D7 фичи в мёртвом файле, DeparturesPage без фона, 17 эмодзи в UI вопреки брендгайду)
> **Оценка:** **5-6 рабочих дней** (по словам дизайнера, ~25-30 ч кодинга)
> **Фаза:** 7 (продуктовый раунд дизайнера)
> **Статус:** review
> **Исполнитель:** GPT-5 Codex

---

## Цель

Накатить пакет от Claude Design (Round 4 / 2026-05-19): полировка фактически внедрённого Phase 7 UI под брендгайд «Суперсимметрия», dark theme до конца, мёртвые классы вычищены, эмодзи заменены на `lucide-react`, P0-фичи D5/D6/D7 физически подключены в прод (сейчас живут в мёртвом `DepartmentPage.tsx`, а App.tsx роутит `DepartmentListPage.tsx`).

---

## Что лежит в репо

### Документы дизайнера — `ai-docs/07-frontend/` (для чтения)

| Файл | Что внутри |
|---|---|
| [`design-handoff-round-4.md`](../../07-frontend/design-handoff-round-4.md) | TL;DR + порядок работы + open questions |
| [`design-audit-2026-05-19.md`](../../07-frontend/design-audit-2026-05-19.md) | 43 пункта баг-репорта с severity (9 P0, 24 P1, 10 P2) |
| [`design-polish-round-3.md`](../../07-frontend/design-polish-round-3.md) | JSX-диффы для сложных мест (ZIP, EventTimeline, TransitionLabels) |
| [`microinteractions-a11y-fixes.md`](../../07-frontend/microinteractions-a11y-fixes.md) | 20 точечных fix'ов: focus rings, skeletons, transitions, ARIA, motion |
| [`mobile-adaptation-plan.md`](../../07-frontend/mobile-adaptation-plan.md) | План Phase 8 (не сейчас) |

### Исторический пакет патчей

Исходный пакет `_design-patches-round-4/frontend-patches/` (17 файлов: 11 drop-in `.tsx`/`.css`/`.html` + 4 snippet'а + README + INTEGRATION.md) уже был использован для PR-1..10 и удалён cleanup-PR'ом.

Источники истины после интеграции:
- `ai-docs/07-frontend/design-handoff-round-4.md`
- `ai-docs/07-frontend/design-audit-2026-05-19.md`
- `ai-docs/07-frontend/design-polish-round-3.md`
- `ai-docs/07-frontend/microinteractions-a11y-fixes.md`
- `ai-docs/08-reports/T-7-100-pr-1.md` ... `T-7-100-pr-13.md`

---

## Зависимости

- **Блокируется:** ничем (можно брать сейчас).
- **Блокирует:** **финальный staging cutover** (UI ещё не соответствует брендгайду, пользователь увидит «программистский UI» при первом входе после rebranding).
- **Open questions, требующие backend follow-up:**
  - Q1 (DL-003): `aggregated_condition` для display — см. [T-7-followup-display-aggregated-condition](T-7-followup-display-aggregated-condition.md).
  - Q3 (PR-10): `app.display.city.slug` в dashboard DTO — см. [T-7-followup-applications-display-city](T-7-followup-applications-display-city.md).
  - Optional: bell deep-link resolve endpoint — см. [T-7-followup-bell-deeplink-resolve](T-7-followup-bell-deeplink-resolve.md).

Эти 3 followup'а можно делать **параллельно** с PR-1..9. PR-10 ждёт Q3.

---

## 10 PR'ов в порядке исполнения

Краткое содержание. Детали фактической интеграции см. в отчётах `08-reports/T-7-100-pr-*.md`.

### PR-1 · `chore/cleanup-dead-styles` (P0, ~2 ч)

Заменить `index.html` + `app/globals.css`. Append `tokens-additions.css.snippet` в конец `tokens.css`. Заменить блок `<Toaster>` в `App.tsx` по snippet'у. Убирает: `<html class="dark">` хардкод, Inter, dead classes, неправильную theme transition.

### PR-2 · `feat/empty-state-icons` (P0, ~1 ч)

Replace `shared/ui/EmptyState.tsx` под ReactNode-иконку. Прогон `git grep -n 'EmptyState icon="'` найдёт ~5 callsite'ов с эмодзи (📭, 🏙️, 🔍, 🚗) → заменить на `<Inbox />`, `<Building2 />`, `<SearchX />`, `<Car />` из lucide.

### PR-3 · `fix/modal-toggle-theme-toggle` (P1, ~30 мин)

Replace `Modal.tsx` (фон на `--bg-1` для контраста), `ThemeToggle.tsx` (3-режимный цикл light → dark → system → light), new `Toggle.tsx`. Зависит от PR-1 (`--bg-1` в обеих темах).

### PR-4 · `feat/profile-sound-toggle` (P1, ~30 мин)

В `pages/profile/ProfilePage.tsx` — inline-замена секции «Звуковые уведомления» по `ProfilePage-sound-section.snippet`. Использует новый `Toggle`. Кнопка «Прослушать» всегда доступна. Зависит от PR-3.

### PR-5 · `fix/login-page` (P1, ~20 мин)

Replace `LoginPage.tsx`. Добавляется слоган «Соединяем важное», переход на `.input` класс, surface через `--bg-1`. Зависит от PR-1 (где `.input` определён в globals.css).

### PR-6 · `fix/header-icon-buttons` (P1, ~30 мин)

Replace `Header.tsx` + `NotificationBell.tsx`. Убирает inline hover handler'ы (всё через `.icon-btn`). Bell pulse-анимация при unread, fix deep-link на `application.target_kind`. Подготовка к hamburger drawer (`hidden md:flex` на nav). Зависит от PR-1, PR-3.

### PR-7 · `fix/departures-tokens` (P0, ~30 мин)

Replace `DeparturesPage.tsx`. Убирает мёртвые `bg-surface-*` классы — сейчас страница рендерится **без фона/границ** в actual UI. EmptyState с `<Car>`-иконкой.

### PR-8 · `feat/department-list-merge` (P0, **самый большой**, ~1.5 дня) ⚠️

**Самый рискованный PR.** Replace `DepartmentListPage.tsx` — переносит sort/filter/quick-links из мёртвого `DepartmentPage.tsx` в **живой** маршрутизированный `DepartmentListPage.tsx`. После применения **удалить**:
- `pages/department/DepartmentPage.tsx`
- `pages/department/DepartmentPage.test.tsx`

`DepartmentPage.test.tsx` нужно **переписать** в `DepartmentListPage.test.tsx` — контракт тот же, RTL + MemoryRouter, проверяет sort/filter/quick-link/empty-state. Sticky-header, sort persist в sessionStorage, city-filter показывается если ≥3 городов, SideRail справа 320px скрыт на mobile.

Делать отдельным PR, ревью внимательнее. Зависит от PR-1, PR-2.

### PR-9 · `chore/zip-display-view-deemoji` (P1, ~3 ч)

**Не drop-in — manual edits по диффам из** `design-polish-round-3.md`:
- `pages/zip/ZipPage.tsx` — `DEPARTMENTS` и `StorageSection`: эмодзи → lucide (§ B.3).
- `pages/display-view/DisplayViewPage.tsx` — `TRANSITION_LABELS`: эмодзи → lucide (§ B.2).
- `entities/application/EventTimeline.tsx` — `STAGE_LABELS`: эмодзи → lucide (§ B.2 patch 3).

### PR-10 · `feat/dashboard-app-link` (P0 функциональный, ~30 мин)

В `pages/menu/MainMenuPage.tsx` — fix `getAppPath()`. Сейчас использует `app.display.slug` как citySlug → ведёт в `/(dept)/(displaySlug)` (без city). Должно быть `app.display.city.slug` → `/(dept)/(citySlug)/(displaySlug)?app_id=...`.

**Зависит от [T-7-followup-applications-display-city](T-7-followup-applications-display-city.md)** — backend должен добавить `city: {slug, name}` в `DisplayMiniSerializer`.

---

## Что НЕ в этом раунде

- **Mobile hamburger drawer.** PR-6 только подготовил `hidden md:flex`. Сам drawer — Phase 8.
- **DisplayView/service mobile (list-mode), MainMenu mobile, заглушки на /zip и /departures для mobile** — Phase 8.
- **PWA** — отдельная задача, ждём ответа владельца (open Q4 в дизайнерском handoff).
- **Tablet адаптация в полном объёме** — `tokens-additions.css.snippet` уже расширяет touch-density на tablet `pointer:coarse`, но dashboard вёрстки для tablet — Phase 8.

---

## Критерии приёмки (после всех 10 PR'ов)

Контракт качества из дизайнерского handoff:

- [x] `git grep 'bg-surface-' frontend/src` — 0 совпадений.
- [x] `git grep 'text-text-' frontend/src` — 0 совпадений.
- [x] `git grep -P '[\\x{1F300}-\\x{1FAFF}]' frontend/src` (исключая тесты и `Condition.icon`) — 0.
- [x] `git grep -E '#[0-9a-fA-F]{3,8}' frontend/src` — только в `tokens.css` и `ApplicationDetailSheet*` (печать).
- [x] Light и dark mode визуально проверены на всех 9 экранах (`logs/t7100b_acceptance_spa/`, recheck `logs/t7100b_monitoring_display_recheck_after_restart/`).
- [x] Tab по любой странице — каждый интерактивный элемент имеет видимый focus ring (`logs/t7100b_acceptance_spa/focus-summary.json`).
- [x] `npm test` зелёный.
- [x] **Файл `_design-patches-round-4/` удалён** (cleanup-PR).

---

## Что НЕ делать

- **Не трогать палитру `tokens.css`** — только append через snippet.
- **Не менять шрифты** — TT Travels уже подключен, Biform ждём отдельно.
- **Не переписывать API `<Button>`, `<Modal>`, `<ConfirmDialog>`** — только косметика (стиль, не контракт).
- **Не выдумывать ответы** на open questions — это работа архитектора. Подними наверх.
- **Не складывать всё в один большой PR.** Делать 10 атомарных. Чтобы при проблемах можно было откатить точечно.
- **Не лезть в Phase 8** (mobile drawer, list-mode, full tablet) — это отдельный спринт после PR-1..10.

---

## Open questions от дизайнера (ответы архитектора)

| ID | Вопрос дизайнера | Ответ архитектора | Блокирует |
|---|---|---|---|
| 1 | `aggregated_condition` экрана в DTO? | **Нет.** Заведена `T-7-followup-display-aggregated-condition`. Кодер делает параллельно или после PR-8. | DL-003 (status bullet) |
| 2 | DisplayView Round-0 — bottom-tabs или RightRail? | **RightRail** (см. фактический код `DisplayViewPage.tsx:466-493`). | DV-003 |
| 3 | `/dashboard/` отдаёт `app.display.city.slug`? | **Нет.** Заведена `T-7-followup-applications-display-city`. Это backend-mini-task; PR-10 ждёт её. | PR-10 |
| 4 | PWA для phone — нужна? Минимальный Android? | **Phase 8, не сейчас.** Решение владельца по timeline'у Phase 8 — после prod cutover. | Phase 8 |
| 5 | Control-роль на phone доступна? | **Phase 8.** Не блокирует Round 4. | Phase 8 |

---

## Команды для кодера

```bash
# 1. Создать ветку
cd frontend
git checkout -b feat/round-4-design-audit

# 2. Открыть в браузере (рядом с кодом)
xdg-open ../ai-docs/07-frontend/design-audit-2026-05-19.md
xdg-open ../ai-docs/07-frontend/design-polish-round-3.md

# 3. Запустить dev + watch tests
npm run dev &
npm test -- --watch &

# 4. Идти по PR-1 → PR-10, каждый — отдельный commit с ссылкой на followup ID
```

Cleanup `PR-11` на удаление `_design-patches-round-4/` уже выполнен.

---

## Отчёт по выполнению

(Заполняет кодер. Отдельный отчёт `08-reports/T-7-100-pr-N.md` на каждый из 10 PR'ов, `T-7-100-pr-11.md` на cleanup, `T-7-100-pr-12.md` на automated acceptance-sweep и `T-7-100-pr-13.md` на restored prod-copy close-out.)
