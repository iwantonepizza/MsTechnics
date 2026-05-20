import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useKeyboard } from '@/shared/lib/useKeyboard'
import { useAuthStore } from '@/features/auth/store'
import type { GlobalSearchResponse } from '@/shared/api/types'
import { CommandPalette } from '@/shared/ui/CommandPalette'
import { useGlobalSearch } from './hooks'
import { loadRecentSearches, saveRecentSearch } from './storage'
import type {
  SearchResultItem,
  SearchSection,
} from './types'

const DEPARTMENTS = ['monitoring', 'control', 'service'] as const

export function GlobalSearch() {
  const navigate = useNavigate()
  const location = useLocation()
  const inputRef = useRef<HTMLInputElement>(null)
  const accessToken = useAuthStore(state => state.accessToken)
  const user = useAuthStore(state => state.user)

  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [recentItems, setRecentItems] = useState<SearchResultItem[]>([])

  useEffect(() => {
    if (!open) return

    setRecentItems(loadRecentSearches())
  }, [open])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim())
    }, 200)

    return () => window.clearTimeout(handle)
  }, [query])

  useEffect(() => {
    if (!open) return

    window.setTimeout(() => inputRef.current?.focus(), 0)
  }, [open])

  const canOpen = Boolean(accessToken) && location.pathname !== '/login'

  useKeyboard(
    {
      '/': () => setOpen(true),
      'Mod+K': () => setOpen(true),
    },
    canOpen,
  )

  const searchQuery = debouncedQuery.length >= 2 ? debouncedQuery : ''
  const search = useGlobalSearch(searchQuery, 8, open && canOpen)

  const sections = useMemo(() => {
    if (query.trim().length === 0) {
      return recentItems.length
        ? ([{ key: 'recent', label: 'Недавние', items: recentItems }] satisfies SearchSection[])
        : []
    }

    if (searchQuery.length < 2 || !search.data) {
      return []
    }

    return buildSearchSections(search.data, {
      pathname: location.pathname,
      permission: user?.permission ?? null,
    })
  }, [location.pathname, query, recentItems, search.data, searchQuery, user?.permission])

  const flatItems = useMemo(() => sections.flatMap(section => section.items), [sections])

  useEffect(() => {
    if (flatItems.length === 0) {
      setActiveIndex(0)
      return
    }

    if (activeIndex > flatItems.length - 1) {
      setActiveIndex(0)
    }
  }, [activeIndex, flatItems.length])

  const closePalette = () => {
    setOpen(false)
    setQuery('')
    setDebouncedQuery('')
    setActiveIndex(0)
  }

  const handleSelect = (item: SearchResultItem) => {
    saveRecentSearch(item)
    setRecentItems(loadRecentSearches())
    closePalette()

    if (item.external) {
      window.location.assign(item.href)
      return
    }

    navigate(item.href)
  }

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      closePalette()
      return
    }

    if (flatItems.length === 0) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex(current => (current + 1) % flatItems.length)
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex(current => (current - 1 + flatItems.length) % flatItems.length)
      return
    }

    if (event.key === 'Enter') {
      event.preventDefault()
      handleSelect(flatItems[activeIndex] ?? flatItems[0])
    }
  }

  return (
    <CommandPalette
      open={open}
      query={query}
      isLoading={search.isFetching}
      sections={sections}
      activeIndex={activeIndex}
      onClose={closePalette}
      onQueryChange={setQuery}
      onActiveIndexChange={setActiveIndex}
      onSelect={handleSelect}
      onInputKeyDown={handleInputKeyDown}
      inputRef={inputRef}
    />
  )
}

