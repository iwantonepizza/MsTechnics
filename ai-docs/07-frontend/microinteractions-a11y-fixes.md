# Microinteractions + accessibility fixes

> **Дата:** 2026-05-19
> **Зона E** дизайн-аудита раунда 4.
> **Цель:** 20–30 точечных CSS/JSX-патчей, которые поднимают UI с уровня «работает» до «приятно использовать», без переделки архитектуры.
> Каждый пункт — отдельная мини-задача `T-7-followup-*` для кодера. Идут по убыванию impact.

---

## E-001 — Глобальный `:focus-visible` (P0 для a11y)

**Проблема:** мозаика focus-стилей по кодбазе:
- `tokens.css` объявляет `.focusable:focus-visible` — но используется в одном-двух местах.
- `LoginPage.tsx` инлайн-`onFocus/onBlur` через `style.borderColor`.
- `Button.tsx` явно `focus-visible:outline-none` БЕЗ компенсирующего стиля — клавиатурный фокус на кнопке не видно.
- `DepartmentListPage` / `ZipPage PanelChip` — корректно используют `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2`.

**Фикс:** один CSS-блок в `tokens.css` через `:where()` для нулевой специфичности:

```css
/* tokens.css, добавить в конец */
:where(button, a, input, select, textarea, summary, [role="button"], [tabindex]):focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: var(--r-sm);
}

/* Внутри ConfirmDialog / inputs, где outline визуально слишком толстый, можно сужать локально через специфичный селектор. */
```

И в `Button.tsx`:
```diff
- 'focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
+ 'disabled:pointer-events-none disabled:opacity-50',
```

В `LoginPage.tsx` — заменить инлайн-handlers на `.input` класс (см. E-002), focus тогда придёт автоматически.

**Уважение к мыши:** `:focus-visible` сам не активируется на `pointer` событиях. То есть мышь не получает «жёлтую обводку» при клике на кнопку — только клавиатура. Это то что нужно.

---

## E-002 — Единая утилита `.input` (P1)

**Проблема:** в 7+ местах повторяется инлайн-style для текстовых полей. В `LoginPage` дополнительно ручной onFocus/onBlur.

**Фикс:** в `globals.css` (после `@apply` блока):

```css
@layer components {
  .input {
    display: inline-flex;
    align-items: center;
    height: var(--h-input);
    padding: 0 10px;
    background: var(--bg-1);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    color: var(--fg);
    font-family: var(--font-sans);
    font-size: 13px;
    transition: border-color 100ms, box-shadow 100ms;
    outline: none;
  }
  .input::placeholder { color: var(--fg-mute); }
  .input:focus-visible {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-faint);
    outline: none;     /* перекрывает E-001 — текстовое поле подсвечивается «обводкой через box-shadow», не двойным контуром */
  }
  .input:disabled { opacity: 0.55; cursor: not-allowed; }

  /* Для <select> и <textarea> можно тот же класс + при необходимости height: auto; */
  textarea.input { height: auto; padding: 8px 10px; }
}
```

Использовать в `LoginPage`, `PanelCreateButton`, `TransitionModal`, `DepartmentListPage` toolbar и т.д.

---

## E-003 — Скелетоны: единая плотность (P1)

**Текущая мозаика высот:**
- `SkeletonList` default — `var(--h-row)` = 28px (touch 40px).
- В коде вызовы с `height="22px"`, `"34px"`, `"42px"`, `"20px"`, `"64px"` — magic numbers.

**Фикс:** ввести семантические токены в `tokens.css`:

```css
:root {
  --skel-h-text: 14px;        /* строка плотного текста */
  --skel-h-row: var(--h-row); /* стандартная строка списка */
  --skel-h-card: 64px;        /* карточка */
  --skel-h-grid-cell: 44px;   /* ячейка display-grid */
  --skel-h-kpi-num: 22px;     /* большая цифра в KPI */
  --skel-h-kpi-label: 10px;   /* подпись KPI */
}
```

