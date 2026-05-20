import type { SearchResultItem } from './types'

const RECENT_SEARCHES_KEY = 'mstechnics-global-search-recent'
const RECENT_SEARCHES_LIMIT = 5

export function loadRecentSearches(): SearchResultItem[] {
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCHES_KEY)
    if (!raw) return []

    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []

    return parsed.filter(isSearchResultItem).slice(0, RECENT_SEARCHES_LIMIT)
  } catch {
    return []
  }
}

export function saveRecentSearch(item: SearchResultItem) {
  const next = [
    item,
    ...loadRecentSearches().filter(existing => existing.key !== item.key),
  ].slice(0, RECENT_SEARCHES_LIMIT)

  try {
    window.localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next))
  } catch {}
}

function isSearchResultItem(value: unknown): value is SearchResultItem {
  if (!value || typeof value !== 'object') return false

  const candidate = value as Record<string, unknown>
  return (
    typeof candidate.key === 'string' &&
    typeof candidate.type === 'string' &&
    typeof candidate.section === 'string' &&
    typeof candidate.title === 'string' &&
    typeof candidate.href === 'string'
  )
}
