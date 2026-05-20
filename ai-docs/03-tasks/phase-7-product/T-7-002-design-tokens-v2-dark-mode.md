# T-7-002. Design tokens v2 + dark mode

> **Тип задачи:** frontend
> **Приоритет:** P1
> **Оценка:** 3-4 часа
> **Фаза:** 7 (product / post-cutover)
> **Статус:** review
> **Исполнитель:** GPT-5 Codex

---

## Цель

Заменить `frontend/src/app/styles/tokens.css` (T-4-001) на новую палитру «Суперсимметрия» (см. `07-frontend/brand-palette-supersymmetria.md`) + добавить полноценную тёмную тему с тoggle'ом в хедере и persist в `localStorage`.

---

## Контекст

- Палитра: `ai-docs/07-frontend/brand-palette-supersymmetria.md` (точные hex'и + готовый CSS-mapping для обеих тем).
- ADR: `ai-docs/adr/ADR-002-rebranding-supersymmetria.md`.
- Текущий `tokens.css` (T-4-001) — частично использует CSS vars через Tailwind config. Это **сохраняется как механизм**, меняются только значения.
- **Цвета состояний панелей и semantic alerts** (красный/жёлтый/оранжевый для warning) — **не входят** в эту замену. Они приходят из БД (`Condition.color`) или семантические токены, которые остаются как были.

---

## Зависимости

- **Блокируется:** ничем. T-7-001 заблокирован SVG-логотипом, но эта задача (T-7-002) от логотипа не зависит — она про цвета и шрифты.
- **Блокирует:** все остальные frontend задачи Phase 7 (любая новая страница должна стартовать на v2 токенах).

### Шрифты — TT Travels ✅ получен, Biform ⏳ ждём

**TT Travels** (2026-05-17) лежит в `frontend/public/fonts/tt-travels/` — полное семейство 11 весов в WOFF + TTF (~3 MB). Подключить через `@font-face` по образцу из [`brand-guidelines-supersymmetria.md` раздел 3](../../07-frontend/brand-guidelines-supersymmetria.md#3-шрифты).

**Действия:**
1. Создать `frontend/src/app/styles/fonts.css` с `@font-face` блоками для Regular/Medium/Bold (минимум). Остальные веса — по мере необходимости.
2. **Сконвертировать WOFF → WOFF2** через `woff2_compress` или `fonttools` — даёт ~30% экономии трафика. Этот шаг — в `T-7-002`, не follow-up.
3. **Обновить `.gitignore`:** TTF/EOT/WOFF можем держать в репо (3 MB total, лицензировано). WOFF2 после генерации — commit.

**Biform Regular** ещё не получен — `--font-body` временно ссылается на `"TT Travels"` (с fallback на `system-ui`). После получения Biform — отдельный mini-PR `T-7-002-followup-biform`.

**Расхождение с гайдбуком:** владелец прислал `TT Travels`, а в гайдбуке указано `TT Travels Text` (родственный, но не идентичный — обычно более узкие литеры). На практике для UI разница не критична. Зафиксировано в `brand-guidelines-supersymmetria.md`.

### Логотип ✅ получен

SVG лежит в `frontend/public/logo-supersymmetria.svg` (600×300, `fill="currentColor"` — управляется CSS-свойством `color`). Подключение в `<Header>` — через inline-SVG-импорт (например `vite-plugin-svgr`), чтобы `color: var(--fg-0)` работал в обеих темах. См. `brand-guidelines` раздел «Логотип — получен».

Если `vite-plugin-svgr` не подключён — добавить в эту задачу:

```bash
npm i -D vite-plugin-svgr
```

И в `vite.config.ts`:

```ts
import svgr from "vite-plugin-svgr"
export default defineConfig({ plugins: [react(), svgr()] })
```

---

## Что нужно сделать

### Шаг 1. Заменить `frontend/src/app/styles/tokens.css`

Содержимое — точно из `brand-palette-supersymmetria.md`, секции «Light theme» и «Dark theme». Без изменений значений.

Структура:

```css
:root {
  /* Light theme — default */
  --bg-0: #fafcff;
  --bg-1: #e1e5ea;
  /* ... все из brand-palette light */
}

[data-theme="dark"] {
  --bg-0: #040f1d;
  /* ... все из brand-palette dark */
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --bg-0: #040f1d;
    /* ... повтор dark — для юзеров, которые не выбрали тему явно */
  }
}
```

### Шаг 2. Проверить `tailwind.config.js`

Он уже использует CSS vars (`bg-bg-0`, `text-fg-0`, …) — это правильно. Просто убедиться, что **все** новые токены добавлены в Tailwind theme. Если в коде есть классы типа `bg-accent-0`, `border-border-1` — они должны существовать.

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      'bg-0': 'var(--bg-0)',
      'bg-1': 'var(--bg-1)',
      'bg-2': 'var(--bg-2)',
      'fg-0': 'var(--fg-0)',
      'fg-1': 'var(--fg-1)',
      'fg-mute': 'var(--fg-mute)',
      'accent-0': 'var(--accent-0)',
      'accent-1': 'var(--accent-1)',
      'accent-2': 'var(--accent-2)',
      'border-0': 'var(--border-0)',
      'border-1': 'var(--border-1)',
      'danger': 'var(--danger)',
      'warning': 'var(--warning)',
      'success': 'var(--success)',
      'info': 'var(--info)',
    }
  }
}
```

### Шаг 3. Theme toggle компонент

`frontend/src/shared/ui/ThemeToggle.tsx`:

```tsx
import { useEffect, useState } from "react"

