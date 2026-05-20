# Polish — Round-3 экраны и Phase 7 компоненты

> **Дата:** 2026-05-19
> **Зоны:** B (5 экранов Round-3) + C (review 6 компонентов Phase 7).
> **Зависимости:** ссылается на пункты из `design-audit-2026-05-19.md` (S-001…S-012, L-001…, etc.). Не дублирует — только дельта.
>
> **Формат патча:** `[файл:строка]` + diff-блок. Если правка большая или новый файл — приведён полный фрагмент.

---

## B.1 — DepartmentList (`/monitoring`, `/control`, `/service`)

**Самое важное:** S-006 / DL-001 — sort + filter + quick-links **не работают в проде**. Кодер реализовал их в `DepartmentPage.tsx`, а маршрутизация ведёт на `DepartmentListPage.tsx`. Полировка зоны B.1 = **слияние двух файлов**, а не косметика.

### Патч 1 — переехать sort+filter+quick-links в живой `DepartmentListPage`

Структуру эталона Round-3 сохраняем (left main + right SideRail 320px). Toolbar с сортировкой и поиском вставляем **в sticky header main-колонки**, рядом с заголовком/счётчиком. Quick-links вшиваются в `DisplayRow`.

`pages/department/DepartmentListPage.tsx`:

```diff
@@ imports
- import { AlertTriangle, ArrowRight, Clock, MapPin, Monitor } from 'lucide-react'
+ import {
+   Activity, AlertTriangle, ArrowRight, ArrowUpDown, ClipboardList,
+   Clock, MapPin, Monitor, Package, Search,
+ } from 'lucide-react'

+ type SortOption = 'name-asc' | 'name-desc' | 'size-desc' | 'size-asc'
+ const SORT_LABELS: Record<SortOption, string> = {
+   'name-asc':  'По названию (А-Я)',
+   'name-desc': 'По названию (Я-А)',
+   'size-desc': 'По размеру (большие выше)',
+   'size-asc':  'По размеру (малые выше)',
+ }
+ const SORT_STORAGE_KEY = 'department.displaySort'
+ const CITY_THRESHOLD_FOR_FILTER = 3
+
+ function readPersistedSort(): SortOption {
+   try {
+     const raw = sessionStorage.getItem(SORT_STORAGE_KEY)
+     if (raw && raw in SORT_LABELS) return raw as SortOption
+   } catch {}
+   return 'name-asc'
+ }
+ function persistSort(v: SortOption) {
+   try { sessionStorage.setItem(SORT_STORAGE_KEY, v) } catch {}
+ }
```

`DisplayRow` — расширяем quick-links:

```diff
function DisplayRow({ display, department }: { display: DisplayListItem; department: Dept }) {
  return (
-   <Link
-     to={`/${department}/${display.city.slug}/${display.slug}`}
-     className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-md border px-3 py-2.5 transition-colors hover:bg-bg-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
-     style={{
-       background: 'var(--bg-2)',
-       borderColor: 'var(--border-subtle)',
-       outlineColor: 'var(--accent)',
-     }}
-   >
-     ...
-   </Link>
+   <div
+     className="grid grid-cols-[1fr_auto] items-start gap-3 rounded-md border px-3 py-2.5 transition-colors hover:bg-bg-3 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2"
+     style={{
+       background: 'var(--bg-1)',           // S-004
+       borderColor: 'var(--border-subtle)',
+       outlineColor: 'var(--accent)',
+     }}
+   >
+     <Link
+       to={`/${department}/${display.city.slug}/${display.slug}`}
+       className="min-w-0 focus:outline-none"
+       data-testid={`display-card-${display.slug}`}
+     >
+       <div className="flex items-center gap-2">
+         <Monitor size={13} style={{ color: 'var(--fg-mute)' }} />
+         <span className="truncate text-sm font-medium" style={{ color: 'var(--fg)' }}>
+           {display.description ?? display.name}
+         </span>
+       </div>
+       <div className="mt-1 flex items-center gap-2 text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
+         <span>{display.rows}×{display.cols}</span>
+         <span style={{ color: 'var(--border)' }}>·</span>
+         <span>{display.name}</span>
+       </div>
+       <div className="mt-2 flex items-center gap-3 text-2xs" style={{ color: 'var(--fg-faint)' }}>
+         <span className="inline-flex items-center gap-1 hover:text-fg-dim" title="ЗИП экрана">
+           <Link to={`/zip/${display.slug}`} className="inline-flex items-center gap-1">
+             <Package size={11} /> ЗИП
+           </Link>
+         </span>
+         <span className="inline-flex items-center gap-1 hover:text-fg-dim" title="Все заявки">
+           <Link to={`/control/${display.city.slug}/${display.slug}`} className="inline-flex items-center gap-1">
+             <ClipboardList size={11} /> Заявки
+           </Link>
+         </span>
+         <span className="inline-flex items-center gap-1 hover:text-fg-dim" title="История">
+           <Link to={`/${department}/${display.city.slug}/${display.slug}?tab=history`} className="inline-flex items-center gap-1">
+             <Activity size={11} /> История
+           </Link>
+         </span>
+       </div>
+     </Link>
+     <ArrowRight size={13} style={{ color: 'var(--fg-faint)', alignSelf: 'center' }} />
+   </div>
  )
}
```

