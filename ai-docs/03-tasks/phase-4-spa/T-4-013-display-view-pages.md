# T-4-013 / T-4-014 / T-4-015. DisplayView — Сервис, Мониторинг, Контроль

> **Тип:** page
> **Приоритет:** P0
> **Оценка:** 7 часов суммарно (3 + 2 + 2)
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex
>
> Объединена в одну карточку т.к. это один компонент `DisplayViewPage` с prop `department`.

---

## Цель

Финализировать `DisplayViewPage` под эталон `frontend-design/screen-display-view.jsx` v2 и расширить под 3 отдела с их разной функциональностью.

---

## Зависимости

- **Блокируется:** T-4-001..T-4-004, T-3-fix-001 (статусы без префикса!)
- **Блокирует:** ничего

---

## Что в эталоне (`frontend-design/`)

- 3-колоночный layout: сетка экрана | KV-инфо панели | timeline rail
- 7 вкладок в нижней секции (для service)
- Footer с SSE-индикатором + горячими клавишами

---

## Различия по отделам

| Аспект | Сервис (T-4-013) | Мониторинг (T-4-014) | Контроль (T-4-015) |
|---|---|---|---|
| Снять/Поставить панель | ✅ есть | ❌ нет | ❌ нет |
| Inline-смена состояния | full dropdown | только work→problem | full с подтверждением |
| Кнопка "Создать заявку" | ❌ нет | ✅ на красных | ✅ есть |
| Главные actions заявки | взять [R] / выполнено [D] | только просмотр | принять [A] / в сервис [S] / архивировать [V] |
| Вкладки | 7 (Запросы, В работе, ...) | 5 (Мои создания, ...) | 7 (Запросы, Принятые, Отправленные...) |
| Назначение исполнителя | ❌ | ❌ | ✅ через "В сервис" |

---

## Что сделать

### Шаг 1. Существующий DisplayViewPage v0 переписать под эталон v2

Использовать `frontend-design/screen-display-view.jsx` как референс структуры. Декомпозировать на:

```
DisplayViewPage
├─ TitleBar (название экрана + city + UTC + 98/100 метрика)
├─ <DisplayGrid>           ← существует
├─ <PanelInfoCard>          ← новый widget на правой панели
├─ <TimelineRail>           ← новый widget (kombi 'история места' + 'история панели')
└─ <ApplicationsPanel>      ← существует, расширить под все отделы
   └─ <TabsRow>
   └─ <ApplicationsTable>
```

### Шаг 2. role-based UI

Использовать prop `department` для скрытия/показа кнопок:

```tsx
const PERMISSIONS = {
  monitoring: {
    canCreateApplication: true,       // на красных
    canMovePanels: false,
    canChangeCondition: 'limited',    // только work→problem
    transitions: [],                  // никаких transition, только просмотр
    tabs: ['my_created', 'in_progress', 'archive', 'history', 'all'],
  },
  control: {
    canCreateApplication: true,
    canMovePanels: false,
    canChangeCondition: true,
    transitions: ['apply_in_control', 'sent_to_service', 'archive_done', 'archive_unable'],
    tabs: ['received', 'accepted', 'sent_to_service', 'completed', 'archive', 'unable', 'all'],
    requireExecutorOn: ['sent_to_service'],   // модалка с executor dropdown
  },
  service: {
    canCreateApplication: false,
    canMovePanels: true,
    canChangeCondition: true,
    transitions: ['work_in_service', 'done', 'unable'],
    tabs: ['received', 'in_progress', 'completed', 'archive', 'history', 'unable', 'all'],
  },
}
```

### Шаг 3. Inline shortcuts

Footer показывает шорткаты по контексту:

```tsx
// Для service когда выбрана заявка
<KbdHint shortcut="R">взять в работу</KbdHint>
<KbdHint shortcut="D">выполнено</KbdHint>
<KbdHint shortcut="U">невозможно</KbdHint>

// Для control
<KbdHint shortcut="A">принять</KbdHint>
<KbdHint shortcut="S">в сервис</KbdHint>
<KbdHint shortcut="V">архивировать</KbdHint>
```

Реализовать через `useKeyboard` hook (см. T-4-033).

### Шаг 4. PanelInfoCard

Новый widget. Структура:

