# T-4-004. AppLayout: Header + crumbs + SSE-индикатор

> **Тип:** widget
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 4
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Цель

Адаптировать `frontend-design/header.jsx` (одобренный архитектором) под TS+React. AppLayout — оболочка для всех авторизованных страниц.

---

## Зависимости

- **Блокируется:** T-4-001 (tokens), T-4-003 (router), T-4-008 (SSE base)
- **Блокирует:** T-4-010..016

---

## Что взять из `frontend-design/header.jsx`

Структура:
```
[MsLogo + name]  [nav-items: Главная|Мониторинг|Контроль|Сервис|ЗИП]  [crumb]  [search|sse|bell|cmd|user-chip]
```

NavItems с `count` — показывают активные заявки в каждом отделе. SSE-индикатор пульсирует зелёным когда соединение живое.

---

## Что сделать

### Шаг 1. `widgets/navigation/Header.tsx`

```tsx
import { Link, useLocation } from 'react-router-dom'
import { Home, Monitor, Clipboard, Wrench, Box, Search, Bell, Command, ChevronDown } from 'lucide-react'

import { useMe } from '@/features/auth/hooks'
import { useApplicationsCount } from '@/features/applications/hooks'  // создать в T-4-008
import { useSSEStatus } from '@/shared/lib/sse'  // создать в T-4-008
import { cn } from '@/shared/lib/utils'

interface HeaderProps {
  crumb?: React.ReactNode
}

export function Header({ crumb }: HeaderProps) {
  const { data: me } = useMe()
  const { pathname } = useLocation()
  const counts = useApplicationsCount()  // { monitoring: 3, control: 12, service: 7 }
  const sseStatus = useSSEStatus()  // 'connected' | 'reconnecting' | 'disconnected'
  
  const role = me?.permission ?? ''
  const isAllowed = (dept: string) =>
    role === 'admin' || role === 'all' || role === dept
  
  const initials = (me?.username ?? 'U').slice(0, 2).toUpperCase()
  
  const navItems = [
    { to: '/menu',       label: 'Главная',    icon: Home,      key: 'home' },
    { to: '/monitoring', label: 'Мониторинг', icon: Monitor,   key: 'monitoring', count: counts.monitoring,
      disabled: !isAllowed('monitoring') },
    { to: '/control',    label: 'Контроль',   icon: Clipboard, key: 'control', count: counts.control,
      disabled: !isAllowed('control') },
    { to: '/service',    label: 'Сервис',     icon: Wrench,    key: 'service', count: counts.service,
      disabled: !isAllowed('service') },
    { to: '/zip',        label: 'ЗИП',        icon: Box,       key: 'zip' },
  ]
  
  return (
    <header className="grid h-header grid-cols-[auto_1fr_auto] items-center gap-5 border-b border-border-subtle bg-bg-1 px-4">
      {/* Brand + nav */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 border-r border-border-subtle pr-3.5 h-7">
          <MsLogo />
          <div className="text-[13px] font-semibold tracking-tight">
            MsTechnics <span className="text-fg-mute font-medium">/ ops</span>
          </div>
        </div>
        <nav className="flex items-center gap-0.5">
          {navItems.map(({ to, label, icon: Icon, key, count, disabled }) => {
            const isActive = pathname.startsWith(to) && (to !== '/menu' || pathname === '/menu')
            return disabled ? (
              <button
                key={key}
                disabled
                className="inline-flex items-center gap-2 h-7 px-2.5 rounded-md text-fg-faint cursor-not-allowed"
              >
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ) : (
              <Link
                key={key}
                to={to}
                data-active={isActive || undefined}
                className={cn(
                  'inline-flex items-center gap-2 h-7 px-2.5 rounded-md text-fg-dim',
                  'transition-colors duration-100',
                  'hover:bg-bg-2 hover:text-fg',
                  'data-[active]:bg-bg-3 data-[active]:text-fg data-[active]:border data-[active]:border-border-subtle'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="text-[12.5px] font-medium">{label}</span>
                {count != null && count > 0 && (
                  <span className="min-w-4 h-4 px-1 rounded-lg bg-accent-faint text-accent text-[10px] font-medium font-mono inline-flex items-center justify-center">
                    {count}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>
      </div>
      
      {/* Crumb */}
      <div className="flex items-center gap-2 text-fg-mute text-[12.5px] truncate">
        {crumb}
      </div>
      
      {/* User cluster */}
      <div className="flex items-center gap-1">
        <button
          title="Поиск · /"
          className="inline-flex items-center gap-1.5 h-btn-sm px-2 rounded-md text-fg-mute hover:bg-bg-2 hover:text-fg"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="text-[12px]">Поиск</span>
          <span className="ml-1 inline-flex items-center justify-center min-w-4 h-4 px-1 rounded-sm bg-bg-3 text-fg-dim border border-border-subtle font-mono text-[10px]">/</span>
        </button>
        <Separator />
        
        <SSEDot status={sseStatus} />
        
        <IconButton title="Уведомления"><Bell /></IconButton>
        <IconButton title="Шорткаты · ?"><Command /></IconButton>
        
        <Separator />
        
        <button className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-bg-2">
          <span className="w-5 h-5 rounded-full bg-accent-faint text-accent inline-flex items-center justify-center text-[10px] font-semibold">{initials}</span>
          <span className="text-[12.5px] text-fg-dim">{me?.username}</span>
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>
    </header>
  )
}

const Separator = () => <span className="w-px h-3.5 bg-border-subtle mx-1" />
const IconButton = ({ children, title }: { children: React.ReactNode; title: string }) => (
  <button title={title} className="w-hit h-hit inline-flex items-center justify-center rounded-md text-fg-dim hover:bg-bg-2 hover:text-fg">
    {children}
  </button>
)
const MsLogo = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
    <rect x="2" y="2" width="20" height="20" rx="4" fill="var(--brand)"/>
    <path d="M6 17V8l3 5 3-5v9M14 17V8h3a2.5 2.5 0 0 1 0 5h-3" stroke="var(--brand-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)
const SSEDot = ({ status }: { status: 'connected' | 'reconnecting' | 'disconnected' }) => (
  <span title={`SSE: ${status}`} className="w-hit h-hit inline-flex items-center justify-center">
    <span className={cn(
      'w-1.5 h-1.5 rounded-full',
      status === 'connected'    && 'bg-ok shadow-[0_0_0_3px] shadow-[var(--ok-faint)]',
      status === 'reconnecting' && 'bg-warn animate-pulse',
      status === 'disconnected' && 'bg-err',
    )} />
  </span>
)
```

