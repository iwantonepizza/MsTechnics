import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'

import { apiClient } from './client'

type AuthState = {
  accessToken: string | null
  setAccessToken: (token: string) => void
  logout: () => void
}

function unauthorized(config: InternalAxiosRequestConfig, detail = 'Unauthorized') {
  const response: AxiosResponse = {
    data: { detail },
    status: 401,
    statusText: 'Unauthorized',
    headers: {},
    config,
  }

  return Promise.reject(
    new AxiosError(detail, 'ERR_BAD_REQUEST', config, undefined, response),
  )
}

describe('apiClient auth refresh interceptor', () => {
  const setAccessToken = vi.fn()
  const logout = vi.fn()
  let authState: AuthState
  let originalAdapter: typeof apiClient.defaults.adapter

  beforeEach(() => {
    authState = {
      accessToken: 'stale-token',
      setAccessToken,
      logout,
    }
    ;(window as Window & { __authStore?: unknown }).__authStore = {
      getState: () => authState,
    }
    originalAdapter = apiClient.defaults.adapter
    setAccessToken.mockReset()
    logout.mockReset()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: 'http://localhost/login' },
    })
  })

  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter
    vi.restoreAllMocks()
  })

  it('does not try refresh for /auth/login 401', async () => {
    const refreshSpy = vi.fn()

    apiClient.defaults.adapter = async (config) => {
      if (config.url?.includes('/auth/refresh')) {
        refreshSpy()
      }
      return unauthorized(config)
    }

    await expect(
      apiClient.post('/auth/login/', { username: 'wrong', password: 'wrong' }),
    ).rejects.toMatchObject({
      response: { status: 401 },
    })

    expect(refreshSpy).not.toHaveBeenCalled()
    expect(logout).not.toHaveBeenCalled()
  })

  it('refreshes token and retries protected request on regular 401', async () => {
    let meCalls = 0

    apiClient.defaults.adapter = async (config) => {
      if (config.url === '/me') {
        meCalls += 1
        const authorization = config.headers?.Authorization
        if (meCalls === 1 && authorization === 'Bearer stale-token') {
          return unauthorized(config)
        }
        return {
          data: { username: 'tester' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        }
      }

      if (config.url === '/auth/refresh/') {
        return {
          data: { access: 'fresh-token' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        }
      }

      throw new Error(`Unexpected URL ${config.url}`)
    }

    const response = await apiClient.get('/me')

    expect(response.status).toBe(200)
    expect(meCalls).toBe(2)
    expect(setAccessToken).toHaveBeenCalledWith('fresh-token')
    expect(logout).not.toHaveBeenCalled()
  })

  it('logs out when refresh itself returns 401', async () => {
    let refreshCalls = 0

    apiClient.defaults.adapter = async (config) => {
      if (config.url === '/me') {
        return unauthorized(config)
      }

      if (config.url === '/auth/refresh/') {
        refreshCalls += 1
        return unauthorized(config, 'Refresh failed')
      }

      throw new Error(`Unexpected URL ${config.url}`)
    }

    await expect(apiClient.get('/me')).rejects.toBeInstanceOf(AxiosError)

    expect(refreshCalls).toBe(1)
    expect(logout).toHaveBeenCalledTimes(1)
  })
})