И заменять hardcoded:

```diff
- <Skeleton style={{ height: '18px', width: '160px', marginBottom: '12px' }} />
+ <Skeleton style={{ height: 'var(--skel-h-row)', width: '160px', marginBottom: '12px' }} />

- <Skeleton style={{ height: '22px', width: '48px' }} />
+ <Skeleton style={{ height: 'var(--skel-h-kpi-num)', width: '48px' }} />

- <Skeleton style={{ width: '44px', height: '44px', borderRadius: '3px' }} />
+ <Skeleton style={{ width: 'var(--skel-h-grid-cell)', height: 'var(--skel-h-grid-cell)', borderRadius: '3px' }} />
```

Опционально — расширить `SkeletonList` поддержкой пресета:

```tsx
type Preset = 'row' | 'card' | 'text'
export function SkeletonList({ rows = 5, preset = 'row' }: { rows?: number; preset?: Preset }) {
  const height = preset === 'card' ? 'var(--skel-h-card)' : preset === 'text' ? 'var(--skel-h-text)' : 'var(--skel-h-row)'
  ...
}
```

Низкий приоритет, можно делать постепенно.

---

## E-004 — NotificationBell pulse (P1)

**Проблема:** при появлении нового уведомления BellRing-иконка и красный бейдж появляются мгновенно, без анимации. Глаз не цепляет.

**Фикс:** add CSS keyframes + applied class when `unreadCount > 0` AND prev count was lower (новое уведомление пришло).

`tokens.css`:
```css
@keyframes bell-pulse {
  0%, 100% { transform: rotate(0deg); }
  10%, 30% { transform: rotate(-10deg); }
  20%, 40% { transform: rotate(10deg); }
  50%      { transform: rotate(0deg); }
}
.bell-pulse {
  animation: bell-pulse 700ms ease-in-out;
}
@media (prefers-reduced-motion: reduce) {
  .bell-pulse { animation: none; }
}
```

`NotificationBell.tsx`:
```tsx
const [pulse, setPulse] = useState(false)
const prevUnread = useRef(unreadCount)

useEffect(() => {
  if (unreadCount > prevUnread.current) {
    setPulse(true)
    const t = setTimeout(() => setPulse(false), 800)
    prevUnread.current = unreadCount
    return () => clearTimeout(t)
  }
  prevUnread.current = unreadCount
}, [unreadCount])

// в JSX:
<Icon size={16} style={{ color: 'var(--fg-dim)' }} className={pulse ? 'bell-pulse' : undefined} />
```

`prefers-reduced-motion: reduce` уважаем — анимация выключается.

---

## E-005 — Theme switch transition (P1)

**Проблема:** переключение темы — резкое (мгновенная замена цветов всех элементов). Глаз не успевает перестроиться, в dark theme при switch на light на долю секунды видишь «выгоревшее» состояние.

**Фикс:** короткий transition на body + основные surface. Осторожно — слишком широкий transition вызывает flash при загрузке страницы.

`tokens.css`:
```css
html, body {
  transition: background-color 160ms ease, color 160ms ease;
}

/* Опционально, для surface-элементов: */
.surface-transition {
  transition: background-color 160ms ease, border-color 160ms ease;
}
```

Чтобы избежать FOUC на первой загрузке — `<html>` сначала добавляем `class="no-theme-transition"`, удаляем после mount:

```ts
// theme.tsx, в useEffect[]
useEffect(() => {
  const id = window.setTimeout(() => {
    document.documentElement.classList.remove('no-theme-transition')
  }, 50)
  return () => window.clearTimeout(id)
}, [])
```

```css
.no-theme-transition,
.no-theme-transition *,
.no-theme-transition *::before,
.no-theme-transition *::after {
  transition: none !important;
}
```

В `index.html`:
```html
<html lang="ru" class="no-theme-transition">
```

