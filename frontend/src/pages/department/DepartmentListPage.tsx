import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, PointerEventHandler } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  Building2,
  Camera,
  Circle,
  Clock,
  Copy,
  Cpu,
  Download,
  FileText,
  Inbox,
  MapPin,
  Monitor,
  Package,
  Phone,
  Search,
  SearchX,
  Trash2,
  Upload,
} from 'lucide-react'
import { toast } from 'sonner'

import { ApplicationCard } from '@/entities/application/ApplicationCard'
import { useInfiniteActivityLog } from '@/entities/activity/hooks'
import { useApplications } from '@/entities/application/hooks'
import { useCities, useDisplayDetail, useDisplays } from '@/entities/display/hooks'
import { useMe } from '@/features/auth/hooks'
import { apiClient } from '@/shared/api/client'
import type { City, DisplayDetail, DisplayListItem, DisplayPhoto } from '@/shared/api/types'
import { useResizableValue, useResizeDrag } from '@/shared/lib/useResizableValue'
import { formatRelative, getErrorMessage } from '@/shared/lib/utils'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { Button } from '@/shared/ui/Button'
import { ConfirmDialog, useConfirmDialog } from '@/shared/ui/ConfirmDialog'
import { EmptyState } from '@/shared/ui/EmptyState'
import { InfiniteScrollSentinel } from '@/shared/ui/InfiniteScrollSentinel'
import { Modal } from '@/shared/ui/Modal'
import { ResizeHandle } from '@/shared/ui/ResizeHandle'
import { Skeleton, SkeletonList } from '@/shared/ui/Skeleton'
import { useCrumb } from '@/widgets/navigation/CrumbContext'

type Dept = 'monitoring' | 'control' | 'service'
type SortOption = 'name-asc' | 'name-desc' | 'size-desc' | 'size-asc'
type DisplayActionKind = 'schematic' | 'project' | 'contacts' | 'photos'
type DisplayActionState = {
  kind: DisplayActionKind
  display: DisplayListItem
} | null

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

const SORT_LABELS: Record<SortOption, string> = {
  'name-asc': 'По названию (А-Я)',
  'name-desc': 'По названию (Я-А)',
  'size-desc': 'По размеру (большие выше)',
  'size-asc': 'По размеру (малые выше)',
}

const SORT_STORAGE_KEY = 'department.displaySort'
const CITY_THRESHOLD_FOR_FILTER = 3

function readPersistedSort(): SortOption {
  try {
    const raw = sessionStorage.getItem(SORT_STORAGE_KEY)
    if (raw && raw in SORT_LABELS) return raw as SortOption
  } catch {
    // Ignore private-mode/sessionStorage issues.
  }
  return 'name-asc'
}

function persistSort(value: SortOption): void {
  try {
    sessionStorage.setItem(SORT_STORAGE_KEY, value)
  } catch {
    // Ignore private-mode/sessionStorage issues.
  }
}

function cityKey(city: City) {
  return city.slug ?? city.name
}

