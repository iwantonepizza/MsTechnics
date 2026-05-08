# Frontend Review Checklist

---

## Архитектура

- [ ] FSD-структура соблюдена: `app/` → `pages/` → `widgets/` → `features/` → `entities/` → `shared/`
- [ ] Слои не лезут вверх (shared не импортит pages)
- [ ] Pages — тонкие: собирают widgets, управляют URL state
- [ ] Бизнес-логика — в features, не в widgets
- [ ] Shared/ui — без бизнес-контекста

## TypeScript

- [ ] `strict: true` работает, нет `any`
- [ ] Нет `as unknown as X` без комментария
- [ ] Нет `@ts-ignore` без tracker-link
- [ ] Типы API взяты из generated (`@/shared/api/types`)
- [ ] Exports именованные (кроме страниц и widgets — default)

## React

- [ ] Function components, не class
- [ ] Хуки соблюдают Rules of Hooks
- [ ] `useCallback` / `useMemo` только там где реально нужно (не на каждый props)
- [ ] Нет `useEffect` для data-fetching — только через `useQuery`
- [ ] Нет `key={index}` в динамических списках
- [ ] Нет inline-функций в часто-перерендериваемых props
- [ ] Списки с виртуализацией (`react-virtual`), если > 100 элементов

## TanStack Query

- [ ] QueryKey структурирован: `['resource', filters]`, не `['resource-' + id]`
- [ ] На мутации — `invalidateQueries` или `setQueryData`
- [ ] Есть обработка error / loading state
- [ ] `staleTime` и `gcTime` явно указаны для ресурсоёмких запросов

## State

- [ ] Server state — **только** TanStack Query
- [ ] Клиентский global state — Zustand, но **минимум** (большинство state можно локально)
- [ ] URL state (фильтры, selected, tab) — через `useSearchParams`
- [ ] Нет useState для того, что лежит на сервере

## Формы

- [ ] React Hook Form
- [ ] Валидация — zod-схема, не просто `required`
- [ ] Disabled-state на submit при `isSubmitting`
- [ ] Ошибки сервера отображаются в полях (через `setError`)

## UI / UX

- [ ] Skeleton есть при первой загрузке
- [ ] Empty-state с контекстом, не «Ничего нет»
- [ ] Error-state с retry
- [ ] Optimistic updates там, где UX выигрывает
- [ ] Mobile < 768 — показывает fallback-экран

## Стили

- [ ] Tailwind, без inline-style (кроме динамических, от БД цветов)
- [ ] Нет хардкоженных цветов — только переменные темы
- [ ] Dark-theme — все цвета имеют контраст AA+
- [ ] Keyboard navigation: focus-visible, tab-order, Enter=submit

## Accessibility

- [ ] Все интерактивные элементы — `<button>` / `<a>`, не `<div onClick>`
- [ ] `aria-label` на иконках без текста
- [ ] Модалки — focus-trap, `aria-modal`
- [ ] Формы — `<label for>` или wrapping label
- [ ] Контраст текста проверен (dev-tools)

## Тесты

- [ ] Компонент с логикой — unit-тест (Vitest + RTL)
- [ ] Stories в Storybook для entities и widgets
- [ ] Happy-path e2e (Playwright) для ключевых потоков
- [ ] MSW для mock-HTTP в тестах

## Производительность

- [ ] Bundle size не вырос > 5% без обоснования
- [ ] Code-splitting для больших страниц (React.lazy)
- [ ] Изображения оптимизированы (WebP, размеры)
- [ ] Нет утечек в useEffect (cleanup есть)

## API

- [ ] Все HTTP — через единый api-client, не голый fetch
- [ ] 401 — refresh flow отрабатывает
- [ ] 403 — toast + не молчим
- [ ] 5xx — retry + toast
- [ ] Offline — баннер

## Документация

- [ ] Storybook stories покрывают варианты компонента
- [ ] README в папке feature/widget, если нетривиально
- [ ] Если поменялся API — согласован с бэком через `api-contract.md`

## Review-gotchas

- «Показываю модалку через `alert()`» — отклоняю
- Кнопка без `type="button"` внутри формы → submit — отклоняю
- `localStorage` для токенов — отклоняю
- `window.location.href` вместо `navigate()` — отклоняю
- Магические строки статусов — в enum
