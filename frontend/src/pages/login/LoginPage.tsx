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
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (accessToken) navigate('/menu', { replace: true })
  }, [accessToken, navigate])

  const onSubmit = async (data: FormData) => {
    try {
      await login.mutateAsync(data)
      navigate('/menu', { replace: true })
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail ?? 'Ошибка входа')
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ background: 'var(--bg-0)' }}
    >
      <div style={{ width: '100%', maxWidth: '340px' }}>
        <div className="mb-8 flex flex-col items-center">
          <img
            src="/logo-supersymmetria.svg"
            alt="Суперсимметрия"
            className="mb-3 h-auto w-[240px]"
          />
          <div
            className="text-lg font-semibold"
            style={{ color: 'var(--fg)', letterSpacing: '-0.01em' }}
          >
            Суперсимметрия
          </div>
          <p className="mt-1 text-xs" style={{ color: 'var(--fg-mute)' }}>
            Соединяем важное
          </p>
        </div>

        <div
          className="p-6"
          style={{
            background: 'var(--bg-1)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-lg)',
          }}
        >
          <h1 className="mb-5 text-sm font-semibold" style={{ color: 'var(--fg)' }}>
            Войти в систему
          </h1>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label
                className="mb-1.5 block text-xs"
                style={{
                  color: 'var(--fg-mute)',
                  fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Логин
              </label>
              <input
                {...register('username')}
                autoComplete="username"
                autoFocus
                className="input w-full"
              />
              {errors.username && (
                <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
                  {errors.username.message}
                </p>
              )}
            </div>

            <div>
              <label
                className="mb-1.5 block text-xs"
                style={{
                  color: 'var(--fg-mute)',
                  fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Пароль
              </label>
              <input
                {...register('password')}
                type="password"
                autoComplete="current-password"
                className="input w-full"
              />
              {errors.password && (
                <p className="mt-1 text-2xs" style={{ color: 'var(--err)' }}>
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={login.isPending}
              className="flex w-full items-center justify-center font-medium transition-colors disabled:opacity-50"
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
