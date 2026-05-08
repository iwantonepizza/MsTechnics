import type { components } from './schema.d'

export type Schemas = components['schemas']

export type ActivityLog = Schemas['ActivityLog']
export type City = Schemas['City']
export type Color = Schemas['Color']
export type Smile = Schemas['Smile']
export type Condition = Schemas['Condition']
export type Department = Schemas['Department']
export type ApplicationStatus = Schemas['ApplicationStatus']
export type DepartureStatus = Schemas['DepartureStatus']
export type DisplayListItem = Schemas['DisplayList'] & {
  slug: string
  rows: number
  cols: number
}
export type DisplayDetail = Omit<Schemas['DisplayDetail'], 'slug' | 'rows' | 'cols' | 'cells'> & {
  slug: string
  rows: number
  cols: number
  cells: Cell[]
}
export type Cell = Schemas['Cell']
export type Panel = Schemas['Panel']
export type PanelOnCell = Schemas['Panel']
export type ApplicationListItem = Omit<Schemas['ApplicationListItem'], 'last_update_date_time'> & {
  last_update_date_time: string | null
}
export type ApplicationDetail = Omit<Schemas['ApplicationDetail'], 'last_update_date_time'> & {
  last_update_date_time: string | null
}
export type ApplicationEvent = Schemas['ApplicationEvent']
export type DepartureListItem = Schemas['DepartureList']
export type Departure = Schemas['DepartureList']
export type Executor = Schemas['ExecutorMini']
export type MeUser = Schemas['Me']

export interface AlarmEvent {
  id: number
  type: 'faulty' | 'recovery'
  receiving_card_no: number
  raw_position: string
  raw_email_subject: string
  occurred_at: string
  resolved_at: string | null
  cell_id: number | null
  cell_position: string | null
  panel_id: number | null
  panel_name: string | null
}

export interface PaginatedResponse<T> {
  results: T[]
  next_cursor: string | null
  prev_cursor: string | null
  has_more: boolean
}

export interface ApiError {
  detail: string
  code: string
  errors: Record<string, string[]> | null
}
