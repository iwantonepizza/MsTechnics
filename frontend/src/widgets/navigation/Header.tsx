import { useQuery } from '@tanstack/react-query'
import {
  Car,
  Home,
  LogOut,
  Monitor,
  Package,
  ShieldCheck,
  Wrench,
  Zap,
  ZapOff,
} from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useMe, useLogout } from '@/features/auth/hooks'
import { apiClient } from '@/shared/api/client'
import { useSSEStatus } from '@/shared/lib/sse'
import { cn } from '@/shared/lib/utils'
import { ThemeToggle } from '@/shared/ui/ThemeToggle'
import { NotificationBell } from './NotificationBell'

interface HeaderProps {
  crumb?: React.ReactNode
}

const NAV_ITEMS = [
  { to: '/menu', label: 'Главная', Icon: Home, perm: null },
  { to: '/monitoring', label: 'Мониторинг', Icon: Monitor, perm: 'monitoring' },
  { to: '/control', label: 'Контроль', Icon: ShieldCheck, perm: 'control' },
  { to: '/service', label: 'Сервис', Icon: Wrench, perm: 'service' },
  { to: '/zip', label: 'ЗИП', Icon: Package, perm: null },
  { to: '/departures', label: 'Выезды', Icon: Car, perm: null },
] as const

interface DashboardData {
  counts: Record<string, number>
}

function useNavCounts(role: string) {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await apiClient.get<DashboardData>('/dashboard/')
      const counts = res.data.counts ?? {}
      return {
        monitoring: counts.sent_to_control ?? 0,
        control: (counts.sent_to_control ?? 0) + (counts.apply_in_control ?? 0),
        service: (counts.sent_to_service ?? 0) + (counts.work_in_service ?? 0),
      }
    },
    refetchInterval: 30_000,
    staleTime: 15_000,
    enabled: !!role,
  })
}

function SSEDot() {
  const status = useSSEStatus()
  const label =
    status === 'connected'
      ? 'SSE подключён'
      : status === 'reconnecting'
        ? 'SSE переподключается'
        : 'SSE отключён'

  return (
    <span
      title={label}
      aria-label={label}
      className="flex w-7 items-center justify-center"
      role="img"
    >
      {status === 'connected' ? (
        <Zap size={12} style={{ color: 'var(--ok)' }} className="animate-pulse" />
      ) : status === 'reconnecting' ? (
        <Zap size={12} style={{ color: 'var(--warn)' }} />
      ) : (
        <ZapOff size={12} style={{ color: 'var(--err)' }} />
      )}
    </span>
  )
}

export function Header({ crumb }: HeaderProps) {
  const { data: me } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  const role = me?.permission ?? ''
  const isAllowed = (perm: string | null) =>
    !perm || role === 'admin' || role === 'all' || role === perm

  const { data: counts } = useNavCounts(role)

  const handleLogout = async () => {
    await logout.mutateAsync()
    navigate('/login', { replace: true })
    toast.info('Вы вышли из системы')
  }

  return (
    <header
      className="app-header flex shrink-0 items-center gap-0 border-b"
      style={{
        height: 'var(--h-header)',
        background: 'var(--bg-0)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      <Link
        to="/menu"
        className="flex h-full shrink-0 items-center gap-3 px-4"
        style={{ borderRight: '1px solid var(--border-subtle)' }}
        aria-label="Суперсимметрия - на главную"
      >
        <img
          src="/logo-supersymmetria.svg"
          alt="Суперсимметрия"
          className="theme-logo hidden h-5 w-auto sm:block"
        />
        <span className="text-sm font-semibold sm:hidden" style={{ color: 'var(--fg)' }}>
          Суперсимметрия
        </span>
      </Link>

      <nav className="hidden h-full items-center px-2 md:flex">
        {NAV_ITEMS.filter(({ perm }) => isAllowed(perm)).map(({ to, label, Icon, perm }) => {
          const count = perm ? counts?.[perm as keyof typeof counts] ?? 0 : 0
          return (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'relative flex h-full items-center gap-1.5 px-3 text-sm transition-colors',
                  isActive ? 'font-medium' : 'hover:opacity-90',
                )
              }
              style={({ isActive }) => ({
                color: isActive ? 'var(--fg)' : 'var(--fg-mute)',
                borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              })}
            >
              <Icon size={13} />
              <span>{label}</span>
              {count > 0 && (
                <span
                  className="flex h-4 min-w-[16px] items-center justify-center rounded px-1 text-2xs font-medium"
                  style={{ background: 'var(--accent-faint)', color: 'var(--accent-ink)' }}
                >
                  {count}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {crumb && (
        <div
          className="flex flex-1 items-center overflow-hidden px-4 text-sm"
          style={{ color: 'var(--fg-dim)' }}
        >
          {crumb}
        </div>
      )}

      <div className="ml-auto flex items-center gap-1 px-3">
        <SSEDot />
        <NotificationBell />
        <ThemeToggle />

        {me && (
          <Link
            to="/lk"
            className="hidden items-center gap-2 rounded-md px-3 py-1 text-sm md:flex"
            style={{ color: 'var(--fg-dim)' }}
            aria-label="Профиль"
          >
            <div
              className="flex h-5 w-5 items-center justify-center rounded-full text-2xs font-medium"
              style={{ background: 'var(--bg-3)', color: 'var(--fg)' }}
            >
              {me.username.slice(0, 2).toUpperCase()}
            </div>
            <span>{me.username}</span>
          </Link>
        )}

        <button
          type="button"
          onClick={handleLogout}
          className="icon-btn hidden md:inline-flex"
          aria-label="Выйти"
          title="Выйти"
        >
          <LogOut size={14} />
        </button>
      </div>
    </header>
  )
}
