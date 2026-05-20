# Design audit — «Суперсимметрия», раунд 4

> **Дата:** 2026-05-19
> **Скоуп:** аудит реально внедрённого UI (Phase 7) на соответствие брендгайду + эталонам Round-0/Round-3.
> **Метод:** статический проход по `frontend/src/**` + grep по hex / legacy classes / эмодзи / `aria-label` / `focus-visible`. Live-скриншоты не запрашивались (по договорённости с владельцем).
> **Цель документа:** не «всё переделать», а собрать список багов, который кодер раскатает отдельной серией `T-7-followup-*` задач.
>
> Формат записи:
> ```
> [ID]  /экран/  light|dark  Проблема.
>       FIX: что делать.
>       owner-action: код-фикс / только полировка JSX
> ```
>
> Severity: **P0** — ломает визуал/брендинг сейчас. **P1** — несоответствие эталону, заметное. **P2** — мелочи, чистота кода.

---

## Сводка

| Категория | P0 | P1 | P2 |
|---|---:|---:|---:|
| Системные (через весь UI) | **6** | 4 | 3 |
| Login | 0 | 2 | 1 |
| Main menu | 1 | 2 | 0 |
| DepartmentList | **1** | 3 | 1 |
| DisplayView | 0 | 2 | 1 |
| ZIP | **1** | 2 | 1 |
| Departures | 0 | 1 | 0 |
| Profile | 0 | 3 | 1 |
| Phase 7 компоненты | 0 | 5 | 2 |
| **Итого** | **9** | **24** | **10** |

Главное — пункты **S-001, S-002, S-003, D-001, Z-001**. Это блокеры брендинга / dark theme / реальной работы фич.

---

## S — Системные находки

### [S-001] /все/ light+dark — В `globals.css` и `index.html` используются классы старой темы (`bg-surface-1`, `text-text-primary`, `bg-surface-3`, `bg-surface-4`). В новом `tailwind.config.js` эти токены НЕ определены → классы no-op'ятся и фоны/цвета не задаются. **P0**

```css
/* globals.css */
body { @apply bg-surface-1 text-text-primary; }
::-webkit-scrollbar-track  { @apply bg-surface-1; }
::-webkit-scrollbar-thumb  { @apply bg-surface-3 rounded-full; }
::-webkit-scrollbar-thumb:hover { @apply bg-surface-4; }

/* index.html */
<body class="bg-surface-1 text-text-primary antialiased">
```

Работает «случайно» — потому что `tokens.css` отдельно ставит `html, body { background: var(--bg-0); color: var(--fg); }`. Но скроллбар-кастомизация → **мёртвая**: дефолтный нативный, в обеих темах.

**FIX:**
```css
/* globals.css */
body { background: var(--bg-0); color: var(--fg); }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track  { background: var(--bg-0); }
::-webkit-scrollbar-thumb  { background: var(--bg-3); border-radius: 6px; border: 2px solid var(--bg-0); }
::-webkit-scrollbar-thumb:hover { background: var(--bg-4); }
```
И в `index.html` снять `class="bg-surface-1 text-text-primary antialiased"` с `<body>` → оставить только `class="antialiased"`.

**owner-action:** `T-7-followup-globals-css`, плюс убрать `class="dark"` с `<html>` (см. **S-002**).

---

### [S-002] /все/ light — `<html lang="ru" class="dark">` в `index.html` всегда содержит `class="dark"`. Tailwind `darkMode: 'class'`, поэтому все `dark:` варианты ВСЕГДА активны — даже когда пользователь выбрал `theme=light` в Profile. **P0**

Скорее всего сейчас спасает то, что `dark:`-вариантов в коде почти нет (видимо, всё переведено на CSS-vars). Но это бомба замедленного действия: первый же `dark:bg-bg-1` в новом компоненте сломает light-режим.

**FIX:** в `index.html` снять `class="dark"`; либо синхронизировать в `ThemeProvider`:
```ts
// theme.tsx, в useEffect[theme]
root.classList.toggle('dark', nextResolvedTheme === 'dark')
```
Я бы шёл первым путём (статический `<html lang="ru">` без класса) — тема рулится через `data-theme` атрибут, который и так корректно проставляет `ThemeProvider`. Tailwind `darkMode: 'class'` оставить можно, нужен он только в редких случаях.

**owner-action:** `T-7-followup-html-dark-class`.

---