(И снять `class="dark"` — см. S-002.)

---

## E-006 — DnD source opacity (P2)

См. **B.3 патч 4**. Уже описано.

---

## E-007 — Toaster theming (P1)

**Проблема:** `sonner` `richColors` использует свои hex, не подчиняется бренду.

**Фикс:** `App.tsx`:
```diff
- <Toaster
-   position="bottom-right"
-   theme={resolvedTheme}
-   richColors
- />
+ <Toaster
+   position="bottom-right"
+   theme={resolvedTheme}
+   toastOptions={{
+     style: {
+       background: 'var(--bg-1)',
+       color: 'var(--fg)',
+       border: '1px solid var(--border-subtle)',
+       fontFamily: 'var(--font-sans)',
+       fontSize: '13px',
+     },
+     classNames: {
+       success: 'sonner-success',
+       error:   'sonner-error',
+       warning: 'sonner-warning',
+       info:    'sonner-info',
+     },
+   }}
+ />
```

В `globals.css` :
```css
[data-sonner-toast].sonner-success [data-icon] { color: var(--ok); }
[data-sonner-toast].sonner-error   [data-icon] { color: var(--err); }
[data-sonner-toast].sonner-warning [data-icon] { color: var(--warn); }
[data-sonner-toast].sonner-info    [data-icon] { color: var(--info); }
```

Готово — тосты в стиле бренда, иконки красятся по семантике.

---

## E-008 — ARIA-labels на icon-only кнопках (P1)

Сделал grep по кодбазе. Покрытие сейчас: 4 места (`NotificationBell`, `ThemeToggle`, `CommandPalette`, MainMenuPage один link).

**Не имеют `aria-label`:**

| Файл | Строка | Элемент |
|---|---:|---|
| `widgets/navigation/Header.tsx` | ~169 | logout `<button>` (есть `title="Выйти"`, нет `aria-label`) |
| `shared/ui/Modal.tsx` | ~45 | `<X>` закрытия модалки (нет ни `title`, ни `aria-label`) |
| `pages/zip/ZipPage.tsx` | ~44 | `PanelChip` `<button>` (только `title` с панель.comment, имени панели в a11y-имени нет) |
| `entities/panel/CellSlot.tsx` | разные ячейки | клик-handler без `aria-label`, screen-reader озвучивает только содержимое |

**Фикс:** добавить `aria-label`:

```diff
// Header.tsx logout
- <button onClick={handleLogout} ... title="Выйти">
+ <button onClick={handleLogout} ... aria-label="Выйти" title="Выйти">

// Modal.tsx
- <button className="...">
-   <X size={14} />
- </button>
+ <button aria-label="Закрыть" className="...">
+   <X size={14} />
+ </button>

// ZipPage PanelChip
- <button ... title={panel.comment ?? undefined}>
+ <button ... aria-label={`Панель ${panel.name}${panel.comment ? `, ${panel.comment}` : ''}`}>
```

---

## E-009 — Header: единый паттерн hover на icon-кнопках (P2)

**Проблема:** в Header три icon-кнопки (SSEDot, NotificationBell, ThemeToggle, logout, user-bubble) делают hover по-разному:
- `Header.tsx` logout — инлайн `onMouseOver/onMouseOut`.
- `ThemeToggle.tsx` — то же.
- `NotificationBell` — Tailwind `hover:bg-bg-1`.
- `MainMenuPage` использует `.icon-btn` utility class (tokens.css).

Утилита `.icon-btn` уже определена в `tokens.css:381` — `28×28px` hit-target, hover bg-bg-2, корректный focus. Это правильный единый паттерн.

