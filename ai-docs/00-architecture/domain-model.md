# Модели домена

Это не схема БД, а схема **домена**. Связи между сущностями, инварианты, правила. Код БД — следствие.

---

## Слой core

### User (бывший MsUser)

```
User
├── username: string, unique
├── first_name, last_name
├── email
├── groups: M2M(Group)       ← Django Groups заменяют permission-поле
├── allowed_cities: M2M(City)
├── telegram_id: string | null
├── max_id: string | null    ← для MAX-бота
├── is_active: bool
├── date_joined
└── ... стандартные поля AbstractUser
```

**Изменение от текущего:**
- `permission` (CharField с choices) → удаляется, заменяется Django Groups (`monitoring`, `control`, `service`, `admin`, `all`, `technical`)
- Добавляется `max_id`
- Класс `ConcreteMsUser` удаляется

### City

```
City
├── id
├── slug: unique
├── name: unique                   (Казань, Ижевск)
├── description
└── timezone: string               ← новое! город может быть в своём часовом поясе
```

### Color

```
Color
├── id
├── name: unique            (бывший уникальный ключ)
├── hex_color: unique       ← регистронезависимо, валидация #RRGGBB
└── __str__: "Красный (#FF0000)"
```

### Icon (бывший Smile)

```
Icon
├── id
├── code: string unique     ← переименовали smile_icon → code (для программного использования)
├── glyph: string           ← сам эмодзи 🟢 / 🔥 / ❌
├── category: choice        ← 'status' / 'event' / 'condition' — чтобы сортировать в админке
└── description
```

**Требование от владельца:** разные смайлики для разных типов событий. `category` это решает — в админке можно фильтровать и задавать.

---

## Слой directory

### Display

```
Display
├── id
├── slug: unique
├── name: unique
├── description
├── city: FK(City)
├── rows, cols: uint
├── camera_link: URL
├── schematic_file: FileField    (бывший file)
├── project_file: FileField
├── attributes: JSONField         ← новое! см. далее
├── created_at, updated_at
│
├── cells: reverse(Cell.display)
├── panels: @property (панели в ячейках)
└── activity: reverse(ActivityLog)
```

### DisplayAttributes (новое, для фиксированной формы заполнения)

От владельца: «форма заполнения к каждому экрану».
Ответ: **фиксированный набор полей** (пункт 8 ответов).

Конкретно какие поля — владелец пришлёт позже. До тех пор — стаб:

```
DisplaySpec (1:1 c Display)
├── address: string
├── power_consumption_kw: Decimal
├── controller_type: string
├── pixel_pitch_mm: Decimal
├── installation_date: Date
├── warranty_until: Date
├── contact_person: string
├── contact_phone: string
├── notes: TextField
```

> **Задача владельцу:** выслать финальный список полей. До этого momentа мы рендерим форму по временной схеме, но миграция нормальная.

### Cell (ячейка)

```
Cell
├── id
├── display: FK(Display)
├── row, col: uint
├── panel: FK(Panel) | null      ← null = ячейка пустая
├── UniqueConstraint(panel)       ← панель может быть только в одной ячейке
├── UniqueConstraint(display, row, col)
└── position: @property → "01".."NN"
```

### Panel

```
Panel
├── id
├── name: unique              (COLOSSEUM-15)
├── display: FK(Display) | null
├── department: FK(Department)
├── condition: FK(Condition)
├── description: TextField
├── created_at, updated_at
│
├── events: reverse(ActivityLog) через GenericFK
└── applications: reverse(Application)
```

**Важно:** `application_status` из панели **удаляется**. Логика «есть ли активная заявка» вычисляется через `panel.applications.exclude(status__in=ARCHIVED_STATUSES).exists()`.
Избыточность текущая — источник багов.

### Department

```
Department
├── id
├── code: string unique       (monitor/service/zip/hand)
├── name: string
├── description
├── color: FK(Color)
├── color_text: FK(Color)
└── icon: FK(Icon)
```

### Condition

