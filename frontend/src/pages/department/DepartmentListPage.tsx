import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Clock, MapPin, Monitor } from 'lucide-react'

import { ApplicationCard } from '@/entities/application/ApplicationCard'
import { useApplications } from '@/entities/application/hooks'
import { useCities, useDisplays } from '@/entities/display/hooks'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Skeleton, SkeletonList } from '@/shared/ui/Skeleton'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import type { City, DisplayListItem } from '@/shared/api/types'

type Dept = 'monitoring' | 'control' | 'service'

const DEPT_CONFIG: Record<Dept, { title: string; railTitle: string; boxForRail: string }> = {
  monitoring: {
    title: 'Мониторинг — список экранов',
    railTitle: 'Последние заявки',
    boxForRail: 'received',
  },
  control: {
    title: 'Контроль — список экранов',
    railTitle: 'Очередь контроля',
    boxForRail: 'received',
  },
  service: {
    title: 'Сервис — список экранов',
    railTitle: 'Мои в работе',
    boxForRail: 'at_work',
  },
}

function cityKey(city: City) {
  return city.slug ?? city.name
}

function groupDisplays(displays: DisplayListItem[], cities: City[]) {
  const byCity = new Map<string, { city: City; displays: DisplayListItem[] }>()

  cities.forEach(city => {
    byCity.set(cityKey(city), { city, displays: [] })
  })

  displays.forEach(display => {
    const key = cityKey(display.city)
    if (!byCity.has(key)) {
      byCity.set(key, { city: display.city, displays: [] })
    }
    byCity.get(key)!.displays.push(display)
  })

  return Array.from(byCity.values())
    .filter(group => group.displays.length > 0)
    .sort((a, b) => a.city.name.localeCompare(b.city.name, 'ru'))
}

