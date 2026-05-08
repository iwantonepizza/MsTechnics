import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30 сек — данные свежие
      gcTime: 5 * 60_000,       // 5 мин — хранить в кэше
      retry: (failureCount, error: unknown) => {
        const status = (error as any)?.response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return failureCount < 2
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
    },
    mutations: {
      retry: 0,
    },
  },
})