### [S-003] /все/ light+dark — Эмодзи в UI. Брендгайд §5 и §3 запрещают эмодзи в рабочем интерфейсе. Текущие места: **P0**

| Файл | Эмодзи | Контекст |
|---|---|---|
| `pages/department/DepartmentListPage.tsx:89,243` | 📭 🏙️ | `<EmptyState icon="..." />` |
| `pages/departures/DeparturesPage.tsx:98` | 🚗 | `<EmptyState />` |
| `widgets/applications-panel/ApplicationsPanel.tsx:59` | 📭 | `<EmptyState />` |
| `pages/zip/ZipPage.tsx:23-26` | 📦 ✋ 🔧 📺 | DEPARTMENTS labels |
| `pages/zip/ZipPage.tsx:188-194` (StorageSection) | 🧩 🔌 🔗 🔋 🪛 | категории расходников |
| `entities/application/EventTimeline.tsx:5-13` | 📋✅📤🔧✔️❌📦 | стадии заявок |
| `pages/display-view/DisplayViewPage.tsx:61-69` | ✅📤🔧✔️❌📦🗑️ | TRANSITION_LABELS — кнопки FSM |

**FIX:** каждое заменить на lucide-react иконку 13–14px, `style={{ color: 'var(--fg-mute)' }}`. Карта замен:

```ts
// EmptyState — переключить пропс на ReactNode (иконка)
📭 → <Inbox size={20} />        // от lucide-react
🏙️ → <Building2 size={20} />
🔍 → <SearchX size={20} />
🚗 → <Car size={20} />

// ZipPage DEPARTMENTS
📦 ЗИП        → <Package />
✋ На руках   → <HandMetal /> или <UserCheck />
🔧 Сервис    → <Wrench />
📺 На экранах → <Monitor />

// ZipPage StorageSection
🧩 Ламели        → <Layers />
🔌 Хабы          → <Network /> или <Cpu />
🔗 Провода       → <Cable />
🔋 Блоки питания → <BatteryFull />
🪛 Коннекторы    → <Plug />

// EventTimeline + TRANSITION_LABELS
📋 → <FilePlus />     ✅ → <Check />        📤 → <Send />
🔧 → <Wrench />        ✔️ → <CheckCheck />   ❌ → <X />
📦 → <Archive />       🗑️ → <Trash2 />
```

**owner-action:** `T-7-followup-deemoji` — один PR, 7 файлов, замена тривиальная.

---

### [S-004] /все/ light+dark — `--bg-2` в `tokens.css` имеет один и тот же hex `#b8bfc6` (Серебро) и в light, и в dark теме. По брендгайду «Серебро = приглушённый текст и иконки», но в коде `--bg-2` используется как ФОН: для Modal (`shared/ui/Modal.tsx:30`), Login form card (`pages/login/LoginPage.tsx:65`), Button `variant=secondary` (`shared/ui/Button.tsx:17`), DepartmentList rows, hover Header user-bubble и т.д. В dark theme получается светло-серый «обрубок» на тёмном фоне — выбивается. **P0**

**FIX:** не трогать палитру (вы запретили). Вместо этого **уменьшить использование `--bg-2` как surface'a** — для всех серфейс-фонов использовать `--bg-1`:

```diff
- background: 'var(--bg-2)'   // Login form card, Modal, secondary Button
+ background: 'var(--bg-1)'
```

Конкретные файлы (5 штук):
- `shared/ui/Modal.tsx:30` — модалка целиком.
- `shared/ui/Button.tsx:17` — `variant=secondary`.
- `pages/login/LoginPage.tsx:65` — login form card.
- `pages/department/DepartmentListPage.tsx:104` — `<DisplayRow>` фон.
- `features/panels/PanelCreateButton.tsx:115,132,158` — поля формы.

`--bg-2` оставляем для **hover-фонов icon-button** (это OK — Серебро как контактный hover). Утилитарные классы `bg-bg-2` через Tailwind config не меняем.

**owner-action:** `T-7-followup-bg-2-as-surface` — 5 файлов.

---

### [S-005] /все/ light+dark — Двойной шрифт-импорт. В `index.html` подгружается Google Font **Inter** (400/500/600) — он явно в списке «не использовать» брендгайда §3. Реальный шрифт UI — TT Travels из `fonts.css`. Inter качается зря, ~30 KB лишнего трафика, плюс риск что где-то `font-family: Inter` останется в legacy CSS. **P0**

