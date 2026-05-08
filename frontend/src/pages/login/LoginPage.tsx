import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useLogin } from '@/features/auth/hooks'
import { useAuthStore } from '@/features/auth/store'

const schema = z.object({
  username: z.string().min(1, 'Введите логин'),
  password: z.string().min(1, 'Введите пароль'),
})
type FormData = z.infer<typeof schema>

export function LoginPage() {
  const navigate = useNavigate()
  const { accessToken } = useAuthStore()
  const login = useLogin()

  const {
    register, handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (accessToken) navigate('/menu', { replace: true })
  }, [accessToken, navigate])

  const onSubmit = async (data: FormData) => {
    try {
      await login.mutateAsync(data)
      navigate('/menu', { replace: true })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Ошибка входа')
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'var(--bg-0)' }}
    >
      <div style={{ width: '100%', maxWidth: '340px' }}>
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="flex items-center gap-2 mb-1"
          >
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg font-mono font-bold text-base"
              style={{ background: 'var(--brand)', color: 'var(--brand-ink)' }}
            >
              MS
            </div>
            <span className="text-lg font-semibold" style={{ color: 'var(--fg)', letterSpacing: '-0.01em' }}>
              Technics
            </span>
          </div>
          <p className="text-xs" style={{ color: 'var(--fg-mute)' }}>
            Управление LED-экранами
          </p>
        </div>

        {/* Form card */}
        <div
          className="p-6"
          style={{
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-lg)',
          }}
        >
          <h1 className="text-sm font-semibold mb-5" style={{ color: 'var(--fg)' }}>
            Войти в систему
          </h1>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label
                className="block text-xs mb-1.5"
                style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}
              >
                Логин
              </label>
              <input
                {...register('username')}
                autoComplete="username"
                autoFocus
                className="w-full text-sm transition-colors focus:outline-none"
                style={{
                  height: 'var(--h-input)',
                  padding: '0 10px',
                  background: 'var(--bg-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  color: 'var(--fg)',
                }}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-faint)' }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
              />
              {errors.username && (
                <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.username.message}</p>
              )}
            </div>

            <div>
              <label
                className="block text-xs mb-1.5"
                style={{ color: 'var(--fg-mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}
              >
                Пароль
              </label>
              <input
                {...register('password')}
                type="password"
                autoComplete="current-password"
                className="w-full text-sm transition-colors focus:outline-none"
                style={{
                  height: 'var(--h-input)',
                  padding: '0 10px',
                  background: 'var(--bg-1)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  color: 'var(--fg)',
                }}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-faint)' }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
              />
              {errors.password && (
                <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={login.isPending}
              className="w-full flex items-center justify-center font-medium transition-colors disabled:opacity-50"
              style={{
                height: 'var(--h-btn-lg)',
                background: 'var(--accent)',
                color: 'var(--accent-ink)',
                borderRadius: 'var(--r-md)',
                fontSize: '13px',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {login.isPending ? 'Вход...' : 'Войти'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
