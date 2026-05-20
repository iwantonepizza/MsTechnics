# T-4-016. ZipPage — переработать под Storage + расходники + history

> **Тип:** page
> **Приоритет:** P1
> **Оценка:** 3 часа
> **Фаза:** 4
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Цель

Главная страница склада ЗИП — 4 колонки панелей (по department) + расходники (lamels/hubs/wires) + history rail.

---

## Зависимости

- **Блокируется:** T-4-001..T-4-004
- **Блокирует:** ничего

---

## Layout (по эталону `frontend-design/`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Title: ЗИП — все экраны | [Фильтр по экрану ▼] | [+ Панель]         │
├────────┬────────┬────────┬────────┬───────────┬──────────────────────┤
│ ЗИП    │ На рук.│ Сервис │ В раб. │ Расходники│ История              │
│ (12)   │ (3)    │ (5)    │ (84)   │           │                      │
├────────┼────────┼────────┼────────┼───────────┼──────────────────────┤
│ <Pnl>  │ <Pnl>  │ <Pnl>  │ <Pnl>  │ Ламели    │ ▷ 14:30 P-12 → ЗИП  │
│ <Pnl>  │ <Pnl>  │        │ <Pnl>  │  Q200: 47 │ ▷ 13:15 ...          │
│ ...    │ ...    │        │ ...    │  Q300: 12 │                      │
│        │        │        │        │ Хабы      │                      │
│        │        │        │        │  A-100: 5 │                      │
└────────┴────────┴────────┴────────┴───────────┴──────────────────────┘
```

---

## Что сделать

### Структура

`frontend/src/pages/zip/ZipPage.tsx`:

```tsx
import { useParams } from 'react-router-dom'
import { useDisplays } from '@/entities/display/hooks'
import { usePanels } from '@/entities/panel/hooks'
import { useStorage } from '@/entities/storage/hooks'  // создать
import { useActivityLog } from '@/entities/activity/hooks'  // создать

export function ZipPage() {
  const { displaySlug } = useParams<{ displaySlug?: string }>()
  
  const filterDisplay = displaySlug ?? null
  const { data: zipPanels } = usePanels({ department: 'zip', display: filterDisplay })
  const { data: handPanels } = usePanels({ department: 'hand', display: filterDisplay })
  const { data: servicePanels } = usePanels({ department: 'service', display: filterDisplay })
  const { data: monitorPanels } = usePanels({ department: 'monitor', display: filterDisplay })
  
  return (
    <div className="h-full flex flex-col">
      <Header displaySlug={filterDisplay} />
      <div className="flex-1 grid grid-cols-[1fr_1fr_1fr_1fr_280px_320px] gap-px bg-border-subtle overflow-hidden">
        <PanelsColumn title="ЗИП" panels={zipPanels} />
        <PanelsColumn title="На руках" panels={handPanels} />
        <PanelsColumn title="Сервис" panels={servicePanels} />
        <PanelsColumn title="В работе" panels={monitorPanels} />
        <ConsumablesColumn displaySlug={filterDisplay} />
        <HistoryColumn displaySlug={filterDisplay} />
      </div>
    </div>
  )
}

function Header({ displaySlug }: any) {
  const { data: displays = [] } = useDisplays({})
  const navigate = useNavigate()
  return (
    <div className="h-12 px-6 flex items-center justify-between border-b border-border-subtle">
      <div className="flex items-center gap-3">
        <h1 className="font-semibold text-[14px]">
          ЗИП {displaySlug && <span className="text-fg-mute">/ <span className="font-mono">{displaySlug}</span></span>}
        </h1>
        <select
          value={displaySlug ?? ''}
          onChange={e => navigate(e.target.value ? `/zip/${e.target.value}` : '/zip')}
          className="h-input px-2 text-[12px] bg-bg-2 border border-border rounded-md"
        >
          <option value="">Все экраны</option>
          {displays.map((d: any) => <option key={d.id} value={d.slug}>{d.description}</option>)}
        </select>
      </div>
      <Button variant="primary" size="md">+ Панель</Button>
    </div>
  )
}

function PanelsColumn({ title, panels = [] }: any) {
  return (
    <div className="bg-bg-1 flex flex-col min-w-0">
      <ColumnHeader title={title} count={panels.length} />
      <div className="flex-1 overflow-auto p-2">
        <VirtualPanelsList items={panels} />  {/* или просто map если < 100 */}
      </div>
    </div>
  )
}

function ConsumablesColumn({ displaySlug }: any) {
  const { data: lamels = [] } = useStorage('lamels', { display: displaySlug })
  const { data: hubs   = [] } = useStorage('hubs', { display: displaySlug })
  const { data: wires  = [] } = useStorage('wires', { display: displaySlug })
  
  return (
    <div className="bg-bg-1 flex flex-col">
      <ColumnHeader title="Расходники" />
      <div className="flex-1 overflow-auto p-3 space-y-3">
        <Group title="Ламели" items={lamels} />
        <Group title="Хабы"   items={hubs} />
        <Group title="Провода" items={wires} />
      </div>
    </div>
  )
}

function HistoryColumn({ displaySlug }: any) {
  const { data: history = [] } = useActivityLog({
    eventTypePrefix: 'panel.',  // только панельные события
    limit: 50,
  })
  return (
    <div className="bg-bg-1 flex flex-col">
      <ColumnHeader title="История" />
      <div className="flex-1 overflow-auto">
        {history.map((e: any) => <HistoryRow key={e.id} entry={e} />)}
      </div>
    </div>
  )
}
```

### Вспомогательные компоненты

```tsx
function ColumnHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="h-8 px-3 flex items-center justify-between border-b border-border-subtle bg-bg-1">
      <span className="text-[10px] uppercase tracking-wider font-mono text-fg-mute">
        {title}
      </span>
      {count != null && (
        <span className="text-[11px] font-mono text-fg-mute">{count}</span>
      )}
    </div>
  )
}

function Group({ title, items }: { title: string; items: any[] }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider font-mono text-fg-mute mb-1">{title}</div>
      <div className="space-y-0.5">
        {items.map(it => (
          <div key={it.id} className="flex items-center justify-between text-[12px]">
            <span className="font-mono">{it.name}</span>
            <span className="text-fg-dim tabular-nums">{it.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## Критерии приёмки

- [ ] 4 колонки панелей с правильной фильтрацией по department
- [ ] Counts в заголовке каждой колонки
- [ ] Колонка расходников с lamels/hubs/wires
- [ ] Колонка истории — последние 50 событий с панелями
- [ ] Filter по экрану (selector сверху) работает (задача владельца #15)
- [ ] URL `/zip/:displaySlug` фильтрует автоматически
- [ ] Click на панель → opens panel detail / modal
- [ ] Skeleton при загрузке
- [ ] Virtualized list (`@tanstack/react-virtual`) если > 100 элементов в колонке

---

## Что НЕ делать

- НЕ показывать архивные панели (`archived=true`) — отфильтровано
- НЕ позволять прямую правку количества расходников (только control/admin) — кнопка disabled для других
- НЕ грузить все 100+ панелей колонки сразу — virtualize или paginate