**Note:** quick-links — это вложенные `<Link>`. Браузер не поддерживает вложенные `<a>` спецификацией. Делаем outer карточкой `<div>` с focus-within outline, основной клик-target — отдельный `<Link>`, quick-links — отдельные `<Link>`. Это правильный паттерн (тот же что в Round-3).

Toolbar в шапке main-колонки + хук с сортировкой/фильтром:

```diff
export function DepartmentListPage({ department }: { department: Dept }) {
  const { citySlug } = useParams<{ citySlug?: string }>()
  const { setCrumb } = useCrumb()
  const { data: cities = [], isLoading: citiesLoading, error: citiesError } = useCities()
  const { data: displays = [], isLoading: displaysLoading, error: displaysError, refetch } = useDisplays()
  const [activeCity, setActiveCity] = useState<string | null>(citySlug ?? null)
+ const [sortBy, setSortBy] = useState<SortOption>(readPersistedSort)
+ const [cityQuery, setCityQuery] = useState('')

  const config = DEPT_CONFIG[department]
  ...

- const groups = useMemo(() => {
-   const filteredDisplays = displays.filter(display => !citySlug || display.city.slug === citySlug)
-   return groupDisplays(filteredDisplays, cities)
- }, [cities, citySlug, displays])
+ const groups = useMemo(() => {
+   const byCity = displays.filter(d => !citySlug || d.city.slug === citySlug)
+   const grouped = groupDisplays(byCity, cities)
+   // city filter
+   const q = cityQuery.trim().toLowerCase()
+   const filtered = q ? grouped.filter(g => g.city.name.toLowerCase().includes(q)) : grouped
+   // sort
+   const cmp = (a: DisplayListItem, b: DisplayListItem) => {
+     switch (sortBy) {
+       case 'name-asc':  return (a.description ?? a.name).localeCompare(b.description ?? b.name, 'ru')
+       case 'name-desc': return (b.description ?? b.name).localeCompare(a.description ?? a.name, 'ru')
+       case 'size-desc': return b.rows * b.cols - a.rows * a.cols
+       case 'size-asc':  return a.rows * a.cols - b.rows * b.cols
+     }
+   }
+   return filtered.map(g => ({ ...g, displays: [...g.displays].sort(cmp) }))
+ }, [cities, citySlug, cityQuery, displays, sortBy])
+
+ const totalCities = new Set(displays.map(d => d.city.slug ?? d.city.name)).size
+ const showCityFilter = totalCities >= CITY_THRESHOLD_FOR_FILTER
+
+ const handleSortChange = (v: SortOption) => { setSortBy(v); persistSort(v) }
```

Заменяем sticky header'ом с toolbar справа:

