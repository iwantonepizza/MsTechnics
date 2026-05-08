# T-4-010. LoginPage — финальный вид

> **Тип:** page
> **Приоритет:** P0
> **Оценка:** 1.5 часа
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Простой логин-экран. Username + password, без forgot-password (внутренний инструмент, пароль через админа).

---

## Зависимости

- **Блокируется:** T-4-001 (tokens), T-4-002 (types), T-4-003 (router)

---

## Что сделать

### Структура

`frontend/src/pages/login/LoginPage.tsx`:

```tsx
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'

import { useLogin } from '@/features/auth/hooks'
import { Button } from '@/shared/ui/Button'

const schema = z.object({
  username: z.string().min(1, 'Введите имя пользователя'),
  password: z.string().min(1, 'Введите пароль'),
})

type FormData = z.infer<typeof schema>

export function LoginPage() {
  const navigate = useNavigate()
  const login = useLogin()
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })
  
  const onSubmit = async (data: FormData) => {
    try {
      await login.mutateAsync(data)
      navigate('/menu')
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? 'Ошибка входа'
      toast.error(msg)
    }
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-0 p-6">
      <div className="w-full max-w-sm bg-bg-1 border border-border-subtle rounded-lg p-6 shadow-modal">
        {/* Логотип + название */}
        <div className="flex items-center gap-3 mb-6">
          <svg width="28" height="28" viewBox="0 0 24 24">
            <rect x="2" y="2" width="20" height="20" rx="4" fill="var(--brand)"/>
            <path d="M6 17V8l3 5 3-5v9M14 17V8h3a2.5 2.5 0 0 1 0 5h-3"
                  stroke="var(--brand-ink)" strokeWidth="1.8" fill="none"
                  strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div>
            <div className="font-semibold text-[16px]">MsTechnics</div>
            <div className="text-fg-mute text-[11px] font-mono uppercase tracking-wider">ops</div>
          </div>
        </div>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field
            label="Имя пользователя"
            error={errors.username?.message}
            {...register('username')}
            autoFocus
          />
          <Field
            label="Пароль"
            type="password"
            error={errors.password?.message}
            {...register('password')}
          />
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Входим...' : 'Войти'}
          </Button>
        </form>
        
        <p className="text-fg-faint text-[11px] mt-4 text-center">
          Если забыли пароль — обратитесь к администратору
        </p>
      </div>
    </div>
  )
}

// Inline Field component
const Field = ({ label, error, ...rest }: any) => (
  <label className="block">
    <span className="text-fg-dim text-[11px] uppercase tracking-wider font-mono mb-1.5 block">
      {label}
    </span>
    <input
      className="w-full h-input px-3 rounded-md bg-bg-2 border border-border text-fg placeholder:text-fg-faint
                 focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent"
      {...rest}
    />
    {error && <span className="text-err text-[11px] mt-1 block">{error}</span>}
  </label>
)
```

### useLogin хук (если ещё не есть)

`frontend/src/features/auth/hooks.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { Me } from '@/shared/api/types'

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: { username: string; password: string }) => {
      const r = await apiClient.post<{ access: string }>('/auth/login/', data)
      localStorage.setItem('mstech_access', r.data.access)
      return r.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useMe() {
  return useQuery<Me>({
    queryKey: ['me'],
    queryFn: async () => (await apiClient.get('/me')).data,
    retry: false,
    staleTime: 60_000,
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.post('/auth/logout/'),
    onSettled: () => {
      localStorage.removeItem('mstech_access')
      qc.clear()
      window.location.href = '/login'
    },
  })
}
```

---

## Критерии приёмки

- [ ] Login form: username + password
- [ ] zod-валидация (пустые поля → inline error)
- [ ] Submit disabled пока isSubmitting
- [ ] При успехе → access в localStorage + navigate `/menu`
- [ ] При 401 → toast «Неверные учётные данные» через sonner
- [ ] При 422 (validation_error от бекенда) → ошибка в поле
- [ ] При 429 (throttle) → toast «Слишком много попыток, подождите»
- [ ] Дизайн соответствует `frontend-design/` (тёмный, OKLCH-палитра)

---

## Что НЕ делать

- НЕ показывать "Forgot password" — нет endpoint'а
- НЕ хранить пароль нигде, даже в state после submit
- НЕ автозаполнять test-значения в prod-сборке
