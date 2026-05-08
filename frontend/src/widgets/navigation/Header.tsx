import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Home, Monitor, ShieldCheck, Wrench, Package, Car, LogOut, Zap, ZapOff } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMe, useLogout } from '@/features/auth/hooks'
import { useSSEStatus } from '@/shared/lib/sse'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import { toast } from 'sonner'

interface HeaderProps {
  crumb?: React.ReactNode
}

const NAV_ITEMS = [
  { to: '/menu',       label: 'Главная',    Icon: Home,         perm: null },
  { to: '/monitoring', label: 'Мониторинг', Icon: Monitor,      perm: 'monitoring' },
  { to: '/control',    label: 'Контроль',   Icon: ShieldCheck,  perm: 'control' },
  { to: '/service',    label: 'Сервис',     Icon: Wrench,       perm: 'service' },
  { to: '/zip',        label: 'ЗИП',        Icon: Package,      perm: null },
  { to: '/departures', label: 'Выезды',     Icon: Car,          perm: null },
]

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
  return (
    <span title={`SSE: ${status}`} className="flex items-center gap-1">
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
      className="flex items-center gap-0 shrink-0 border-b"
      style={{
        height: 'var(--h-header)',
        background: 'var(--bg-0)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Logo */}
      <Link
        to="/menu"
        className="flex items-center gap-2 px-4 shrink-0 h-full"
        style={{ borderRight: '1px solid var(--border-subtle)' }}
      >
        <div
          className="flex items-center justify-center w-6 h-6 rounded font-mono font-bold text-xs"
          style={{ background: 'var(--brand)', color: 'var(--brand-ink)' }}
        >
          MS
        </div>
        <span className="text-sm font-semibold hidden sm:block" style={{ color: 'var(--fg)' }}>
          Technics
        </span>
      </Link>

      {/* Nav */}
      <nav className="flex items-center h-full px-2">
        {NAV_ITEMS.filter(({ perm }) => isAllowed(perm)).map(({ to, label, Icon, perm }) => {
          const count = perm ? counts?.[perm as keyof typeof counts] ?? 0 : 0
          return (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => cn(
                'flex items-center gap-1.5 px-3 h-full text-sm transition-colors relative',
                isActive
                  ? 'font-medium'
                  : 'hover:opacity-90',
              )}
              style={({ isActive }) => ({
                color: isActive ? 'var(--fg)' : 'var(--fg-mute)',
                borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              })}
            >
              <Icon size={13} />
              <span>{label}</span>
              {count > 0 && (
                <span
                  className="flex items-center justify-center min-w-[16px] h-4 px-1 rounded text-2xs font-medium"
                  style={{ background: 'var(--accent-faint)', color: 'var(--accent)' }}
                >
                  {count}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Crumb */}
      {crumb && (
        <div className="flex-1 flex items-center px-4 text-sm" style={{ color: 'var(--fg-dim)' }}>
          {crumb}
        </div>
      )}

      {/* Right: SSE + user + logout */}
      <div className="ml-auto flex items-center gap-1 px-3">
        <SSEDot />

        {me && (
          <div
            className="flex items-center gap-2 px-3 py-1 rounded-md text-sm"
            style={{ color: 'var(--fg-dim)' }}
          >
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-2xs font-medium"
              style={{ background: 'var(--bg-3)', color: 'var(--fg)' }}
            >
              {me.username.slice(0, 2).toUpperCase()}
            </div>
            <span className="hidden md:block">{me.username}</span>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="flex items-center justify-center w-8 h-8 rounded-md transition-colors"
          style={{ color: 'var(--fg-mute)' }}
          onMouseOver={e => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseOut={e => (e.currentTarget.style.background = 'transparent')}
          title="Выйти"
        >
          <LogOut size={14} />
        </button>
      </div>
    </header>
  )
}