```diff
- <div className="sticky top-0 z-10 flex h-13 items-center justify-between bg-bg-0 px-6" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
-   <div>
-     <h1 className="text-md font-semibold" style={{ color: 'var(--fg)' }}>{config.title}</h1>
-     <div className="mt-0.5 flex items-center gap-2 text-2xs" style={{ color: 'var(--fg-faint)' }}>
-       <Clock size={11} />
-       <span>{groups.length} городов · ...</span>
-     </div>
-   </div>
- </div>
+ <div
+   className="sticky top-0 z-10 flex flex-wrap items-end justify-between gap-3 bg-bg-0 px-6 py-3"
+   style={{ borderBottom: '1px solid var(--border-subtle)' }}
+ >
+   <div>
+     <h1 className="text-md font-semibold" style={{ color: 'var(--fg)' }}>{config.title}</h1>
+     <div className="mt-0.5 flex items-center gap-2 text-2xs" style={{ color: 'var(--fg-faint)' }}>
+       <Clock size={11} />
+       <span>{groups.length} городов · {groups.reduce((s, g) => s + g.displays.length, 0)} экранов</span>
+     </div>
+   </div>
+   <div className="flex items-center gap-2">
+     {showCityFilter && (
+       <label className="relative flex items-center" data-testid="city-filter">
+         <Search size={12} className="absolute left-2 pointer-events-none" style={{ color: 'var(--fg-mute)' }} />
+         <input
+           type="search"
+           placeholder="Город…"
+           value={cityQuery}
+           onChange={e => setCityQuery(e.target.value)}
+           className="input pl-7 w-40"  /* `.input` — см. E-section */
+         />
+       </label>
+     )}
+     <label className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--fg-mute)' }} data-testid="sort-select">
+       <ArrowUpDown size={11} />
+       <select
+         value={sortBy}
+         onChange={e => handleSortChange(e.target.value as SortOption)}
+         className="input"
+       >
+         {Object.entries(SORT_LABELS).map(([v, l]) => (
+           <option key={v} value={v}>{l}</option>
+         ))}
+       </select>
+     </label>
+   </div>
+ </div>
```

`<input className="input">` / `<select className="input">` — единая утилита из `globals.css` (см. зону E). Это убирает «нативно-серое поле формы» и приводит контролы к токенам.

### Патч 2 — DL-002 / DL-003 / DL-004

Один блок:

```diff
- {active && (
-   <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--accent)' }}>
-     activity
-   </span>
- )}
+ {/* удалено: literal-debug. Активность подсвечивается фоном CityBlock. */}
```

```diff
- <span title="Статус экрана" className="text-sm">●</span>
+ {/* DL-003: статусный bullet требует aggregated_condition в DTO. Открытый вопрос к владельцу.
+      Сейчас — убрать, оставить только ArrowRight. */}
```

```diff
- <EmptyState icon="📭" title="Пусто" className="py-10" />
+ <EmptyState icon={<Inbox size={20} />} title="Пусто" className="py-10" />

- <EmptyState icon="🏙️" title="Нет доступных экранов" description="..." />
+ <EmptyState icon={<Building2 size={20} />} title="Нет доступных экранов" description="..." />
```

`EmptyState.tsx` — расширить пропс `icon: string | React.ReactNode`. Тривиально:
```tsx
{typeof icon === 'string' ? <span>{icon}</span> : icon}
```

### Патч 3 — Удалить `pages/department/DepartmentPage.tsx` + `DepartmentPage.test.tsx`

После переезда. Тесты перенести в `DepartmentListPage.test.tsx` (создать) — sort/filter — стандартные RTL.

---

## B.2 — DisplayView (`/monitoring|/control|/service/:city/:display`)

3 роли разделяются ROLE_TRANSITIONS — это правильный паттерн. Визуально все три рендерятся через один `DisplayViewPage`. Полировка ниже не делит по ролям — она общая.

### Патч 1 — TRANSITION_LABELS без эмодзи

```diff
+ import { Check, Send, Wrench, CheckCheck, X, Archive, Trash2 } from 'lucide-react'

- const TRANSITION_LABELS: Record<TransitionKind, { emoji: string; label: string }> = {
-   apply_in_control: { emoji: '✅', label: 'Принять' },
-   sent_to_service: { emoji: '📤', label: 'В сервис' },
-   work_in_service: { emoji: '🔧', label: 'В работу' },
-   done: { emoji: '✔️', label: 'Выполнено' },
-   unable: { emoji: '❌', label: 'Невозможно' },
-   archive_done: { emoji: '📦', label: 'Архив' },
-   archive_unable: { emoji: '📦', label: 'Архив' },
-   delete_application: { emoji: '🗑️', label: 'Удалить' },
- }
+ const TRANSITION_LABELS: Record<TransitionKind, { Icon: React.ComponentType<{ size?: number }>; label: string }> = {
+   apply_in_control:   { Icon: Check,      label: 'Принять'   },
+   sent_to_service:    { Icon: Send,       label: 'В сервис'  },
+   work_in_service:    { Icon: Wrench,     label: 'В работу'  },
+   done:               { Icon: CheckCheck, label: 'Выполнено' },
+   unable:             { Icon: X,          label: 'Невозможно'},
+   archive_done:       { Icon: Archive,    label: 'Архив'     },
+   archive_unable:     { Icon: Archive,    label: 'Архив'     },
+   delete_application: { Icon: Trash2,     label: 'Удалить'   },
+ }
```

