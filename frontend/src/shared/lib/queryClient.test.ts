import { describe, expect, it } from 'vitest'

import { shouldRetryQuery } from './queryClient'

describe('shouldRetryQuery', () => {
  it('does not amplify rate limiting responses', () => {
    expect(shouldRetryQuery(0, { response: { status: 429 } })).toBe(false)
  })

  it('keeps bounded retries for transient failures', () => {
    expect(shouldRetryQuery(0, { response: { status: 503 } })).toBe(true)
    expect(shouldRetryQuery(2, { response: { status: 503 } })).toBe(false)
  })
})
