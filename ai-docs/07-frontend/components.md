# Components Library

Каталог компонентов с точной ответственностью. FSD-подобная нарезка:
- `shared/ui/` — глупые, без бизнес-контекста (Button, Input, Modal, Spinner)
- `entities/` — одна доменная сущность (ApplicationCard, PanelBadge, CellSlot)
- `features/` — одна функциональная возможность (CreateApplicationForm, TransitionApplicationButton)
- `widgets/` — композиция entities + features (DisplayGrid, ApplicationsTab)
- `pages/` — страницы, собираются из widgets
- `app/` — роутинг, providers, theme

---

## shared/ui

### Button
`<Button variant="primary|secondary|danger|ghost" size="sm|md|lg" disabled loading />`

- `primary` — основной акцент (amber)
- `secondary` — нейтрал
- `danger` — красный (для «Удалить», «Невозможно»)
- `ghost` — прозрачный с ховером

### IconButton
`<IconButton icon={IconName} label="..." tooltip="..." />`
Все иконки — из `lucide-react`. Эмодзи только для отображения данных из БД (icon поле).

### Input, Textarea, Select
shadcn/ui + RHF + zod. Общий стиль.

### Modal
```tsx
<Modal open={open} onClose={...} title="...">
  <Modal.Body>...</Modal.Body>
  <Modal.Footer>
    <Button onClick={onClose} variant="ghost">Отмена</Button>
    <Button onClick={onSubmit} variant="primary">Подтвердить</Button>
  </Modal.Footer>
</Modal>
```
- Закрытие: Esc, клик по overlay, X
- Фокус-ловушка, aria-modal
- Optimistic state: `submitting` → кнопки disabled

### Tabs
```tsx
<Tabs value={activeBox} onChange={setActiveBox}>
  <Tabs.Item value="received">Запросы</Tabs.Item>
  <Tabs.Item value="at_work">В работе</Tabs.Item>
  <Tabs.Item value="complete">Выполненные</Tabs.Item>
  <Tabs.Dropdown label="Другое">
    <Tabs.Item value="archive">Архив</Tabs.Item>
    <Tabs.Item value="application_history">История</Tabs.Item>
    <Tabs.Item value="all_application">Все</Tabs.Item>
    <Tabs.Item value="unable">Невозможные</Tabs.Item>
  </Tabs.Dropdown>
</Tabs>
```
- Значение синхронизируется с URL query-param `?app_box=...`
- Каждая вкладка хранит свою сортировку в памяти (useState на уровне родителя с ключом по tab-name)

### Popover
Для hover-tooltip'ов с контентом. Использование: preview заявки при ховере на ID (задача #1), раскрытие длинного комментария (задача #2).

### Toast
`toast.success("...")`, `toast.error("...")`, `toast.info("...")`. shadcn/sonner.

### Skeleton
Для плейсхолдеров при загрузке. Должен визуально совпадать с конечной формой.

---

## entities

### ApplicationCard
`<ApplicationCard application={app} variant="full|compact" />`

