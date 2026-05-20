# Mobile / Android adaptation plan

> **Дата:** 2026-05-19
> **Зона D** дизайн-аудита раунда 4.
> **Контекст:** A2 ответ владельца — сервисмены работают с десктопов, ноутбуков **и Android-телефонов**. Текущий UI рассчитан на ≥1280px. Phase 7 уже подняла плотность через `[data-density="touch"]` для `pointer: coarse`, но layout всё ещё ломается ниже 1024px.
> **Этот документ — план**, не исполнение. JSX-эскизы для 4 mobile-экранов идут отдельным файлом `mobile-sketches.html` (design_canvas). Реальная имплементация — Phase 8 / отдельный Round-5.

---

## 1. Breakpoints

| Имя | Ширина | Целевые устройства |
|---|---|---|
| `mobile` | ≤ 767px | Android phone (Pixel 6 = 412×915, Galaxy A = 360×800) |
| `tablet` | 768 – 1023px | iPad Mini, Android планшеты 8-10", split-screen на ноуте |
| `desktop` | ≥ 1024px | основной target — рабочее место в офисе |

В Tailwind config **ничего менять не надо** — дефолтные `sm:` (640), `md:` (768), `lg:` (1024), `xl:` (1280), `2xl:` (1536) совпадают. Используем `md:`/`lg:` для tablet/desktop.

Density-токены в `tokens.css` уже имеют автомеханику:
```css
@media (max-width: 1280px) and (pointer: coarse) { /* touch density */ }
```
Это **слишком широко** — `data-density="touch"` сейчас включается даже на iPad в landscape с stylus'ом. **Фикс зоны D:**
```css
@media (max-width: 1024px) and (pointer: coarse), (max-width: 767px) {
  :root:not([data-density]) { /* touch density */ }
}
```

И **44px touch-target** (Apple HIG) — это `--hit-target: 44px` в touch density. Уже выполнено.

---

## 2. Что сервисмену реально нужно в поле

Из A2 ответа владельца + здравого смысла — **в поле сервисмен**:

1. Видит **свои назначенные заявки** (DisplayView/service, фильтр «мои»).
2. **Принимает заявку в работу** (FSM transition).
3. **Снимает / ставит панель** (модалка с фото).
4. **Меняет condition панели** на месте.
5. **Открывает карточку заявки** для чтения (печать с phone не нужна — она была про офисный принтер).

**В поле НЕ нужно:**

- ZIP overview — он для офиса (учёт остатков).
- Departures — это контроль, не сервис.
- Глобальный поиск `Cmd+K` — на phone нет физической клавиатуры.
- Drag-and-drop ZIP колонок — невозможно на touch.
- Печатать карточку — нет принтера.
- Profile activity / theme settings — не критично, можно скрыть в drawer.

---

## 3. Матрица «экран × breakpoint»

`full` — полная функциональность.
`compact` — частично сжатый layout.
`drawer` — основной контент уменьшен, второстепенное в drawer/bottom-sheet.
`hidden` — экран целиком прячется (или редирект на 404-friendly заглушку «не поддерживается на этом устройстве»).
`replaced` — отдельный mobile-layout, не масштабирование.

| Экран | mobile (≤767) | tablet (768–1023) | desktop (≥1024) |
|---|---|---|---|
| `/login` | replaced (одна колонка) | full | full |
| `/menu` (MainMenu 4-кол) | replaced (1 кол стек) | compact (2 кол) | full (4 кол) |
| `/monitoring`, `/control`, `/service` | replaced (cards, без SideRail) | compact (SideRail сворачивается в drawer) | full |
| `/monitoring/:c/:d` DisplayView | replaced (list-mode без grid) | compact (grid + drawer RightRail) | full |
| `/control/:c/:d` DisplayView | replaced (см. выше, без service-actions) | compact | full |
| `/service/:c/:d` DisplayView | **replaced — главный mobile-экран** | compact | full |
| `/zip`, `/zip/:slug` | hidden (toast «не поддерживается на phone, откройте на компе») | drawer (табы по отделам вместо 6 колонок) | full |
| `/departures` | hidden | compact (без detail-rail) | full |
| `/lk` | full (естественно stacked) | full | full |
| ApplicationDetailSheet (print) | n/a (нет принтера) | n/a | n/a |