**Фикс:** в Header заменить:
```diff
// logout
- <button onClick={handleLogout}
-   className="flex items-center justify-center w-8 h-8 rounded-md transition-colors"
-   style={{ color: 'var(--fg-mute)' }}
-   onMouseOver={e => (e.currentTarget.style.background = 'var(--bg-2)')}
-   onMouseOut={e => (e.currentTarget.style.background = 'transparent')}
-   title="Выйти">
+ <button onClick={handleLogout} className="icon-btn" aria-label="Выйти" title="Выйти">
    <LogOut size={14} />
  </button>

// ThemeToggle.tsx — целиком переписываем под .icon-btn
- <button
-   ...
-   className="flex h-8 w-8 items-center justify-center rounded-md transition-colors"
-   style={{ color: 'var(--fg-mute)' }}
-   onMouseOver={...}
-   onMouseOut={...}
- >
+ <button
+   type="button"
+   aria-label="Сменить тему"
+   title={label}
+   onClick={cycle}
+   className="icon-btn"
+ >
    <Icon size={14} />
  </button>

// NotificationBell.tsx
- <button ... className="relative rounded p-2 hover:bg-bg-1">
+ <button ... className="icon-btn relative">
```

NotificationBell badge остаётся `absolute -top-0.5 -right-0.5` — фитится в `.icon-btn` 28×28 без правок.

---

## E-010 — Header: убрать смешение `--fg-mute` / `--fg-dim` (P2)

**Проблема:** в Header текст пользователя в user-bubble использует `var(--fg-dim)`, аватарка-инициалы — `var(--fg)`, лого-fallback (на мобильном sm:hidden) — `var(--fg)`, NavLink неактивный — `var(--fg-mute)`. Это **рабочая палитра**, но не единая система:

| Элемент | Текущий цвет | Должен быть |
|---|---|---|
| NavLink, неактивный | `--fg-mute` | `--fg-mute` ✓ |
| NavLink, активный | `--fg` | `--fg` ✓ |
| Username | `--fg-dim` | `--fg-dim` ✓ |
| Logout icon | `--fg-mute` | `--fg-mute` ✓ |
| Theme toggle icon | `--fg-mute` | `--fg-mute` ✓ |
| Bell icon | `--fg-dim` | **→ `--fg-mute`** для консистентности с другими icon-кнопками |

```diff
// NotificationBell.tsx
- <Icon size={16} style={{ color: 'var(--fg-dim)' }} />
+ <Icon size={16} style={{ color: 'var(--fg-mute)' }} />
```

Мелочь, но Header после этого выглядит «спокойно» — все иконки одного веса, выделяется только активный навлинк через цвет + жёлтый bottom-border.

---

## E-011 — CommandPalette результаты (P2)

Не читал детально, но из brief'а — это `CommandPalette.tsx` (`/` или `Cmd+K`), уже использует `aria-label="Глобальный поиск"`. Минимум, что стоит проверить: search-match highlight через `<mark>` с брендовым жёлтым — это явное место, где «маркерное выделение» из брендбука §5 уместно.

```css
mark {
  background: var(--accent);
  color: var(--accent-ink);
  padding: 0 2px;
  border-radius: 2px;
}
```

И в результатах поиска:
```tsx
{result.matchedSegments.map((seg, i) =>
  seg.matched ? <mark key={i}>{seg.text}</mark> : <span key={i}>{seg.text}</span>
)}
```

Аналогично — в city-filter (B.1). Не блокер, но «брендинговый момент».

---

## E-012 — Reduced-motion (P1, a11y)

**Проблема:** анимации не уважают `prefers-reduced-motion: reduce`:
- `skeleton-shimmer` shimmer animation (tokens.css:474).
- `SSEDot` `animate-pulse` (Tailwind).
- Будущая `bell-pulse` (E-004 уже это учитывает).

**Фикс:** в `tokens.css`:
```css
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    background: var(--skeleton-bg) !important;
    background-image: none !important;
    animation: none !important;
  }
  .animate-pulse {
    animation: none !important;
  }
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
  }
}
```

---

## E-013 — Login form transitions (P2)

После применения `.input` (E-002) фокус-стиль уже работает через `:focus-visible`. Можно убрать инлайн `onFocus/onBlur` в LoginPage:

