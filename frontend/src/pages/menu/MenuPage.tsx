import { Link } from 'react-router-dom'
import { Monitor, Shield, Wrench, Package, Car, ArrowRight } from 'lucide-react'
import { useMe } from '@/features/auth/hooks'
import { useApplications } from '@/entities/application/hooks'
import { Badge } from '@/shared/ui/Badge'
import { Spinner } from '@/shared/ui/Spinner'

const DEPT_CARDS = [
  {
    to: '/monitoring', label: 'Мониторинг', icon: Monitor,
    perm: 'monitoring', color: '#22c55e',
    desc: 'Наблюдение за состоянием экранов, создание заявок',
  },
  {
    to: '/control', label: 'Контроль', icon: Shield,
    perm: 'control', color: '#fbbf24',
    desc: 'Обработка заявок, отправка в сервис',
  },
  {
    to: '/service', label: 'Сервис', icon: Wrench,
    perm: 'service', color: '#3b82f6',
    desc: 'Ремонт и замена панелей',
  },
  {
    to: '/zip', label: 'ЗИП', icon: Package,
    perm: null, color: '#a78bfa',
    desc: 'Склад запасных панелей и расходников',
  },
  {
    to: '/departures', label: 'Выезды', icon: Car,
    perm: null, color: '#f97316',
    desc: 'Управление выездными бригадами',
  },
]

export function MenuPage() {
  const { data: me, isLoading } = useMe()

  if (isLoading) {
    return <div className="flex items-center justify-center h-full"><Spinner className="w-6 h-6" /></div>
  }

  const userPerm = me?.permission ?? ''
  const isAdmin = ['admin', 'all'].includes(userPerm)

  const visible = DEPT_CARDS.filter(c => !c.perm || isAdmin || userPerm === c.perm)

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-xl font-semibold">Добро пожаловать, {me?.username}</h1>
        <p className="text-sm text-text-muted mt-1">
          {me?.allowed_cities.map(c => c.name).join(', ') || 'Нет доступных городов'}
        </p>
      </div>

      {/* Department cards */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        {visible.map(({ to, label, icon: Icon, color, desc }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col gap-3 p-4 bg-surface-2 border border-surface-3 rounded-xl hover:border-surface-4 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${color}22` }}
                >
                  <Icon size={16} style={{ color }} />
                </div>
                <span className="text-sm font-medium">{label}</span>
              </div>
              <ArrowRight size={14} className="text-text-muted group-hover:text-text-secondary transition-colors" />
            </div>
            <p className="text-xs text-text-muted">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
