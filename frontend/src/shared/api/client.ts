import axios, { AxiosError } from 'axios'

// Lazy import — избегаем circular deps
const getToken = () => {
  try {
    return (window as any).__authStore?.getState?.()?.accessToken ?? null
  } catch { return null }
}
const setToken = (t: string) => {
  try { (window as any).__authStore?.getState?.()?.setAccessToken(t) } catch {}
}
const doLogout = () => {
  try { (window as any).__authStore?.getState?.()?.logout() } catch {}
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let _refreshPromise: Promise<string> | null = null

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean }
    if (error.response?.status === 401 && !original?._retry) {
      original._retry = true
      if (!_refreshPromise) {
        _refreshPromise = apiClient
          .post<{ access: string }>('/auth/refresh/')
          .then((r) => r.data.access)
          .finally(() => { _refreshPromise = null })
      }
      try {
        const newToken = await _refreshPromise
        setToken(newToken)
        if (original) {
          original.headers!.Authorization = `Bearer ${newToken}`
          return apiClient(original)
        }
      } catch {
        doLogout()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
