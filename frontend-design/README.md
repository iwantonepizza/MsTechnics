# frontend-design/ — эталонные макеты

Здесь лежат **одобренные архитектором** эталонные макеты от Claude Design (v2).
Это не прод-код SPA — это **референс**, с которого кодер строит реальный React-проект.

## Что здесь

| Файл | Что |
|---|---|
| `MsTechnics_Screens.html` | Точка входа. Открыть в браузере. |
| `tokens.css` | Дизайн-токены: цвета, типографика, плотность, скелетоны. Источник правды визуального языка. |
| `Visual_Language.html` | Дока визуального языка (палитра, типография, компоненты). |
| `design-canvas.jsx` | Фреймовая обвязка (артборды, разметка). |
| `icons.jsx` | SVG-иконки (lucide-style). Минимальный набор для прототипа. |
| `header.jsx` | Компонент Header (навигация + поиск + user-chip). |
| `screen-display-view.jsx` | **Эталон #1.** Display View — рабочее окно сервисника. |
| `screen-main-menu.jsx` | **Эталон #2.** Main Menu — операционный дашборд смены. |

## Статус ревью (архитектор)

- Display View v2 — ✅ **Принят** после 4 правок (адаптивная сетка, chip CSS-vars, 3-строчный clamp + popover, кликабельный timeline)
- Main Menu v2 — ✅ **Принят**. Hero убран, KPI-строка с 4 метриками, 4 колонки департаментов, стоки в ЗИП, шорткат-бар снизу
- `tokens.css` v2 — ✅ **Принят**. OKLCH + hex-fallback, 3 уровня плотности (compact/comfortable/touch) с media-query auto-switch, skeleton-класс, popover-стили
- `header.jsx` — ✅ **Принят**. Навигация с активным отделом, счётчиками, крошками, SSE-индикатором, user-chip

## Следующие экраны (порядок утверждён)

Claude Design делает в этом порядке:

1. **Display View / Мониторинг** — вариация эталона. Кнопки: создать заявку (🆕), отметить проблему
2. **Display View / Контроль** — вариация эталона. Вкладки: Запросы, Принятые, В сервисе, Выполненные
3. **Department List** — `/monitoring`, `/control`, `/service` — карточки городов + списки экранов
4. **ZIP Overview** — `/zip`, `/zip/:display` — 4 колонки панелей + фильтры + история
5. **Модалки transition** — confirm действий с optimistic feedback

## Как использовать этот референс

**Backend (GPT-кодер):**
Не трогает. Использует `ai-docs/07-frontend/api-contract.md` как источник правды для REST.

**Frontend-кодер (когда начнётся Фаза 4):**
1. Поднимает React + Vite + TS по `ai-docs/07-frontend/design-brief.md`
2. Копирует `tokens.css` в проект как `src/app/styles/tokens.css`
3. Конвертирует JSX-эталоны в React-компоненты:
   - `header.jsx` → `src/widgets/Header/Header.tsx`
   - `screen-display-view.jsx` → `src/pages/DisplayViewPage` + `src/widgets/*` (декомпозировать!)
   - `screen-main-menu.jsx` → `src/pages/MainMenuPage`
4. Иконки — **не копировать** `icons.jsx`, поставить `lucide-react` npm-пакет
5. Моки данных (seed-объекты) — заменить на TanStack Query хуки из `src/shared/api`
6. CSS-in-JSX через `<style>` — перенести в Tailwind классы (задача декомпозиции — сделать 1:1, но через Tailwind)

## Правила работы с дизайном

1. **`tokens.css` — неприкосновенен.** Значения меняются только через PR с обоснованием + утверждение архитектора.
2. **Добавление токена > изменение.** Если нужен новый цвет/размер — добавь, не переопределяй существующий.
3. **Не тащи hex-коды в JSX.** Всё через `var(--token)` или props из БД (`--chip-bg`, `--chip-fg`).
4. **Не добавляй эмодзи.** Иконки только через `lucide-react`. Эмодзи в UI допустимы только как данные из БД (`Condition.icon`).
5. **Плотность через `data-density`.** Для планшета сервисника — `data-density="touch"` на корне.

## Что делает `tokens.css` специально хорошо

- **OKLCH** → равномерная яркость между семантическими цветами
- **@supports not(oklch)** → fallback в hex для Android-браузеров
- **3 уровня плотности** — переключение по атрибуту + автоматически на touch-девайсах
- **Inter stylistic sets** (`cv11,ss03,ss01,tnum`) → цифры в таблицах не прыгают
- **Skeleton с shimmer** → готов к двухпороговой загрузке (< 300мс / > 300мс) из design-brief
- **Popover** стиль для hover-раскрытий комментариев и timeline

## Что спрашивать у Claude Design при следующей итерации

- «Покажи компонент X в Storybook story с состояниями: default / hover / active / disabled / loading / empty / error»
- «Декомпозируй widget на features и entities — напиши файловую структуру»
- «Как ведёт себя {экран} на 1366px ширине — что свернётся первым»
- «Что видит пользователь без доступа к отделу на этом экране»

## Что НЕ спрашивать

- «Сделай ещё 3 варианта» — нет, он должен рекомендовать один
- «Нарисуй админку SPA» — нет, админка остаётся на Django
- «Сделай светлую тему» — нет, пока только dark
- «Сделай мобильную версию < 768px» — нет, mobile не поддерживается

---

## Открыть эталон

```bash
cd frontend-design/
python3 -m http.server 8080
# открой http://localhost:8080/MsTechnics_Screens.html
```

Или просто дважды кликнуть `MsTechnics_Screens.html` — Chrome откроет, зальёт React+Babel с CDN, отрендерит. На современных браузерах работает сразу.