```diff
- <input
-   {...register('username')}
-   className="w-full text-sm transition-colors focus:outline-none"
-   style={{
-     height: 'var(--h-input)',
-     padding: '0 10px',
-     background: 'var(--bg-1)',
-     border: '1px solid var(--border)',
-     borderRadius: 'var(--r-md)',
-     color: 'var(--fg)',
-   }}
-   onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-faint)' }}
-   onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
- />
+ <input {...register('username')} className="input w-full" autoComplete="username" autoFocus />
```

Минус 11 строк, плюс единообразие.

---

## E-014 — Hover-микроанимации (P2)

В большинстве мест `transition: background-color 100ms linear` — корректно. Несколько мест используют `transition-colors` Tailwind = 150ms — тоже OK. Не унифицируем — это не bottleneck.

**Один реальный фикс:** ThemeToggle / Header NavLink — добавить лёгкий `transform: translateY` на active state. Это **по желанию владельца**, не блокер. Можно скип.

---

## E-015 — Toggle (CSS-only switch) в `shared/ui/Toggle.tsx` (P1)

См. **P-001**. Полный код компонента:

```tsx
// shared/ui/Toggle.tsx
import { cn } from '@/shared/lib/utils'

interface ToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
  label?: string         // видимая подпись (опционально)
  ariaLabel?: string     // для случая, когда подписи нет
  disabled?: boolean
  size?: 'sm' | 'md'
}

export function Toggle({ checked, onChange, label, ariaLabel, disabled, size = 'md' }: ToggleProps) {
  const w = size === 'sm' ? 32 : 36
  const h = size === 'sm' ? 18 : 20
  const knob = h - 4
  const x = checked ? w - knob - 2 : 2
  return (
    <label
      className={cn('inline-flex items-center gap-2 cursor-pointer select-none', disabled && 'opacity-55 cursor-not-allowed')}
      style={{ color: 'var(--fg)' }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        disabled={disabled}
        className="sr-only"
        aria-label={ariaLabel ?? label}
      />
      <span
        className="relative inline-block transition-colors"
        style={{
          width: w,
          height: h,
          borderRadius: 999,
          background: checked ? 'var(--accent)' : 'var(--bg-3)',
        }}
      >
        <span
          className="absolute top-0.5 transition-transform"
          style={{
            width: knob,
            height: knob,
            borderRadius: '50%',
            background: 'var(--bg-0)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
            transform: `translateX(${x}px)`,
          }}
        />
      </span>
      {label && <span style={{ color: 'var(--fg-dim)' }} className="text-sm">{label}</span>}
    </label>
  )
}
```

В `ProfilePage`:
```diff
- <label className="inline-flex cursor-pointer items-center gap-2 text-sm" ...>
-   <input type="checkbox" checked={soundEnabled} onChange={e => handleSoundToggle(e.target.checked)} ... />
-   {soundEnabled ? 'Включено' : 'Выключено'}
- </label>
+ <Toggle
+   checked={soundEnabled}
+   onChange={handleSoundToggle}
+   label={soundEnabled ? 'Включено' : 'Выключено'}
+   ariaLabel="Звуковые уведомления"
+ />
```

---

## E-016 — `prefers-reduced-motion` для DnD outline animation (P2)

`PanelColumn` outline `2px dashed var(--accent)` статичен — OK. Никаких лишних анимаций. Не трогаем.

---

## E-017 — Печатная карточка ApplicationDetailSheet (P2)

Уже использует `@media print { background: #fff; color: #000 }` — корректно. Внутри есть hardcoded `#000` / `#444` / `#d4d4d4` — это **по делу для бумаги**, не правим.

Один штрих: добавить `print-color-adjust: exact` чтобы Chrome не пытался экономить тонер:

```css
/* application-detail-sheet.css */
@media print {
  .print-sheet {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
}
```

---

