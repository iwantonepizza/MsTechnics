# T-4-011. MainMenuPage — переработка под Main Menu v2

> **Тип:** page
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Переработать существующий `MainMenuPage` под одобренный эталон `frontend-design/screen-main-menu.jsx`. Главное отличие от текущего: **нет hero**, KPI-строкой 14-18px сверху, 4 колонки отделов под ней.

---

## Зависимости

- **Блокируется:** T-4-001..T-4-004
- **Блокирует:** ничего

---

## Эталон в `frontend-design/`

Структура:
```
[KPI strip — одной строкой 14-18px:
   ● 23 активных заявки      ● 7 у меня в работе      ● 2 выезда сегодня      ● 4 просрочено SLA]

[4 колонки отделов]
┌────────────┬────────────┬────────────┬────────────┐
│ Мониторинг │  Контроль  │   Сервис   │ ЗИП + Выезды│
│            │            │            │             │
│ Города:    │ Очередь:   │ Мои в раб.:│ Стоки:      │
│ Ижевск 🟢  │ ID-4567 ●  │ ID-4520 ●  │ Ламели Q200 │
│ Пермь  ⚠️  │ ID-4566 ●  │ ID-4521 ●  │ Хабы A-100  │
│ Екб    🟢  │ ...        │ ...        │             │
│            │            │            │ Выезды:     │
│            │            │            │ ▷ Иванов→Изж│
└────────────┴────────────┴────────────┴────────────┘
```

Каждая ячейка KPI: цветной dot + число + лейбл маленьким шрифтом моно UPPERCASE.

---

## Что сделать

### Шаг 1. Удалить существующее (если hero есть)

```bash
# Текущий MainMenuPage.tsx переписываем
# Сохраним структуру file path, но содержимое — новое
```

### Шаг 2. Структура

`frontend/src/pages/menu/MainMenuPage.tsx`:

```tsx
import { useEffect } from 'react'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import { useMe } from '@/features/auth/hooks'
import { useApplications } from '@/entities/application/hooks'
import { useDepartures } from '@/entities/departure/hooks'  // создать в T-4-016 если нет

import { KpiStrip } from '@/widgets/menu/KpiStrip'
import { MonitoringColumn } from '@/widgets/menu/MonitoringColumn'
import { ControlColumn } from '@/widgets/menu/ControlColumn'
import { ServiceColumn } from '@/widgets/menu/ServiceColumn'
import { ZipColumn } from '@/widgets/menu/ZipColumn'

export function MainMenuPage() {
  const { setCrumb } = useCrumb()
  useEffect(() => { setCrumb(null); return () => setCrumb(null) }, [setCrumb])
  
  return (
    <div className="h-full flex flex-col">
      <KpiStrip />
      <div className="flex-1 grid grid-cols-4 gap-px bg-border-subtle overflow-hidden">
        <MonitoringColumn />
        <ControlColumn />
        <ServiceColumn />
        <ZipColumn />
      </div>
    </div>
  )
}
```

### Шаг 3. KpiStrip

`frontend/src/widgets/menu/KpiStrip.tsx`:

```tsx
import { useApplicationsKpi } from '@/features/applications/hooks'

export function KpiStrip() {
  const { data: kpi, isLoading } = useApplicationsKpi()
  
  return (
    <div className="h-9 px-4 flex items-center gap-6 border-b border-border-subtle bg-bg-1">
      <KpiItem dot="ok" value={kpi?.active ?? '—'} label="активных заявок" />
      <KpiItem dot="info" value={kpi?.my_in_progress ?? '—'} label="у меня в работе" />
      <KpiItem dot="warn" value={kpi?.departures_today ?? '—'} label="выездов сегодня" />
      <KpiItem dot="err" value={kpi?.overdue_sla ?? '—'} label="просрочено SLA" />
    </div>
  )
}

function KpiItem({ dot, value, label }: { dot: 'ok'|'warn'|'err'|'info'; value: number | string; label: string }) {
  const dotColor = { ok: 'bg-ok', warn: 'bg-warn', err: 'bg-err', info: 'bg-info' }[dot]
  return (
    <div className="flex items-baseline gap-2">
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} self-center`} />
      <span className="text-[14px] font-semibold tabular-nums">{value}</span>
      <span className="text-[10px] uppercase tracking-wider font-mono text-fg-mute">{label}</span>
    </div>
  )
}
```

### Шаг 4. Колонки отделов

Каждая — отдельный widget с заголовком + контентом. Пример MonitoringColumn:

```tsx
// frontend/src/widgets/menu/MonitoringColumn.tsx
import { Link } from 'react-router-dom'
import { useCitiesWithStats } from '@/features/cities/hooks'  // create