function buildSearchSections(
  data: GlobalSearchResponse,
  context: { pathname: string; permission: string | null },
): SearchSection[] {
  const sections: SearchSection[] = [
    {
      key: 'displays',
      label: 'Экраны',
      items: data.displays.map(display => ({
        key: `display:${display.id}`,
        type: 'display',
        section: 'displays',
        title: display.description ?? display.name,
        subtitle: display.city_name,
        badge: display.slug,
        href: buildDisplayHref({
          citySlug: display.city_slug,
          displaySlug: display.slug,
          pathname: context.pathname,
          permission: context.permission,
        }),
      })),
    },
    {
      key: 'panels',
      label: 'Панели',
      items: data.panels.map(panel => {
        const displayHref = buildDisplayHref({
          citySlug: panel.city_slug,
          displaySlug: panel.display_slug,
          pathname: context.pathname,
          permission: context.permission,
          query: panel.active_application_id
            ? { app_id: String(panel.active_application_id) }
            : { panel_id: String(panel.id) },
        })

        return {
          key: `panel:${panel.id}`,
          type: 'panel',
          section: 'panels',
          title: panel.name,
          subtitle: panel.display_name ?? panel.department_name ?? 'ЗИП',
          badge: panel.condition_name,
          href: panel.display_slug && panel.city_slug
            ? displayHref
            : `/zip?panel_id=${panel.id}#panel-${panel.id}`,
        }
      }),
    },
    {
      key: 'applications',
      label: 'Заявки',
      items: data.applications.map(application => ({
        key: `application:${application.id}`,
        type: 'application',
        section: 'applications',
        title: `Заявка #${application.id}`,
        subtitle: [application.panel_name, application.cell_position, application.initial_comment]
          .filter(Boolean)
          .join(' • ') || application.display_name,
        badge: application.status_name,
        href: buildDisplayHref({
          citySlug: application.city_slug,
          displaySlug: application.display_slug,
          pathname: context.pathname,
          permission: context.permission,
          query: { app_id: String(application.id) },
        }),
      })),
    },
    {
      key: 'departures',
      label: 'Выезды',
      items: data.departures.map(departure => ({
        key: `departure:${departure.id}`,
        type: 'departure',
        section: 'departures',
        title: departure.description ?? `Выезд #${departure.id}`,
        subtitle: departure.executor_name,
        badge: departure.status_name,
        href: `/departures?departure_id=${departure.id}`,
      })),
    },
    {
      key: 'users',
      label: 'Пользователи',
      items: data.users.map(user => ({
        key: `user:${user.id}`,
        type: 'user',
        section: 'users',
        title: user.username,
        subtitle: user.full_name,
        badge: user.permission,
        href: `/admin/user/msuser/${user.id}/change/`,
        external: true,
      })),
    },
    {
      key: 'storage',
      label: 'ЗИП',
      items: data.storage.map(item => ({
        key: `storage:${item.kind}:${item.id}`,
        type: 'storage',
        section: 'storage',
        title: item.name,
        subtitle: item.description,
        badge: `${storageKindLabel(item.kind)} ${item.count}`,
        href: `/zip#storage-${item.kind}-${item.id}`,
      })),
    },
  ]

  return sections.filter(section => section.items.length > 0)
}

function buildDisplayHref({
  citySlug,
  displaySlug,
  pathname,
  permission,
  query,
}: {
  citySlug: string | null
  displaySlug: string | null
  pathname: string
  permission: string | null
  query?: Record<string, string>
}) {
  if (!citySlug || !displaySlug) return '/menu'

  const department = resolveDepartment(pathname, permission)
  const params = new URLSearchParams(query)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return `/${department}/${citySlug}/${displaySlug}${suffix}`
}

function resolveDepartment(pathname: string, permission: string | null) {
  const fromPath = pathname.split('/')[1]
  if (DEPARTMENTS.includes(fromPath as (typeof DEPARTMENTS)[number])) {
    return fromPath
  }

  if (DEPARTMENTS.includes(permission as (typeof DEPARTMENTS)[number])) {
    return permission as (typeof DEPARTMENTS)[number]
  }

  return 'control'
}

function storageKindLabel(kind: string) {
  switch (kind) {
    case 'wires':
      return 'Провода'
    case 'hubs':
      return 'Хабы'
    case 'lamels':
      return 'Ламели'
    case 'power-blocks':
      return 'БП'
    case 'connectors':
      return 'Коннекторы'
    default:
      return 'ЗИП'
  }
}
