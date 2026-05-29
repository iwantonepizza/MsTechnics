import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { MeUser } from '@/shared/api/types'

import { isAccessTokenExpired } from './token'

interface AuthState {
  accessToken: string | null
  user: MeUser | null
  setAccessToken: (token: string) => void
  setUser: (user: MeUser) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,

      setAccessToken: (token) => {
        set({ accessToken: token })
        // Регистрируем store глобально для axios interceptor
        ;(window as any).__authStore = useAuthStore
      },

      setUser: (user) => set({ user }),

      logout: () => {
        set({ accessToken: null, user: null })
      },
    }),
    {
      name: 'mstech-auth',
      partialize: (state) => ({ accessToken: state.accessToken }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<AuthState> | undefined
        const token = persisted?.accessToken

        if (typeof token === 'string' && isAccessTokenExpired(token)) {
          return currentState
        }

        return {
          ...currentState,
          ...persisted,
        }
      },
    }
  )
)

// Регистрируем глобально при загрузке (для axios interceptor)
;(window as any).__authStore = useAuthStore
