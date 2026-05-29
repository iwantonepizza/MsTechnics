import { describe, expect, it } from 'vitest'

import { isAccessTokenExpired } from './token'

function createToken(expSeconds: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  const payload = btoa(JSON.stringify({ exp: expSeconds }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')

  return `${header}.${payload}.signature`
}

describe('isAccessTokenExpired', () => {
  it('returns true for expired tokens', () => {
    const token = createToken(100)

    expect(isAccessTokenExpired(token, 101_000)).toBe(true)
  })

  it('returns false for fresh tokens', () => {
    const token = createToken(200)

    expect(isAccessTokenExpired(token, 199_000)).toBe(false)
  })

  it('does not break on malformed tokens', () => {
    expect(isAccessTokenExpired('bad-token')).toBe(false)
  })
})
