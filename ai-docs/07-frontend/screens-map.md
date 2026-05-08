# Screens Map — карта экранов MsTechnics SPA

Детализация каждого экрана: путь, data requirements, компоненты, состояния, действия.

---

## 0. Login `/login`

**Задача:** аутентификация.

**API:**
- `POST /api/v1/auth/login` → `{ access, refresh }`
- `POST /api/v1/auth/refresh` → `{ access }`

**Компоненты:**
- `<LoginForm>` — логин, пароль, кнопка «Войти», ошибка

**Состояния:**
- idle / submitting / error

**Поведение:**
- После успеха — redirect на `?next` или `/menu`
- 2-3 неудачные попытки → rate limit (это на бэке)

---

## 1. Main Menu `/menu`

**Задача:** дашборд — обзор всего, куда у юзера есть доступ.

**API:**
- `GET /api/v1/dashboard/` → `{ monitoring: {...}, control: {...}, service: {...}, zip: {...} }`

**Компоненты:**
- `<Header>` (глобальный) — навигация + «Выход»
- `<DashboardBlock department="monitoring">` — последние события + быстрый переход
- `<DashboardBlock department="control">` — заявки в работе, свёрнуто
- `<DashboardBlock department="service">` — заявки на ремонт, свёрнуто
- `<DashboardBlock department="departures">` — активные выезды
- `<ApplicationCard>` (мелкая версия) — в блоках

**Состояния:**
- loading / loaded / empty (у юзера нет доступов) / error

**Поведение:**
- Видны только те блоки, в которые доступ (`request.user.permission in allowed.to_<dept>`)
- Клик по блоку → переход в `/<department>/`
- Клик по карточке заявки → `/<department>/<city>/<display>?app_id=<id>`

---

## 2. Department List `/monitoring`, `/control`, `/service`

**Задача:** выбрать город → экран.

**API:**
- `GET /api/v1/cities/?department=<dept>` → `[ { id, name, slug, displays: [ {id, name, description, slug, current_condition, ...} ] } ]`
- Только города, к которым у юзера доступ (`user.allowed_cities`)

**Компоненты:**
- `<CityBlock>` — заголовок города + список экранов
- `<DisplayListItem>` — имя, статус, ссылки: Электросхема / Проект / Контакт-лист / Фото / Открыть

**Состояния:**
- loading / loaded / no access (пустой список)

**Поведение:**
- Клик «Открыть» / по имени экрана → `/<dept>/<city-slug>/<display-slug>`
- Клик «Контакт-лист» → модалка с контактами
- Клик «Фото» → модалка с галереей
- Для `/control` справа от города — колонка активных заявок города

---

## 3. Display View — Сервис `/service/:city/:display`

**Задача:** основная рабочая зона сервисника.

**URL-параметры:**
- `?cell=<position>` — выбранная ячейка (например `03`)
- `?panel_id=<id>` — выбранная панель (если без ячейки)
- `?app_box=<state>` — вкладка заявок (`received` / `at_work` / `complete` / `archive` / `application_history` / `all_application` / `unable`)
- `?app_id=<id>` — открытая заявка

**API:**
- `GET /api/v1/displays/<city_slug>/<display_slug>/` → полная модель экрана со всеми ячейками
- `GET /api/v1/panels/?display=<id>&department=service` → свободные панели для замены
- `GET /api/v1/applications/?display=<id>&cell=<position>&box=<box>` → заявки для вкладки
- `PATCH /api/v1/panels/<id>/` → изменение состояния/комментария
- `POST /api/v1/applications/<id>/transition/` → переход заявки по FSM

**Layout (12-колоночная сетка):**
```
┌─────────────────────────────────────────────┐
│ Header (global)                             │
├──────────────┬──────────────────────────────┤
│ Title bar:   │ [Сервис Name]  [→ ЗИП]       │
├──────────────┴──────────────┬───────────────┤
│                              │               │
│  <DisplayGrid>               │ <PanelInfo>   │
│  10×10 сетка ячеек           │ выбранная     │
│                              │ панель +      │
│                              │ действия      │
│                              │               │
├──────────────────────────────┼───────────────┤
│ <HistoryBlock>  место+панель │ <Actions>     │
├──────────────────────────────┴───────────────┤
│ <ApplicationsTabs>  Запросы/В работе/...     │
│ <ApplicationsList>                           │
└──────────────────────────────────────────────┘
```

