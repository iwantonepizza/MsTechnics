import type { GlobalSearchResponse } from '@/shared/api/types'

export type SearchSectionKey =
  | 'displays'
  | 'panels'
  | 'applications'
  | 'departures'
  | 'users'
  | 'storage'
  | 'recent'

export type SearchItemType =
  | 'display'
  | 'panel'
  | 'application'
  | 'departure'
  | 'user'
  | 'storage'

export interface SearchResultItem {
  key: string
  type: SearchItemType
  section: SearchSectionKey
  title: string
  subtitle: string | null
  badge: string | null
  href: string
  external?: boolean
}

export interface SearchSection {
  key: SearchSectionKey
  label: string
  items: SearchResultItem[]
}
