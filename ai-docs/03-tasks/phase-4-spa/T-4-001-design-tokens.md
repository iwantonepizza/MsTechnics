# T-4-001. Интеграция дизайн-токенов из `frontend-design/`

> **Тип:** integration / styles
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 4
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Цель

Перенести `frontend-design/tokens.css` (одобренные эталоны Claude Design v2) в `frontend/src/app/styles/tokens.css` и подключить к Tailwind. Без этого фронт визуально расходится с дизайном.

---

## Что есть

`frontend-design/tokens.css` (9 KB) содержит:
- OKLCH-based палитра (`--bg-0..4`, `--fg`, `--accent`, `--ok/warn/err/info`)
- `@supports not (color: oklch(...))` — hex-fallback для Android-браузеров
- 3 уровня плотности: `[data-density="compact|comfortable|touch"]` + auto-switch на coarse pointer
- Inter + JetBrains Mono с `font-feature-settings`
- Skeleton/shimmer/popover классы
- Размеры: `--h-row: 28px`, `--h-btn-md: 26px`, `--h-header: 44px`

---

## Зависимости

- **Блокируется:** ничего, можно делать первой
- **Блокирует:** T-4-010..016 (все экраны)

---

## Что сделать

### Шаг 1. Скопировать tokens.css

```bash
mkdir -p frontend/src/app/styles
cp frontend-design/tokens.css frontend/src/app/styles/tokens.css
```

### Шаг 2. Подключить в `main.tsx`

```ts
// frontend/src/main.tsx
import './app/styles/tokens.css'  // ПЕРВОЙ строкой, до всего остального
import './app/styles/index.css'   // Tailwind directives
```

### Шаг 3. Tailwind config — мостик

`frontend/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',  // не используем — у нас всегда dark
  theme: {
    extend: {
      colors: {
        bg: {
          0: 'var(--bg-0)', 1: 'var(--bg-1)', 2: 'var(--bg-2)',
          3: 'var(--bg-3)', 4: 'var(--bg-4)',
        },
        fg: {
          DEFAULT: 'var(--fg)',
          dim:   'var(--fg-dim)',
          mute:  'var(--fg-mute)',
          faint: 'var(--fg-faint)',
        },
        border: {
          DEFAULT: 'var(--border)',
          subtle:  'var(--border-subtle)',
          strong:  'var(--border-strong)',
        },
        brand: { DEFAULT: 'var(--brand)', ink: 'var(--brand-ink)' },
        accent: {
          DEFAULT: 'var(--accent)',
          hover:   'var(--accent-hover)',
          press:   'var(--accent-press)',
          faint:   'var(--accent-faint)',
          ink:     'var(--accent-ink)',
        },
        ok:    'var(--ok)',
        warn:  'var(--warn)',
        err:   'var(--err)',
        info:  'var(--info)',
      },
      fontFamily: {
        sans: 'var(--font-sans)',
        mono: 'var(--font-mono)',
      },
      spacing: {
        'header': 'var(--h-header)',
        'row':    'var(--h-row)',
        'btn-sm': 'var(--h-btn-sm)',
        'btn-md': 'var(--h-btn-md)',
        'btn-lg': 'var(--h-btn-lg)',
        'input':  'var(--h-input)',
        'hit':    'var(--hit-target)',
      },
      borderRadius: {
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
      },
      boxShadow: {
        popover: 'var(--shadow-popover)',
        modal:   'var(--shadow-modal)',
      },
    },
  },
  plugins: [],
}
```

### Шаг 4. `index.css` Tailwind setup

`frontend/src/app/styles/index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body {
    @apply bg-bg-0 text-fg font-sans;
    font-feature-settings: 'cv11', 'ss03', 'ss01', 'tnum';
    -webkit-font-smoothing: antialiased;
  }
  *, *::before, *::after { box-sizing: border-box; }
}
```

### Шаг 5. Density на root

В `App.tsx`:

```tsx
import { useEffect } from 'react'

export function App() {
  useEffect(() => {
    // Auto-detect density: touch на планшетах, comfortable на десктопе
    const isTouch = window.matchMedia('(pointer: coarse)').matches
    document.documentElement.dataset.density = isTouch ? 'touch' : 'comfortable'
  }, [])
  
  // ... routes
}
```

### Шаг 6. Удалить хардкод

Найти в `frontend/src/`:

```bash
grep -rn 'bg-zinc\|text-zinc\|bg-slate\|text-slate\|bg-gray\|text-gray\|#[0-9a-f]\{3,6\}' \
  frontend/src --include='*.tsx' --include='*.ts' | head -20
```

Заменить на токены: `bg-bg-2`, `text-fg-dim`, `border-border` и т.д.

### Шаг 7. Smoke проверка

```bash
cd frontend
pnpm dev
# Открыть localhost:5173 — все экраны выглядят как в frontend-design/MsTechnics_Screens.html
# Особенно: цвет фона, контраст, шрифт Inter, моно для ID-чипов
```

---

## Критерии приёмки

- [ ] `frontend/src/app/styles/tokens.css` существует, идентичен `frontend-design/tokens.css`
- [ ] Все цвета в Tailwind через CSS-переменные (`bg-bg-0`, `text-fg`, и т.д.)
- [ ] `data-density` автоматически выставляется на основе pointer
- [ ] Inter + JetBrains Mono подключены (через Google Fonts)
- [ ] `grep -rn 'bg-zinc\|bg-slate\|text-gray' frontend/src` — пусто
- [ ] Визуально страница display-view совпадает с `frontend-design/MsTechnics_Screens.html` (тестово сравни)

---

## Что НЕ делать

- НЕ переписывать `tokens.css` руками — копировать ровно
- НЕ убирать @supports fallback — он нужен для Android-браузеров
- НЕ удалять "data-density" режимы — они для планшетов сервисников
