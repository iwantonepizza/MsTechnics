# T-4-012. DepartmentListPage

> **Тип:** page
> **Приоритет:** P1
> **Оценка:** 3 часа
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Список городов и их экранов для конкретного отдела. Один компонент, prop `department='monitoring' | 'control' | 'service'`, поведение по эталону `frontend-design/`.

---

## Зависимости

- **Блокируется:** T-4-001..T-4-004
- **Блокирует:** ничего

---

## Layout

```
┌──────────────────────────────────────────────┬──────────────┐
│ City: Ижевск (3 экрана, 2 проблемы)          │              │
│  ┌────────────────────────────────┐          │ Очередь      │
│  │ Колизей          🟢            │          │ заявок       │
│  │ 10×10 · 1 проблема  · открыть  │          │ (control)    │
│  ├────────────────────────────────┤          │              │
│  │ Ленина 60        🟢            │          │ ID-4567      │
│  │ 8×6 · 0 проблем · открыть      │          │ ID-4566      │
│  └────────────────────────────────┘          │              │
│                                               │              │
│ City: Пермь                                   │              │
│  ...                                          │              │
└──────────────────────────────────────────────┴──────────────┘
```

Правый рейл:
- **monitoring**: последние созданные заявки (создал я)
- **control**: очередь заявок текущего города
- **service**: мои заявки в работе

---

## Что сделать

### Шаг 1. Структура

`frontend/src/pages/department/DepartmentListPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import { useCities } from '@/features/cities/hooks'
import { useDisplays } from '@/entities/display/hooks'

interface DepartmentListPageProps {
  department: 'monitoring' | 'control' | 'service'
}

const TITLES = {
  monitoring: 'Мониторинг — список экранов',
  control:    'Контроль — список экранов',
  service:    'Сервис — список экранов',
}

export function DepartmentListPage({ department }: DepartmentListPageProps) {
  const { setCrumb } = useCrumb()
  useEffect(() => {
    setCrumb(<>{department} · все города</>)
    return () => setCrumb(null)
  }, [setCrumb, department])
  
  const { data: cities = [] } = useCities()
  const [activeCity, setActiveCity] = useState<string | null>(null)
  
  return (
    <div className="h-full grid grid-cols-[1fr_320px] gap-px bg-border-subtle">
      {/* Left: cities + displays */}
      <div className="bg-bg-0 overflow-auto">
        <div className="px-6 py-4 border-b border-border-subtle">
          <h1 className="text-[16px] font-semibold">{TITLES[department]}</h1>
        </div>
        
        {cities.map(city => (
          <CityBlock
            key={city.id}
            city={city}
            department={department}
            isActive={activeCity === city.slug}
            onActivate={() => setActiveCity(city.slug)}
          />
        ))}
      </div>
      
      {/* Right rail */}
      <div className="bg-bg-1 overflow-auto">
        <SideRail department={department} activeCity={activeCity} />
      </div>
    </div>
  )
}

function CityBlock({ city, department, isActive, onActivate }: any) {
  const { data: displays = [] } = useDisplays({ city: city.slug })
  const problems = displays.filter((d: any) => d.current_condition?.name !== 'work').length
  
  return (
    <div className="border-b border-border-subtle" onClick={onActivate}>
      <div className="px-6 py-3 flex items-center justify-between bg-bg-1/50">
        <div className="flex items-center gap-2">
          <span className="text-[14px] font-medium">{city.name}</span>
          <span className="text-fg-mute text-[12px]">
            {displays.length} экранов{problems > 0 && `, ${problems} ${problems === 1 ? 'проблема' : 'проблем'}`}
          </span>
        </div>
        {isActive && <span className="text-[10px] uppercase tracking-wider font-mono text-accent">activity →</span>}
      </div>
      
      <div className="px-6 py-3 space-y-1">
        {displays.map((d: any) => (
          <Link
            key={d.id}
            to={`/${department}/${city.slug}/${d.slug}`}
            className="flex items-center justify-between p-3 rounded-md bg-bg-2 hover:bg-bg-3"
          >
            <div>
              <div className="text-[13px] font-medium">{d.description}</div>
              <div className="text-fg-mute text-[11px] font-mono mt-0.5">
                {d.rows}×{d.cols}
              </div>
            </div>
            <ConditionBadge condition={d.current_condition} />
          </Link>
        ))}
      </div>
    </div>
  )
}

function ConditionBadge({ condition }: any) {
  if (!condition) return null
  return (
    <span className="text-[16px]">{condition.icon?.unicode_symbol ?? '—'}</span>
  )
}

function SideRail({ department, activeCity }: any) {
  // ... в зависимости от department показать один из 3 виджетов:
  // - monitoring: <RecentApplications createdBy='me' limit={20} />
  // - control: <ControlQueue citySlug={activeCity} />
  // - service: <MyApplicationsInProgress />
  return <div className="p-4 text-fg-mute text-[12px]">Side rail TBD</div>
}
```

---

## Критерии приёмки

- [ ] 3 пути работают: `/monitoring`, `/control`, `/service`
- [ ] Список городов с экранами внутри
- [ ] У каждого экрана: название, размеры (rows×cols), статус-эмоджи
- [ ] Правый рейл уникальный для каждого отдела
- [ ] Click на экран → DisplayView того же отдела
- [ ] Hover-state работает, focus-visible
- [ ] Skeleton при загрузке

---

## Что НЕ делать

- НЕ объединять с MainMenu (это разные экраны)
- НЕ показывать архивные экраны (отфильтровано на бекенде)