export function MonitoringColumn() {
  const { data: cities = [] } = useCitiesWithStats()
  
  return (
    <Column title="Мониторинг" linkTo="/monitoring">
      <div className="space-y-1 p-3">
        {cities.map(city => (
          <Link
            key={city.id}
            to={`/monitoring/${city.slug}`}
            className="flex items-center justify-between p-2 rounded-md bg-bg-2 hover:bg-bg-3"
          >
            <span className="text-[13px]">{city.name}</span>
            <CityStatusEmoji problems={city.problems_count} />
          </Link>
        ))}
      </div>
    </Column>
  )
}

const CityStatusEmoji = ({ problems }: { problems: number }) => {
  if (problems === 0) return <span title="Нет проблем">🟢</span>
  if (problems < 5)   return <span title={`${problems} проблем`}>⚠️</span>
  return <span title={`${problems}+ проблем`}>❌</span>
}

function Column({ title, linkTo, children }: { title: string; linkTo: string; children: React.ReactNode }) {
  return (
    <div className="bg-bg-1 flex flex-col">
      <div className="h-8 px-3 flex items-center justify-between border-b border-border-subtle">
        <span className="text-[10px] uppercase tracking-wider font-mono text-fg-mute">{title}</span>
        <Link to={linkTo} className="text-[11px] text-accent hover:text-accent-hover">Открыть →</Link>
      </div>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}
```

Аналогично:
- `ControlColumn` — список заявок в очереди (status=`sent_to_control`), кликабельные
- `ServiceColumn` — мои заявки в работе (filter executor=me OR status=`work_in_service`)
- `ZipColumn` — стоки расходников (lamels, hubs) с числами + последние выезды

### Шаг 5. KPI hook

`frontend/src/features/applications/hooks.ts` — добавить:

```ts
export function useApplicationsKpi() {
  return useQuery({
    queryKey: ['applications', 'kpi'],
    queryFn: async () => {
      const [active, mine, departures, overdue] = await Promise.all([
        apiClient.get('/applications/?box=at_work&page_size=1'),
        apiClient.get('/applications/?my=true&box=at_work&page_size=1'),
        apiClient.get('/departures/?status=in_progress&page_size=1'),
        apiClient.get('/applications/?overdue_sla=true&page_size=1'),
      ])
      return {
        active: active.data.count ?? active.data.results?.length ?? 0,
        my_in_progress: mine.data.count ?? 0,
        departures_today: departures.data.count ?? 0,
        overdue_sla: overdue.data.count ?? 0,
      }
    },
    refetchInterval: 30_000,
  })
}
```

**Замечание архитектора:** на бекенде нужно вернуть `count` в paginated response — либо через CursorPagination override, либо отдельным endpoint `/api/v1/applications/count/`. Если нет — сделать отдельную задачу T-3-XXX.

---

## Критерии приёмки

- [ ] Hero убран, страница начинается с KPI строки
- [ ] 4 колонки в `grid-cols-4`
- [ ] Каждый отдел с правильными данными (cities/queue/my-work/stocks)
- [ ] KPI обновляется каждые 30 секунд
- [ ] При клике на город → переход на `/monitoring/<slug>`
- [ ] Loading state — skeleton
- [ ] При полном отсутствии прав на отдел — колонка показывает «Нет доступа»

---

## Что НЕ делать

- НЕ возвращать hero «Привет, Михаил» — это внутренний инструмент
- НЕ ставить декоративную графику — Linear-стиль
- НЕ хардкодить города — из API