**Глобальные компоненты:**

| Компонент | mobile | tablet | desktop |
|---|---|---|---|
| Header NAV (6 пунктов) | hamburger menu | compact (иконки без подписей) | full |
| NotificationBell | full-width popover (overlay) | popover 320px | popover 320px |
| ThemeToggle | в drawer профиля | в Header | в Header |
| CommandPalette | hidden | full | full |
| SSEDot | tooltip | tooltip | tooltip |

---

## 4. Что прячем на phone (детально)

### `/zip` и `/zip/:slug`

Сервисмену в поле ЗИП не нужен — это бухгалтерия панелей. Показываем заглушку:

```tsx
// pages/zip/ZipPage.tsx, в начале JSX
if (isMobile) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
      <Smartphone size={32} style={{ color: 'var(--fg-mute)' }} />
      <h2 className="text-base font-semibold" style={{ color: 'var(--fg)' }}>
        ЗИП доступен на компьютере
      </h2>
      <p className="text-sm" style={{ color: 'var(--fg-mute)' }}>
        Чтобы перемещать панели между складом, руками и сервисом, откройте систему на ноутбуке или стационарном компьютере.
      </p>
      <Link to="/menu" className="btn btn-secondary">К главной</Link>
    </div>
  )
}
```

`useIsMobile()` — хук на `window.matchMedia('(max-width: 767px)')` с listener'ом. Один хук на весь проект.

### `/departures`

То же — заглушка. «Управление выездными бригадами — для контроля. Откройте на компе.»

### CommandPalette

В `App.tsx`:
```tsx
{!isMobile && <GlobalSearch />}
```

И в `useKeyboard` не регистрировать `?` shortcut на mobile.

---

## 5. Header на mobile

Сейчас в Header 6 NavLink'ов + bell + theme + user + logout. На 360px не помещается.

**Решение:** hamburger drawer + минимальный header:

```
┌─────────────────────────────────────────┐
│ [≡]  Суперсимметрия               [🔔]  │   44px
└─────────────────────────────────────────┘
```

- Hamburger ([≡]) — слева. Tap → bottom-sheet drawer со всем нав-меню, темой, профилем, logout.
- Логотип-текст (без знака) — центр или левее.
- Bell (счётчик уведомлений) — справа.
- Всё остальное (ThemeToggle, user-bubble, logout) — внутри drawer'a.

Драфт drawer:

```
┌─────────────────────────────────────────┐
│ Меню                              [✕]   │
├─────────────────────────────────────────┤
│  [🏠]  Главная                          │
│  [📺]  Мониторинг                       │
│  [✓]   Контроль                         │
│  [🔧]  Сервис                           │
│  [📦]  ЗИП                              │
│  [🚗]  Выезды                           │
├─────────────────────────────────────────┤
│  Тема:  ( ○ Светлая  ● Тёмная  ○ Сист.) │
├─────────────────────────────────────────┤
│  IV  Иван Сервисов · service            │
│  [Выйти]                                │
└─────────────────────────────────────────┘
```

(Иконки тут условные — в код идут lucide по карте замен из S-003.)

Realization — Radix Dialog + slide-from-left анимация, focus-trap встроен.

---

## 6. DisplayView/service mobile — главный экран

Сейчас на десктопе: 3-колоночный layout (Grid 10×10 + PanelInfo + RightRail с заявками).

На phone 360×800 — **сразу видим вкладку «Мои в работе»** заявок, grid убираем. Юзер тапает заявку → переходит на детальную карточку с фото-аплоадом и FSM-кнопкой.