И где-то ниже, где рендерится кнопка перехода:

```diff
- <Button ...>
-   {TRANSITION_LABELS[kind].emoji} {TRANSITION_LABELS[kind].label}
- </Button>
+ <Button icon={<TRANSITION_LABELS[kind].Icon size={12} />} ...>
+   {TRANSITION_LABELS[kind].label}
+ </Button>
```

`<Button>` уже принимает `icon: React.ReactNode` — менять API не надо.

### Патч 2 — Тост успеха в TransitionModal

```diff
- toast.success(`✅ ${config.buttonLabel}`)
+ toast.success(config.buttonLabel)
```

`sonner` сам выставляет иконку при `richColors` или при кастомных стилях из зоны E.

### Патч 3 — EventTimeline (`entities/application/EventTimeline.tsx`)

```diff
- const STAGE_LABELS: Record<string, { label: string; emoji: string }> = {
-   monitoring_create:  { label: 'Создана мониторингом', emoji: '📋' },
-   control_apply:      { label: 'Принята контролем',    emoji: '✅' },
-   ...
- }
+ import { Archive, Check, CheckCheck, FilePlus, Send, Wrench, X } from 'lucide-react'
+
+ const STAGE_LABELS: Record<string, { label: string; Icon: React.ComponentType<{ size?: number }> }> = {
+   monitoring_create: { label: 'Создана мониторингом',     Icon: FilePlus   },
+   control_apply:     { label: 'Принята контролем',         Icon: Check      },
+   control_send:      { label: 'Отправлена в сервис',       Icon: Send       },
+   service_apply:     { label: 'Принята сервисом',          Icon: Wrench     },
+   service_complete:  { label: 'Ремонт выполнен',           Icon: CheckCheck },
+   service_unable:    { label: 'Ремонт невозможен',         Icon: X          },
+   archive_done:      { label: 'Архивирована',              Icon: Archive    },
+   archive_unable:    { label: 'Архивирована (невозможно)', Icon: Archive    },
+ }
```

И в JSX компонента — `<meta.Icon size={12} />` вместо `meta.emoji`.

### Патч 4 — Inline-стили (DV-002)

**Только под плановый рефакторинг**, не блокер. Один из массовых: заменить
```tsx
<span style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)' }}>
```
на
```tsx
<span className="font-mono text-fg-mute">
```
Tailwind-токены `text-fg-mute / text-fg-dim / text-fg-faint / text-fg / font-mono` ВСЕ есть в config'е. Можно сделать sed-replace.

### Патч 5 — Отличия ролей (control vs monitoring vs service)

По screens-map должны отличаться **только доступные actions** (через `ROLE_TRANSITIONS`), не visual. Текущий код это и делает — все три роли используют `DisplayViewPage` + одинаковый layout. **OK, нет правок.**

---

## B.3 — ZIP Overview (`/zip`, `/zip/:slug`)

### Патч 1 — DEPARTMENTS без эмодзи + lucide

```diff
+ import { HandMetal, Monitor, Package, Wrench } from 'lucide-react'

- const DEPARTMENTS = [
-   { key: 'zip',     label: 'ЗИП',         emoji: '📦' },
-   { key: 'hand',    label: 'На руках',     emoji: '✋' },
-   { key: 'service', label: 'Сервис',       emoji: '🔧' },
-   { key: 'monitor', label: 'На экранах',   emoji: '📺' },
- ]
+ const DEPARTMENTS: Array<{ key: string; label: string; Icon: React.ComponentType<{ size?: number }> }> = [
+   { key: 'zip',     label: 'ЗИП',         Icon: Package  },
+   { key: 'hand',    label: 'На руках',     Icon: HandMetal },
+   { key: 'service', label: 'Сервис',       Icon: Wrench   },
+   { key: 'monitor', label: 'На экранах',   Icon: Monitor  },
+ ]
```

