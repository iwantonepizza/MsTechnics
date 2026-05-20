# T-4-030 / T-4-031. SSE интеграция + Optimistic mutations

> **Тип:** integration / UX
> **Приоритет:** P0
> **Оценка:** 3.5 часа (2 + 1.5)
> **Фаза:** 4
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Зависимости

- **Блокируется:** T-3-041 (SSE backend) уже готов
- **Блокирует:** T-4-032

---

## T-4-030. SSE: subscribe + invalidate

### Цель

`text/event-stream` от backend → react query инвалидирует соответствующие запросы.

### Что есть

`frontend/src/shared/lib/sse.ts` (по progress'у — есть «соединение есть, реакция на события — задача T-4-008»). Проверить и доделать.

### Что сделать

```ts
// frontend/src/shared/lib/sse.ts
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { create } from 'zustand'

interface ServerEvent {
  type: string  // 'application.transitioned', 'panel.condition_changed', etc.
  payload: any
  occurred_at: string
}

const useSSEStore = create<{
  status: 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
  setStatus: (s: any) => void
}>(set => ({
  status: 'connecting',
  setStatus: (status) => set({ status }),
}))

export const useSSEStatus = () => useSSEStore(s => s.status)

export function useSSESubscription() {
  const qc = useQueryClient()
  const setStatus = useSSEStore(s => s.setStatus)
  
  useEffect(() => {
    const access = localStorage.getItem('mstech_access')
    if (!access) return
    
    const url = `${import.meta.env.VITE_API_URL ?? '/api/v1'}/events/stream?token=${encodeURIComponent(access)}`
    let eventSource: EventSource | null = null
    let backoff = 1000
    let reconnectTimer: number | null = null
    
    const connect = () => {
      eventSource = new EventSource(url)
      
      eventSource.onopen = () => {
        setStatus('connected')
        backoff = 1000
      }
      
      eventSource.onmessage = (e) => {
        try {
          const event: ServerEvent = JSON.parse(e.data)
          handleEvent(event, qc)
        } catch (err) {
          console.error('SSE parse error', err)
        }
      }
      
      eventSource.onerror = () => {
        setStatus('reconnecting')
        eventSource?.close()
        reconnectTimer = window.setTimeout(connect, backoff)
        backoff = Math.min(backoff * 2, 30_000)  // exp до 30s
      }
    }
    
    connect()
    
    return () => {
      eventSource?.close()
      if (reconnectTimer) clearTimeout(reconnectTimer)
      setStatus('disconnected')
    }
  }, [qc, setStatus])
}

function handleEvent(event: ServerEvent, qc: QueryClient) {
  // Маппинг типа события на queryKey'и для инвалидации
  const { type, payload } = event
  
  if (type.startsWith('application.')) {
    qc.invalidateQueries({ queryKey: ['applications'] })
    if (payload.application_id) {
      qc.invalidateQueries({ queryKey: ['application', payload.application_id] })
    }
  }
  
  if (type.startsWith('panel.')) {
    qc.invalidateQueries({ queryKey: ['panels'] })
    if (payload.panel_id) {
      qc.invalidateQueries({ queryKey: ['panel', payload.panel_id] })
    }
    if (payload.display_id) {
      qc.invalidateQueries({ queryKey: ['display', payload.display_id] })
    }
  }
  
  if (type.startsWith('display.')) {
    qc.invalidateQueries({ queryKey: ['displays'] })
  }
  
  if (type.startsWith('departure.')) {
    qc.invalidateQueries({ queryKey: ['departures'] })
  }
}
```

### Подключить в App.tsx

```tsx
function App() {
  useSSESubscription()  // глобальная подписка для всех страниц
  // ...
}
```

### Тест

```ts
test('SSE: применяет invalidation при transition событии', () => {
  // mock EventSource через msw или fake-eventsource
  // эмулировать message с type='application.transitioned'
  // проверить что qc.invalidateQueries вызван с ['applications']
})
```

---

## T-4-031. Optimistic mutations + rollback

### Цель

Все мутирующие действия — мгновенное обновление UI, rollback если сервер вернул ошибку.

### Где обязательно optimistic

| Action | Optimistic update | Rollback на error |
|---|---|---|
| Application transition | Меняем `status.name` сразу | Восстановить previous |
| Application create | Добавить в список новую | Удалить из списка |
| Application delete | Убрать из списка | Вернуть в список |
| Panel change condition | Меняем `condition.name` сразу | Восстановить previous |
| Panel move to cell | Перерисовать grid | Восстановить previous |
| Panel remove from cell | Очистить ячейку | Восстановить previous |

### Паттерн (используется во всех hooks)

```ts
useMutation({
  mutationFn: (data) => apiClient.post(...),
  
  onMutate: async (variables) => {
    const queryKey = ['display', displayId]  // или другой
    
    await qc.cancelQueries({ queryKey })
    const previous = qc.getQueryData(queryKey)
    
    qc.setQueryData(queryKey, (old) => {
      // ... оптимистичная мутация
      return modifiedOld
    })
    
    return { previous, queryKey }  // ctx для rollback
  },
  
  onError: (err, variables, ctx) => {
    if (ctx?.previous) {
      qc.setQueryData(ctx.queryKey, ctx.previous)
    }
    toast.error(err?.response?.data?.detail ?? 'Ошибка')
  },
  
  onSettled: (_, __, variables) => {
    qc.invalidateQueries({ queryKey: ctx.queryKey })
  },
})
```

### Где НЕ использовать optimistic

- **Создание заявки с file upload** — не угадать `id` и `events[]` структуру.
- **Долгие операции с side effects** (например, change_department с side-effect в ZIP).

В таких случаях — pessimistic с pending-state на кнопке.

---

## Критерии приёмки T-4-030

- [ ] SSE подключается на старте, статус `connected`
- [ ] При сетевой ошибке — `reconnecting` + exponential backoff
- [ ] Server события вызывают `qc.invalidateQueries`
- [ ] Header SSE-индикатор обновляется (зелёный/жёлтый/красный)
- [ ] При закрытии вкладки — `eventSource.close()`

## Критерии приёмки T-4-031

- [ ] 6 мутирующих действий — optimistic
- [ ] При 5xx error — UI откатывается + toast
- [ ] При 409 (FSM/business error) — UI откатывается + специфичный toast «Нельзя: <reason>»
- [ ] При 403 — UI откатывается + toast «Нет прав»
- [ ] Concurrent mutations не конфликтуют (`cancelQueries` работает)

---

## Что НЕ делать

- НЕ держать SSE в специфичной странице (только глобально в App.tsx)
- НЕ полагаться только на SSE — **всегда** invalidate на onSettled (страховка)
- НЕ optimistic-у-обновлять то что зависит от backend (ID, computed fields)
