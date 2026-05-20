import { Inbox } from 'lucide-react'
import { useState } from 'react'

import { ApplicationCard } from '@/entities/application/ApplicationCard'
import { useApplications } from '@/entities/application/hooks'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { EmptyState } from '@/shared/ui/EmptyState'
import { SkeletonList } from '@/shared/ui/Skeleton'
import { Tabs } from '@/shared/ui/Tabs'

type Dept = 'monitoring' | 'control' | 'service'

const TABS: Record<Dept, Array<{ value: string; label: string }>> = {
  monitoring: [
    { value: 'received', label: 'Запросы' },
    { value: 'all', label: 'Все' },
  ],
  control: [
    { value: 'received', label: 'Запросы' },
    { value: 'at_work', label: 'В работе' },
    { value: 'complete', label: 'Выполненные' },
    { value: 'archive', label: 'Архив' },
    { value: 'unable', label: 'Невозможные' },
  ],
  service: [
    { value: 'at_work', label: 'В работе' },
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

export function ApplicationsPanel({
  displaySlug,
  department,
  onApplicationSelect,
  selectedId,
}: ApplicationsPanelProps) {
  const tabs = TABS[department]
  const [box, setBox] = useState(tabs[0].value)

  const { data, isLoading } = useApplications({ display: displaySlug, box })
  const showSkeleton = useDeferredLoading(isLoading)
  const apps = data?.results ?? []

  return (
    <div className="flex h-full flex-col" style={{ background: 'var(--bg-1)' }}>
      <div className="shrink-0 px-3 py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <Tabs value={box} onChange={setBox} className="flex-wrap">
          {tabs.map(tab => (
            <Tabs.Item key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Item>
          ))}
        </Tabs>
      </div>

      <div className="flex-1 overflow-y-auto px-1 py-1">
        {showSkeleton ? (
          <SkeletonList rows={6} height="var(--h-row)" />
        ) : apps.length === 0 ? (
          <EmptyState icon={<Inbox size={20} />} title="Заявок нет" className="py-10" />
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