Layout:

```
┌─────────────────────────────────────────┐
│ [≡]  Сервис · СПб · Невский 12     [🔔]│   44px
├─────────────────────────────────────────┤
│  ┌─ Мои ────┐ Все           Архив       │   tabs, 36px
│  └──────────┘                           │
├─────────────────────────────────────────┤
│ ┌───────────────────────────────────┐  │
│ │ #142  ●  поз.03  P-014             │  │
│ │ Не светит верхняя строка пикселей  │  │
│ │ ─────────────────────────────────  │  │
│ │ Назначена 14:32                    │  │
│ │ [Принять в работу →]               │  │   primary btn 44px
│ └───────────────────────────────────┘  │
│                                         │
│ ┌───────────────────────────────────┐  │
│ │ #138  ●  поз.07  P-009             │  │
│ │ Тёмное пятно 4×4                   │  │
│ │ ...                                │  │
│ └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

Карточка заявки на phone — стек: id + status pill + cell pos + panel name → desc → meta → action button. Все touch-targets ≥44px.

**Детальный режим** (tap по карточке) → fullscreen overlay (bottom-sheet drawer 90vh):

```
┌─────────────────────────────────────────┐
│ [←]  Заявка #142                  [...] │
├─────────────────────────────────────────┤
│  ●  Принята сервисом                    │
│  СПб · Невский 12 · поз.03 · P-014      │
│                                         │
│  Описание                               │
│  ────────                               │
│  Не светит верхняя строка пикселей,     │
│  заметно с 5 метров.                    │
│                                         │
│  Снимки от мониторинга:                 │
│  [фото] [фото]                          │
│                                         │
│  Состояние панели                       │
│  ────────────────                       │
│  P-014 · work → problem                 │
│  [ Поменять состояние ↓ ]               │
│                                         │
│  Заменить панель                        │
│  ────────────────                       │
│  [ Снять с ячейки ]                     │
│  [ Установить из ЗИП ]                  │
│                                         │
│  Завершить заявку                       │
│  ──────────────────                     │
│  [ ✔ Выполнено ]                        │
│  [ ✕ Невозможно отремонтировать ]       │
└─────────────────────────────────────────┘
```

Кнопки разнесены по группам действий, не сжаты в одну строку. Прокрутка вертикальная.

**Что НЕ показываем** на phone-карточке:
- 10×10 grid экрана (нет физического места).
- История места + история панели (это для расследования в офисе).
- Соседние ячейки.

Эти разделы появляются на tablet (≥768px), где грид сжимается до ~360px ширины.

---

## 7. Department List на phone

```
┌─────────────────────────────────────────┐
│ [≡]  Сервис · экраны              [🔔] │
├─────────────────────────────────────────┤
│  [🔍 Поиск города]                      │   только если городов ≥3
├─────────────────────────────────────────┤
│  МОСКВА · 4 экрана                      │
│  ┌─────────────────────────────────┐    │
│  │ Тверская 7                  →   │    │   72px карточка
│  │ 12×8 · m-tver-7                 │    │
│  │ [ЗИП] [Заявки] [История]        │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ Арбат 25                    →   │    │
│  │ 10×6 · m-arbat-25               │    │
│  └─────────────────────────────────┘    │
│  ...                                    │
│                                         │
│  САНКТ-ПЕТЕРБУРГ · 3 экрана             │
│  ...                                    │
└─────────────────────────────────────────┘
```

Карточки экранов — на всю ширину, без 3-колоночной сетки. SideRail (последние заявки) — **в bottom-sheet** через кнопку «↑ N свежих» вверху списка, opt-in.

---

## 8. Main menu на phone

Из 4-колоночного дашборда на десктопе → одна колонка stack'ом:

```
┌─────────────────────────────────────────┐
│ Главная                                 │
├─────────────────────────────────────────┤
│ Привет, Иван                            │
│ СПб, Москва                             │
├─────────────────────────────────────────┤
│ Сводка                                  │
│ ┌──────┬──────┬──────┬──────┐           │
│ │  12  │  8   │  3   │ 0:54 │           │   KPI 4-up — горизонтальный скролл
│ │Запрос│Контр.│Серв. │ зад. │           │
│ └──────┴──────┴──────┴──────┘           │
├─────────────────────────────────────────┤
│ Мониторинг — последние                  │
│  #142 · СПб/Невский/03                  │
│  #141 · СПб/Невский/12                  │
│  → Все                                  │
├─────────────────────────────────────────┤
│ Контроль — очередь                      │
│  ...                                    │
├─────────────────────────────────────────┤
│ Сервис — мои                            │
│  ...                                    │
├─────────────────────────────────────────┤
│ ЗИП — статистика                        │
│  Ламели:  12   Хабы:  4                 │
│  ...                                    │
└─────────────────────────────────────────┘
```

Каждый блок — collapsable (default collapsed для сервисмена, expand'нут «Сервис — мои»).

---

## 9. Open question — определение «mobile»

**Делать ли свитч по media-query через CSS-only или по JS-хуку через `useIsMobile`?**

- **CSS-only**: проще, нет JS-логики, но не позволяет полностью **переключить дерево компонентов** (для DisplayView mobile-list-mode vs desktop-grid-mode).
- **JS-хук**: `useIsMobile()` через `matchMedia` + `useSyncExternalStore`. Позволяет рендерить ДРУГОЕ дерево.

**Решение:** для DisplayView, ZIP, Departures — **JS-хук** (разные компоненты). Для Header, карточек экрана, MenuPage — **CSS-only** через Tailwind responsive утилитки.

```ts
// shared/lib/useIsMobile.ts
import { useSyncExternalStore } from 'react'

