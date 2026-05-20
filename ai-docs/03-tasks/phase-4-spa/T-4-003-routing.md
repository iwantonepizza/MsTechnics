# T-4-003. React Router v6 + protected routes + RBAC

> **Тип:** core
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 4
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Цель

Полная карта роутинга с проверкой авторизации и роли. Без него страницы не связаны.

---

## Зависимости

- **Блокируется:** T-4-002 (Me тип из OpenAPI)
- **Блокирует:** T-4-010..016

---

## Карта URL

| URL | Страница | Требует роль |
|---|---|---|
| `/login` | LoginPage | — (анонимный) |
| `/menu` | MainMenuPage | любой авторизованный |
| `/monitoring` | DepartmentListPage(monitoring) | monitoring/admin/all |
| `/monitoring/:citySlug/:displaySlug` | DisplayViewPage(monitoring) | monitoring/admin/all + city access |
| `/control` | DepartmentListPage(control) | control/admin/all |
| `/control/:citySlug/:displaySlug` | DisplayViewPage(control) | control/admin/all + city |
| `/service` | DepartmentListPage(service) | service/admin/all |
| `/service/:citySlug/:displaySlug` | DisplayViewPage(service) | service/admin/all + city |
| `/zip` | ZipPage | любой |
| `/zip/:displaySlug` | ZipPage(filtered) | любой + city |
| `/departures` | DeparturesPage | service/admin/all |
| `/profile` | ProfilePage | любой авторизованный |
| `/*` | NotFoundPage | — |

---

## Что сделать

### Шаг 1. Структура роутера

`frontend/src/app/Router.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useMe } from '@/features/auth/hooks'
import { AppLayout } from '@/widgets/navigation/AppLayout'
import { Spinner } from '@/shared/ui/Spinner'

import { LoginPage } from '@/pages/login/LoginPage'
import { MainMenuPage } from '@/pages/menu/MainMenuPage'
import { DepartmentListPage } from '@/pages/department/DepartmentListPage'
import { DisplayViewPage } from '@/pages/display-view/DisplayViewPage'
import { ZipPage } from '@/pages/zip/ZipPage'
import { DeparturesPage } from '@/pages/departures/DeparturesPage'
import { ProfilePage } from '@/pages/profile/ProfilePage'
import { NotFoundPage } from '@/pages/not-found/NotFoundPage'

// Protected route wrapper
function ProtectedRoute({ requiredRoles }: { requiredRoles?: string[] }) {
  const { data: me, isLoading, error } = useMe()
  
  if (isLoading) return <div className="flex h-screen items-center justify-center"><Spinner /></div>
  if (error || !me) return <Navigate to="/login" replace />
  
  if (requiredRoles && requiredRoles.length > 0) {
    const allowed = me.permission === 'admin' || me.permission === 'all' 
                  || requiredRoles.includes(me.permission)
    if (!allowed) return <Navigate to="/menu" replace />
  }
  
  return <AppLayout><Outlet /></AppLayout>
}

export function Router() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Authenticated */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Navigate to="/menu" replace />} />
          <Route path="/menu" element={<MainMenuPage />} />
          <Route path="/zip" element={<ZipPage />} />
          <Route path="/zip/:displaySlug" element={<ZipPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        
        {/* Department: monitoring */}
        <Route element={<ProtectedRoute requiredRoles={['monitoring']} />}>
          <Route path="/monitoring" element={<DepartmentListPage department="monitoring" />} />
          <Route path="/monitoring/:citySlug/:displaySlug" element={<DisplayViewPage department="monitoring" />} />
        </Route>
        
        {/* Department: control */}
        <Route element={<ProtectedRoute requiredRoles={['control']} />}>
          <Route path="/control" element={<DepartmentListPage department="control" />} />
          <Route path="/control/:citySlug/:displaySlug" element={<DisplayViewPage department="control" />} />
        </Route>
        
        {/* Department: service */}
        <Route element={<ProtectedRoute requiredRoles={['service']} />}>
          <Route path="/service" element={<DepartmentListPage department="service" />} />
          <Route path="/service/:citySlug/:displaySlug" element={<DisplayViewPage department="service" />} />
          <Route path="/departures" element={<DeparturesPage />} />
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### Шаг 2. App.tsx обновить

```tsx
// frontend/src/app/App.tsx
import { useEffect } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'sonner'

import { queryClient } from '@/shared/lib/queryClient'
import { Router } from './Router'

export function App() {
  useEffect(() => {
    const isTouch = window.matchMedia('(pointer: coarse)').matches
    document.documentElement.dataset.density = isTouch ? 'touch' : 'comfortable'
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <Toaster position="bottom-right" theme="dark" />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### Шаг 3. Перехватчик 401 → /login

`frontend/src/shared/api/client.ts` — должно быть так:

```ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  withCredentials: true,  // для refresh-cookie
})

apiClient.interceptors.request.use((config) => {
  const access = localStorage.getItem('mstech_access')
  if (access) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

let refreshing: Promise<string> | null = null

apiClient.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    
    // 401 → попытка refresh
    if (error.response?.status === 401 && !original._retry && !original.url.includes('/auth/')) {
      original._retry = true
      
      // Дедупликация параллельных refresh
      if (!refreshing) {
        refreshing = apiClient.post('/auth/refresh/').then(r => {
          const access = r.data.access
          localStorage.setItem('mstech_access', access)
          return access
        }).catch(() => {
          localStorage.removeItem('mstech_access')
          window.location.href = '/login'
          return null
        }).finally(() => { refreshing = null })
      }
      
      const newAccess = await refreshing
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`
        return apiClient(original)
      }
    }
    
    return Promise.reject(error)
  }
)
```

### Шаг 4. Тесты

`frontend/src/app/__tests__/Router.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Router } from '../Router'

// нужны mock'и useMe — отдельный setup
// тут — smoke

test('Router рендерится без ошибок', () => {
  render(<Router />)  // проверка что нет throw
})
```

---

## Критерии приёмки

- [ ] Все 13 URL из карты работают
- [ ] Неавторизованный → `/login`
- [ ] Авторизованный без нужной роли → `/menu`
- [ ] 401 на API → автоматический refresh, при провале → `/login`
- [ ] City access проверяется на бекенде (T-3-003 done) — фронт просто получает 403/404
- [ ] Layout (AppLayout) обёртывает все авторизованные страницы
- [ ] `/` редиректит на `/menu`
- [ ] `/*` показывает 404

---

## Что НЕ делать

- НЕ хранить access в cookie — только в localStorage (refresh — в httpOnly)
- НЕ делать логику `if user.permission === 'X'` в каждом компоненте — только в `ProtectedRoute`
- НЕ дублировать city-check на фронте — это делает бекенд