function groupDisplays(displays: DisplayListItem[], cities: City[]) {
  const byCity = new Map<string, { city: City; displays: DisplayListItem[] }>()

  cities.forEach(city => byCity.set(cityKey(city), { city, displays: [] }))

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

function sortDisplays(displays: DisplayListItem[], sortBy: SortOption) {
  return [...displays].sort((a, b) => {
    switch (sortBy) {
      case 'name-asc':
        return (a.description ?? a.name).localeCompare(b.description ?? b.name, 'ru')
      case 'name-desc':
        return (b.description ?? b.name).localeCompare(a.description ?? a.name, 'ru')
      case 'size-desc':
        return b.rows * b.cols - a.rows * a.cols
      case 'size-asc':
        return a.rows * a.cols - b.rows * b.cols
    }
  })
}

function isPdfUrl(url: string | null) {
  return Boolean(url?.toLowerCase().includes('.pdf'))
}

function formatPhotoDate(value: string | null) {
  if (!value) return 'Без даты'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('ru-RU')
}

function getDisplayConditionMeta(display: DisplayListItem) {
  const condition = display.aggregated_condition
  if (!condition) {
    return {
      color: 'var(--fg-faint)',
      label: 'Состояние не определено',
      testId: `display-condition-${display.slug}-empty`,
    }
  }
  return {
    color: condition.color.hex,
    label: condition.description ?? condition.name,
    testId: `display-condition-${display.slug}-${condition.name}`,
  }
}

function ActionLink({
  href,
  label,
  icon,
}: {
  href: string
  label: string
  icon: React.ReactNode
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors"
      style={{
        background: 'var(--accent)',
        color: 'var(--accent-ink)',
      }}
    >
      {icon}
      {label}
    </a>
  )
}

function SideRail({
  department,
  activeCity,
  showActivityFeed,
  activityHeight,
  onActivityResize,
}: {
  department: Dept
  activeCity: string | null
  showActivityFeed: boolean
  activityHeight: number
  onActivityResize: PointerEventHandler<HTMLButtonElement>
}) {
  const config = DEPT_CONFIG[department]
  const { data, isLoading, error, refetch } = useApplications({ box: config.boxForRail })
  const showSkeleton = useDeferredLoading(isLoading)
  const items = data?.results?.slice(0, 10) ?? []

  return (
    <aside className="flex min-h-0 flex-col bg-bg-1">
      <div className="min-h-0 flex flex-1 flex-col">
        <div
          className="h-11 shrink-0 px-4 py-3"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-2xs font-mono uppercase tracking-wider"
              style={{ color: 'var(--fg-mute)' }}
            >
              {config.railTitle}
            </span>
            {activeCity ? (
              <span
                className="truncate text-2xs font-mono"
                style={{ color: 'var(--fg-faint)' }}
              >
                {activeCity}
              </span>
            ) : null}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-1.5">
          {error ? (
            <div
              className="flex h-40 flex-col items-center justify-center gap-2 text-xs"
              style={{ color: 'var(--err)' }}
            >
              <AlertTriangle size={18} />
              <span>Не удалось загрузить</span>
              <button className="btn btn-secondary sm" onClick={() => refetch()}>
                Повторить
              </button>
            </div>
          ) : showSkeleton ? (
            <SkeletonList rows={6} height="var(--h-row)" />
          ) : items.length === 0 ? (
            <EmptyState icon={<Inbox size={20} />} title="Пусто" className="py-10" />
          ) : (
            items.map(app => <ApplicationCard key={app.id} application={app} compact />)
          )}
        </div>
      </div>

      {showActivityFeed ? (
        <>
          <ResizeHandle
            orientation="horizontal"
            label="Изменить высоту ленты активности"
            onPointerDown={onActivityResize}
            testId="department-activity-resize-handle"
          />
          <ActivityFeedBand height={activityHeight} />
        </>
      ) : null}
    </aside>
  )
}

function ActivityFeedBand({ height }: { height: number }) {
  const activityQuery = useInfiniteActivityLog({ feed: true, limit: 60 })
  const data = activityQuery.entries
  const show = useDeferredLoading(activityQuery.isLoading)

  return (
    <div
      className="flex shrink-0 flex-col"
      style={{
        height,
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-0)',
      }}
      data-testid="department-activity-feed"
    >
      <div
        className="flex h-9 shrink-0 items-center justify-between px-3"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: 'var(--fg)' }}>
          <Activity size={13} style={{ color: 'var(--fg-dim)' }} />
          Последние действия
        </div>
        <span className="rounded px-1.5 py-0.5 text-2xs" style={{ color: 'var(--fg-faint)' }}>
          Всё время
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {show ? (
          <SkeletonList rows={4} height="28px" />
        ) : activityQuery.isError && data.length === 0 ? (
          <div
            className="flex h-full flex-col items-center justify-center gap-2 text-xs"
            style={{ color: 'var(--err)' }}
          >
            <span>Не удалось загрузить последние действия</span>
            <button type="button" className="btn btn-secondary sm" onClick={() => void activityQuery.refetch()}>
              Повторить
            </button>
          </div>
        ) : data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs" style={{ color: 'var(--fg-faint)' }}>
            Действий за период нет
          </div>
        ) : (
          <div className="space-y-1">
            {data.map(entry => (
              <div
                key={entry.id}
                className="flex items-center justify-between gap-2 rounded px-2 py-1 text-xs"
                style={{ background: 'var(--bg-1)' }}
              >
                <span className="truncate" style={{ color: 'var(--fg-dim)' }}>
                  {entry.description}
                </span>
                <span className="flex shrink-0 gap-2 text-2xs" style={{ color: 'var(--fg-faint)' }}>
                  <span className="font-mono">{entry.actor_name}</span>
                  <span>{formatRelative(entry.occurred_at)}</span>
                </span>
              </div>
            ))}
            <InfiniteScrollSentinel
              hasMore={Boolean(activityQuery.hasNextPage)}
              loading={activityQuery.isFetchingNextPage}
              onLoadMore={() => void activityQuery.fetchNextPage()}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function AssetModal({
  open,
  onClose,
  title,
  slug,
  kind,
  url,
  loading,
  canManage,
  onRefresh,
}: {
  open: boolean
  onClose: () => void
  title: string
  slug: string
  kind: 'schematic' | 'project'
  url: string | null
  loading: boolean
  canManage: boolean
  onRefresh: () => Promise<unknown>
}) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!open) {
      setError(null)
      setUploading(false)
    }
  }, [open])

  const handleUpload = async (file: File | null | undefined) => {
    if (!file) return
    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      await apiClient.post(`/displays/${slug}/assets/${kind}/`, formData)
      await onRefresh()
      if (inputRef.current) inputRef.current.value = ''
      toast.success('Файл загружен')
    } catch (uploadError: unknown) {
      setError(getErrorMessage(uploadError))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={title} size="lg">
      <Modal.Body className="space-y-4">
        {canManage ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
            style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
          >
            <div>
              <div className="text-sm font-medium" style={{ color: 'var(--fg)' }}>
                {url ? 'Обновить файл' : 'Загрузить файл'}
              </div>
              <div className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
                Поддерживаются PDF и изображения до 10 МБ.
              </div>
            </div>
            <label
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-colors"
              style={{
                background: 'var(--accent)',
                color: 'var(--accent-ink)',
                opacity: uploading ? 0.7 : 1,
              }}
            >
              <Upload size={12} />
              {uploading ? 'Загрузка...' : 'Выбрать файл'}
              <input
                ref={inputRef}
                type="file"
                accept="image/*,application/pdf"
                className="sr-only"
                data-testid={`asset-upload-${kind}`}
                onChange={event => void handleUpload(event.target.files?.[0])}
              />
            </label>
          </div>
        ) : null}

        {error ? (
          <div
            className="rounded-md border px-3 py-2 text-xs"
            style={{ color: 'var(--err)', borderColor: 'var(--err-faint)' }}
          >
            {error}
          </div>
        ) : null}

        {loading ? (
          <Skeleton style={{ height: '420px', borderRadius: 'var(--r-md)' }} />
        ) : !url ? (
          <EmptyState
            icon={<FileText size={20} />}
            title="Файл не загружен"
            description={canManage ? 'Нажмите «Выбрать файл», чтобы добавить вложение.' : 'Для этого экрана пока нет вложения.'}
          />
        ) : isPdfUrl(url) ? (
          <iframe
            src={url}
            title={title}
            className="w-full rounded-md"
            style={{ height: '65vh', border: '1px solid var(--border-subtle)' }}
          />
        ) : (
          <a href={url} target="_blank" rel="noreferrer" title="Открыть в новой вкладке">
            <img
              src={url}
              alt={title}
              className="max-h-[65vh] w-full rounded-md object-contain"
              style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-0)' }}
            />
          </a>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="ghost" onClick={onClose}>
          Закрыть
        </Button>
        {url ? <ActionLink href={url} label="Скачать" icon={<Download size={12} />} /> : null}
      </Modal.Footer>
    </Modal>
  )
}