function SideRail({ department, activeCity }: { department: Dept; activeCity: string | null }) {
  const config = DEPT_CONFIG[department]
  const { data, isLoading, error, refetch } = useApplications({ box: config.boxForRail })
  const showSkeleton = useDeferredLoading(isLoading)
  const items = data?.results?.slice(0, 10) ?? []

  return (
    <aside className="flex min-h-0 flex-col bg-bg-1">
      <div className="h-11 shrink-0 px-4 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center justify-between gap-2">
          <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-mute)' }}>
            {config.railTitle}
          </span>
          {activeCity && (
            <span className="truncate text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
              {activeCity}
            </span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-1.5">
        {error ? (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-xs" style={{ color: 'var(--err)' }}>
            <AlertTriangle size={18} />
            <span>Не удалось загрузить</span>
            <button className="btn btn-secondary sm" onClick={() => refetch()}>Повторить</button>
          </div>
        ) : showSkeleton ? (
          <SkeletonList rows={6} height="var(--h-row)" />
        ) : items.length === 0 ? (
          <EmptyState icon="📭" title="Пусто" className="py-10" />
        ) : (
          items.map(app => <ApplicationCard key={app.id} application={app} compact />)
        )}
      </div>
    </aside>
  )
}

function DisplayRow({ display, department }: { display: DisplayListItem; department: Dept }) {
  return (
    <Link
      to={`/${department}/${display.city.slug}/${display.slug}`}
      className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-md border px-3 py-2.5 transition-colors hover:bg-bg-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      style={{
        background: 'var(--bg-2)',
        borderColor: 'var(--border-subtle)',
        outlineColor: 'var(--accent)',
      }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Monitor size={13} style={{ color: 'var(--fg-mute)' }} />
          <span className="truncate text-sm font-medium" style={{ color: 'var(--fg)' }}>
            {display.description ?? display.name}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
          <span>{display.rows}x{display.cols}</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>{display.name}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span title="Статус экрана" className="text-sm">●</span>
        <ArrowRight size={13} style={{ color: 'var(--fg-faint)' }} />
      </div>
    </Link>
  )
}

function CityBlock({
  city,
  displays,
  department,
  active,
  onActivate,
}: {
  city: City
  displays: DisplayListItem[]
  department: Dept
  active: boolean
  onActivate: () => void
}) {
  return (
    <section
      className="border-b"
      style={{ borderColor: 'var(--border-subtle)', background: active ? 'var(--bg-1)' : 'transparent' }}
      onMouseEnter={onActivate}
      onFocus={onActivate}
    >
      <button
        type="button"
        onClick={onActivate}
        className="flex w-full items-center justify-between px-6 py-3 text-left transition-colors hover:bg-bg-1"
      >
        <div className="flex min-w-0 items-center gap-2">
          <MapPin size={13} style={{ color: 'var(--fg-faint)' }} />
          <span className="truncate text-sm font-semibold" style={{ color: 'var(--fg)' }}>
            {city.name}
          </span>
          <span className="text-xs" style={{ color: 'var(--fg-mute)' }}>
            {displays.length} экранов
          </span>
        </div>
        {active && (
          <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--accent)' }}>
            activity
          </span>
        )}
      </button>

      <div className="grid gap-2 px-6 pb-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
        {displays.map(display => (
          <DisplayRow key={display.id} display={display} department={department} />
        ))}
      </div>
    </section>
  )
}

export function DepartmentListPage({ department }: { department: Dept }) {
  const { citySlug } = useParams<{ citySlug?: string }>()
  const { setCrumb } = useCrumb()
  const { data: cities = [], isLoading: citiesLoading, error: citiesError } = useCities()
  const { data: displays = [], isLoading: displaysLoading, error: displaysError, refetch } = useDisplays()
  const [activeCity, setActiveCity] = useState<string | null>(citySlug ?? null)

  const config = DEPT_CONFIG[department]
  const showSkeleton = useDeferredLoading(citiesLoading || displaysLoading)
  const error = citiesError || displaysError

  const groups = useMemo(() => {
    const filteredDisplays = displays.filter(display => !citySlug || display.city.slug === citySlug)
    return groupDisplays(filteredDisplays, cities)
  }, [cities, citySlug, displays])

  useEffect(() => {
    setCrumb(
      <span className="flex items-center gap-2 text-xs" style={{ color: 'var(--fg-mute)' }}>
        <span>{config.title}</span>
        {citySlug && <span className="font-mono" style={{ color: 'var(--fg-faint)' }}>/{citySlug}</span>}
      </span>
    )
    return () => setCrumb(null)
  }, [citySlug, config.title, setCrumb])

  useEffect(() => {
    if (!activeCity && groups[0]) setActiveCity(cityKey(groups[0].city))
  }, [activeCity, groups])

  return (
    <div className="grid h-full min-h-0 grid-cols-[1fr_320px]" style={{ background: 'var(--border-subtle)' }}>
      <main className="min-h-0 overflow-y-auto bg-bg-0">
        <div className="sticky top-0 z-10 flex h-13 items-center justify-between bg-bg-0 px-6" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div>
            <h1 className="text-md font-semibold" style={{ color: 'var(--fg)' }}>{config.title}</h1>
            <div className="mt-0.5 flex items-center gap-2 text-2xs" style={{ color: 'var(--fg-faint)' }}>
              <Clock size={11} />
              <span>{groups.length} городов · {groups.reduce((sum, group) => sum + group.displays.length, 0)} экранов</span>
            </div>
          </div>
        </div>

        {error ? (
          <div className="flex h-80 flex-col items-center justify-center gap-3 text-xs" style={{ color: 'var(--err)' }}>
            <AlertTriangle size={22} />
            <span>Не удалось загрузить список экранов</span>
            <button className="btn btn-secondary sm" onClick={() => refetch()}>Повторить</button>
          </div>
        ) : showSkeleton ? (
          <div className="space-y-4 p-6">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index}>
                <Skeleton style={{ height: '18px', width: '160px', marginBottom: '12px' }} />
                <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
                  {Array.from({ length: 4 }).map((__, itemIndex) => (
                    <Skeleton key={itemIndex} style={{ height: '64px', borderRadius: 'var(--r-md)' }} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : groups.length === 0 ? (
          <EmptyState icon="🏙️" title="Нет доступных экранов" description="Попросите администратора добавить города" />
        ) : (
          groups.map(group => (
            <CityBlock
              key={cityKey(group.city)}
              city={group.city}
              displays={group.displays}
              department={department}
              active={activeCity === cityKey(group.city)}
              onActivate={() => setActiveCity(cityKey(group.city))}
            />
          ))
        )}
      </main>

      <SideRail department={department} activeCity={activeCity} />
    </div>
  )
}