const QUERY = '(max-width: 767px)'

function subscribe(cb: () => void) {
  const m = window.matchMedia(QUERY)
  m.addEventListener('change', cb)
  return () => m.removeEventListener('change', cb)
}
function getSnapshot() {
  return window.matchMedia(QUERY).matches
}
function getServerSnapshot() {
  return false
}
export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
```

Один хук, реюзить везде где нужен `if (isMobile)` branch.

---

## 10. Конкретные Tailwind responsive utilities — где

### Header

```diff
// widgets/navigation/Header.tsx
- <nav className="flex items-center h-full px-2">
+ <nav className="hidden md:flex items-center h-full px-2">
  ...
+ {/* На mobile показываем hamburger */}
+ <button
+   className="icon-btn md:hidden mr-2"
+   aria-label="Меню"
+   onClick={() => setDrawerOpen(true)}
+ >
+   <Menu size={18} />
+ </button>

  {/* Username — только md+ */}
- <span className="hidden md:block">{me.username}</span>

  {/* Logout — только md+, на mobile уходит в drawer */}
- <button onClick={handleLogout} ... title="Выйти">
+ <button onClick={handleLogout} className="icon-btn hidden md:inline-flex" aria-label="Выйти" title="Выйти">
```

### DepartmentListPage

```diff
- <div className="grid h-full min-h-0 grid-cols-[1fr_320px]" ...>
+ <div className="grid h-full min-h-0 grid-cols-1 md:grid-cols-[1fr_320px]" ...>
  ...
