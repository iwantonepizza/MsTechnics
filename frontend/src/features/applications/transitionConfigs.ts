/**
 * T-4-020: Конфиг для всех 12 типов переходов/действий.
 * Определяет что показывать в модалке для каждого transition kind.
 */
import { z } from 'zod'

export type TransitionKind =
  | 'apply_in_control'
  | 'sent_to_service'
  | 'work_in_service'
  | 'done'
  | 'unable'
  | 'archive_done'
  | 'archive_unable'
  | 'delete_application'

export interface TransitionConfig {
  title: string
  description?: string
  buttonLabel: string
  buttonVariant: 'primary' | 'danger' | 'ok' | 'ghost'
  commentRequired?: boolean
  commentPlaceholder?: string
  filePresent?: boolean
  needsExecutor?: boolean
  confirmRequired?: boolean   // доп. подтверждение (checkbox)
  confirmText?: string
}

export const TRANSITION_CONFIGS: Record<TransitionKind, TransitionConfig> = {
  apply_in_control: {
    title: 'Принять заявку',
    buttonLabel: 'Принять',
    buttonVariant: 'primary',
    commentPlaceholder: 'Комментарий (опционально)...',
  },
  sent_to_service: {
    title: 'Отправить в сервис',
    buttonLabel: 'Отправить',
    buttonVariant: 'primary',
    needsExecutor: true,
    commentPlaceholder: 'Описание задачи для сервиса...',
  },
  work_in_service: {
    title: 'Взять в работу',
    buttonLabel: 'Взять в работу',
    buttonVariant: 'ok',
    commentPlaceholder: 'Комментарий...',
  },
  done: {
    title: 'Ремонт выполнен',
    buttonLabel: 'Подтвердить выполнение',
    buttonVariant: 'ok',
    filePresent: true,
    commentPlaceholder: 'Что было сделано...',
  },
  unable: {
    title: 'Ремонт невозможен',
    buttonLabel: 'Подтвердить',
    buttonVariant: 'danger',
    commentRequired: true,
    commentPlaceholder: 'Укажите причину...',
    confirmRequired: true,
    confirmText: 'Подтверждаю: ремонт невозможен',
  },
  archive_done: {
    title: 'Архивировать (выполнено)',
    buttonLabel: 'Архивировать',
    buttonVariant: 'ghost',
    commentPlaceholder: 'Комментарий...',
  },
  archive_unable: {
    title: 'Архивировать (невозможно)',
    buttonLabel: 'Архивировать',
    buttonVariant: 'ghost',
    commentPlaceholder: 'Комментарий...',
  },
  delete_application: {
    title: 'Удалить заявку',
    description: 'Это действие необратимо. Заявка будет удалена из системы.',
    buttonLabel: 'Удалить',
    buttonVariant: 'danger',
    commentPlaceholder: 'Причина удаления...',
    confirmRequired: true,
    confirmText: 'Подтверждаю удаление заявки',
  },
}

// Валидация schema по конфигу
export function buildTransitionSchema(config: TransitionConfig) {
  return z.object({
    comment: config.commentRequired
      ? z.string().min(1, 'Комментарий обязателен')
      : z.string().optional().default(''),
    executor_id: config.needsExecutor
      ? z.preprocess(
          value => typeof value === 'number' && Number.isNaN(value) ? undefined : value,
          z.number({ required_error: 'Выберите исполнителя' }).positive('Выберите исполнителя'),
        )
      : z.number().optional(),
    confirmed: config.confirmRequired
      ? z.boolean().refine(v => v === true, 'Необходимо подтверждение')
      : z.boolean().optional(),
  })
}