type Theme = "light" | "dark" | "system"

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("theme") as Theme) ?? "system"
  )

  useEffect(() => {
    const root = document.documentElement
    if (theme === "system") {
      root.removeAttribute("data-theme")
    } else {
      root.setAttribute("data-theme", theme)
    }
    localStorage.setItem("theme", theme)
  }, [theme])

  return [theme, setTheme]
}

export function ThemeToggle() {
  const [theme, setTheme] = useTheme()
  return (
    <button
      aria-label="Сменить тему"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="rounded p-2 hover:bg-bg-1"
    >
      {theme === "dark" ? "🌙" : "☀️"}
    </button>
  )
}
```

Подключить в `Header` рядом с SSE-индикатором.

В `frontend/src/pages/profile/ProfilePage.tsx` (или аналог) — добавить radio-group с тремя вариантами: «Светлая / Тёмная / Системная».

### Шаг 4. Audit существующих компонентов

```bash
grep -rln "background:\s*'\|color:\s*'\|#[0-9a-fA-F]" frontend/src/ --include='*.{ts,tsx,css}'
```

Все inline `style={{ background: '#xxx' }}` и hardcoded hex в компонентах — заменить на Tailwind class (`bg-bg-0`, `text-fg-0`) или CSS var (`background: var(--bg-0)`). Это уже отмечалось архитектором в `architect-review-after-hotfixes.md` пункт 5.

**Исключения** — где hex остаётся:
- `condition.color` из API (это данные).
- Семантические `danger`/`warning`/`success` через CSS vars.

### Шаг 5. Проверка WCAG контраста

Прогнать через axe DevTools (или вручную через https://webaim.org/resources/contrastchecker/) ключевые состояния:

- Светлая: `--fg-0` на `--bg-0`, `--fg-1` на `--bg-1`, `--accent-0` на `--bg-0`.
- Тёмная: то же самое.
- Любая текстовка на `--accent-0` (yellow buttons) — там лучше всего `--fg-0` (тёмный текст на жёлтом).

В отчёте — таблица «селектор → контраст ratio → AA/AAA pass». Если где-то fail — это блокер задачи, нужно поднять архитектору, не подгонять цвета.

### Шаг 6. Snapshot-тесты

Если есть `vitest` + `@testing-library/react` — добавить smoke-тест:

```tsx
test("ThemeToggle переключает data-theme на html", async () => {
  render(<ThemeToggle />)
  expect(document.documentElement.getAttribute("data-theme")).toBe(null)
  await userEvent.click(screen.getByRole("button", { name: /смени/i }))
  expect(document.documentElement.getAttribute("data-theme")).toBe("dark")
})
```

---

## Критерии приёмки

- [ ] `tokens.css` v2 содержит точно палитру из `brand-palette-supersymmetria.md`.
- [ ] `tailwind.config.js` экспонирует все новые токены как classes.
- [ ] `ThemeToggle` компонент работает: toggle меняет `<html data-theme>`, persist в `localStorage`.
- [ ] В `Header` есть кнопка toggle, в `Profile` — radio-group из 3 опций.
- [ ] `prefers-color-scheme` респектируется по умолчанию.
- [ ] Все inline-hex в компонентах заменены на токены (audit прошёл).
- [ ] WCAG ratio таблица в отчёте, все основные пары проходят AA минимум.
- [ ] `vitest` snapshot тест на toggle.
- [ ] Manual smoke: `npm run dev`, открыть login → menu → display view в обеих темах. Скриншоты или описание в отчёте.
- [ ] Отчёт `08-reports/T-7-002.md`.

---

## Что НЕ делать

- Не менять цвета `Condition` в БД. Это владельца business data.
- Не менять semantic `danger`/`warning`/`success` ID — только их **значения** в обеих темах.
- Не делать auto-detect времени суток для смены темы — пользователь выбирает явно или через OS.
- Не добавлять более 2 тем (high-contrast, sepia, etc.) — это overengineering, пока только 2 + system.

---

## Вопросы для архитектора

- [ ] Где в существующем UI hardcoded цвета? — Кодер найдёт `grep`'ом, решение по каждому — token.
- [ ] Если компонент visually ломается в dark — фикс в этой задаче или follow-up? — **Ответ:** если фикс мелкий (изменить class на токен) — здесь. Если требует редизайна компонента — follow-up `T-7-002-followup-<component>`.

---

## Отчёт по выполнению

(Заполняет кодер.)
