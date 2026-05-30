import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  Building2,
  Camera,
  Circle,
  ClipboardList,
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
import { useApplications } from '@/entities/application/hooks'
import { useCities, useDisplayDetail, useDisplays } from '@/entities/display/hooks'
import { apiClient } from '@/shared/api/client'
import type { City, DisplayDetail, DisplayListItem, DisplayPhoto } from '@/shared/api/types'
import { useDeferredLoading } from '@/shared/lib/useDeferredLoading'
import { Button } from '@/shared/ui/Button'
import { ConfirmDialog, useConfirmDialog } from '@/shared/ui/ConfirmDialog'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Modal } from '@/shared/ui/Modal'
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
    title: 'РњРѕРЅРёС‚РѕСЂРёРЅРі вЂ” СЃРїРёСЃРѕРє СЌРєСЂР°РЅРѕРІ',
    railTitle: 'РџРѕСЃР»РµРґРЅРёРµ Р·Р°СЏРІРєРё',
    boxForRail: 'received',
  },
  control: {
    title: 'РљРѕРЅС‚СЂРѕР»СЊ вЂ” СЃРїРёСЃРѕРє СЌРєСЂР°РЅРѕРІ',
    railTitle: 'РћС‡РµСЂРµРґСЊ РєРѕРЅС‚СЂРѕР»СЏ',
    boxForRail: 'received',
  },
  service: {
    title: 'РЎРµСЂРІРёСЃ вЂ” СЃРїРёСЃРѕРє СЌРєСЂР°РЅРѕРІ',
    railTitle: 'РњРѕРё РІ СЂР°Р±РѕС‚Рµ',
    boxForRail: 'at_work',
  },
}

const SORT_LABELS: Record<SortOption, string> = {
  'name-asc': 'РџРѕ РЅР°Р·РІР°РЅРёСЋ (Рђ-РЇ)',
  'name-desc': 'РџРѕ РЅР°Р·РІР°РЅРёСЋ (РЇ-Рђ)',
  'size-desc': 'РџРѕ СЂР°Р·РјРµСЂСѓ (Р±РѕР»СЊС€РёРµ РІС‹С€Рµ)',
  'size-asc': 'РџРѕ СЂР°Р·РјРµСЂСѓ (РјР°Р»С‹Рµ РІС‹С€Рµ)',
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
  if (!value) return 'Р‘РµР· РґР°С‚С‹'
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

function SideRail({ department, activeCity }: { department: Dept; activeCity: string | null }) {
  const config = DEPT_CONFIG[department]
  const { data, isLoading, error, refetch } = useApplications({ box: config.boxForRail })
  const showSkeleton = useDeferredLoading(isLoading)
  const items = data?.results?.slice(0, 10) ?? []

  return (
    <aside className="flex min-h-0 flex-col bg-bg-1">
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
            <span>РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ</span>
            <button className="btn btn-secondary sm" onClick={() => refetch()}>
              РџРѕРІС‚РѕСЂРёС‚СЊ
            </button>
          </div>
        ) : showSkeleton ? (
          <SkeletonList rows={6} height="var(--h-row)" />
        ) : items.length === 0 ? (
          <EmptyState icon={<Inbox size={20} />} title="РџСѓСЃС‚Рѕ" className="py-10" />
        ) : (
          items.map(app => <ApplicationCard key={app.id} application={app} compact />)
        )}
      </div>
    </aside>
  )
}

