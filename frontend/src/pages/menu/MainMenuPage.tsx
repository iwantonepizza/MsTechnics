import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Car,
  Circle,
  ClipboardCheck,
  MapPin,
  Monitor,
  Package,
  Wrench,
} from 'lucide-react'

import { apiClient } from '@/shared/api/client'
import { useMe } from '@/features/auth/hooks'
import { useDisplays } from '@/entities/display/hooks'
import { useStorage } from '@/entities/storage/hooks'
import { Badge } from '@/shared/ui/Badge'
import { Skeleton, SkeletonList } from '@/shared/ui/Skeleton'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { formatDate, formatRelative } from '@/shared/lib/utils'
import { useCrumb } from '@/widgets/navigation/CrumbContext'
import type { ApplicationListItem, DepartureListItem, DisplayListItem, PaginatedResponse } from '@/shared/api/types'

interface DashboardData {
  counts: Record<string, number>
  monitoring: { recent: ApplicationListItem[] }
  control: { queue: ApplicationListItem[] }
  service: { mine: ApplicationListItem[] }
}

interface StorageItem {
  id: number
  name: string
  count: number
}

type Dept = 'monitoring' | 'control' | 'service'

const DEPT_LABELS: Record<Dept, string> = {
  monitoring: 'Мониторинг',
  control: 'Контроль',
  service: 'Сервис',
}

function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await apiClient.get<DashboardData>('/dashboard/')
      return res.data
    },
    refetchInterval: 30_000,
    staleTime: 15_000,
  })
}

function useDeparturesToday() {
  return useQuery({
    queryKey: ['departures', 'today-summary'],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<DepartureListItem>>('/departures/')
      return res.data.results ?? []
    },
    refetchInterval: 30_000,
    staleTime: 15_000,
  })
}

function canAccess(permission: string, dept: Dept | 'zip') {
  return permission === 'admin' || permission === 'all' || permission === dept
}

export function getAppPath(app: ApplicationListItem, dept: Dept) {
  const citySlug = app.display.city?.slug ?? ''
  const displaySlug = app.display.slug ?? ''
  return citySlug && displaySlug
    ? `/${dept}/${citySlug}/${displaySlug}?app_id=${app.id}`
    : `/${dept}`
}

function ColumnShell({
  title,
  subtitle,
  icon,
  linkTo,
  allowed = true,
  children,
}: {
  title: string
  subtitle?: string
  icon: React.ReactNode
  linkTo: string
  allowed?: boolean
  children: React.ReactNode
}) {
  return (
    <section className="flex min-h-0 flex-col bg-bg-0" style={{ borderRight: '1px solid var(--border-subtle)' }}>
      <div className="flex h-11 shrink-0 items-center justify-between px-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--fg)' }}>
            {icon}
            <span className="truncate">{title}</span>
          </div>
          {subtitle && (
            <div className="mt-0.5 truncate text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-faint)' }}>
              {subtitle}
            </div>
          )}
        </div>
        <Link aria-label={`Открыть ${title}`} to={linkTo} className="icon-btn">
          <ArrowUpRight size={13} />
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {allowed ? children : (
          <div className="flex h-32 items-center justify-center text-xs" style={{ color: 'var(--fg-faint)' }}>
            Нет доступа
          </div>
        )}
      </div>
    </section>
  )
}

function KpiStrip({ counts, departuresCount, loading }: {
  counts: Record<string, number>
  departuresCount: number
  loading: boolean
}) {
  const kpis = [
    { label: 'активных заявок', value: counts.active_total ?? 0, tone: 'info', link: '/control' },
    { label: 'ждут контроля', value: counts.sent_to_control ?? 0, tone: 'warn', link: '/control' },
    { label: 'в сервисе', value: (counts.sent_to_service ?? 0) + (counts.work_in_service ?? 0), tone: 'ok', link: '/service' },
    { label: 'выездов сегодня', value: departuresCount, tone: 'neutral', link: '/departures' },
  ] as const

  return (
    <div className="grid h-[58px] shrink-0 grid-cols-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      {loading ? (
        Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="px-4 py-3" style={{ borderRight: index < 3 ? '1px solid var(--border-subtle)' : undefined }}>
            <Skeleton style={{ height: '10px', width: '110px', marginBottom: '8px' }} />
            <Skeleton style={{ height: '22px', width: '48px' }} />
          </div>
        ))
      ) : (
        kpis.map((kpi, index) => (
          <Link
            key={kpi.label}
            to={kpi.link}
            className="flex items-center justify-between px-4 transition-colors hover:bg-bg-1"
            style={{ borderRight: index < 3 ? '1px solid var(--border-subtle)' : undefined }}
          >
            <div className="flex items-center gap-2">
              <Circle size={8} fill={`var(--${kpi.tone === 'neutral' ? 'fg-faint' : kpi.tone})`} strokeWidth={0} />
              <span className="font-mono text-2xl font-semibold tabular-nums" style={{ color: 'var(--fg)' }}>
                {kpi.value}
              </span>
              <span className="text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-mute)' }}>
                {kpi.label}
              </span>
            </div>
          </Link>
        ))
      )}
    </div>
  )
}