```
Condition
├── id
├── code: string unique       (work/problem/unrecoverable)
├── name: string
├── description
├── color: FK(Color)
├── color_text: FK(Color)
├── icon: FK(Icon)
├── allows_work: bool         ← новое! можно ли считать панель рабочей
└── is_terminal: bool          ← новое! unrecoverable = terminal
```

### Storage (склад)

```
StorageItem (абстрактный)
├── id
├── name: unique
├── description
├── count: uint ≥ 0
├── photo: ImageField
└── updated_at

Wires(StorageItem)
Hubs(StorageItem)
Lamels(StorageItem)
```

**Улучшение:** `count` управляется только через методы `adjust(delta, reason, actor)`, не через прямое присвоение. Это даёт событие в ActivityLog.

---

## Слой workflow

### Application

```
Application
├── id
├── display: FK(Display)
├── panel: FK(Panel)
├── cell: FK(Cell)               ← на момент создания
├── status: FK(ApplicationStatus)
├── executor: FK(Executor) | null
├── created_at, updated_at
│
├── events: reverse(ApplicationEvent)
└── activity: GenericRelation(ActivityLog)
```

### ApplicationStatus

```
ApplicationStatus
├── id
├── code: unique
├── name
├── description
├── color, color_text, icon
├── order: uint                   ← для сортировки в UI
└── is_terminal: bool             ← archive_done/archive_unable
```

### ApplicationEvent

```
ApplicationEvent
├── id
├── application: FK(Application)
├── stage: CharField              ← monitoring_create, control_apply, control_send, service_apply, service_complete, service_unable, archive_done, archive_unable, delete
├── from_status: FK(ApplicationStatus) | null   ← null для создания
├── to_status: FK(ApplicationStatus)
├── comment: TextField
├── file: FileField | null
├── actor: FK(User) | null
├── occurred_at: DateTime
```

Все старые поля `comment_monitoring`, `time_control_apply` и т.д. = `application.events.filter(stage='monitoring_create').first()` и т.д.

### Executor

Практически без изменений от текущего. Добавляется `max_id`.

### Departure

```
Departure
├── id
├── description
├── executor: FK(Executor)
├── status: FK(DepartureStatus)  ← новое! не CharField
├── time_created, time_updated
├── time_start, time_end
├── result: TextField
└── creator: FK(User)
```

### DepartureStatus (новое)

Вместо CharField с значениями строками — справочник:

```
DepartureStatus
├── code: unique (created, in_progress, done, archived)
├── name, color, icon
└── is_terminal
```

### DailyTask

Практически без изменений, но:
- уведомления идут через NotificationQueue, не напрямую
- `last_completed_date` вычисляется из last event
- `alert/deadline/lost/start/completed_notification_sent` (5 boolean-флагов) → одно поле `notified_stages: JSONField([stage_codes])`

---

## Слой activity

### ActivityLog (центральная таблица)

```
ActivityLog
├── id
├── actor: FK(User) | null       ← кто сделал
├── target_type: FK(ContentType)
├── target_id: int
├── target: GenericFK
├── event_type: CharField         ← см. список ниже
├── description: TextField        ← человекочитаемое (с эмодзи)
├── comment: TextField            ← пользовательский коммент
├── payload: JSONField            ← структурированные доп. данные
├── ip_address: IPAddress | null
└── occurred_at: DateTime
```

### Каталог event_type

| Группа          | event_type              | target      | Описание                    |
|-----------------|-------------------------|-------------|-----------------------------|
| application     | application.created     | Application | Заявка создана              |
| application     | application.transitioned| Application | Статус заявки изменён       |
| application     | application.deleted     | Application | Заявка удалена              |
| application     | application.executor_changed | Application | Сменили исполнителя      |
| panel           | panel.created           | Panel       |                             |
| panel           | panel.moved             | Panel       | Перемещение между отделами  |
| panel           | panel.condition_changed | Panel       | Смена состояния             |
| panel           | panel.comment_added     | Panel       | Ручной комментарий          |
| panel           | panel.installed         | Panel       | Установлена в ячейку        |
| panel           | panel.removed           | Panel       | Снята с ячейки              |
| display         | display.created         | Display     |                             |
| display         | display.updated         | Display     |                             |
| display         | display.photo_added     | Display     |                             |
| departure       | departure.created       | Departure   |                             |
| departure       | departure.completed     | Departure   |                             |
| departure       | departure.archived      | Departure   |                             |
| storage         | storage.count_changed   | Wires/Hubs/Lamels |                       |
| daily_task      | daily_task.started      | DailyTask   |                             |
| daily_task      | daily_task.completed    | DailyTask   |                             |
| daily_task      | daily_task.missed       | DailyTask   |                             |

