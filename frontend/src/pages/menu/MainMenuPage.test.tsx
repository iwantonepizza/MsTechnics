import { describe, expect, it } from 'vitest'

import { getAppPath, shouldShowMobileControlTasks } from './MainMenuPage'
import type { ApplicationListItem } from '@/shared/api/types'

function makeApplicationListItem(): ApplicationListItem {
  return {
    id: 42,
    display: {
      slug: 'ekb-center',
      name: 'EKB-1',
      description: 'Екатеринбург Центр',
      city: {
        slug: 'ekaterinburg',
        name: 'Екатеринбург',
      },
    },
    panel: {
      id: 10,
      name: 'P-001',
    },
    cell: {
      id: 5,
      position: '01',
    },
    status: {
      id: 2,
      name: 'sent_to_control',
      description: 'Отправлена в контроль',
      color: { id: 3, name: 'yellow', hex: 'yellow' },
      color_text: { id: 2, name: 'white', hex: 'white' },
      icon: { id: 4, unicode_symbol: '!' },
      next_possible: [],
    },
    executor: null,
    comment_monitoring: 'test',
    last_update_date_time: '2026-05-20T10:00:00Z',
  } as unknown as ApplicationListItem
}

describe('getAppPath', () => {
  it('builds display route with city and display slugs', () => {
    const path = getAppPath(makeApplicationListItem(), 'control')

    expect(path).toBe('/control/ekaterinburg/ekb-center?app_id=42')
  })

  it('falls back to department root when city slug is missing', () => {
    const app = makeApplicationListItem()
    app.display.city.slug = null

    const path = getAppPath(app, 'service')

    expect(path).toBe('/service')
  })
})

describe('shouldShowMobileControlTasks', () => {
  it('shows the mobile tasks shortcut only for control role', () => {
    expect(shouldShowMobileControlTasks('control')).toBe(true)
    expect(shouldShowMobileControlTasks('monitoring')).toBe(false)
    expect(shouldShowMobileControlTasks('service')).toBe(false)
    expect(shouldShowMobileControlTasks('admin')).toBe(false)
  })
})
