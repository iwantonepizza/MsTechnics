import { Link, useParams } from 'react-router-dom'
import { useCities, useDisplays } from '@/entities/display/hooks'
import { Spinner } from '@/shared/ui/Spinner'
import { EmptyState } from '@/shared/ui/EmptyState'
import { MapPin, Monitor } from 'lucide-react'

interface DepartmentPageProps {
  department: 'monitoring' | 'control' | 'service'
}

const DEPT_LABELS = {
  monitoring: 'Мониторинг',
  control: 'Контроль',
  service: 'Сервис',
}

export function DepartmentPage({ department }: DepartmentPageProps) {
  const { data: displays, isLoading } = useDisplays()
  const { data: cities } = useCities()

  if (isLoading) {
    return <div className="flex items-center justify-center h-full"><Spinner className="w-6 h-6" /></div>
  }

  if (!displays?.length) {
    return (
      <div className="flex items-center justify-center h-full">
        <EmptyState icon="🏙️" title="Нет доступных экранов" description="Попросите администратора добавить города" />
      </div>
    )
  }

  // Группируем по городам
  const byCityMap = new Map<string, typeof displays>()
  displays.forEach(d => {
    const cityName = d.city.name
    if (!byCityMap.has(cityName)) byCityMap.set(cityName, [])
    byCityMap.get(cityName)!.push(d)
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">{DEPT_LABELS[department]}</h1>
        <p className="text-sm text-text-muted mt-0.5">Выберите экран</p>
      </div>

      <div className="space-y-6">
        {Array.from(byCityMap.entries()).map(([cityName, cityDisplays]) => (
          <div key={cityName}>
            <div className="flex items-center gap-2 mb-3">
              <MapPin size={13} className="text-text-muted" />
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{cityName}</h2>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {cityDisplays.map(display => (
                <Link
                  key={display.id}
                  to={`/${department}/${display.city.slug}/${display.slug}`}
                  className="flex flex-col gap-2 p-3 bg-surface-2 border border-surface-3 rounded-xl hover:border-surface-4 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Monitor size={13} className="text-text-muted flex-shrink-0" />
                    <span className="text-sm font-medium truncate">{display.description ?? display.name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <span>{display.rows}×{display.cols}</span>
                    <span className="text-surface-3">·</span>
                    <span className="font-mono text-2xs">{display.name}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