**Расширяемый.** Добавить новый — задача «add event_type `<foo>`» + миграция хранит это в БД (иначе — хардкод).

---

## Слой notifications

### Notification

```
Notification
├── id
├── recipient: FK(User) | FK(Executor)   ← ровно один из двух
├── channel: CharField                   ← telegram / max / email
├── status: CharField                    ← pending / sent / failed / retrying
├── payload: JSONField                   ← {"text": "...", "buttons": [...]}
├── source_event_id: int | null          ← связь с ActivityLog
├── attempts: int
├── last_error: TextField | null
├── created_at, sent_at, updated_at
```

### NotificationPreference

```
NotificationPreference
├── user: FK(User)
├── event_type: CharField         ← какие события хочет получать
├── channel: CharField            ← по какому каналу
├── enabled: bool
```

Заменяет хардкод в `sorting_message.get_workers()`.

---

## Слой integrations

### GmailMessage / Alarm

Без изменений от текущего, но:
- перенос в `apps/integrations/gmail/`
- парсер выделяется в чистую функцию без БД-зависимостей (тестируется изолированно)

---

## Инварианты (то, что гарантирует БД + clean())

1. **Панель в одной ячейке.** `UniqueConstraint(Cell.panel)` — уже есть.
2. **Ячейка уникальна на экране.** `UniqueConstraint(display, row, col)` — уже есть.
3. **Активная заявка = не в terminal-статусе.** Проверяется через `status.is_terminal`.
4. **Панель в экране ⇔ находится в ячейке И `department=monitor`.** Не может быть в ячейке с другим department.
5. **Нельзя переместить панель в ЗИП с активной заявкой.** Проверка в `PanelMover.move()` + тест.
6. **DisplaySpec 1:1 с Display.** Создаётся в `DisplayFactory`.
7. **ApplicationEvent.to_status совпадает с текущим статусом заявки после создания события.** Проверяется в `ApplicationStateMachine`.
8. **У Cell.panel.display совпадает с Cell.display.** Иначе панель в «чужом» экране.

---

## Диаграмма связей (текстовая)

```
                     User
                      │
             ┌────────┼────────┐
       allowed_cities M:M   groups M:M
             │                 │
             ▼                 ▼
            City            Group (monitor/control/service/admin)

      City ──1:N──► Display ──1:1──► DisplaySpec
                      │
                      │ 1:N
                      ▼
                     Cell ──0..1──► Panel
                                      │
                                      ├── FK ──► Department
                                      ├── FK ──► Condition
                                      └── 1:N ──► Application ──► ApplicationStatus
                                                      │
                                                      ├── FK ──► Executor
                                                      └── 1:N ──► ApplicationEvent

      Departure ──FK──► Executor
      Departure ──FK──► DepartureStatus

      ActivityLog ──GenericFK──► any of [Panel, Display, Application, Departure, DailyTask, StorageItem]
      ActivityLog ──FK──► User (actor)

      Notification ──FK──► User | Executor
      Notification ──opt. ──► ActivityLog (source_event)
```

---

## Что мы НЕ добавляем (чтобы не раздуть скоуп)

- Комментарии к заявкам отдельной сущностью (Comment model) — пока живут внутри ApplicationEvent
- Тэги / метки — не нужны
- Прикреплённые файлы множественные — одна связь на этап, если нужно больше → вложенная модель потом
- Soft-delete — только для `Application` и `Departure`, остальное — `on_delete=PROTECT`
