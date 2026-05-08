# T-4-032 / T-4-033 / T-4-040 / T-4-041. Skeleton states, shortcuts, tests

> **Тип:** UX-полировка + tests
> **Приоритет:** P1
> **Оценка:** 5 часов суммарно (1 + 1 + 1 + 2)
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## T-4-032. Skeleton/Empty/Error на всех страницах

### Двухпороговая загрузка

Из `ai-docs/07-frontend/design-brief.md`: **<300ms — ничего, >300ms — skeleton.**

```ts
// frontend/src/shared/lib/useDeferredLoading.ts
import { useEffect, useState } from 'react'

export function useDeferredLoading(isLoading: boolean, threshold = 300): boolean {
  const [show, setShow] = useState(false)
  
  useEffect(() => {
    if (!isLoading) {
      setShow(false)
      return
    }
    const t = window.setTimeout(() => setShow(true), threshold)
    return () => window.clearTimeout(t)
  }, [isLoading, threshold])
  
  return show
}
```

Использование:
```tsx
const { data, isLoading, error } = useDisplays(...)
const showSkeleton = useDeferredLoading(isLoading)

if (error)              return <ErrorState onRetry={refetch} />
if (showSkeleton)       return <DisplaysListSkeleton />
if (data?.length === 0) return <EmptyState message="Экранов нет" />
return <DisplaysList items={data!} />
```

### Skeleton использует token

```tsx
function DisplayListSkeleton() {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="skeleton h-12 rounded-md" />
      ))}
    </div>
  )
}
```

`.skeleton` уже есть в `tokens.css`.

### Empty / Error компоненты

```tsx
// shared/ui/EmptyState.tsx (вероятно есть, проверить)
export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-fg-mute py-12 gap-3">
      <span className="text-[14px]">{message}</span>
      {action}
    </div>
  )
}

export function ErrorState({ message = 'Не удалось загрузить', onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-err py-12 gap-3">
      <AlertTriangle className="w-6 h-6" />
      <span className="text-[13px]">{message}</span>
      {onRetry && <Button variant="ghost" size="sm" onClick={onRetry}>Повторить</Button>}
    </div>
  )
}
```

### Критерии

- [ ] `useDeferredLoading` создан и используется
- [ ] Все основные страницы имеют 3 состояния
- [ ] Skeleton использует `.skeleton` из `tokens.css`
- [ ] EmptyState с иконкой и сообщением
- [ ] ErrorState с retry-кнопкой

---

## T-4-033. Keyboard shortcuts

### Список

| Shortcut | Действие | Контекст |
|---|---|---|
| `/` | Фокус в глобальный поиск | Anywhere |
| `?` | Открыть help-overlay со списком shortcuts | Anywhere |
| `Esc` | Закрыть модалку | Modal open |
| `Ctrl+Enter` / `Cmd+Enter` | Submit формы | Modal open |
| `R` | Взять в работу заявку | Service display-view, выбрана заявка |
| `D` | Выполнено | Service, выбрана заявка |
| `U` | Невозможно | Service, выбрана заявка |
| `A` | Принять (control) | Control, выбрана заявка |
| `S` | В сервис (control) | Control, выбрана заявка |
| `V` | Архивировать | Control, выбрана заявка с `done`/`unable` |
| `N` | Создать заявку | monitoring/control, выбрана ячейка |

### Hook

```ts
// frontend/src/shared/lib/useKeyboard.ts
import { useEffect } from 'react'

interface ShortcutMap {
  [key: string]: () => void
}

export function useKeyboard(shortcuts: ShortcutMap, enabled = true) {
  useEffect(() => {
    if (!enabled) return
    
    const handler = (e: KeyboardEvent) => {
      // Игнорируем если фокус в input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }
      
      const combo = [
        e.ctrlKey || e.metaKey ? 'Mod+' : '',
        e.shiftKey ? 'Shift+' : '',
        e.key,
      ].join('')
      
      const handler = shortcuts[combo] ?? shortcuts[e.key]
      if (handler) {
        e.preventDefault()
        handler()
      }
    }
    
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [shortcuts, enabled])
}
```

### Использование на DisplayView