В `<PanelColumn>` header:
```diff
- <span>{dept.emoji}</span>
+ <dept.Icon size={12} style={{ color: 'var(--fg-mute)' }} />
```

### Патч 2 — StorageSection без эмодзи

```diff
+ import { BatteryFull, Cable, Cpu, Layers, Plug } from 'lucide-react'

- { key: 'lamels',       label: '🧩 Ламели',          ... },
- { key: 'hubs',         label: '🔌 Хабы',            ... },
- { key: 'wires',        label: '🔗 Провода',         ... },
- { key: 'power-blocks', label: '🔋 Блоки питания',   ... },
- { key: 'connectors',   label: '🪛 Коннекторы',      ... },
+ { key: 'lamels',       label: 'Ламели',          Icon: Layers,      ... },
+ { key: 'hubs',         label: 'Хабы',            Icon: Cpu,         ... },
+ { key: 'wires',        label: 'Провода',         Icon: Cable,       ... },
+ { key: 'power-blocks', label: 'Блоки питания',   Icon: BatteryFull, ... },
+ { key: 'connectors',   label: 'Коннекторы',      Icon: Plug,        ... },
```

### Патч 3 — PanelChip surface

```diff
  style={{
-   background: selected ? 'var(--bg-3)' : 'var(--bg-2)',
+   background: selected ? 'var(--bg-3)' : 'var(--bg-1)',
    ...
  }}
```

### Патч 4 — DnD: not-allowed cue + source opacity (Z-002, Z-004)

```diff
function PanelChip({ panel, selected, onSelect }) {
- const handleDragStart = (e) => {
+ const handleDragStart = (e: React.DragEvent<HTMLButtonElement>) => {
    e.dataTransfer.setData(DRAG_MIME, String(panel.id))
    e.dataTransfer.setData('text/plain', panel.name)
    e.dataTransfer.effectAllowed = 'move'
+   e.currentTarget.style.opacity = '0.4'
  }
+ const handleDragEnd = (e: React.DragEvent<HTMLButtonElement>) => {
+   e.currentTarget.style.opacity = '1'
+ }
  return (
-   <button ... onDragStart={handleDragStart} ...>
+   <button ... onDragStart={handleDragStart} onDragEnd={handleDragEnd} ...>
```

PanelColumn — not-allowed feedback:
```diff
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
-   if (!isDropTarget) return
-   if (!e.dataTransfer.types.includes(DRAG_MIME)) return
-   e.preventDefault()
-   e.dataTransfer.dropEffect = 'move'
-   setDragHover(true)
+   if (!e.dataTransfer.types.includes(DRAG_MIME)) return
+   e.preventDefault()
+   e.dataTransfer.dropEffect = isDropTarget ? 'move' : 'none'
+   setDragHover(true)
  }
```

Стили колонки — два состояния:
```diff
  style={{
    borderRight: '1px solid var(--border-subtle)',
-   background: dragHover ? 'var(--accent-faint)' : undefined,
-   outline: dragHover ? '2px dashed var(--accent)' : undefined,
+   background: dragHover && isDropTarget ? 'var(--accent-faint)' : undefined,
+   outline: dragHover
+     ? (isDropTarget ? '2px dashed var(--accent)' : '2px dashed var(--fg-faint)')
+     : undefined,
    outlineOffset: '-2px',
+   cursor: dragHover && !isDropTarget ? 'not-allowed' : undefined,
  }}
```

### Патч 5 — `PanelCreateButton` inputs surface

```diff
  style={{
-   background: 'var(--bg-2)',
+   background: 'var(--bg-1)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-sm)',
    color: 'var(--fg)',
  }}
```
В 3 местах (`name input`, `display select`, `comment textarea`). Лучше — выкидываем эти inline-style и пишем `className="input"` (см. зону E).

---

## B.4 — Departures (`/departures`)