```tsx
function PanelInfoCard({ panel, cell, department }: Props) {
  return (
    <div className="bg-bg-1 border-l border-border-subtle p-4 space-y-4">
      {/* Header */}
      <div>
        <Label>панель</Label>
        <div className="font-mono text-[14px]">{panel.name}</div>
      </div>
      
      {/* KV-table */}
      <dl className="grid grid-cols-[92px_1fr] gap-y-1.5 text-[12.5px]">
        <Kv k="ячейка" v={cell.position} />
        <Kv k="состояние"    v={<ConditionPill condition={panel.condition} />} />
        <Kv k="отдел"        v={panel.department_name} />
        <Kv k="ID"           v={<IdChip>{panel.id}</IdChip>} />
        <Kv k="last move"    v={formatDate(panel.last_moved_at)} />
        <Kv k="комментарий"  v={panel.comment ?? '—'} />
      </dl>
      
      {/* Active applications */}
      {panel.active_application_status_name && panel.active_application_status_name !== 'default' && (
        <ActiveApplicationCard panelId={panel.id} />
      )}
      
      {/* Actions — role-based */}
      <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border-subtle">
        {department === 'monitoring' && (
          <Button variant="primary" size="md" disabled={!canCreate}>
            🆕 Создать заявку <Kbd>N</Kbd>
          </Button>
        )}
        {department === 'service' && (
          <>
            <Button variant="secondary" size="md">Поставить</Button>
            <Button variant="ghost" size="md">Снять</Button>
          </>
        )}
        {(department === 'service' || department === 'control') && (
          <Button variant="ghost" size="md">Сменить состояние</Button>
        )}
      </div>
    </div>
  )
}
```

### Шаг 5. TimelineRail

Объединение «история места» + «история панели» через `useActivityLog({ targetType, targetId })`:

```tsx
function TimelineRail({ cellId, panelId }: Props) {
  const { data: cellHistory = [] } = useActivityLog({ targetType: 'Cell', targetId: cellId, limit: 30 })
  const { data: panelHistory = [] } = useActivityLog({ targetType: 'Panel', targetId: panelId, limit: 30 })
  
  return (
    <div className="border-l border-border-subtle bg-bg-0 overflow-y-auto">
      <Section title="История места">
        {cellHistory.map(e => <TimelineRow key={e.id} entry={e} clickable />)}
      </Section>
      <Section title="История панели">
        {panelHistory.map(e => <TimelineRow key={e.id} entry={e} clickable />)}
      </Section>
    </div>
  )
}

// Каждая строка — кликабельная (по задаче владельца #11)
function TimelineRow({ entry, clickable }: { entry: ActivityLog; clickable?: boolean }) {
  const navigate = useNavigate()
  const onClick = () => {
    // Если в payload есть application_id — открыть модалку заявки
    if (entry.payload?.application_id) {
      navigate(`?modal=application&id=${entry.payload.application_id}`)
    }
  }
  return (
    <button
      onClick={clickable ? onClick : undefined}
      className="w-full text-left px-3 py-1.5 hover:bg-bg-2 text-[12px]"
    >
      <span className="font-mono text-fg-mute">{formatTime(entry.occurred_at)}</span>{' '}
      {entry.description}
    </button>
  )
}
```

### Шаг 6. Tabs row под отдел

```tsx
const tabs = PERMISSIONS[department].tabs.map(t => ({
  key: t,
  label: TAB_LABELS[t],  // 'Запросы', 'В работе', и т.д.
  count: useApplicationsCountByBox(displaySlug, t),
}))

<TabsRow value={activeTab} onChange={setActiveTab} items={tabs} />
```

---

## Критерии приёмки

- [ ] DisplayViewPage работает для всех 3 ролей с правильным набором кнопок
- [ ] Inline-смена состояния панели для monitoring ограничена (только work→problem)
- [ ] Создание заявки работает только для monitoring/control
- [ ] Снять/поставить панель — только для service
- [ ] Назначение исполнителя — модалка только для control при `target=sent_to_service`
- [ ] Timeline кликабельный (задача владельца #11)
- [ ] PanelInfoCard показывает active applications
- [ ] Шорткаты работают в зависимости от контекста выбранной заявки
- [ ] Сетка адаптируется под `cols/rows` экрана (не хардкод 16:9)
- [ ] ID-чипы используют CSS-переменные `--chip-bg/--chip-fg`, не хардкод hex
- [ ] 3-line clamp + popover для комментариев заявок

---

## Что НЕ делать

- НЕ дублировать код для 3 страниц — один компонент с prop
- НЕ хардкодить цвета — токены
- НЕ обходить FSM на фронте — через transition modal → API → ответ → react query invalidate
- НЕ блокировать UI оптимистичными обновлениями без rollback