### Шаг 2. AppLayout

```tsx
// frontend/src/widgets/navigation/AppLayout.tsx
import { Header } from './Header'

export function AppLayout({ children, crumb }: { children: React.ReactNode; crumb?: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen bg-bg-0 text-fg">
      <Header crumb={crumb} />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
```

### Шаг 3. Crumb через context

Чтобы каждая страница могла задать свой `crumb`:

```tsx
// frontend/src/widgets/navigation/CrumbContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react'

const CrumbContext = createContext<{
  crumb: ReactNode | null
  setCrumb: (c: ReactNode | null) => void
}>({ crumb: null, setCrumb: () => {} })

export const CrumbProvider = ({ children }: { children: ReactNode }) => {
  const [crumb, setCrumb] = useState<ReactNode | null>(null)
  return <CrumbContext.Provider value={{ crumb, setCrumb }}>{children}</CrumbContext.Provider>
}

export const useCrumb = () => useContext(CrumbContext)
```

В странице:
```tsx
const { setCrumb } = useCrumb()
useEffect(() => {
  setCrumb(<>service · <span className="font-mono">{citySlug}</span> / <span className="font-mono">{displaySlug}</span></>)
  return () => setCrumb(null)
}, [citySlug, displaySlug])
```

---

## Критерии приёмки

- [ ] Header рендерится с правильными nav-items (отделы, к которым у юзера нет доступа — disabled)
- [ ] Active link подсвечивается (data-active)
- [ ] User-chip с инициалами + dropdown
- [ ] SSE-индикатор отражает статус (после T-4-008)
- [ ] Counts из `useApplicationsCount()` (badge на nav)
- [ ] Crumb меняется per-page через context
- [ ] Адаптивно: на узком экране (1366) ничего не вылазит за пределы

---

## Что НЕ делать

- НЕ копировать JSX из `frontend-design/header.jsx` 1:1 — там UMD React, у нас TS+JSX
- НЕ хардкодить counts — реальные через React Query
- НЕ забыть про `disabled` для отделов вне роли