**Найденный P0 не из аудита:** `DeparturesPage.tsx` использует мёртвые классы `bg-surface-2`, `bg-surface-3`, `text-text-muted`, `text-text-primary` — те же что в MenuPage.tsx (мёртвом) и DepartmentPage.tsx (тоже мёртвом). Но **DeparturesPage активно маршрутизирован** в `App.tsx`. То есть live-страница не имеет фона/цвета карточек и кнопок фильтра в light **И** dark.

**Это блокер. Добавляю в followup-list под номером 16:** `T-7-followup-departures-tokens`.

### Патч 1 — заменить все surface-* классы

```diff
- <p className="text-sm text-text-muted mt-0.5">Управление выездными бригадами</p>
+ <p className="text-sm mt-0.5" style={{ color: 'var(--fg-mute)' }}>Управление выездными бригадами</p>
```

```diff
- <button ... className={cn(
-   'px-3 py-1 rounded-lg text-xs font-medium transition-colors',
-   status === value
-     ? 'bg-surface-3 text-text-primary'
-     : 'text-text-muted hover:text-text-primary hover:bg-surface-2',
- )}>
+ <button
+   className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
+   style={{
+     background: status === value ? 'var(--bg-3)' : 'transparent',
+     color: status === value ? 'var(--fg)' : 'var(--fg-mute)',
+   }}
+   onMouseEnter={(e) => { if (status !== value) { e.currentTarget.style.background = 'var(--bg-1)'; e.currentTarget.style.color = 'var(--fg)' } }}
+   onMouseLeave={(e) => { if (status !== value) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--fg-mute)' } }}
+ >
```

Ещё лучше — переделать как сегмент-контрол. Шаблон:

```tsx
const TABS = [
  { value: '', label: 'Все' },
  { value: 'created', label: 'Создан' },
  { value: 'completed', label: 'Выполнен' },
  { value: 'archived', label: 'Архив' },
]
// в JSX:
<div
  role="tablist"
  className="inline-flex rounded-md p-0.5"
  style={{ background: 'var(--bg-1)', border: '1px solid var(--border-subtle)' }}
>
  {TABS.map(t => (
    <button
      key={t.value}
      role="tab"
      aria-selected={status === t.value}
      onClick={() => setStatus(t.value)}
      className="px-3 py-1 text-xs font-medium rounded-sm transition-colors"
      style={{
        background: status === t.value ? 'var(--bg-0)' : 'transparent',
        color: status === t.value ? 'var(--fg)' : 'var(--fg-mute)',
        boxShadow: status === t.value ? '0 1px 2px rgba(0,0,0,0.06)' : undefined,
      }}
    >
      {t.label}
    </button>
  ))}
</div>
```

Карточки выезда:
```diff
- <div ... className="flex items-center gap-4 px-4 py-3 bg-surface-2 border border-surface-3 rounded-xl"
-   style={{
-     background: dep.id === selectedDepartureId ? 'var(--accent-faint)' : undefined,
-     borderColor: dep.id === selectedDepartureId ? 'var(--accent-edge)' : undefined,
-   }}>
+ <div ... className="flex items-center gap-4 px-4 py-3 rounded-xl border"
+   style={{
+     background: dep.id === selectedDepartureId ? 'var(--accent-faint)' : 'var(--bg-1)',
+     borderColor: dep.id === selectedDepartureId ? 'var(--accent-edge)' : 'var(--border-subtle)',
+   }}>
```

```diff
- <div className="flex items-center gap-3 text-xs text-text-muted">
+ <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--fg-mute)' }}>
```

### Патч 2 — DE-001 emoji

```diff
- <EmptyState icon="🚗" title="Выездов нет" />
+ <EmptyState icon={<Car size={20} />} title="Выездов нет" />
```

### Патч 3 — DE-002 (departures↔application M2M, blocked T-7-004)

**Заметка, не патч.** Когда T-7-004 разморозят, в `<DepartureRow>` под основной строкой добавить чипы:

```tsx
{dep.application_ids?.length > 0 && (
  <div className="flex flex-wrap items-center gap-1 mt-1">
    <span className="text-2xs" style={{ color: 'var(--fg-mute)' }}>заявки:</span>
    {dep.application_ids.map(id => (
      <Link key={id} to={`/control?app_id=${id}`} className="idchip hover:opacity-80">
        #{id}
      </Link>
    ))}
  </div>
)}
```

Не реализуем сейчас, оставляем как design-decision для T-7-004.

---

## B.5 — Модалки