function AssetModal({
  open,
  onClose,
  title,
  url,
  loading,
}: {
  open: boolean
  onClose: () => void
  title: string
  url: string | null
  loading: boolean
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="lg">
      <Modal.Body className="space-y-4">
        {loading ? (
          <Skeleton style={{ height: '420px', borderRadius: 'var(--r-md)' }} />
        ) : !url ? (
          <EmptyState
            icon={<FileText size={20} />}
            title="Р¤Р°Р№Р» РЅРµ Р·Р°РіСЂСѓР¶РµРЅ"
            description="Р”Р»СЏ СЌС‚РѕРіРѕ СЌРєСЂР°РЅР° РїРѕРєР° РЅРµС‚ РІР»РѕР¶РµРЅРёСЏ"
          />
        ) : isPdfUrl(url) ? (
          <iframe
            src={url}
            title={title}
            className="w-full rounded-md"
            style={{ height: '65vh', border: '1px solid var(--border-subtle)' }}
          />
        ) : (
          <img
            src={url}
            alt={title}
            className="max-h-[65vh] w-full rounded-md object-contain"
            style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-0)' }}
          />
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="ghost" onClick={onClose}>
          Р—Р°РєСЂС‹С‚СЊ
        </Button>
        {url ? <ActionLink href={url} label="РЎРєР°С‡Р°С‚СЊ" icon={<Download size={12} />} /> : null}
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
            title="РљРѕРЅС‚Р°РєС‚РѕРІ РЅРµС‚"
            description="Р”Р»СЏ СЌС‚РѕРіРѕ СЌРєСЂР°РЅР° РµС‰С‘ РЅРµ РґРѕР±Р°РІРёР»Рё РєРѕРЅС‚Р°РєС‚-Р»РёСЃС‚"
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
                    {contact.full_name || 'Р‘РµР· РёРјРµРЅРё'}
                  </div>
                  <div className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
                    {contact.description || 'Р‘РµР· РґРѕР»Р¶РЅРѕСЃС‚Рё'}
                  </div>
                  <div className="mt-1 text-xs font-mono" style={{ color: 'var(--fg-faint)' }}>
                    {contact.phone || 'РўРµР»РµС„РѕРЅ РЅРµ СѓРєР°Р·Р°РЅ'}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {contact.phone ? (
                    <a href={`tel:${contact.phone}`}>
                      <Button variant="ghost" size="sm">РџРѕР·РІРѕРЅРёС‚СЊ</Button>
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
                    {copiedId === contact.id ? 'РЎРєРѕРїРёСЂРѕРІР°РЅРѕ' : 'РљРѕРїРёСЂРѕРІР°С‚СЊ'}
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
        await apiClient.post(`/displays/${slug}/photos/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      await onRefresh()
      if (inputRef.current) inputRef.current.value = ''
      toast.success('Р¤РѕС‚РѕРіСЂР°С„РёРё Р·Р°РіСЂСѓР¶РµРЅС‹')
    } catch (uploadError: unknown) {
      const detailMessage = (
        uploadError as { response?: { data?: { detail?: string } } }
      )?.response?.data?.detail
      setError(detailMessage ?? 'РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ С„РѕС‚РѕРіСЂР°С„РёРё')
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
      toast.success('Р¤РѕС‚Рѕ СѓРґР°Р»РµРЅРѕ')
    } catch (deleteError: unknown) {
      const detailMessage = (
        deleteError as { response?: { data?: { detail?: string } } }
      )?.response?.data?.detail
      setError(detailMessage ?? 'РќРµ СѓРґР°Р»РѕСЃСЊ СѓРґР°Р»РёС‚СЊ С„РѕС‚Рѕ')
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
                  Р”РѕР±Р°РІРёС‚СЊ С„РѕС‚РѕРіСЂР°С„РёРё
                </div>
                <div className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
                  РњРѕР¶РЅРѕ РІС‹Р±СЂР°С‚СЊ СЃСЂР°Р·Сѓ РЅРµСЃРєРѕР»СЊРєРѕ С„Р°Р№Р»РѕРІ
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
                {uploading ? 'Р—Р°РіСЂСѓР·РєР°...' : 'Р’С‹Р±СЂР°С‚СЊ С„Р°Р№Р»С‹'}
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
              title="Р¤РѕС‚РѕР±Р°РЅРє РїСѓСЃС‚"
              description="Р”Р»СЏ СЌС‚РѕРіРѕ СЌРєСЂР°РЅР° РїРѕРєР° РЅРµС‚ Р·Р°РіСЂСѓР¶РµРЅРЅС‹С… С„РѕС‚РѕРіСЂР°С„РёР№"
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
                    <img src={photo.url} alt={`Р¤РѕС‚Рѕ ${photo.id}`} className="h-44 w-full object-cover" />
                  ) : (
                    <div
                      className="flex h-44 items-center justify-center text-xs"
                      style={{ color: 'var(--fg-faint)' }}
                    >
                      РќРµС‚ РїСЂРµРІСЊСЋ
                    </div>
                  )}
                  <div className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="text-2xs" style={{ color: 'var(--fg-faint)' }}>
                      {formatPhotoDate(photo.uploaded_at)}
                    </span>
                    <div className="flex items-center gap-2">
                      {photo.url ? (
                        <ActionLink href={photo.url} label="РћС‚РєСЂС‹С‚СЊ" icon={<Download size={12} />} />
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
                          РЈРґР°Р»РёС‚СЊ
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
        title="РЈРґР°Р»РёС‚СЊ С„РѕС‚Рѕ?"
        description={
          photoToDelete
            ? `Р¤РѕС‚РѕРіСЂР°С„РёСЏ #${photoToDelete.id} Р±СѓРґРµС‚ СѓРґР°Р»РµРЅР° Р±РµР· РІРѕР·РјРѕР¶РЅРѕСЃС‚Рё РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ.`
            : 'Р¤РѕС‚РѕРіСЂР°С„РёСЏ Р±СѓРґРµС‚ СѓРґР°Р»РµРЅР° Р±РµР· РІРѕР·РјРѕР¶РЅРѕСЃС‚Рё РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ.'
        }
        confirmText="РЈРґР°Р»РёС‚СЊ"
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
            title="Р­Р»РµРєС‚СЂРѕСЃС…РµРјР°"
            data-testid={`display-action-schematic-${display.slug}`}
          >
            <Cpu size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('project', display)}
            className="icon-btn"
            title="РџСЂРѕРµРєС‚"
            data-testid={`display-action-project-${display.slug}`}
          >
            <FileText size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('contacts', display)}
            className="icon-btn"
            title="РљРѕРЅС‚Р°РєС‚С‹"
            data-testid={`display-action-contacts-${display.slug}`}
          >
            <Phone size={13} />
          </button>
          <button
            type="button"
            onClick={() => onOpenAction('photos', display)}
            className="icon-btn"
            title="Р¤РѕС‚РѕР±Р°РЅРє"
            data-testid={`display-action-photos-${display.slug}`}
          >
            <Camera size={13} />
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-2xs" style={{ color: 'var(--fg-faint)' }}>
          <Link
            to={`/zip/${display.slug}`}
            className="inline-flex items-center gap-1 hover:text-fg-dim"
            title="Р—РРџ СЌРєСЂР°РЅР°"
            data-testid={`quicklink-zip-${display.slug}`}
          >
            <Package size={11} /> Р—РРџ
          </Link>
          <Link
            to={`/control/${display.city.slug}/${display.slug}`}
            className="inline-flex items-center gap-1 hover:text-fg-dim"
            title="Р’СЃРµ Р·Р°СЏРІРєРё РїРѕ СЌРєСЂР°РЅСѓ"
            data-testid={`quicklink-applications-${display.slug}`}
          >
            <ClipboardList size={11} /> Р—Р°СЏРІРєРё
          </Link>
          <Link
            to={`/${department}/${display.city.slug}/${display.slug}?tab=history`}
            className="inline-flex items-center gap-1 hover:text-fg-dim"
            title="Р–СѓСЂРЅР°Р» СЃРѕР±С‹С‚РёР№ РїРѕ СЌРєСЂР°РЅСѓ"
            data-testid={`quicklink-history-${display.slug}`}
          >
            <Activity size={11} /> РСЃС‚РѕСЂРёСЏ
          </Link>
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
            {displays.length} СЌРєСЂР°РЅРѕРІ
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
  const { data: cities = [], isLoading: citiesLoading, error: citiesError } = useCities()
  const {
    data: displays = [],
    isLoading: displaysLoading,
    error: displaysError,
    refetch,
  } = useDisplays()
  const [activeCity, setActiveCity] = useState<string | null>(citySlug ?? null)
  const [sortBy, setSortBy] = useState<SortOption>(readPersistedSort)
  const [cityQuery, setCityQuery] = useState('')
  const [activeAction, setActiveAction] = useState<DisplayActionState>(null)

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
        className="grid h-full min-h-0 grid-cols-1 md:grid-cols-[1fr_320px]"
        style={{ background: 'var(--border-subtle)' }}
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
                  {groups.length} РіРѕСЂРѕРґРѕРІ В·{' '}
                  {groups.reduce((sum, group) => sum + group.displays.length, 0)} СЌРєСЂР°РЅРѕРІ
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
                    placeholder="Р“РѕСЂРѕРґ..."
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
              <span>РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ СЃРїРёСЃРѕРє СЌРєСЂР°РЅРѕРІ</span>
              <button className="btn btn-secondary sm" onClick={() => refetch()}>
                РџРѕРІС‚РѕСЂРёС‚СЊ
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
                title="Р“РѕСЂРѕРґРѕРІ РЅРµ РЅР°Р№РґРµРЅРѕ"
                description={`РџРѕ Р·Р°РїСЂРѕСЃСѓ В«${cityQuery}В» РЅРёС‡РµРіРѕ РЅРµ РЅР°С€Р»РѕСЃСЊ`}
              />
            ) : (
              <EmptyState
                icon={<Building2 size={24} />}
                title="РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… СЌРєСЂР°РЅРѕРІ"
                description="РџРѕРїСЂРѕСЃРёС‚Рµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° РґРѕР±Р°РІРёС‚СЊ РіРѕСЂРѕРґР°"
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

        <div className="hidden min-h-0 md:block">
          <SideRail department={department} activeCity={activeCity} />
        </div>
      </div>

      {activeAction?.kind === 'schematic' ? (
        <AssetModal
          open
          onClose={closeAction}
          title={`Р­Р»РµРєС‚СЂРѕСЃС…РµРјР° · ${activeAction.display.description ?? activeAction.display.name}`}
          url={activeDisplayDetail?.file_url ?? null}
          loading={detailLoading}
        />
      ) : null}

      {activeAction?.kind === 'project' ? (
        <AssetModal
          open
          onClose={closeAction}
          title={`РџСЂРѕРµРєС‚ · ${activeAction.display.description ?? activeAction.display.name}`}
          url={activeDisplayDetail?.project_photo_url ?? null}
          loading={detailLoading}
        />
      ) : null}

      {activeAction?.kind === 'contacts' ? (
        <ContactsModal
          open
          onClose={closeAction}
          title={`РљРѕРЅС‚Р°РєС‚С‹ · ${activeAction.display.description ?? activeAction.display.name}`}
          detail={activeDisplayDetail}
          loading={detailLoading}
        />
      ) : null}

      {activeAction?.kind === 'photos' ? (
        <PhotoBankModal
          open
          onClose={closeAction}
          title={`Р¤РѕС‚РѕР±Р°РЅРє · ${activeAction.display.description ?? activeAction.display.name}`}
          slug={activeAction.display.slug}
          detail={activeDisplayDetail}
          loading={detailLoading}
          canManage={department === 'service'}
          onRefresh={refetchDetail}
        />
      ) : null}
    </>
  )
}