**FIX:** `index.html` — снять link на Inter. JetBrains Mono — оставить, он явно используется как `--font-mono`. Заодно добавить preload для TT Travels Regular/Bold, чтобы избежать FOUT:

```html
<link rel="preload" href="/fonts/tt-travels/TTTravels-Regular.woff2" as="font" type="font/woff2" crossorigin />
<link rel="preload" href="/fonts/tt-travels/TTTravels-Bold.woff2" as="font" type="font/woff2" crossorigin />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

**owner-action:** `T-7-followup-drop-inter`.

---

### [S-006] /все/ light+dark — Дублированный мёртвый код двух экранов. **P0**

- `pages/menu/MenuPage.tsx` — НЕ используется в `App.tsx` (используется `MainMenuPage`), но содержит `bg-surface-2`, `border-surface-3`, `text-text-muted` и т.д. — старые легась-классы.
- `pages/department/DepartmentPage.tsx` — НЕ используется в `App.tsx` (используется `DepartmentListPage`), но **содержит реализованный sort+filter+quick-links** (D5/D6/D7), которая по `screens-map.md` помечена ✅. В реальном `DepartmentListPage.tsx` этих фич НЕТ — пользователь их не видит.

Это критично: фичи **D5/D6/D7** в проде ОТСУТСТВУЮТ, хотя в брифе и map они отмечены как сделанные. Кодер забыл смерджить ветки.

**FIX:**
1. Удалить `pages/menu/MenuPage.tsx` целиком (мёртвый код).
2. Перенести sort+filter+quick-links из `DepartmentPage.tsx` в `DepartmentListPage.tsx`, переведя на токены (`var(--bg-1)`, `var(--border-subtle)` и т.д.). После переноса — удалить `DepartmentPage.tsx`.
3. Обновить `DepartmentPage.test.tsx` под `DepartmentListPage`.
4. Поправить `screens-map.md`: D5/D6/D7 на самом деле ⬜, не ✅.

**owner-action:** `T-7-followup-merge-department-pages` — большой PR на 1–2 дня кодера.

---

### [S-007] /все/ light+dark — Нет единого focus-ring через `:focus-visible`. **P1**

Текущая мозаика:
- `tokens.css` определяет `.focusable:focus-visible` с двойным box-shadow — но почти нигде не применяется.
- `LoginPage.tsx` и input'ы — `focus:outline-none` + ручной `onFocus/onBlur` инлайн-JS (фрагильно).
- `DepartmentListPage.tsx` `<DisplayRow>` — нативный `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2` — то что надо.
- `ZipPage.tsx PanelChip` — то же, OK.
- `Button.tsx` — `focus-visible:outline-none` без компенсации фокус-стиля → клавиатура не видит фокус на кнопке. **P0 для a11y, но я отмечаю P1 — Button используется не для primary-action на login**.

**FIX:** один глобальный паттерн через утилиту:

```css
/* tokens.css, в конец */
:where(button, a, input, select, textarea, [role="button"], [tabindex]):focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: var(--r-sm);
}
```

И отдельно `<Button>` — убрать `focus-visible:outline-none`, оставить пустым (вышеуказанный `:where` применится).

**owner-action:** `T-7-followup-focus-visible-system`.

---

### [S-008] /все/ — Toaster (`sonner`) подключён с `richColors`, но без кастомного `--toast-bg/--toast-color`. На light-теме `richColors` использует свои hex; брендингу не подчиняется. **P1**

**FIX:** в `App.tsx`:
```tsx
<Toaster
  position="bottom-right"
  theme={resolvedTheme}
  toastOptions={{
    style: {
      background: 'var(--bg-1)',
      color: 'var(--fg)',
      border: '1px solid var(--border-subtle)',
      fontFamily: 'var(--font-sans)',
    },
  }}