function groupDisplaysByCity(displays: DisplayListItem[]) {
  const map = new Map<string, { id: number; name: string; slug: string; displays: DisplayListItem[] }>()
  displays.forEach((display) => {
    const city = display.city
    const key = city.slug ?? city.name
    if (!map.has(key)) {
      map.set(key, { id: city.id, name: city.name, slug: city.slug ?? '', displays: [] })
    }
    map.get(key)!.displays.push(display)
  })
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name, 'ru'))
}

function MonitoringColumn({ displays, loading, allowed }: {
  displays: DisplayListItem[]
  loading: boolean
  allowed: boolean
}) {
  const cities = useMemo(() => groupDisplaysByCity(displays), [displays])

  return (
    <ColumnShell
      title="Мониторинг"
      subtitle={`${cities.length} городов · ${displays.length} экранов`}
      icon={<Monitor size={14} style={{ color: 'var(--fg-dim)' }} />}
      linkTo="/monitoring"
      allowed={allowed}
    >
      {loading ? <SkeletonList rows={7} height="34px" /> : (
        <div className="space-y-1">
          {cities.map((city) => {
            const problemCount = city.displays.length
            return (
              <Link
                key={city.id}
                to={`/monitoring/${city.slug}`}
                className="grid grid-cols-[1fr_auto] items-center gap-2 rounded-md px-2.5 py-2 transition-colors hover:bg-bg-2"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--fg)' }}>
                    <MapPin size={12} style={{ color: 'var(--fg-faint)' }} />
                    <span className="truncate">{city.name}</span>
                  </div>
                  <div className="mt-0.5 text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
                    {city.displays.length} экранов
                  </div>
                </div>
                <Badge
                  label={String(problemCount)}
                  variant={problemCount > 6 ? 'warn' : 'neutral'}
                />
              </Link>
            )
          })}
        </div>
      )}
    </ColumnShell>
  )
}

function ApplicationQueueColumn({ dept, title, apps, count, loading, allowed }: {
  dept: Dept
  title: string
  apps: ApplicationListItem[]
  count: number
  loading: boolean
  allowed: boolean
}) {
  return (
    <ColumnShell
      title={title}
      subtitle={`${count} в очереди`}
      icon={dept === 'control' ? <ClipboardCheck size={14} style={{ color: 'var(--fg-dim)' }} /> : <Wrench size={14} style={{ color: 'var(--fg-dim)' }} />}
      linkTo={`/${dept}`}
      allowed={allowed}
    >
      {loading ? <SkeletonList rows={7} height="42px" /> : apps.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-xs" style={{ color: 'var(--fg-faint)' }}>
          Заявок нет
        </div>
      ) : (
        <div className="space-y-1.5">
          {apps.slice(0, 8).map(app => (
            <Link
              key={app.id}
              to={getAppPath(app, dept)}
              className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-md border px-2.5 py-2 transition-colors hover:bg-bg-2"
              style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}
            >
              <span className="font-mono text-2xs" style={{ color: app.status.color.hex }}>#{app.id}</span>
              <div className="min-w-0">
                <div className="truncate text-xs" style={{ color: 'var(--fg-dim)' }}>
                  {app.display.description ?? app.display.slug ?? DEPT_LABELS[dept]}
                </div>
                <div className="mt-0.5 flex gap-1 text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
                  <span>{app.panel.name}</span>
                  <span>/</span>
                  <span>{app.cell.position ?? '—'}</span>
                </div>
              </div>
              <span className="text-2xs" style={{ color: 'var(--fg-faint)' }}>
                {formatRelative(app.last_update_date_time)}
              </span>
            </Link>
          ))}
        </div>
      )}
    </ColumnShell>
  )
}

