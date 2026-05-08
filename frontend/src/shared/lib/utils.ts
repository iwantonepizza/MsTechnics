import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return format(parseISO(iso), 'dd.MM.yyyy HH:mm', { locale: ru })
}

export function formatRelative(iso: string | null | undefined) {
  if (!iso) return '—'
  return formatDistanceToNow(parseISO(iso), { addSuffix: true, locale: ru })
}

export function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const e = error as { response?: { data?: { detail?: string } } }
    return e.response?.data?.detail ?? 'Произошла ошибка'
  }
  if (error instanceof Error) return error.message
  return 'Произошла ошибка'
}
