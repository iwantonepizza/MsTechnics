import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import { useAuthStore } from './store'
import type { MeUser } from '@/shared/api/types'

export function useLogin() {
  const { setAccessToken } = useAuthStore()
  return useMutation({
    mutationFn: async (data: { username: string; password: string }) => {
      const res = await apiClient.post<{ access: string }>('/auth/login/', data)
      return res.data
    },
    onSuccess: (data) => setAccessToken(data.access),
  })
}

export function useLogout() {
  const { logout } = useAuthStore()
  return useMutation({
    mutationFn: () => apiClient.post('/auth/logout/'),
    onSettled: () => logout(),
  })
}

export function useMe() {
  const { accessToken, setUser } = useAuthStore()
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const res = await apiClient.get<MeUser>('/me')
      setUser(res.data)
      return res.data
    },
    enabled: !!accessToken,
    staleTime: 60_000,
  })
}
