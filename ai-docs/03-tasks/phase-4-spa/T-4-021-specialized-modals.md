# T-4-021 / T-4-022 / T-4-023. CreateApplication / Move-Remove-Cell / ChangeCondition-Department

> **Тип:** feature
> **Приоритет:** P1
> **Оценка:** 4 часа суммарно (1.5 + 1.5 + 1)
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex
>
> Объединены — это специализированные модалки той же конструкции что T-4-020.

---

## Зависимости

- **Блокируется:** T-4-020 (универсальная Modal-структура)

---

## T-4-021. CreateApplicationModal

**Триггер:** monitoring/control нажимает «🆕 Создать заявку» на красной/проблемной ячейке.

**Поля:**
- `comment` (обязателен, min 1 char)
- `file` (опционально, image/*)

**Pre-filled:** `display_id`, `panel_id`, `cell_id` — приходят из контекста (выбранная ячейка).

**API:** `POST /api/v1/applications/` (multipart если есть file).

**Заметка:** есть в `frontend/src/features/applications/CreateApplicationModal.tsx` уже. Привести под итоговый шаблон Modal v2 + добавить optimistic update.

---

## T-4-022. RemoveFromCellModal + MoveToCellModal

### RemoveFromCell

**Триггер:** service нажимает «Снять» на ячейке с панелью.

**Поля:**
- `condition_id` (dropdown — work/problem/broken/unrecoverable; default — текущее)
- `comment` (опционально)

**API:** `POST /api/v1/panels/<id>/remove-from-cell/`

### MoveToCell

**Триггер:** service нажимает «Поставить» на пустой ячейке.

**Поля:**
- `panel_id` (dropdown — свободные панели в department=zip|hand)
- `comment` (опционально)

**API:** `POST /api/v1/panels/<id>/move-to-cell/`

**UX-детали:**
- Dropdown панелей сортируется: сначала те что в `department=zip` со state=`work`, потом `hand`, потом всё остальное.
- Показывается id-чип + condition + текущее место (если есть).

---

## T-4-023. ChangeConditionModal + ChangeDepartmentModal

### ChangeCondition

**Триггер:** service/control/admin нажимает «Сменить состояние» на панели.

**Поля:**
- `condition_id` (dropdown условий; текущее не доступно)
- `comment` (опционально, рекомендуется при ухудшении)

**API:** `POST /api/v1/panels/<id>/change-condition/`

### ChangeDepartment

**Триггер:** action из ZIP page или PanelInfoCard.

**Поля:**
- `department_name` (dropdown: zip / hand / service / monitor)
- `comment` (опционально)

**API:** `POST /api/v1/panels/<id>/change-department/`

**Warning при активной заявке:**

```tsx
const { data: panel } = usePanelDetail(panelId)
const hasActive = panel.active_application_status_name && panel.active_application_status_name !== 'default'

if (hasActive) {
  return (
    <WarningBanner>
      У панели активная заявка <IdChip>ID-{panel.active_application_id}</IdChip>.
      Сначала закройте заявку, потом меняйте отдел.
    </WarningBanner>
  )
  // submit-кнопка disabled
}
```

API сам вернёт 409 `panel_has_active_application`, но мы не делаем запрос если знаем заранее.

---

## Общая структура

Все 5 модалок (1 Create + 2 Move + 2 Change) делятся на компоненты:

```tsx
function ActionModal<TFormData>({
  title, schema, defaultValues, onSubmit, fields,
}: {
  title: string
  schema: ZodSchema<TFormData>
  defaultValues?: TFormData
  onSubmit: (data: TFormData) => Promise<void>
  fields: ReactNode  // jsx с полями
}) {
  // Универсальная обёртка с Dialog + form + buttons
}
```

Содержимое (`fields`) специфично для каждой модалки.

---

## Критерии приёмки

- [ ] CreateApplicationModal работает: pre-filled context, comment + file, success → invalidate
- [ ] RemoveFromCellModal — dropdown condition, опциональный comment
- [ ] MoveToCellModal — dropdown свободных панелей с сортировкой
- [ ] ChangeConditionModal — текущее условие исключено из dropdown
- [ ] ChangeDepartmentModal — warning при активной заявке, submit-disable
- [ ] Все 5 — Esc/Cmd+Enter, optimistic update, rollback при error
- [ ] Toast'ы об успехе и ошибке (sonner)

---

## Что НЕ делать

- НЕ дублировать код шапки/футера модалок — общий компонент `ActionModal`
- НЕ блокировать запрос если активная заявка — кнопка disabled, можно показать toast объяснения
- НЕ слать file как base64 — multipart/form-data