- <aside className="flex min-h-0 flex-col bg-bg-1">
+ <aside className="hidden md:flex min-h-0 flex-col bg-bg-1">
```

Карточки экранов:
```diff
- <div className="grid gap-2 px-6 pb-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
+ <div className="grid gap-2 px-4 pb-4 sm:px-6 grid-cols-1 md:grid-cols-2 lg:[grid-template-columns:repeat(auto-fill,minmax(230px,1fr))]">
```

(Сложный inline `grid-template-columns` оборачиваем `lg:[..]` Tailwind arbitrary syntax.)

### MainMenuPage

Самое сложное, делаем отдельным mobile-вариантом по JS-хуку:

```tsx
export function MainMenuPage() {
  const isMobile = useIsMobile()
  if (isMobile) return <MainMenuMobile />
  return <MainMenuDesktop />  // нынешний код
}
```

### DisplayViewPage

То же:
```tsx
export function DisplayViewPage({ department }) {
  const isMobile = useIsMobile()
  if (isMobile) return <DisplayViewMobile department={department} />
  // ... existing 3-column code
}
```

---

## 11. Этапы внедрения (предложение для Phase 8)

| # | Задача | Время | Зависит от |
|---:|---|---|---|
| 1 | `useIsMobile` hook | 30 мин | — |
| 2 | Header hamburger drawer + nav в drawer | 1 день | 1 |
| 3 | Mobile заглушки на /zip и /departures | 30 мин | 1 |
| 4 | DepartmentList responsive (CSS-only) | 4 часа | — |
| 5 | MainMenu mobile вариант | 1 день | 1 |
| 6 | DisplayView/service mobile (list-mode + detail-sheet) | 2 дня | 1 |
| 7 | DisplayView/monitoring + control mobile | 1 день | 6 |
| 8 | Touch-density media-query fix | 15 мин | — |
| 9 | Mobile testing на реальных Android (?) | по факту | 1-8 |

**Суммарно:** ~5-6 рабочих дней кодера для P0 mobile-функций (header + service-mobile + заглушки). Полный mobile UX — 8-10 дней.

---

## 12. Что НЕ делаем сейчас

- iOS Safari testing. Сервисмены на Android — тестируем только Android Chrome.
- Offline-mode / PWA service worker. Это отдельная задача Phase 9.
- Push-notifications. Сейчас только звук в открытой вкладке.
- Native-камера API для фото-аплоада — через стандартный `<input type="file" accept="image/*" capture="environment">`, чего достаточно.
- Геолокация / привязка выезда к координатам.
- Биометрия (отпечаток для логина).

---

## 13. Открытые вопросы к владельцу

1. На phone сервисмен открывает приложение **в браузере** или нужна PWA (иконка на главном экране, full-screen)? Если PWA — добавим `manifest.json` (он уже частично есть через `<link rel="manifest">`? — проверить).
2. Какой целевой Android (минимальный)? Если ≥Android 9 — Chrome ≥80, без полифилов. Если ниже — `useSyncExternalStore` может быть проблемой (но React 18+ совместим).
3. Хочется ли биометрия / SSO для входа? Сейчас на phone тоже логин-пароль вручную.
4. Сервисмену **доступен ли control** на phone? Я предположил «нет» (только service). Подтвердить.
5. Фото для заявки — **одно** или **несколько**? Сейчас в `TransitionModal` `<input type="file">` одно-файловый. На phone камера снимает по одному фото — может быть несколько, может загружаться по очереди.

---

## 14. Эскизы

Эскизы 4 mobile-экранов (Login, Menu, DepartmentList, DisplayView service) в обеих темах — отдельный файл:

`mobile-sketches.html`

В нём — design_canvas с Android-frame'ами 412×915 (Pixel 6). Каждый экран — два артборда: light + dark. Подписи под каждым.

Цель эскизов — **показать кодеру композицию**, не production-ready код. Цвета через токены, шрифт TT Travels, эмодзи убраны (lucide-плейсхолдеры).

---

*Это последний документ зоны D. После этого все 4 deliverables из чек-листа Round-4 сданы:*
- `design-audit-2026-05-19.md` (зона A)
- `design-polish-round-3.md` (зона B + краткая C)
- `microinteractions-a11y-fixes.md` (зона E)
- `mobile-adaptation-plan.md` + `mobile-sketches.html` (зона D)