## E-018 — Спиннер в Spinner.tsx — заменить кастом-CSS на lucide Loader2 (P2)

Не проверял прицельно. Если `Spinner.tsx` рисует свой spinner через CSS-rotate — оставить, но добавить:
```css
@media (prefers-reduced-motion: reduce) {
  .spinner { animation-duration: 0s !important; opacity: 0.7; }
}
```

Если использует Lucide `<Loader2 className="animate-spin">` — уже учтено в E-012.

---

## E-019 — High-contrast / forced-colors (P2, future)

В Windows High Contrast Mode CSS-vars типа `var(--accent)` могут не применяться, и текст становится System Color. Минимум, что можно добавить:

```css
@media (forced-colors: active) {
  .btn-primary, .icon-btn:focus-visible {
    outline: 2px solid ButtonText;
    outline-offset: 2px;
  }
}
```

Не блокер. Отметить в карточке a11y будущей задачи.

---

## E-020 — Focus-trap в модалках (P2)

`<Modal>` использует Radix Dialog — он сам управляет focus-trap'ом. **Проверить:** что в `TransitionModal` после открытия фокус оказывается на первом input'е (executor select или comment textarea). Сейчас явного `autoFocus` нет — Radix берёт первый focusable элемент, что в порядке. **OK.**

`ConfirmDialog` имеет `autoFocus` на confirm-кнопке. **OK.**

---

## Сводка по приоритетам

| Приоритет | Пункты |
|---|---|
| **P0** | E-001 (focus-visible) |
| **P1** | E-002 (.input), E-003 (skeleton tokens), E-004 (bell pulse), E-005 (theme transition), E-007 (toaster theme), E-008 (aria-labels), E-012 (reduced-motion), E-015 (Toggle component) |
| **P2** | E-009 (Header hover unify), E-010 (Header color unify), E-011 (CommandPalette mark), E-013 (Login .input), E-014 (hover anims), E-017 (print-color-adjust), E-018 (Spinner reduced-motion), E-019 (forced-colors), E-020 (focus-trap проверить) |

---

## Список `T-7-followup-*` после E

Добавляются (продолжая нумерацию из polish-doc'а):

| # | ID | Источник | Время |
|---:|---|---|---|
| 20 | `focus-visible-where` | E-001 | 30 мин |
| 21 | `input-utility-class` | E-002 | 1 час |
| 22 | `skeleton-tokens` | E-003 | 1 час |
| 23 | `bell-pulse` | E-004 | 30 мин |
| 24 | `theme-transition` | E-005 | 30 мин |
| 25 | `toaster-themed` | E-007 (входит в 14 из polish — фактически объединяем) | — |
| 26 | `aria-labels-missing` | E-008 | 30 мин |
| 27 | `header-icon-btn-unify` | E-009 + E-010 | 30 мин |
| 28 | `reduced-motion-guard` | E-012 | 20 мин |
| 29 | `command-palette-mark` | E-011 | 30 мин |

**Суммарно E:** ~5 часов работы кодера на 9 мини-PR'ов.

После B+C+E: **6 рабочих дней кодера** перекрывают весь visual debt раунда 4.

---

## Что в зону E не вошло (отложено в Phase 8 / отдельные ADR)

- Полноценная design-system документация / Storybook.
- Анимированные state-transitions для FSM-кнопок (`apply_in_control → sent_to_service`).
- Анимация переходов между tab'ами `ApplicationsTabs`.
- Sound onboarding (один раз показать «звуковые уведомления требуют клика на странице, чтобы автоплей не блокировался браузером»).
- Tooltip-система (`title` сейчас браузерный — медленный и не стилизуемый). Можно подключить Radix Tooltip в будущей фазе, не сейчас.

---

*Дальше — зона D: mobile / Android adaptation plan. Запускаю по плану — `mobile-adaptation-plan.md` + JSX-эскизы 4 mobile-экранов в одном HTML через design_canvas.*
