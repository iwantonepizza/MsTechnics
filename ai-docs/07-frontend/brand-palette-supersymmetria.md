# Brand palette — «Суперсимметрия»

Брендбук владельца, раунд 2026-05-13. Эта палитра — **источник истины** для `tokens.css` (T-7-002 заменит старый `tokens.css` под этот брендинг).

---

## Основные цвета (используется большая часть площади)

| Имя | Hex | RGB | CMYK | Pantone | Назначение |
|---|---|---|---|---|---|
| **Призрачно белый** | `#fafcff` | 250, 252, 255 | 1, 0, 0, 0 | 11-0601 TCX | основной фон (light theme) |
| **Платина** | `#e1e5ea` | 225, 229, 234 | 10, 6, 4, 92 | 649 C | вторичный фон / divider / hover |
| **Серебро** | `#b8bfc6` | 186, 191, 198 | 27, 19, 16, 0 | 14-4309 TCX | приглушённый текст, иконки |
| **Ночное небо** | `#040f1d` | 4, 15, 29 | 84, 74, 58, 77 | Black 6C | основной фон (dark theme) |
| **Ночная дымка** | `#3c4856` | 60, 72, 86 | 30, 16, 0, 66 | 432 | вторичный фон dark / hover dark |

## Акцентные цвета (используются редко, для выделения)

| Имя | Hex | RGB | CMYK | Pantone | Назначение |
|---|---|---|---|---|---|
| **Солнечный луч** | `#ffea00` | 255, 234, 0 | 0, 8, 100, 0 | 102 | primary action, brand accent |
| **Ночное окно** | `#fdd734` | 253, 215, 52 | 2, 13, 89, 0 | 610 C | secondary accent, hover на primary |
| **Закат** | `#fdb734` | 253, 183, 52 | 0, 28, 79, 1 | 2010 | warning state, alert, attention |

> Акцентные цвета **не используются в больших заливках**. Они — точечные акценты.

---

## Что НЕ заменяется

- **Цвета состояний панелей** (`Condition.color`) — остаются как есть в БД. Это рабочие данные владельца, их не трогаем.
- **Семантические предупреждения** — красный и жёлтый для «низкий остаток ЗИП», «ошибка SSE», «панель невосстановима» — остаются. Они вне брендинговой палитры.

---

## Mapping в design tokens (`tokens.css`)

### Light theme

```css
:root {
  /* Surfaces */
  --bg-0: #fafcff;    /* main background — Призрачно белый */
  --bg-1: #e1e5ea;    /* secondary surface — Платина */
  --bg-2: #b8bfc6;    /* tertiary — Серебро */

  /* Text */
  --fg-0: #040f1d;    /* primary text — Ночное небо */
  --fg-1: #3c4856;    /* secondary text — Ночная дымка */
  --fg-mute: #b8bfc6; /* placeholder, disabled */

  /* Accent (brand) */
  --accent-0: #ffea00;  /* primary — Солнечный луч */
  --accent-1: #fdd734;  /* hover — Ночное окно */
  --accent-2: #fdb734;  /* warning attention — Закат */

  /* Semantic (не трогаем, как в текущем tokens.css) */
  --danger: #e23a3a;
  --warning: #ffb020;
  --success: #2eaa67;
  --info: #3a8fe2;

  /* Borders / dividers */
  --border-0: #e1e5ea;
  --border-1: #b8bfc6;
}
```

### Dark theme (новое требование A3)

```css
[data-theme="dark"] {
  /* Surfaces — инвертированы */
  --bg-0: #040f1d;    /* Ночное небо */
  --bg-1: #3c4856;    /* Ночная дымка */
  --bg-2: #b8bfc6;    /* Серебро как третичный */

  /* Text — инвертированы */
  --fg-0: #fafcff;    /* Призрачно белый */
  --fg-1: #e1e5ea;    /* Платина */
  --fg-mute: #b8bfc6; /* Серебро */

  /* Accent — те же (брендовые) */
  --accent-0: #ffea00;
  --accent-1: #fdd734;
  --accent-2: #fdb734;

  /* Semantic — чуть приглушены под dark, но узнаваемы */
  --danger: #ff5b5b;
  --warning: #ffc14d;
  --success: #4fd095;
  --info: #5ba8ff;

  /* Borders / dividers */
  --border-0: #3c4856;
  --border-1: #b8bfc6;
}
```

### Theme switching

```css
/* Default — system */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    /* применить dark переменные */
  }
}
```

JS toggle: `document.documentElement.setAttribute('data-theme', 'light' | 'dark')`, persist в `localStorage.theme`.

---

## Контрастность (WCAG)

Проверь при имплементации T-7-002 через https://webaim.org/resources/contrastchecker/:

- `#040f1d` на `#fafcff` → contrast ratio ~17:1 — **AAA** ✓
- `#3c4856` на `#e1e5ea` → ~9.3:1 — **AAA** ✓
- `#fafcff` на `#040f1d` → 17:1 — **AAA** ✓
- `#ffea00` на `#040f1d` → 16:1 — **AAA** ✓ (текст по brand background)
- `#040f1d` на `#ffea00` → 16:1 — **AAA** ✓ (текст на brand button)
- `#b8bfc6` на `#fafcff` → 1.7:1 — **fail** для основного текста; только для placeholder / disabled.

Если где-то contrast fail при имплементации — поднять архитектору, не подгоняй цвета руками.

---

## Логотип

`frontend/public/logo-supersymmetria.svg` (TBD — владелец прислал PNG, дизайнер векторизует).

Применение:
- Login page — крупный, по центру.
- Header — мелкая иконка слева + «Суперсимметрия» текстом.
- Favicon — 32×32 / 16×16.
- PWA manifest icons — 192×192, 512×512.

`<title>` тегов и meta-description тоже обновить: «Суперсимметрия — система управления экранами».
