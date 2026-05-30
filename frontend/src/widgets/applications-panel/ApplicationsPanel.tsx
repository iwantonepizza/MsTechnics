import { Inbox } from 'lucide-react'
import { useState } from 'react'

import { useActivityLog, type ActivityLogEntry } from '@/entities/activity/hooks'
import { ApplicationCard } from '@/entities/application/ApplicationCard'
import { useApplications } from '@/entities/application/hooks'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { formatRelative } from '@/shared/lib/utils'
import { EmptyState } from '@/shared/ui/EmptyState'
import { SkeletonList } from '@/shared/ui/Skeleton'
import { Tabs } from '@/shared/ui/Tabs'

type Dept = 'monitoring' | 'control' | 'service'

const TABS: Record<Dept, Array<{ value: string; label: string }>> = {
  monitoring: [
    { value: 'received', label: 'Созданные' },
    { value: 'all', label: 'Все' },
    { value: 'history', label: 'История' },
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
  const isHistoryTab = department === 'monitoring' && box === 'history'

  const { data, isLoading } = useApplications({
    display: displaySlug,
    box,
    enabled: !isHistoryTab,
  })
  const { data: history = [], isLoading: historyLoading } = useActivityLog(
    isHistoryTab ? { display: displaySlug, kind: 'application.' } : {},
  )

  const showSkeleton = useDeferredLoading(isHistoryTab ? historyLoading : isLoading)
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
        ) : isHistoryTab ? (
          <ApplicationHistoryTab entries={history} />
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

function ApplicationHistoryTab({
  entries,
}: {
  entries: ActivityLogEntry[]
}) {
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<Inbox size={20} />}
        title="История пуста"
        className="py-10"
      />
    )
  }

  return (
    <div className="space-y-1.5 px-2 py-2" data-testid="applications-history-tab">
      {entries.map(entry => (
        <article
          key={entry.id}
          className="rounded-md border px-3 py-2.5"
          style={{
            borderColor: 'var(--border-subtle)',
            background: 'var(--bg-1)',
          }}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs" style={{ color: 'var(--fg-dim)' }}>
                {entry.description ?? entry.event_type}
              </div>
              {entry.comment ? (
                <div className="mt-1 text-2xs" style={{ color: 'var(--fg-faint)' }}>
                  {entry.comment}
                </div>
              ) : null}
            </div>
            <span
              className="shrink-0 text-2xs"
              style={{ color: 'var(--fg-faint)' }}
            >
              {formatRelative(entry.occurred_at)}
            </span>
          </div>
          <div
            className="mt-1.5 flex items-center justify-between gap-2 text-2xs"
            style={{ color: 'var(--fg-faint)' }}
          >
            <span style={{ fontFamily: 'var(--font-mono)' }}>
              {entry.actor_name ?? 'Система'}
            </span>
            {entry.target_summary ? (
              <span style={{ fontFamily: 'var(--font-mono)' }}>
                {entry.target_summary.kind} #{entry.target_summary.id}
              </span>
            ) : null}
          </div>
        </article>
      ))}
    </div>
  )
}