- `full` — разворачивается во всех деталях, показывает историю событий через `<EventTimeline>`
- `compact` — одна строка с ID, статусом, исполнителем (для меню, свёрнутых колонок)
- ID с цветом фона из `app.status.color` (задача #1: hover → preview-popover)
- Комментарий обрезан по 3 строкам (задача #2), на hover — полный текст в popover

### PanelBadge
`<PanelBadge panel={p} size="sm|md" onClick={...} />`
- Тултип: модель, ID, состояние, комментарий
- Цвет фона — `panel.application_status.color.hex`
- Иконка — `panel.condition.icon`

### CellSlot
`<CellSlot cell={c} selected={bool} onClick={...} />`
- Показывает: номер слота, цвет панели, иконку состояния
- Hover: блок с ID панели (как сейчас в `.panel_id_hover_block`)
- Selected: выделение рамкой

### StatusPill
`<StatusPill status={s} />` — для ApplicationStatus, Condition, Department. Универсальный.

### UserChip
`<UserChip user={u} />` — имя + мелкий индикатор «онлайн/офлайн» (по `last_activity`).

### ConditionSelector
`<ConditionSelector value={c} onChange={...} allowedTransitions={[...]} />`
- Dropdown с возможными состояниями (задача #5: inline смена состояния)

### ColorSwatch
`<ColorSwatch color={c} editable={bool} />` — квадратик цвета, hover — hex в tooltip.

---

## features

### CreateApplicationFeature
`<CreateApplicationButton panelId={id} />` + модалка + форма.

- Проверка: только если `panel.condition == problem && no active application`
- Поля: комментарий (required), файл (опционально)
- submit → optimistic: добавить заявку в список, закрыть модалку, показать toast «Заявка создана»

### TransitionApplicationFeature
`<TransitionButton application={a} target="apply_in_control" />` + модалка.

- Поля формы зависят от `target`:
  - `apply_in_control` / `sent_to_service` / `work_in_service` → комментарий опционально
  - `unable` → комментарий **обязательно**
  - `done` → комментарий + файл-фото опционально
- Успех: SSE → сервер пушнёт всем клиентам invalidate → списки обновятся

### ChangePanelConditionFeature
Dropdown + модалка подтверждения (для monitoring это одна кнопка, для service — полный dropdown с запрещёнными transitions — серые).

### MovePanelFeature
Инкапсулирует `remove-from-cell`, `assign-to-cell`, `change-department`.
- `remove-from-cell` → dropdown: в какое состояние перевести панель
- `assign-to-cell` → dropdown свободных панелей
- `change-department` → 3 варианта (service/zip/hand) с блокировкой если есть активная заявка (задача #8)

### CommentInlineEditFeature
`<InlineEditableComment value={v} onSave={s} />` для `panel.comment`. Клик → input, Enter или `✔` → сохранение.

### ApplicationHistoryFeature (задача владельца #3)
Кнопка-глазик на карточке заявки → модалка с `<EventTimeline>` всей истории заявки.

### OpenApplicationFromLogFeature (задача владельца #11)
В `<ActivityLog>` клик по строке связанной с заявкой → открывает `<ApplicationDetailModal>`.

---

## widgets

### Header
Навигация по отделам, profile-меню, toast-container, SSE-status-indicator.

### DisplayGrid
Сетка ячеек с CSS Grid, параметризованная `rows/cols`. Внутри — `<CellSlot>`.

### PanelInfoPanel
Правая панель на Display View: панель, действия, состояние, комментарий, заявки панели.

### HistoryBlock
Два столбца: история места + история панели. Заголовок кликабельный для добавления нового комментария.

### ApplicationsTab
Вкладки + список заявок текущей вкладки с сортировкой и пагинацией.

### DashboardBlock
Одна колонка дашборда: заголовок отдела, свёрнутые карточки, ссылка «Перейти».

### ZipOverviewGrid
4 колонки с плитками панелей. Фильтры сверху (экран, состояние).

### DisplayListByCity
Список городов, у каждого — список экранов с действиями.

---

## pages

Каждый — тонкий слой: собирает widgets, передаёт props, управляет URL state.

- `LoginPage`
- `MenuPage`
- `DepartmentListPage` — один на три отдела с параметром
- `DisplayViewPage` — один для monitoring / control / service
- `ZipOverviewPage`
- `ZipDisplayPage`
- `ProfilePage`
- `NotFoundPage`

---

## Stories / Playwright

Каждый компонент `features/` и `widgets/` — минимум одна Storybook story + 1 happy-path e2e-тест в Playwright.

Для `entities/` — Storybook по всем вариациям (compact, full, loading, error).

---

## Темизация

Одна тема — тёмная. Переключения на светлую пока нет. Цвета определены в `app/styles/theme.css` через CSS-переменные:
```css
:root {
  --bg-primary: #18181b;
  --bg-secondary: #27272a;
  --accent: #fbbf24;
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --border: #3f3f46;
}
```
Tailwind мапит эти переменные.

---

## Типы

Все типы ответов API — сгенерированы из OpenAPI-схемы (см. `ai-docs/06-integrations/openapi-generation.md`). Ничего не пишем руками. Команда: `pnpm generate:api-types`.