Проверены: `TransitionModal`, `CreateApplicationModal`, `PanelActionModals` (Remove/ChangeCondition/ChangeDepartment/MoveToCell), `ConfirmDialog`, `PanelCreateButton`.

Все используют один и тот же `<Modal>` базовый компонент (`shared/ui/Modal.tsx`) — это правильно. Дельта только косметика:

| Модалка | Замечание | Severity |
|---|---|---|
| `Modal` (база) | `background: var(--bg-2)` — Серебро. По S-004 → `var(--bg-1)`. | P0 (через S-004) |
| `Modal` | Кнопка `<X>` закрытия — нет `aria-label`. | P1 |
| `Modal` | Нет focus-trap на Tab вне Radix — Radix уже даёт его, OK. | OK |
| `TransitionModal` | Дублирует `inputStyle` локально — можно перенести на `.input`. | P2 |
| `TransitionModal` | `toast.success('✅ ...')` — эмодзи в тосте. См. B.2 патч 2. | P0 (через S-003) |
| `TransitionModal` | `<input type="file">` нативный — стилизация ОС, минорно. | P2 |
| `CreateApplicationModal` | OK, использует токены. | OK |
| `PanelActionModals` | Все 4 используют токены через inline. OK. | OK |
| `ConfirmDialog` | OK по логике (см. C-001..C-002). | OK |
| `PanelCreateButton` (модалка) | Inputs — `bg-2`. См. B.3 патч 5. | P0 (через S-004) |

Базовый Modal патч:

```diff
- <Dialog.Content
-   ...
-   style={{
-     maxWidth: SIZE_W[size],
-     background: 'var(--bg-2)',
-     border: '1px solid var(--border)',
-     ...
-   }}
- >
+ <Dialog.Content
+   ...
+   style={{
+     maxWidth: SIZE_W[size],
+     background: 'var(--bg-1)',
+     border: '1px solid var(--border-subtle)',
+     ...
+   }}
+ >

  <Dialog.Close asChild>
    <button
+     aria-label="Закрыть"
      className="flex items-center justify-center w-6 h-6 rounded transition-colors"
      style={{ color: 'var(--fg-mute)' }}
+     onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-2)'; e.currentTarget.style.color = 'var(--fg)' }}
+     onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--fg-mute)' }}
    >
      <X size={14} />
    </button>
  </Dialog.Close>
```

---

## C — Review Phase 7 компонентов (короткие заметки, дельта к разделу C аудита)

### ConfirmDialog

OK. Не трогаем API. Description-fallback на ошибку backend'а в `PanelDeleteButton` — отлично работает. Title остаётся стабильным («Удалить панель X?»). **Бриф ошибся** про переписывание title — в коде этого нет.

**Опциональный subtitle**: на `ConfirmDialog` без `description` показывать default «Действие нельзя отменить» вместо пустоты — это улучшает читаемость в 80% случаев. Можно дописать:

```diff
- description?: string
+ description?: string
+ /** Если description не задан, при variant='danger' показывается стандартное предупреждение. */
+
  ...
- <Modal open={open} onClose={onClose} title={title} description={description} size="sm">
+ <Modal
+   open={open}
+   onClose={onClose}
+   title={title}
+   description={description ?? (variant === 'danger' ? 'Действие нельзя отменить.' : undefined)}
+   size="sm"
+ />
```

Но `<Modal>` description сейчас `sr-only` (для a11y). Если хотим показать визуально — нужен дополнительный prop в Modal или рендерить description в children. Пока не трогаем — текущий контракт работает.

### NotificationBell

- Popover **w-80 (320px)** — лучше чем 250 из брифа. На phone нужен `w-full` — зона D.
- BellRing-иконка при unread > 0 — слабо заметно. Pulse-анимация — зона E (E-004).
- Время в `formatRelative` — OK.
- `<Link>` для deep-link на `/applications/${target_id}` — но в `App.tsx` нет роута `/applications/:id`. Поведение: 404. **P1 функциональный баг.** Кодеру: либо добавить route и редирект, либо сразу строить путь через display.

**owner-action:** добавить в followup `T-7-followup-bell-deeplink-route`. Сейчас bell-deeplinks работают только для `panel` (через `/zip?panel_id=`) и `departure` (через `/departures/:id`), а `application` ведёт в 404. Нужно либо `/control?app_id=:id`, либо resolve через display.

