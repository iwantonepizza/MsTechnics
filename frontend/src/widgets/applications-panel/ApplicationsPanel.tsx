import { useState } from 'react'
import { Tabs } from '@/shared/ui/Tabs'
import { SkeletonList } from '@/shared/ui/Skeleton'
import { EmptyState } from '@/shared/ui/EmptyState'
import { ApplicationCard } from '@/entities/application/ApplicationCard'
import { useApplications } from '@/entities/application/hooks'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'

type Dept = 'monitoring' | 'control' | 'service'

const TABS: Record<Dept, Array<{ value: string; label: string }>> = {
  monitoring: [
    { value: 'received', label: 'Запросы' },
    { value: 'all',      label: 'Все' },
  ],
  control: [
    { value: 'received',             label: 'Запросы' },
    { value: 'at_work',              label: 'В работе' },
    { value: 'complete',             label: 'Выполненные' },
    { value: 'archive',              label: 'Архив' },
    { value: 'unable',               label: 'Невозможные' },
  ],
  service: [
    { value: 'at_work',  label: 'В работе' },
    { value: 'received', label: 'Новые' },
    { value: 'complete', label: 'Выполненные' },
  ],
}

interface ApplicationsPanelProps {
  displaySlug: string
  department: Dept
  onApplicationSelect?: (id: number) => void
  selectedId?: number | null
}

export function ApplicationsPanel({ displaySlug, department, onApplicationSelect, selectedId }: ApplicationsPanelProps) {
  const tabs = TABS[department]
  const [box, setBox] = useState(tabs[0].value)

  const { data, isLoading } = useApplications({ display: displaySlug, box })
  const showSkeleton = useDeferredLoading(isLoading)
  const apps = data?.results ?? []

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--bg-1)' }}>
      {/* Tabs */}
      <div className="px-3 py-2 shrink-0" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <Tabs value={box} onChange={setBox} className="flex-wrap">
          {tabs.map(t => <Tabs.Item key={t.value} value={t.value}>{t.label}</Tabs.Item>)}
        </Tabs>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-1 px-1">
        {showSkeleton ? (
          <SkeletonList rows={6} height="var(--h-row)" />
        ) : apps.length === 0 ? (
          <EmptyState icon="📭" title="Заявок нет" className="py-10" />
        ) : (
          apps.map(app => (
            <ApplicationCard
              key={app.id}
              application={app}
              selected={app.id === selectedId}
              onClick={() => onApplicationSelect?.(app.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