**Компоненты:**
- `<DisplayGrid>` — сетка ячеек, выделение активной, цвет по статусу заявки
- `<PanelInfoCard>` — инфо о выбранной панели: ID, модель, состояние, комментарий (inline-edit), активные заявки (с hover-preview — задача владельца #1), кнопки действий в зависимости от роли и статуса
- `<PlaceHistoryBlock>` — история места + история панели (две колонки)
- `<ApplicationTabs>` — 7 вкладок, см. задачу владельца #6 (у каждой своя сортировка)
- `<ApplicationCard>` + кнопки действий по статусу

**Состояния:**
- no-cell-selected / cell-selected-empty-slot / cell-selected-with-panel / no-applications / loading

**Ключевые действия:**
- Выбор ячейки: клик на `<Cell>` → URL `?cell=03` → right-side обновляется
- Снять панель: `<Modal panel-remove>` → POST `/api/v1/panels/<id>/remove-from-cell`
- Поставить панель: Dropdown со свободными → `<Modal change-panel>` → POST `/api/v1/cells/<id>/assign-panel`
- Изменить состояние панели: только если доступно; inline dropdown (задача владельца #5)
- Переход заявки по FSM: кнопка → `<Modal next-step>` → POST `/api/v1/applications/<id>/transition`

---

## 4. Display View — Мониторинг `/monitoring/:city/:display`

Как сервис, но:
- Нет кнопок «снять панель», «принять заявку», «ремонт»
- Есть кнопка «создать заявку» (🆕), активна только на красных панелях
- Можно менять состояние панели только `work → problem` (не `→ unrecoverable`)
- Вкладка заявок: только что видит монитор (`sent_to_control` и архивные свои)

---

## 5. Display View — Контроль `/control/:city/:display`

Как сервис, но:
- Вкладки: Запросы (sent_to_control) / Принятые (apply_in_control) / Отправленные в сервис (sent_to_service) / Выполненные сервисом (done) / Архив / Невозможные / История / Все
- Действия: Принять в работу → Отправить в сервис → Архивировать → (если не сделано)
- Можно переходить в архив с любого статуса

---

## 6. ZIP `/zip`, `/zip/:display`

**Задача:** учёт и перемещение панелей между складом/службами.

**API:**
- `GET /api/v1/panels/?department=<dept>&display=<slug>` — список по слотам
- `GET /api/v1/displays/<slug>/zip-filter/` — параметры фильтрации
- `PATCH /api/v1/panels/<id>/move/` — смена отдела
- `GET /api/v1/panels/<id>/history/` — история перемещений/состояний/поломок/сервиса
- `GET /api/v1/zip/modules/` — хабы, ламели, провода (глобально по экрану)

**Layout:**
```
┌─────────────────────────────────────────────┐
│ [ЗИП] [На руках] [Сервис] [В работе]        │
│ сетки панелей по каждому столбцу            │
├──────────────┬───────────────┬──────────────┤
│ <PanelInfo>  │ <ZipModules>  │ <Histories>  │
│ как в сервисе│ ламели/хабы/  │ перемещения  │
│              │ провода       │ состояния    │
│              │               │ поломки      │
│              │               │ сервис       │
└──────────────┴───────────────┴──────────────┘
```

**Ключевые особенности:**
- На `/zip` — фильтры: по экрану (одному конкретному), по состоянию панели (задача владельца #16)
- На `/zip/:display` — панели отфильтрованы по одному экрану, модули — тоже этого экрана
- Блокировка перемещения панели с активной заявкой (задача владельца #8)

---

## 7. Admin-related `/admin/*` (опционально)

Продолжаем использовать Django Admin для:
- Управление пользователями и разрешениями
- Настройка цветов, иконок, состояний панелей
- Настройка исполнителей
- Управление ежедневными задачами
- Фикстуры для DisplaySpec

Кастомной SPA-админки **не делаем.**

---

## 8. Личный кабинет `/lk`

**Задача:** смена пароля, просмотр своих разрешений.

**API:**
- `GET /api/v1/me/` → `{ username, email, permission, allowed_cities, telegram_id, max_chat_id }`
- `POST /api/v1/me/change-password/`
- `PATCH /api/v1/me/` → контакты

**Компоненты:** `<Profile>`, `<ChangePasswordForm>`, `<IntegrationsStatus>` (TG/MAX подключён?)

---

## 9. Инварианты роутинга

- **Неавторизованный** на любом пути → `/login?next=<path>`
- **Авторизованный без доступа к отделу** → `/menu` + toast «Нет доступа»
- **Авторизованный без доступа к городу** → экран отдела, но город не отображается
- **404** → кастомный NotFound, ссылка на `/menu`

---

## 10. Чеклист для каждого экрана перед мёржем

- [ ] Skeleton при загрузке
- [ ] Empty-state с объяснением что делать
- [ ] Error-state с кнопкой retry
- [ ] URL отражает состояние (selected, filters, tabs)
- [ ] Back button работает корректно
- [ ] Разрешения проверяются на клиенте (для UX) И на сервере (для безопасности)
- [ ] Все мутации — optimistic + обработка ошибки
- [ ] A11y: tab-order, focus-visible, aria-labels
- [ ] Mobile < 768 — «не поддерживается» экран