function ZipDeparturesColumn({ allowed }: { allowed: boolean }) {
  const lamels = useStorage('lamels')
  const hubs = useStorage('hubs')
  const wires = useStorage('wires')
  const departures = useDeparturesToday()
  const loading = lamels.isLoading || hubs.isLoading || wires.isLoading || departures.isLoading
  const showSkeleton = useDeferredLoading(loading)

  const storage = [
    { label: 'Ламели', items: (lamels.data ?? []) as StorageItem[], link: '/zip' },
    { label: 'Хабы', items: (hubs.data ?? []) as StorageItem[], link: '/zip' },
    { label: 'Провода', items: (wires.data ?? []) as StorageItem[], link: '/zip' },
  ]

  return (
    <ColumnShell
      title="ЗИП и выезды"
      subtitle="склад · маршруты"
      icon={<Boxes size={14} style={{ color: 'var(--fg-dim)' }} />}
      linkTo="/zip"
      allowed={allowed}
    >
      {showSkeleton ? <SkeletonList rows={8} height="34px" /> : (
        <div className="space-y-4">
          <div>
            <div className="mb-2 flex items-center gap-2 px-1 text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-mute)' }}>
              <Package size={12} />
              Расходники
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {storage.map(section => {
                const total = section.items.reduce((sum, item) => sum + (item.count ?? 0), 0)
                return (
                  <Link
                    key={section.label}
                    to={section.link}
                    className="rounded-md border px-2 py-2 transition-colors hover:bg-bg-2"
                    style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}
                  >
                    <div className="text-2xs font-mono uppercase" style={{ color: 'var(--fg-mute)' }}>{section.label}</div>
                    <div className="mt-1 font-mono text-lg font-semibold tabular-nums" style={{ color: total < 5 ? 'var(--warn)' : 'var(--fg)' }}>
                      {total}
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center gap-2 px-1 text-2xs font-mono uppercase tracking-wider" style={{ color: 'var(--fg-mute)' }}>
              <Car size={12} />
              Выезды
            </div>
            <div className="space-y-1">
              {(departures.data ?? []).slice(0, 5).map(dep => (
                <Link
                  key={dep.id}
                  to="/departures"
                  className="grid grid-cols-[1fr_auto] gap-2 rounded-md px-2.5 py-2 transition-colors hover:bg-bg-2"
                >
                  <div className="min-w-0">
                    <div className="truncate text-xs" style={{ color: 'var(--fg-dim)' }}>
                      {dep.description ?? `Выезд #${dep.id}`}
                    </div>
                    <div className="mt-0.5 text-2xs" style={{ color: 'var(--fg-faint)' }}>
                      {dep.executor ? `${dep.executor.first_name} ${dep.executor.last_name}` : 'Без исполнителя'}
                    </div>
                  </div>
                  <span className="text-2xs font-mono" style={{ color: 'var(--fg-faint)' }}>
                    {formatDate(dep.time_start)}
                  </span>
                </Link>
              ))}
              {(departures.data ?? []).length === 0 && (
                <div className="flex items-center gap-2 px-2 py-4 text-xs" style={{ color: 'var(--fg-faint)' }}>
                  <AlertTriangle size={13} />
                  Выездов нет
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </ColumnShell>
  )
}

export function MainMenuPage() {
  const { setCrumb } = useCrumb()
  const { data: me } = useMe()
  const dashboard = useDashboard()
  const displays = useDisplays()
  const departures = useDeparturesToday()

  useEffect(() => {
    setCrumb(null)
    return () => setCrumb(null)
  }, [setCrumb])

  const permission = me?.permission ?? ''
  const counts = dashboard.data?.counts ?? {}
  const showKpiSkeleton = useDeferredLoading(dashboard.isLoading || departures.isLoading)
  const showDisplaysSkeleton = useDeferredLoading(displays.isLoading)

  return (
    <div className="flex h-full flex-col overflow-hidden" style={{ background: 'var(--bg-0)' }}>
      <KpiStrip
        counts={counts}
        departuresCount={departures.data?.length ?? 0}
        loading={showKpiSkeleton}
      />

      <div className="grid min-h-0 flex-1 grid-cols-4">
        <MonitoringColumn
          displays={displays.data ?? []}
          loading={showDisplaysSkeleton}
          allowed={canAccess(permission, 'monitoring')}
        />
        <ApplicationQueueColumn
          dept="control"
          title="Контроль"
          apps={dashboard.data?.control.queue ?? []}
          count={(counts.sent_to_control ?? 0) + (counts.apply_in_control ?? 0)}
          loading={showKpiSkeleton}
          allowed={canAccess(permission, 'control')}
        />
        <ApplicationQueueColumn
          dept="service"
          title="Сервис"
          apps={dashboard.data?.service.mine ?? []}
          count={(counts.sent_to_service ?? 0) + (counts.work_in_service ?? 0)}
          loading={showKpiSkeleton}
          allowed={canAccess(permission, 'service')}
        />
        <ZipDeparturesColumn allowed={canAccess(permission, 'zip')} />
      </div>
    </div>
  )
}