/>
```
`richColors` снять — он перекрывает наши brand-варианты.

---

### [S-009] /все/ light+dark — `localStorage` ключ `mstechnics-global-search-recent` (`features/search/storage.ts:3`). По ADR-002 имя «MsTechnics» допустимо в коде/БД/домене, но **в ключах локального хранилища пользователь видит через DevTools**. **P2**

**FIX:** Можно оставить (миграция стоит «потерять историю поиска» — некритично). Если решаете мигрировать:
```ts
const RECENT_SEARCHES_KEY = 'sup.search.recent'
// migration: при отсутствии нового ключа — читаем старый и переписываем, удаляем старый.
```

Рекомендую **оставить как есть**, добавить TODO-комментарий «после Phase 8 переименуем». Не повод тратить время кодера сейчас.

---

### [S-010] /все/ light+dark — `<Header>` использует **смешанные паттерны** для hover/active: `onMouseOver/onMouseOut` инлайн-JS на logout-кнопке (`Header.tsx:170-172`), CSS-классы на NavLink. Непредсказуемо при keyboard focus. **P2**

**FIX:** заменить onMouseOver/onMouseOut на CSS-класс или утилиту `.icon-btn` (она уже есть в tokens.css). Достаточно:
```tsx
<button onClick={handleLogout} className="icon-btn" title="Выйти" aria-label="Выйти">
  <LogOut size={14} />