function ContactsModal({
  open,
  onClose,
  title,
  detail,
  loading,
}: {
  open: boolean
  onClose: () => void
  title: string
  detail: DisplayDetail | undefined
  loading: boolean
}) {
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const handleCopy = async (id: number, phone: string | null) => {
    if (!phone) return
    await navigator.clipboard.writeText(phone)
    setCopiedId(id)
    window.setTimeout(() => {
      setCopiedId(current => (current === id ? null : current))
    }, 1200)
  }

  return (
    <Modal open={open} onClose={onClose} title={title} size="md">
      <Modal.Body>
        {loading ? (
          <SkeletonList rows={4} height="var(--h-row)" />
        ) : !detail || detail.contacts.length === 0 ? (
          <EmptyState
            icon={<Phone size={20} />}
            title="Контактов нет"
            description="Для этого экрана ещё не добавили контакт-лист"
          />
        ) : (
          <div className="space-y-2">
            {detail.contacts.map(contact => (
              <div
                key={contact.id}
                className="flex items-center justify-between gap-3 rounded-md border p-3"
                style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium" style={{ color: 'var(--fg)' }}>
                    {contact.full_name || 'Без имени'}
                  </div>
                  <div className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
                    {contact.description || 'Без должности'}
                  </div>
                  <div className="mt-1 text-xs font-mono" style={{ color: 'var(--fg-faint)' }}>
                    {contact.phone || 'Телефон не указан'}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {contact.phone ? (
                    <a href={`tel:${contact.phone}`}>
                      <Button variant="ghost" size="sm">Позвонить</Button>
                    </a>
                  ) : null}
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<Copy size={12} />}
                    onClick={() => void handleCopy(contact.id, contact.phone)}
                    data-testid={`contact-copy-${contact.id}`}
                    disabled={!contact.phone}
                  >
                    {copiedId === contact.id ? 'Скопировано' : 'Копировать'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal.Body>
    </Modal>
  )
}

function PhotoBankModal({
  open,
  onClose,
  title,
  slug,
  detail,
  loading,
  canManage,
  onRefresh,
}: {
  open: boolean
  onClose: () => void
  title: string
  slug: string
  detail: DisplayDetail | undefined
  loading: boolean
  canManage: boolean
  onRefresh: () => Promise<unknown>
}) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [photoToDelete, setPhotoToDelete] = useState<DisplayPhoto | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const confirmDelete = useConfirmDialog()

  useEffect(() => {
    if (!open) {
      setError(null)
      setPhotoToDelete(null)
    }
  }, [open])

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    setError(null)

    try {
      for (const file of Array.from(files)) {
        const formData = new FormData()
        formData.append('file', file)
        await apiClient.post(`/displays/${slug}/photos/`, formData)
      }
      await onRefresh()
      if (inputRef.current) inputRef.current.value = ''
      toast.success('Фотографии загружены')
    } catch (uploadError: unknown) {
      setError(getErrorMessage(uploadError))
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!photoToDelete) return
    setError(null)
    try {
      await apiClient.delete(`/displays/${slug}/photos/${photoToDelete.id}/`)
      await onRefresh()
      setPhotoToDelete(null)
      toast.success('Фото удалено')
    } catch (deleteError: unknown) {
      setError(getErrorMessage(deleteError))
      throw deleteError
    }
  }

  return (
    <>
      <Modal open={open} onClose={onClose} title={title} size="lg">
        <Modal.Body className="space-y-4">
          {canManage ? (
            <div
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
              style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
            >
              <div>
                <div className="text-sm font-medium" style={{ color: 'var(--fg)' }}>
                  Добавить фотографии
                </div>
                <div className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
                  Можно выбрать сразу несколько файлов
                </div>
              </div>
              <label
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-colors"
                style={{
                  background: 'var(--accent)',
                  color: 'var(--accent-ink)',
                  opacity: uploading ? 0.7 : 1,
                }}
              >
                <Upload size={12} />
                {uploading ? 'Загрузка...' : 'Выбрать файлы'}
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  className="sr-only"
                  data-testid="photo-upload-input"
                  onChange={event => void handleUpload(event.target.files)}
                />
              </label>
            </div>
          ) : null}

          {error ? (
            <div
              className="rounded-md border px-3 py-2 text-xs"
              style={{ color: 'var(--err)', borderColor: 'var(--err-faint)' }}
            >
              {error}
            </div>
          ) : null}

          {loading ? (
            <SkeletonList rows={4} height="160px" />
          ) : !detail || detail.photos.length === 0 ? (
            <EmptyState
              icon={<Camera size={20} />}
              title="Фотобанк пуст"
              description="Для этого экрана пока нет загруженных фотографий"
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {detail.photos.map(photo => (
                <div
                  key={photo.id}
                  className="overflow-hidden rounded-md border"
                  style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-0)' }}
                >
                  {photo.url ? (
                    <a href={photo.url} target="_blank" rel="noreferrer" title="Открыть фото">
                      <img src={photo.url} alt={`Фото ${photo.id}`} className="h-44 w-full object-cover" />
                    </a>
                  ) : (
                    <div
                      className="flex h-44 items-center justify-center text-xs"
                      style={{ color: 'var(--fg-faint)' }}
                    >
                      Нет превью
                    </div>
                  )}
                  <div className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="text-2xs" style={{ color: 'var(--fg-faint)' }}>
                      {formatPhotoDate(photo.uploaded_at)}
                    </span>
                    <div className="flex items-center gap-2">
                      {photo.url ? (
                        <ActionLink href={photo.url} label="Открыть" icon={<Download size={12} />} />
                      ) : null}
                      {canManage ? (
                        <Button
                          variant="danger"
                          size="sm"
                          icon={<Trash2 size={12} />}
                          onClick={() => {
                            setPhotoToDelete(photo)
                            confirmDelete.ask()
                          }}
                          data-testid={`photo-delete-${photo.id}`}
                        >
                          Удалить
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Modal.Body>
      </Modal>

      <ConfirmDialog
        {...confirmDelete.props}
        onConfirm={handleDelete}
        title="Удалить фото?"
        description={
          photoToDelete
            ? `Фотография #${photoToDelete.id} будет удалена без возможности восстановления.`
            : 'Фотография будет удалена без возможности восстановления.'
        }
        confirmText="Удалить"
        variant="danger"
      />
    </>
  )
}

function DisplayRow({
  display,
  department,
  onOpenAction,
}: {
  display: DisplayListItem
  department: Dept
  onOpenAction: (kind: DisplayActionKind, display: DisplayListItem) => void
}) {
  const conditionMeta = getDisplayConditionMeta(display)

  return (
    <div
      className="rounded-md border transition-colors hover:bg-bg-3 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2"
      style={{
        background: 'var(--bg-1)',
        borderColor: 'var(--border-subtle)',
        outlineColor: 'var(--accent)',
      }}
    >
      <Link
        to={`/${department}/${display.city.slug}/${display.slug}`}
        className="grid grid-cols-[1fr_auto] items-center gap-3 px-3 py-2.5 focus:outline-none"
        data-testid={`display-card-${display.slug}`}
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center"
              title={conditionMeta.label}
              aria-label={conditionMeta.label}
              data-testid={conditionMeta.testId}
            >
              <Circle size={10} fill={conditionMeta.color} stroke={conditionMeta.color} />
            </span>
            <Monitor size={13} style={{ color: 'var(--fg-mute)' }} />
            <span className="truncate text-sm font-medium" style={{ color: 'var(--fg)' }}>
              {display.description ?? display.name}
            </span>
          </div>
          <div
            className="mt-1 flex items-center gap-2 text-2xs font-mono"
            style={{ color: 'var(--fg-faint)' }}
          >
            <span>
              {display.rows}x{display.cols}
            </span>
            <span style={{ color: 'var(--border)' }}>В·</span>
            <span>{display.name}</span>
          </div>
        </div>
        <ArrowRight size={13} style={{ color: 'var(--fg-faint)' }} />
      </Link>

      <div
        className="space-y-2 px-3 pb-2 pt-1"
        style={{ borderTop: '1px solid var(--border-subtle)' }}
      >
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => onOpenAction('schematic', display)}
            className="icon-btn"
            title="Электросхема"
            data-testid={`display-action-schematic-${display.slug}`}
          >
            <Cpu size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('project', display)}
            className="icon-btn"
            title="Проект"
            data-testid={`display-action-project-${display.slug}`}
          >
            <FileText size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('contacts', display)}
            className="icon-btn"
            title="Контакты"
            data-testid={`display-action-contacts-${display.slug}`}
          >
            <Phone size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('photos', display)}
            className="icon-btn"
            title="Фотобанк"
            data-testid={`display-action-photos-${display.slug}`}
          >
            <Camera size={13} />
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-2xs" style={{ color: 'var(--fg-faint)' }}>
          <Link
            to={`/zip/${display.slug}`}
            className="inline-flex items-center gap-1 hover:text-fg-dim"
            title="ЗИП экрана"
            data-testid={`quicklink-zip-${display.slug}`}
          >
            <Package size={11} /> ЗИП
          </Link>
          {display.application_count > 0 ? (
            <span
              className="inline-flex items-center gap-1"
              style={{ color: 'var(--fg-dim)' }}
              data-testid={`display-application-count-${display.slug}`}
            >
              Заявки: {display.application_count}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function CityBlock({
  city,
  displays,
  department,
  active,
  onActivate,
  onOpenAction,
}: {
  city: City
  displays: DisplayListItem[]
  department: Dept
  active: boolean
  onActivate: () => void
  onOpenAction: (kind: DisplayActionKind, display: DisplayListItem) => void
}) {
  return (
    <section
      className="border-b"
      style={{
        borderColor: 'var(--border-subtle)',
        background: active ? 'var(--bg-1)' : 'transparent',
      }}
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
      </button>

      <div
        className="grid gap-2 px-6 pb-4"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}
      >
        {displays.map(display => (
          <DisplayRow
            key={display.id}
            display={display}
            department={department}
            onOpenAction={onOpenAction}
          />
        ))}
      </div>
    </section>
  )
}

export function DepartmentListPage({ department }: { department: Dept }) {
  const { citySlug } = useParams<{ citySlug?: string }>()
  const { setCrumb } = useCrumb()
  const { data: me } = useMe()
  const {
    data: cities = [],
    isLoading: citiesLoading,
    error: citiesError,
    refetch: refetchCities,
  } = useCities()
  const {
    data: displays = [],
    isLoading: displaysLoading,
    error: displaysError,
    refetch: refetchDisplays,
  } = useDisplays()
  const [activeCity, setActiveCity] = useState<string | null>(citySlug ?? null)
  const [sortBy, setSortBy] = useState<SortOption>(readPersistedSort)
  const [cityQuery, setCityQuery] = useState('')
  const [activeAction, setActiveAction] = useState<DisplayActionState>(null)
  const showActivityFeed = Boolean((me as { show_activity_feed?: boolean } | undefined)?.show_activity_feed)
  const canManageMedia = department === 'service' || me?.permission === 'admin' || me?.permission === 'all'
  const [railWidth, setRailWidth] = useResizableValue({
    storageKey: `department-list:${department}:rail-width`,
    defaultValue: 320,
    min: 260,
    max: 520,
  })
  const [activityHeight, setActivityHeight] = useResizableValue({
    storageKey: `department-list:${department}:activity-height`,
    defaultValue: 170,
    min: 120,
    max: 420,
  })
  const onRailResize = useResizeDrag({
    value: railWidth,
    setValue: setRailWidth,
    axis: 'x',
    direction: -1,
    min: 260,
    max: 520,
  })
  const onActivityResize = useResizeDrag({
    value: activityHeight,
    setValue: setActivityHeight,
    axis: 'y',
    direction: -1,
    min: 120,
    max: 420,
  })

  const config = DEPT_CONFIG[department]
  const showSkeleton = useDeferredLoading(citiesLoading || displaysLoading)
  const error = citiesError || displaysError
  const { data: activeDisplayDetail, isLoading: detailLoading, refetch: refetchDetail } =
    useDisplayDetail(activeAction?.display.slug ?? null)

  const handleSortChange = (value: SortOption) => {
    setSortBy(value)
    persistSort(value)
  }

  const groups = useMemo(() => {
    const filteredByRoute = displays.filter(display => !citySlug || display.city.slug === citySlug)
    const grouped = groupDisplays(filteredByRoute, cities)
    const query = cityQuery.trim().toLowerCase()
    const filteredByCity = query
      ? grouped.filter(group => group.city.name.toLowerCase().includes(query))
      : grouped

    return filteredByCity.map(group => ({
      ...group,
      displays: sortDisplays(group.displays, sortBy),
    }))
  }, [cities, cityQuery, citySlug, displays, sortBy])

  const totalCities = new Set(displays.map(display => display.city.slug ?? display.city.name)).size
  const showCityFilter = totalCities >= CITY_THRESHOLD_FOR_FILTER

  useEffect(() => {
    setCrumb(
      <span className="flex items-center gap-2 text-xs" style={{ color: 'var(--fg-mute)' }}>
        <span>{config.title}</span>
        {citySlug ? (
          <span className="font-mono" style={{ color: 'var(--fg-faint)' }}>
            /{citySlug}
          </span>
        ) : null}
      </span>,
    )
    return () => setCrumb(null)
  }, [citySlug, config.title, setCrumb])

  useEffect(() => {
    if (!activeCity && groups[0]) {
      setActiveCity(cityKey(groups[0].city))
    }
  }, [activeCity, groups])

  const openAction = (kind: DisplayActionKind, display: DisplayListItem) => {
    setActiveAction({ kind, display })
  }

  const closeAction = () => {
    setActiveAction(null)
  }

  return (
    <>
      <div
        className="department-list-layout h-full min-h-0"
        style={{
          '--department-rail-width': `${railWidth}px`,
          background: 'var(--border-subtle)',
        } as CSSProperties}
        data-testid="department-list-layout"
      >
        <main className="min-h-0 overflow-y-auto bg-bg-0">
          <div
            className="sticky top-0 z-10 flex flex-wrap items-end justify-between gap-3 bg-bg-0 px-6 py-3"
            style={{ borderBottom: '1px solid var(--border-subtle)' }}
          >
            <div>
              <h1 className="text-md font-semibold" style={{ color: 'var(--fg)' }}>
                {config.title}
              </h1>
              <div
                className="mt-0.5 flex items-center gap-2 text-2xs"
                style={{ color: 'var(--fg-faint)' }}
              >
                <Clock size={11} />
                <span>
                  {groups.length} городов ·{' '}
                  {groups.reduce((sum, group) => sum + group.displays.length, 0)} экранов
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {showCityFilter ? (
                <label className="relative flex items-center" data-testid="city-filter">
                  <Search
                    size={12}
                    className="pointer-events-none absolute left-2"
                    style={{ color: 'var(--fg-mute)' }}
                  />
                  <input
                    type="search"
                    placeholder="Город..."
                    value={cityQuery}
                    onChange={event => setCityQuery(event.target.value)}
                    className="input pl-7"
                    style={{ width: 160 }}
                  />
                </label>
              ) : null}

              <label
                className="flex items-center gap-1.5 text-xs"
                style={{ color: 'var(--fg-mute)' }}
                data-testid="sort-select"
              >
                <ArrowUpDown size={11} />
                <select
                  value={sortBy}
                  onChange={event => handleSortChange(event.target.value as SortOption)}
                  className="input"
                >
                  {(Object.entries(SORT_LABELS) as [SortOption, string][]).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {error ? (
            <div
              className="flex h-80 flex-col items-center justify-center gap-3 text-xs"
              style={{ color: 'var(--err)' }}
            >
              <AlertTriangle size={22} />
              <span>Не удалось загрузить список экранов</span>
              <button
                className="btn btn-secondary sm"
                onClick={() => void Promise.all([refetchCities(), refetchDisplays()])}
              >
                Повторить
              </button>
            </div>
          ) : showSkeleton ? (
            <div className="space-y-4 p-6">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index}>
                  <Skeleton
                    style={{ height: 'var(--skel-h-row)', width: '160px', marginBottom: '12px' }}
                  />
                  <div
                    className="grid gap-2"
                    style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}
                  >
                    {Array.from({ length: 4 }).map((__, itemIndex) => (
                      <Skeleton
                        key={itemIndex}
                        style={{ height: 'var(--skel-h-card)', borderRadius: 'var(--r-md)' }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : groups.length === 0 ? (
            cityQuery ? (
              <EmptyState
                icon={<SearchX size={24} />}
                title="Городов не найдено"
                description={`По запросу «${cityQuery}» ничего не нашлось`}
              />
            ) : (
              <EmptyState
                icon={<Building2 size={24} />}
                title="Нет доступных экранов"
                description="Попросите администратора добавить города"
              />
            )
          ) : (
            groups.map(group => (
              <CityBlock
                key={cityKey(group.city)}
                city={group.city}
                displays={group.displays}
                department={department}
                active={activeCity === cityKey(group.city)}
                onActivate={() => setActiveCity(cityKey(group.city))}
                onOpenAction={openAction}
              />
            ))
          )}
        </main>

        <ResizeHandle
          orientation="vertical"
          label="Изменить ширину правой панели"
          className="hidden md:flex"
          onPointerDown={onRailResize}
          testId="department-rail-resize-handle"
        />

        <div className="hidden min-h-0 md:block">
          <SideRail
            department={department}
            activeCity={activeCity}
            showActivityFeed={showActivityFeed}
            activityHeight={activityHeight}
            onActivityResize={onActivityResize}
          />
        </div>
      </div>

      {activeAction?.kind === 'schematic' ? (
        <AssetModal
          open
          onClose={closeAction}
          title={`Электросхема · ${activeAction.display.description ?? activeAction.display.name}`}
          slug={activeAction.display.slug}
          kind="schematic"
          url={activeDisplayDetail?.file_url ?? null}
          loading={detailLoading}
          canManage={canManageMedia}
          onRefresh={refetchDetail}
        />
      ) : null}

      {activeAction?.kind === 'project' ? (
        <AssetModal
          open
          onClose={closeAction}
          title={`Проект · ${activeAction.display.description ?? activeAction.display.name}`}
          slug={activeAction.display.slug}
          kind="project"
          url={activeDisplayDetail?.project_photo_url ?? null}
          loading={detailLoading}
          canManage={canManageMedia}
          onRefresh={refetchDetail}
        />
      ) : null}

      {activeAction?.kind === 'contacts' ? (
        <ContactsModal
          open
          onClose={closeAction}
          title={`Контакты · ${activeAction.display.description ?? activeAction.display.name}`}
          detail={activeDisplayDetail}
          loading={detailLoading}
        />
      ) : null}

      {activeAction?.kind === 'photos' ? (
        <PhotoBankModal
          open
          onClose={closeAction}
          title={`Фотобанк · ${activeAction.display.description ?? activeAction.display.name}`}
          slug={activeAction.display.slug}
          detail={activeDisplayDetail}
          loading={detailLoading}
          canManage={canManageMedia}
          onRefresh={refetchDetail}
        />
      ) : null}
    </>
  )
}