```tsx
function DisplayViewPage({ department }: Props) {
  const [selectedApp, setSelectedApp] = useState<Application | null>(null)
  
  useKeyboard({
    R: () => department === 'service' && selectedApp?.status.name === 'sent_to_service' && openTransition('work_in_service'),
    D: () => department === 'service' && selectedApp?.status.name === 'work_in_service' && openTransition('done'),
    U: () => department === 'service' && selectedApp?.status.name === 'work_in_service' && openTransition('unable'),
    A: () => department === 'control' && selectedApp?.status.name === 'sent_to_control' && openTransition('apply_in_control'),
    S: () => department === 'control' && selectedApp?.status.name === 'apply_in_control' && openTransition('sent_to_service'),
    V: () => department === 'control' && (selectedApp?.status.name === 'done' || selectedApp?.status.name === 'unable') && openTransition('archive_done'),
    N: () => (department === 'monitoring' || department === 'control') && selectedCell && openCreateApplication(),
    '?': () => openShortcutsHelp(),
    '/': () => focusGlobalSearch(),
  })
}
```

### Help overlay

```tsx
function ShortcutsHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-bg-0/80" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[420px] bg-bg-1 border border-border rounded-lg p-5">
          <Dialog.Title className="font-semibold mb-4">Горячие клавиши</Dialog.Title>
          <dl className="grid grid-cols-[80px_1fr] gap-y-2 text-[13px]">
            <dt><Kbd>/</Kbd></dt><dd>Поиск</dd>
            <dt><Kbd>?</Kbd></dt><dd>Эта подсказка</dd>
            {/* ... остальные */}
          </dl>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
```

### Критерии

- [ ] `useKeyboard` hook готов
- [ ] Shortcuts работают только когда фокус не в input/textarea
- [ ] Help overlay открывается на `?`
- [ ] Каждый shortcut выполняется только в правильном контексте (роль + статус заявки)
- [ ] Footer DisplayView показывает релевантные shortcut'ы

---

## T-4-040. Vitest unit-tests

### Что покрыть

```
features/auth/hooks.test.ts        — useLogin, useMe, useLogout
features/applications/hooks.test.ts — useTransitionApplication (optimistic + rollback)
features/applications/transitionConfigs.test.ts — buildSchema для каждого config
shared/lib/useKeyboard.test.ts     — handler invocation, ignored on input
shared/lib/useDeferredLoading.test.ts
shared/api/client.test.ts          — interceptor, refresh logic
entities/application/hooks.test.ts — caching, queryKey
```

### Setup

`frontend/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
})
```

### Критерии

- [ ] Vitest настроен
- [ ] Coverage ≥ 60% по hooks/lib
- [ ] CI прогоняет `pnpm test`

---

## T-4-041. Playwright e2e

### Сценарии

```ts
// frontend/e2e/login.spec.ts
test('Логин и переход на главное меню', async ({ page }) => {
  await page.goto('/login')
  await page.fill('input[name=username]', 'control_user')
  await page.fill('input[name=password]', 'test_password')
  await page.click('button:has-text("Войти")')
  await expect(page).toHaveURL('/menu')
})

// frontend/e2e/transition.spec.ts
test('Контролёр принимает заявку', async ({ page, context }) => {
  await loginAs(page, 'control_user')
  await page.goto('/control/izhevsk/colosseum')
  await page.click('text=Запросы')
  await page.click('[data-app-id="4567"]')
  await page.keyboard.press('A')  // shortcut
  await expect(page.locator('.transition-modal')).toBeVisible()
  await page.click('button:has-text("Принять заявку")')
  await expect(page.locator('.transition-modal')).not.toBeVisible()
  await expect(page.locator('[data-app-id="4567"] .pill-info')).toContainText('apply_in_control')
})

// frontend/e2e/sse.spec.ts
test('SSE: панель меняет цвет при event\'е от другого пользователя', async ({ browser }) => {
  // 2 контекста: A (мониторинг) и B (сервис)
  // A открывает display-view
  // B меняет condition панели
  // A через SSE видит изменение без рефреша
})
```

### Setup

```bash
cd frontend
pnpm dlx playwright install
pnpm playwright test
```

### Критерии

- [ ] Playwright config работает
- [ ] 3+ сценария: login, transition, sse-realtime
- [ ] CI запускает e2e в headless режиме (можно отключить пока, если slow)
- [ ] Скриншоты на failure
- [ ] DB seeded для e2e (отдельная команда `pnpm seed:e2e`)

---

## Что НЕ делать

- НЕ пытаться покрыть 100% — фокус на критичных путях (auth, transitions, SSE)
- НЕ запускать e2e на каждый push — только на main + PR
- НЕ хардкодить URL/credentials в тестах — env vars