</button>
```

То же — для ThemeToggle (`ThemeToggle.tsx:23-37`).

---

### [S-011] /все/ light+dark — `--h-row: 28px`, `--hit-target: 28px` для default density. На touch-устройстве `@media (max-width: 1280px) and (pointer: coarse)` поднимается до 40/44px — хорошо. Но это `max-width: 1280px` — на Android-телефоне в landscape всё ещё может быть 28px. **P1, готовится к зоне D.**

**FIX:** в зоне D обсудим — предлагаю поднять breakpoint до `1024px`, и/или включать `touch` density по `pointer: coarse` ONLY.

---

### [S-012] /все/ light+dark — В нескольких местах внешние компоненты получают `style={{ color: '#000' }}` или `'#fff'` для печати (`ApplicationDetailSheet.tsx`, `NotificationBell.tsx:57`). Это **по делу** (печать всегда чёрно-белая, fallback `var(--err-ink, #fff)` оправдан). Не фиксим. Отмечаю чтобы не путать с реальными hex-литералами в UI. **OK, не баг.**

---

## L — Login

### [L-001] /login/ light+dark — Нет фирменного слогана. По решению владельца (см. план) на login subtitle должен быть слоган **«Соединяем важное»**. Сейчас: «Управление LED-экранами». **P1**

```diff
- <p className="text-xs" style={{ color: 'var(--fg-mute)' }}>
-   Управление LED-экранами
- </p>
+ <p className="text-xs" style={{ color: 'var(--fg-mute)' }}>
+   Соединяем важное
+ </p>
```

Можно второй строкой добавить мелким `text-2xs`: «внутренняя система · управление экранами» если боитесь, что слоган без контекста запутает первого юзера. Но я бы оставил **только слоган** — это login-page «бренд-момент», а контекст системы пользователь уже знает.

---

### [L-002] /login/ dark — Карта формы рендерится на `var(--bg-2)` = `#b8bfc6` (Серебро) — серый прямоугольник на тёмном фоне. По брендгайду Серебро не для заливок. Эталон Round-0 — карта на surface-1. См. **S-004**. **P1**

`FIX` уже в S-004: `background: var(--bg-1)`. В dark это даст Ночную дымку `#3c4856` — мягкая глубина на основном фоне `#040f1d`.

---

### [L-003] /login/ light+dark — Inline-обработчики `onFocus/onBlur` на input'ах с прямым изменением `style.borderColor`/`style.boxShadow`. Хрупко, не следует системе. **P2**

**FIX:** переписать на CSS-класс. Создать в `globals.css`:
```css
.input {
  height: var(--h-input);
  padding: 0 10px;
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  color: var(--fg);
  font-size: 13px;
  transition: border-color 100ms, box-shadow 100ms;
}
.input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-faint); outline: none; }
```
И использовать `<input className="input" ... />`.

Это же `.input` подойдёт для `PanelCreateButton.tsx` и других мест, где сейчас инлайн-стиль повторяется.

---

## M — Main menu

### [M-001] /menu/ light+dark — Использует `MainMenuPage.tsx`, у владельца помечен ✅ Round-0 эталон. Визуально — соответствует. Однако: **P0 для функционала, не визуала** — `getAppPath()` в `MainMenuPage.tsx:74-77` строит URL через `app.display.slug` без `citySlug`, тогда как DisplayView ожидает `/<dept>/<citySlug>/<displaySlug>`:
```ts
const citySlug = app.display.slug ?? ''   // !!! это displaySlug, не citySlug
return citySlug ? `/${dept}/${citySlug}?app_id=${app.id}` : `/${dept}`
```
Маршруты в `App.tsx` ждут `/control/:citySlug/:displaySlug`. На клик с дашборда юзер летит на не-валидный URL → DepartmentListPage по `citySlug == displaySlug`. **P0 функциональный**, не визуальный — но всплыл в аудите.

**FIX:** хоткей `T-7-followup-dashboard-app-link` — починить путь:
```ts
return `/${dept}/${app.display.city.slug}/${app.display.slug}?app_id=${app.id}`
```
Нужно убедиться, что в DTO `app.display.city.slug` приходит — если нет, надо расширить serializer на бэке.

---

### [M-002] /menu/ light+dark — Заголовок страницы и фразы повторяют функции отделов в три места (Header, breadcrumb, MainMenu cards). Тон правильный, но **карточки контроля/сервиса показывают «Очередь контроля» / «Мои в работе» без подсказки что это значит** (как и эталон). **P1, низкий приоритет.**

**FIX:** под заголовком каждой колонки в шапке `<ColumnShell subtitle="...">` (он уже есть). Сейчас subtitle используется только для `permission` ярлыка. Добавить one-liner:
- monitoring → «sent_to_control · последние»
- control → «sent_to_control + apply_in_control»
- service → «at_work · мои»

Но это мелочь, можно скип.

---

### [M-003] /menu/ light+dark — Mode «карточка с цветным мини-иконком отдела» (стиль `MenuPage.tsx`, который мёртв) визуально интересней «таблицы 4 колонки» MainMenuPage'a. Но эталон Round-0 — именно таблица 4 колонки. Не трогаем. **P1, отмечаю как «решено владельцем».**

---

## DL — DepartmentList

### [DL-001] /monitoring|/control|/service/ light+dark — Sort + filter + quick-links НЕ работают. См. **S-006**. **P0**

---

### [DL-002] /monitoring|/control|/service/ light+dark — Метка активного города отрисовывает **литерал строки `activity`**:

```tsx
{active && (
  <span ... style={{ color: 'var(--accent)' }}>
    activity     {/* ← debug-string */}
  </span>
)}
```
Видимо placeholder для иконки `<Activity>` от lucide. Сейчас юзер видит дословно слово «activity» жёлтым моноширинным. **P1**

**FIX:**
```diff
- <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--accent)' }}>
-   activity
- </span>
+ <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--accent)' }}>
+   Активный
+ </span>
```
Или совсем убрать индикатор — активность подсвечивается фоном `var(--bg-1)`. Этого достаточно.

---

### [DL-003] /monitoring|/control|/service/ light+dark — Индикатор статуса экрана — голый bullet-символ `●` с дефолтным цветом `var(--fg)`:

```tsx
<span title="Статус экрана" className="text-sm">●</span>
```
То есть он всегда чёрный (или белый в dark). Не отражает реальный статус. **P1**

**FIX:** привязать к данным или скрыть. Минимум — задать `var(--ok)` и переименовать `title` в «Подключён». А идеально — выводить агрегатный статус из `display.aggregated_condition` (если backend такое отдаёт) и красить в три цвета (ok/warn/err). Если нет — снять символ, оставить только `ArrowRight`.

---

### [DL-004] /monitoring|/control|/service/ light+dark — EmptyState на пустой `SideRail` использует эмодзи 📭. См. **S-003**. **P0**

---

### [DL-005] /monitoring|/control|/service/ light+dark — `<DisplayRow>` имеет `background: var(--bg-2)` (Серебро, см. **S-004**). Кроме того — `outlineColor: 'var(--accent)'` задан, но Tailwind-классы `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2` — корректно. Этот pattern лучший в кодбазе сейчас, его и распространяем. **P1, fix via S-004.**

---

### [DL-006] /monitoring|/control|/service/ light+dark — Внешний grid имеет `style={{ background: 'var(--border-subtle)' }}` — использование border-токена как surface'a. Случайно работает (как разделитель между main и aside), но семантически грязно. **P2**

**FIX:** заменить на `background: 'var(--border-0)'` или (лучше) убрать вообще — sticky header под `bg-bg-0`, sideRail под `bg-bg-1`, между ними 1px-border задаётся явно.

---

## DV — DisplayView (3 роли)

### [DV-001] /monitoring|/control|/service/:city/:display/ light+dark — Эмодзи в TRANSITION_LABELS (см. **S-003**). На кнопках FSM `🔧 В работу`, `📤 В сервис` и т.д. **P0**

---

### [DV-002] /monitoring|/control|/service/:city/:display/ light+dark — Inline-стили громоздкие (>50 `style={{...}}` блоков в одном `DisplayViewPage.tsx`). Большинство — повторяющиеся: `{ color: 'var(--fg-mute)' }`, `{ color: 'var(--fg-faint)' }`, `{ fontFamily: 'var(--font-mono)' }`. **P1, чистка.**

**FIX:** заменить на Tailwind утилитки, которые УЖЕ есть в config (`text-fg-mute`, `text-fg-faint`, `font-mono`). Можно безболезненно — за один PR, чисто механическая замена.

```diff
- <span style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}>
+ <span className="font-mono text-fg-mute">
```

**owner-action:** `T-7-followup-inline-style-cleanup` (не срочно, в плановом рефакторе).

---

### [DV-003] /service/:city/:display/ light+dark — Эталон Round-0 (Display View v2) проверен по описанию screens-map: 12-колоночная сетка, RightRail, Tabs снизу. Текущий код держит layout, но я **не вижу bottom-tabs** в `DisplayViewPage.tsx` в первой 600 строках — только Tabs внутри RightRail. Уточнить у владельца — это by design или регрессия. **P2 — нужен ответ владельца.**

---

## Z — ZIP

### [Z-001] /zip/ + /zip/:slug/ light+dark — Эмодзи в DEPARTMENTS + StorageSection (см. **S-003**). Это **главный экран сервисмена** — эмодзи бросаются в глаза. **P0**

---

### [Z-002] /zip/ light+dark — Колонка `monitor` (на экранах) **не принимает drop**, но визуально неотличима от drop-целевых. Юзер тащит панель в monitor, понимает что зря, отпускает — тишина. **P1**

**FIX:** показывать «not allowed» визуальный feedback:
```tsx
// PanelColumn — добавить cue когда зашли над monitor
const handleDragOver = (e) => {
  if (!isDropTarget) {
    // показываем not-allowed
    e.preventDefault()
    e.dataTransfer.dropEffect = 'none'
    setDragHover(true)   // но рисуем другой стиль
    return
  }
  ...
}
```
И в `style` вынести отдельную ветку для not-allowed:
```ts
outline: dragHover ? (isDropTarget ? '2px dashed var(--accent)' : '2px dashed var(--fg-faint)') : undefined,
background: dragHover ? (isDropTarget ? 'var(--accent-faint)' : 'transparent') : undefined,
```

---

### [Z-003] /zip/ light+dark — `PanelChip` использует `background: var(--bg-2)` (Серебро) для невыбранного состояния. См. **S-004**. **P1**

**FIX:** `var(--bg-1)` для базового, `var(--bg-3)` (`#d2d8df`/`#4c5967`) для selected. И убрать `bg-2` оттуда.

---

### [Z-004] /zip/ light+dark — Когда тянем chip, source-карточка не «выцветает» — DnD outline есть на target'ах, но source выглядит как обычно. **P2**

**FIX:** на `PanelChip` HTML5-нативное:
```tsx
onDragStart={(e) => { /* существующее */ ; e.currentTarget.style.opacity = '0.4' }}
onDragEnd={(e) => { e.currentTarget.style.opacity = '1' }}
```

---

## DE — Departures

### [DE-001] /departures/ light+dark — EmptyState с 🚗 (см. **S-003**). **P0** (через S-003)

---

### [DE-002] /departures/ light+dark — Связь «эта заявка входит в выезды #5 и #7» по brief'у пока не нужна (blocked T-7-004). Готовый паттерн — `pill-neutral` с `idchip`:
```tsx
<span className="idchip">#5</span> <span className="idchip">#7</span>
```
Когда T-7-004 разморозят. **P1, заметка.**

---

## P — Profile

### [P-001] /lk/ light+dark — Звук-секция использует **нативный `<input type="checkbox">`** без стиля — программистский UI. Брендгайд: «Не делать программистский UI». **P1**

**FIX:** заменить на toggle-switch в стиле системы. Минимальный CSS-only toggle (без новых deps):
```tsx
<label className="inline-flex items-center gap-2 cursor-pointer">
  <input type="checkbox" className="sr-only peer"
         checked={soundEnabled}
         onChange={e => handleSoundToggle(e.target.checked)} />
  <span
    className="relative h-5 w-9 rounded-full transition-colors"
    style={{ background: soundEnabled ? 'var(--accent)' : 'var(--bg-3)' }}
  >
    <span
      className="absolute top-0.5 h-4 w-4 rounded-full transition-transform"
      style={{
        background: 'var(--bg-0)',
        transform: soundEnabled ? 'translateX(18px)' : 'translateX(2px)',
      }}
    />
  </span>
  <span style={{ color: 'var(--fg-dim)' }}>{soundEnabled ? 'Включено' : 'Выключено'}</span>
</label>
```

И вынести этот toggle в `shared/ui/Toggle.tsx` — переиспользуем в Profile sound + (потенциально) ThemeToggle.

---

### [P-002] /lk/ light+dark — Кнопка «Прослушать» `disabled={!soundEnabled}` — нелогично: чтобы услышать как звучит уведомление, я должен сначала включить. Должно работать наоборот: «прослушать» доступно всегда, **включает** же чекбокс реальную доставку звуков. **P1**

**FIX:**
```diff
- <Button ... onClick={() => playNotificationSound(true)} disabled={!soundEnabled}>
+ <Button ... onClick={() => playNotificationSound(true)}>
    Прослушать
  </Button>
```
Аргумент `true` в `playNotificationSound(true)` — судя по сигнатуре, force-mode (играть даже если выключено). То что нужно.

---

### [P-003] /lk/ light+dark — Тема-radio: визуально неплохо, но **карточки выделяются жёлтым кантом** `border: var(--accent)` + `background: var(--accent-faint)`. Жёлтый «фоновой подсвет» — это про **primary action**, тут это **выбор настройки**. Слабый дисбаланс смысла. **P1, низкий приоритет.**

**FIX (опция):** выбранную карту красить через 2px-кант без жёлтой заливки:
```diff
- background: selected ? 'var(--accent-faint)' : 'var(--bg-0)',
- borderColor: selected ? 'var(--accent)' : 'var(--border-subtle)',
+ background: selected ? 'var(--bg-0)' : 'var(--bg-0)',
+ borderColor: selected ? 'var(--accent)' : 'var(--border-subtle)',
+ borderWidth: selected ? '2px' : '1px',
```
И padding на selected уменьшить на 1px, чтобы layout не дрожал. Это субъективное улучшение — можно скип.

---

### [P-004] /lk/ light+dark — История действий — плоский `<ol>` с карточками. Брендбук вообще никак не указывает паттерн timeline, но из эталона DisplayView у нас уже есть `EventTimeline` с дотами. Если хотим единообразия — переиспользовать. Но `ActivityLogEntry` и `EventTimeline.props` разные DTO. **P2, можно скип.**

---

## C — Phase 7 компоненты (review)

### [C-001] /global/ ConfirmDialog — visual OK, наследует Modal'у. **Title по умолчанию «Точно?» — короткий, бренд-tone-of-voice ✅.** Description опциональна. Не нужна доп. полировка. **OK.**

### [C-002] /global/ ConfirmDialog — `useConfirmDialog()` хук возвращает `props: { open, onClose }` — `onConfirm` остаётся снаружи. В `PanelDeleteButton` это используется правильно: ошибка backend'a проставляется в `description` через `setError`, **title не переписывается** — заголовок остаётся «Удалить панель X?». В брифе ошибочно сказано, что ошибка попадает в title. Я перепроверил — там OK. **OK, нет фикса.**

### [C-003] /header/ NotificationBell — ширина popover'a 320px (`w-80`), не 250 как в брифе. Это лучше — текст уведомлений не режется. На tablet (1024+) — OK. На phone — будет шире viewport, нужен fix в зоне D. **P1 для зоны D.**

### [C-004] /header/ NotificationBell — НЕ имеет **pulse-анимации** на новый item. Глаз сейчас не цепляет; колокольчик меняется `Bell → BellRing` + красный бейдж появляется. Анимация добавит акцента. **P1, переходит в зону E.**

### [C-005] /zip/ PanelCreateButton — поля формы используют `bg-2` (Серебро) как фон. См. **S-004**. **P1, fix через S-004.**

### [C-006] /zip/ PanelCreateButton — `<select>` для выбора экрана: длинный список городов и экранов, без поиска. На 10+ экранах будет неудобно. **P2.**

**FIX:** если экранов меньше 15 — оставить нативный select. Иначе заменить на компонент с inline-фильтром (Radix Combobox или свой). Сейчас (Phase 7) — оставить.

### [C-007] /global/ ThemeToggle — иконка меняется (Sun/Moon/Monitor), `aria-label="Сменить тему"`, `title=` показывает текущую тему. **OK на 80%**. Минус: hover через инлайн `onMouseOver`/`onMouseOut` — см. **S-010**. Должно быть `.icon-btn`. **P2.**

### [C-008] /lk/ ProfileSoundSection — нативный checkbox. См. **P-001**. **P1.**

### [C-009] /lk/ ProfileActivitySection — flat list. См. **P-004**. **P2.**

---

## Сводка `T-7-followup-*` для кодера

В порядке приоритета:

1. **`T-7-followup-merge-department-pages`** (S-006, DL-001) — вытащить sort+filter+quick-links в живой `DepartmentListPage`, выкинуть дубли. **2 дня кодера.**
2. **`T-7-followup-deemoji`** (S-003, DV-001, Z-001, DE-001) — заменить эмодзи на lucide-иконки в 7 файлах. **1 день, тривиально.**
3. **`T-7-followup-globals-css`** (S-001) — почистить globals.css от мёртвых классов, восстановить кастом-scrollbar. **2 часа.**
4. **`T-7-followup-html-dark-class`** (S-002) — снять `class="dark"` с `<html>`. **15 минут.**
5. **`T-7-followup-bg-2-as-surface`** (S-004, L-002, DL-005, Z-003, C-005) — заменить `--bg-2` на `--bg-1` как surface в 5 местах. **2 часа.**
6. **`T-7-followup-drop-inter`** (S-005) — снять Inter, добавить preload TT Travels. **20 минут.**
7. **`T-7-followup-dashboard-app-link`** (M-001) — починить URL с MainMenu карточек заявок. **1 час.**
8. **`T-7-followup-debug-activity-label`** (DL-002) — заменить literal `activity` на «Активный». **5 минут.**
9. **`T-7-followup-focus-visible-system`** (S-007) — глобальный `:focus-visible` через `:where`. **1 час.**
10. **`T-7-followup-soundtoggle-ui`** (P-001) — CSS-only Toggle в `shared/ui/Toggle.tsx`, использовать в Profile. **2 часа.**
11. **`T-7-followup-sound-preview-enabled`** (P-002) — снять `disabled` с preview-кнопки. **5 минут.**
12. **`T-7-followup-zip-not-allowed-cue`** (Z-002) — визуальный feedback для drop в `monitor`. **30 минут.**
13. **`T-7-followup-toaster-theme`** (S-008) — кастом-стили `sonner`. **15 минут.**
14. **`T-7-followup-status-bullet`** (DL-003) — статусный bullet привязать к данным или снять. Требует решения **по данным** (есть ли `aggregated_condition` на бэке?). **1 час + ответ владельца.**
15. **`T-7-followup-inline-style-cleanup`** (DV-002) — замена `style={{...}}` на Tailwind. **1 день, плановый рефакторинг.**

**Суммарно:** ~4 дня плотной работы кодера. После этого UI визуально соответствует брендгайду и эталонам.

---

## Что не покрыто этим аудитом

- **DisplayView Round-0 vs реал** — нужен живой скриншот или попадание в эталон-файлы Round-0. Сейчас имею только текстовый screens-map. Возможен пробел DV-003.
- **Реальная палитра в браузере** — все hex-проверки сделаны статически, не через `getComputedStyle()` в живом DOM. Если в чьём-то extension'е или devtools-override переопределён `--bg-0` — не увидим.
- **Печатная карточка ApplicationDetailSheet** — пробежал по коду, всё OK (явно `#000`/`#fff` для бумаги, медиа-запрос работает). Не выношу отдельных пунктов.
- **Animation/motion** — отдельно в зоне E.

---

## Открытые вопросы к владельцу

1. `aggregated_condition` экрана — поле в DTO есть? Нужно для DL-003.
2. DV-003 — bottom-tabs в DisplayView в эталоне Round-0 были или это RightRail-only?
3. `dashboard` endpoint — отдаёт `app.display.city.slug`? (M-001 фикс зависит)

---

*Дальше — зоны B (polish 5 экранов), C (review компонентов — частично перекрыто разделом «C» этого файла), D (mobile), E (микровзаимодействия). Согласуйте план следующей зоны.*
