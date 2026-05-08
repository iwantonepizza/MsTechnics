import './styles/tokens.css'
import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'sonner'

import { queryClient } from '@/shared/lib/queryClient'
import { useAuthStore } from '@/features/auth/store'
import { useMe } from '@/features/auth/hooks'
import { useSSESubscription } from '@/shared/lib/sse'
import { AppLayout } from '@/widgets/navigation/AppLayout'
import { LoginPage } from '@/pages/login/LoginPage'
import { MainMenuPage } from '@/pages/menu/MainMenuPage'
import { DepartmentListPage } from '@/pages/department/DepartmentListPage'
import { DisplayViewPage } from '@/pages/display-view/DisplayViewPage'
import { DeparturesPage } from '@/pages/departures/DeparturesPage'
import { ZipPage } from '@/pages/zip/ZipPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { useKeyboard } from '@/shared/lib/useKeyboard'
import { ShortcutsHelp } from '@/shared/ui/ShortcutsHelp'
import { Spinner } from '@/shared/ui/Spinner'

// Инициализируем SSE при монтировании приложения
function SSEInit() {
  useSSESubscription()
  return null
}

function RequireAuth({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { accessToken } = useAuthStore()
  const { data: me, isLoading, isError } = useMe()

  if (!accessToken) return <Navigate to="/login" replace />
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg-0 text-fg">
        <Spinner />
      </div>
    )
  }
  if (isError || !me) return <Navigate to="/login" replace />

  if (roles?.length) {
    const allowed = me.permission === 'admin' || me.permission === 'all' || roles.includes(me.permission)
    if (!allowed) return <Navigate to="/menu" replace />
  }

  return <>{children}</>
}

export function App() {
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  useEffect(() => {
    const isTouch = window.matchMedia('(pointer: coarse)').matches
    document.documentElement.dataset.density = isTouch ? 'touch' : 'comfortable'
  }, [])

  useKeyboard({
    '?': () => setShortcutsOpen(true),
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <SSEInit />
        <Routes>
          {/* Публичные */}
          <Route path="/login" element={<LoginPage />} />

          {/* Авторизованные */}
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route index element={<Navigate to="/menu" replace />} />
            <Route path="/menu" element={<MainMenuPage />} />

            <Route path="/monitoring" element={<RequireAuth roles={['monitoring']}><DepartmentListPage department="monitoring" /></RequireAuth>} />
            <Route path="/monitoring/:citySlug" element={<RequireAuth roles={['monitoring']}><DepartmentListPage department="monitoring" /></RequireAuth>} />
            <Route path="/monitoring/:citySlug/:displaySlug" element={<RequireAuth roles={['monitoring']}><DisplayViewPage department="monitoring" /></RequireAuth>} />

            <Route path="/control" element={<RequireAuth roles={['control']}><DepartmentListPage department="control" /></RequireAuth>} />
            <Route path="/control/:citySlug" element={<RequireAuth roles={['control']}><DepartmentListPage department="control" /></RequireAuth>} />
            <Route path="/control/:citySlug/:displaySlug" element={<RequireAuth roles={['control']}><DisplayViewPage department="control" /></RequireAuth>} />

            <Route path="/service" element={<RequireAuth roles={['service']}><DepartmentListPage department="service" /></RequireAuth>} />
            <Route path="/service/:citySlug" element={<RequireAuth roles={['service']}><DepartmentListPage department="service" /></RequireAuth>} />
            <Route path="/service/:citySlug/:displaySlug" element={<RequireAuth roles={['service']}><DisplayViewPage department="service" /></RequireAuth>} />

            <Route path="/zip" element={<ZipPage />} />
            <Route path="/zip/:displaySlug" element={<ZipPage />} />
            <Route path="/departures" element={<RequireAuth roles={['service', 'control']}><DeparturesPage /></RequireAuth>} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="bottom-right"
        theme="dark"
        richColors
      />
      <ShortcutsHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