### PanelCreateButton

OK по структуре. Минусы: `bg-2`-inputs (B.3 патч 5). Длинный `<select>` без поиска — терпимо при текущих ~8 экранах, см. C-006 аудита.

### PanelDeleteButton

OK. Error handling правильный (re-throw чтобы Confirm не закрылся). Title не переписывается. См. C-002.

### ThemeToggle

OK на 80%. Инлайн hover (S-010) — фикс в зоне E. Иконка корректно меняется. `aria-label` есть.

**Плюс одно улучшение:** сейчас toggle делает `light → dark → light` (2 значения), а в Profile у нас 3 (light/dark/system). Юзер выбирает «system», тыкает на ThemeToggle → попадает в light/dark **и теряет system-режим до следующего раза**. Не баг по сути, но недокументированно. Можно либо:
- цикл `light → dark → system → light` (3 значения, иконка тогда меняется по `theme`, не по `resolvedTheme`).
- оставить как есть, но в `title` дописать «(удерживать Shift для system)» или подобный shortcut.

Рекомендую **первое — 3-режимный цикл**. Иконка по `theme`:
```diff
- const Icon = theme === 'system'
-   ? Monitor
-   : resolvedTheme === 'dark' ? Moon : Sun

+ const Icon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor

  const cycle = () => setTheme(
    theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
  )
- onClick={toggleTheme}
+ onClick={cycle}
```

И в Profile radio синхронизация остаётся бесшовной.

### Profile sound section

P-001/P-002 — заменить нативный checkbox на toggle. Кнопка «Прослушать» — снять `disabled`. Подробно в `microinteractions-a11y-fixes.md`.

### Profile activity section

P-004 — плоский список OK. Timeline-вариант — отложить, низкий приоритет.

---

## Обновлённый `T-7-followup-*` список (после B+C)

Добавлены новые / обновлены приоритеты:

| # | ID | Источник | Время |
|---:|---|---|---|
| 1 | `merge-department-pages` | S-006, DL-001, B.1 | 2 дня |
| 2 | `departures-tokens` (новый, P0) | B.4 | 4 часа |
| 3 | `deemoji` | S-003 + B.2/B.3/B.4 | 1 день |
| 4 | `globals-css` | S-001 | 2 часа |
| 5 | `html-dark-class` | S-002 | 15 мин |
| 6 | `bg-2-as-surface` | S-004 + B.5 | 2 часа |
| 7 | `drop-inter` | S-005 | 20 мин |
| 8 | `dashboard-app-link` | M-001 | 1 час |
| 9 | `debug-activity-label` | DL-002 | 5 мин |
| 10 | `focus-visible-system` | S-007 | 1 час |
| 11 | `soundtoggle-ui` | P-001 | 2 часа |
| 12 | `sound-preview-enabled` | P-002 | 5 мин |
| 13 | `zip-not-allowed-cue` + drag opacity | Z-002, Z-004, B.3 патч 4 | 30 мин |
| 14 | `toaster-theme` | S-008 | 15 мин |
| 15 | `status-bullet` | DL-003 | 1 час + owner |
| 16 | `inline-style-cleanup` | DV-002 | 1 день |
| 17 | `bell-deeplink-route` (новый) | C-NotificationBell | 1 час |
| 18 | `theme-toggle-3-cycle` (новый, опционально) | C-ThemeToggle | 30 мин |
| 19 | `modal-aria-close` (новый) | B.5 базовый Modal | 10 мин |

**Суммарно:** ~5 дней работы кодера. Все правки **косметические + bugfix**, ни одной структурной переработки модалок/Button/Modal API.

---

## Что отложено

- DV-003 (bottom-tabs в DisplayView эталоне) — нужен ответ владельца.
- DL-003 (status bullet привязать к данным) — нужен ответ по DTO.
- M-001 (dashboard app link) — нужен ответ по DTO.
- DE-002 (departure↔application M2M) — blocked T-7-004.
- Storybook / Storybook-like компонент-каталог — отдельный проект.

---

*Следующий шаг: `microinteractions-a11y-fixes.md` (зона E) — focus rings, skeleton uniformity, theme switch transition, bell pulse, aria-labels, Toast theming.*
