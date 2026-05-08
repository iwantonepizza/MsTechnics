# Аудит текущего состояния проекта

Этот документ фиксирует **всё, что я нашёл** при первом проходе. Каждая строка — кандидат на задачу в `03-tasks/`. Ничего не додумано — всё со ссылками на файлы и строки.

Сортировано по слоям. Внутри слоя — по убыванию критичности.

---

## Часть 1. Модели (apps)

### MDL-001. Application имеет 28 полей-дубликатов

**Файл:** `application/models.py:4-83`

```python
comment_monitoring, time_monitoring, file_monitoring, user_monitoring,
comment_control_apply, time_control_apply, file_control_apply, user_control_apply,
... (ещё 5 этапов × 4 поля)
```

**Проблема:**
- Добавление нового этапа = миграция модели + 4 новых поля
- Запросы по истории = невозможны без OR-цепочек
- В админке — неудобно (всё в плоской форме)
- `apply_application()` — 150 строк копипаста по веткам на каждый этап

**Решение:** ApplicationEvent (см. `00-architecture/domain-model.md`).
**Задача:** T-2-001 «Миграция Application → нормализованная модель с ApplicationEvent».

---

### MDL-002. Пять идентичных HistoryReport моделей

**Файлы:**
- `application/models.py:ApplicationHistoryReport`
- `main_menu/models.py:DisplayHistoryReport`
- `main_menu/models.py:PanelHistoryReport`
- `main_menu/models.py:DailyTaskHistoryReport`
- `departure/models.py:DepartureHistoryReport`

Все имеют одинаковый набор полей: `description`, `comment`, `time`, `user`, + FK к целевой сущности.

**Проблема:**
- Невозможно сделать ленту «все события по экрану» без UNION 5 таблиц
- Любое изменение (новое поле — например, `ip_address`) — 5 миграций
- Отчёт пользователя **«видеть все действия в одном месте»** — фича-невозможно

**Решение:** единая `ActivityLog` с `ContentType.GenericForeignKey`.
**Задача:** T-2-002 «Создать ActivityLog, мигрировать 5 таблиц».

---

### MDL-003. FK везде по `to_field='name'`

**Файлы:** `application/models.py`, `zip/models.py`, `main/models.py`, `main_menu/models.py`.

Примеры:
```python
display = ForeignKey(Display, to_field='name')
panel = ForeignKey(Panels, to_field='name')
condition = ForeignKey(Condition, to_field='name')
```

**Проблема:**
- Переименовать `Condition.name` = каскадное обновление FK (или нарушение целостности)
- Индекс на `name` (string) тяжелее, чем на `id` (int)
- Миграции `makemigrations` нестабильны с `to_field`

**Исключение:** Если поле действительно стабильно (например, slug), можно оставить для конкретной модели — но в проекте это **везде**.

**Задача:** T-2-003 «Перевести все FK на PK».

---

### MDL-004. `ConcreteMsUser(MsUser)` — мёртвый класс

**Файл:** `user/models.py:37-38`

```python
class ConcreteMsUser(MsUser):
    pass
```

Импортируется один раз в `zip/models.py:11`:
```python
from user.models import ConcreteMsUser
```

Но нигде не используется. Это создаёт лишнюю таблицу при миграции (`user_concretemsuser`).

**Задача:** T-2-004 «Удалить ConcreteMsUser».

---

### MDL-005. `Display.save()` делает кучу побочки

**Файл:** `zip/models.py:70-119`

```python
def save(self, *args, **kwargs):
    is_new = self.pk is None
    extra_panels = getattr(self, "_extra_panels", 10)
    with transaction.atomic():
        super().save(*args, **kwargs)
        if is_new:
            # создание Cell × rows×cols
            # создание Panel × (rows×cols + 10)
            # привязка Panel к Cell
            # в цикле — создание PanelHistoryReport и DisplayHistoryReport (N записей INSERT)
```

**Проблемы:**
1. Хардкод `extra_panels = 10` — вне контекста откуда число
2. Внутри bulk_create — цикл с `cell.save()` (= UPDATE на каждую!) + создание истории в цикле
3. Для экрана 10×10 = 100 UPDATE + 200 INSERT в одной транзакции
4. Нельзя создать экран без ячеек (например, чтобы потом настроить руками)
5. Тест модели = тест всего мира

**Решение:** `DisplayFactory.create(name, city, rows, cols, extra_panels=10)` — фабрика.
**Задача:** T-2-005 «Вытащить логику Display.save в DisplayFactory».

---

### MDL-006. DailyTask хранит 5 boolean-флагов уведомлений

**Файл:** `zip/models.py:242-246`

```python
alert_notification_sent = BooleanField()
deadline_notification_sent = BooleanField()
lost_notification_sent = BooleanField()
start_notification_sent = BooleanField()
completed_notification_sent = BooleanField()
```

**Проблема:** Добавление нового этапа = миграция. `reset_task()` их обнуляет простыней. Тестирование `check_status` — mocking 5 полей.

**Решение:**
```python
notified_stages = ArrayField(CharField(max_length=32), default=list)
# или
notified_stages = JSONField(default=list)  # ['alert', 'start', 'deadline']
```

**Задача:** T-2-006 «DailyTask → notified_stages JSONField».

---

### MDL-007. `Departure.status` — CharField вместо FK

**Файл:** `departure/models.py:18`

```python
status = models.CharField(blank=True, default='Создан')
# сравнения: .exclude(status='В архиве'), if departure.status == 'Создан'
```

**Проблема:**
- Русский текст в коде (`'В архиве'`)
- Нельзя добавить цвет/иконку без CharField-choices и захардкоженных строк
- Опечатка в коде → фильтр не находит

**Решение:** Справочник `DepartureStatus` (code, name, color, icon).

---

### MDL-008. `Panel.application_status` — дубль

**Файл:** `zip/models.py:186`

```python
application_status = ForeignKey("application.ApplicationStatus", default='default')
```

Дублирует информацию, которая уже есть в `Application.status`. Это источник рассинхронизации: `apply_application()` меняет оба поля в двух разных местах, и я могу представить, как они рассинхронизируются при гонках.

**Решение:** удалить поле, вычислять через `panel.applications.exclude(...).first().status`.

---

### MDL-009. Signals пишет `sender` в CharField

**Файл:** `application/signals.py:17`

```python
@receiver(pre_delete, sender=Application)
def save_application_history(sender, instance, **kwargs):
    ApplicationHistoryReport.objects.create(
        ...
        user=sender  # ← sender это класс Application!
    )
```

При удалении заявки в `ApplicationHistoryReport.user` записывается `"<class 'application.models.Application'>"` (max_length=40 обрежет).

**Баг** — никто не замечал, потому что этот путь используется редко.

**Задача:** T-1-006 «Поправить signals.py, передавать actor».

---

### MDL-010. `change_panel_condition` — `if Panels:` вместо `if panel:`

**Файл:** `main/Db/orm_query.py:22`

```python
def change_panel_condition(panel, new_condition, ...):
    if type(panel) is str:
        panel = Panels.objects.get(name=panel)
    if Panels:   # ← класс, всегда truthy
        old_condition = panel.condition.description
        ...
```

«Работает» потому что `Panels` (класс) всегда truthy. Но если `panel` пришёл `None` — упадёт на `.condition.description`.

---

### MDL-011. `delete_application` зовёт presend **после** delete

**Файл:** `application/utils.py:41-63`

```python
def delete_application(app_id, user, comment, time_event):
    app = Application.objects.get(pk=int(app_id))
    ...
    if app.status.name in allowed_statuses:
        cell = Cell.objects.filter(panel=app.panel).first()
        app.panel.application_status = statuses.filter(name='default').first()
        app.panel.save()
        saved_text = (f'Удалена заявка {app_id}\n'
                      ...
                      f'Экран - {app.display} {cell.position}\n'   # ← если cell=None → AttributeError
```

При этом перед:
- если у заявки `cell=None` (невозможно по модели, но в БД с `PROTECT` и историей такое могло остаться)
- → упадёт в построении сообщения до `app.delete()`
- pre_delete сигнал не сработает

Тонкая ситуация. В новой архитектуре с transaction.on_commit и stateless message builder — эта проблема уходит.

---

## Часть 2. Views / Бизнес-логика

### VW-001. `apply_application` — 150 строк копипаста

**Файл:** `application/utils.py:78-231`

8 веток `if target_department == 'control_apply' / 'control_send' / ...`. В каждой:

```python
application.time_control_apply = application.last_update_date_time = time_event
if comment:
    application.comment_control_apply = comment
if file:
    application.file_control_apply = file
if user:
    application.user_control_apply = f'{user.first_name} {user.last_name}'
application.status = ApplicationStatus.objects.get(name='application_apply_in_control')
ApplicationHistoryReport.objects.create(...)
application.save()
application.panel.application_status = application.status
application.panel.save()
```

Каждая ветка = та же структура, меняется только 4 суффикса (`control_apply` → `control_send`).

**Это один из самых больных мест.** FSM-рефакторинг решает всё.

**Задача:** T-2-010 «Переписать apply_application в ApplicationStateMachine».

---

### VW-002. Бизнес-логика расползлась по 4 файлам

- `application/utils.py` — заявки
- `main/Db/orm_query.py` — панели (но туда залезла и dailytask)
- `zip/views.py` — логика смены департамента панели прямо во view
- `service/views.py` — change_panel_in_cell call + тонкая обвязка

Ни одного сервисного класса. Тесты → невозможны без mocking всей БД.

**Задача:** большая категория задач T-3-xxx «Вытащить логику в services».

---

### VW-003. `except Exception as e: messages.error(..., f"Ошибка: ,{e}!")`

**~30 вхождений.**

Это **не обработка**, это **глушилка**. Когда упадёт в проде — пользователь увидит `Ошибка: ,duplicate key value violates unique constraint "unique_panel"!`, и ни один инженер не поймёт, что значит «,» в начале.

Варианты фиксов:
1. Заменить на конкретные исключения (`Panel.DoesNotExist`, `IntegrityError`)
2. Глобальный exception middleware → generic для клиента, stacktrace в log
3. При переходе на DRF — exception handlers из коробки

---

### VW-004. `redirect(request.META['HTTP_REFERER'])` везде

**~20 вхождений.** См. SEC-005 в security-issues.md.

---

### VW-005. N+1 в `control_main` и `monitoring_main`

**Файлы:** `control/views.py:55`, `monitoring/views.py:37`

```python
application_report = ApplicationHistoryReport.objects.order_by('-time')
```

**Без limit'а**, без фильтра. Передаётся в шаблон. При рендере:
- Шаблон итерирует `{% for application in application_report %}`
- Обращается `{{ application.user }}` — CharField, OK
- Но мы **тащим всю историю заявок при каждом открытии страницы**

При 10k записей истории = несколько секунд рендер, десятки мегабайт RAM.

**Задача:** T-1-010 «Ограничить QuerySets списков в views limit=50 + pagination».

---

### VW-006. `service_main` prefetch'ит 7 уровней

**Файл:** `service/views.py:40-53`

```python
display = Display.objects.prefetch_related(
    "cell_set__panel__application_status__color",
    "cell_set__panel__application_status__color_text",
    "cell_set__panel__application_status",
    "cell_set__panel__condition",
    "cell_set__panel__condition__icon",
    "cell_set__panel__department",
    "cell_set__panel__display"
).get(name=display_name)
```

Тут уже понимание проблемы есть (автор знал про N+1). Но:
1. Это **mega-join**, не prefetch на самом деле
2. Далее в view **ещё** делается `get_display_application()` с 9-ю .filter
3. `free_panels = Panels.objects.filter(...)` — отдельно

Итого — 12+ SQL на один рендер. Для 30×30 экрана — 900 обращений в шаблоне через prefetch кэш.

**Решение:** REST API + React, экран собирается из нескольких API-вызовов, каждый оптимизирован. На бэке — один QuerySet с `select_related`.

---

### VW-007. `position` как @property → цикл по ячейкам в Python

**Файл:** `zip/models.py:143-157` + `service/views.py:62-63`

```python
# во view
cell = Cell.objects.filter(display=display)
cell = next((c for c in cell if c.position == get_position), None)
```

`position` — это property, вычисляется в Python:
```python
position_number = (self.row - 1) * cols_count + self.col
```

На экране 20×20 — 400 объектов тянется в Python, чтобы найти один по `position='15'`.

**Решение:**
```python
row, col = divmod(position_int - 1, display.cols)
cell = Cell.objects.get(display=display, row=row + 1, col=col + 1)
```

Или сделать `position` денормализованным полем с индексом.

---

### VW-008. `panel_change_department` не проверяет активную заявку

**Файл:** `zip/views.py:221-242`

```python
@require_POST
def panel_change_department(request):
    try:
        panel_id = request.POST.get('target_panel_id')
        target_department = request.POST.get('target_department')
        comment = request.POST.get('comment')
        panel = Panels.objects.get(id=panel_id)
        department = Department.objects.get(name=target_department)
        panel.department = department
        panel.save()
        # ← нет проверки: если у панели активная заявка, нельзя в ЗИП
```

**Это прямо одна из задач владельца:**
> «обработка исключений по типу активных заявок в перемещении между отделами в зипе»

**Задача:** T-2-011 «PanelMover: запрет перемещения с активной заявкой».

---

### VW-009. `get_display_application['all_new']` тащит архивные

**Файл:** `application/utils.py:244-246`

```python
'all': applications_at_display.exclude(status__in=('archive_done', 'archive_unable')),
'all_new': applications_at_display,
```

`all_new` включает архив. Шаблоны смешанно используют оба. Пользователь жалуется:
> «если заявка в архиве то не показывать в панели заявки»

Значит в каком-то месте в шаблоне рендерится `all_new` вместо `all`. Надо найти и убрать.

**Задача:** T-1-011 «Аудит использования applications в шаблонах, убрать all_new».

---

### VW-010. Дубль JSON-обработки модалок

Десятки вьюх вида:

```python
@login_required
def modal_xxx(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/xxx.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
```

Дубль × 10+. Все они — костыль для динамической подгрузки модалок через `fetch`. При переходе на SPA **все удаляются**: модалки — компонент React, данные — через API.

---

## Часть 3. Инфраструктура

### INF-001. `requirements.txt` в UTF-16

Подтверждено: `file requirements.txt` показывает BOM + null-byte padding. `pip install -r requirements.txt` падает в CI.

**Задача:** T-1-001 «Перенести зависимости в pyproject.toml, UTF-8».

---

### INF-002. `Config/` внутри репо, секреты в git

См. SEC-001..SEC-002.

---

### INF-003. Docker не определяет postgres сервис

**Файл:** `docker-compose.yml`

```yaml
services:
  web:
    env_file:
      - Config/.env
  tg_sender: ...
  manage_control: ...
  daily_checker: ...
  redis: ...

volumes:
  pgdata:   ← объявлен, но не используется
```

В `.env` есть `POSTGRES_HOST`, но **postgres-сервиса нет**. Значит либо используется внешний (IP сервера?), либо при `docker-compose up` падает.

Объявлен `pgdata` volume, но никуда не маунтится.

**Задача:** T-1-002 «Починить docker-compose: добавить postgres, split на dev/prod».

---

### INF-004. `requirements.txt` не пинован по хешам

Для прод-деплоя это риск supply-chain. Фикс — `pip-tools` или `poetry`.

---

### INF-005. Нет pre-commit hooks

Линтеры есть, но не обязательны. Кодер может закоммитить всё.

**Задача:** T-1-003 «Добавить pre-commit с ruff/black/mypy/djlint».

---

### INF-006. `print()` везде

~50 вхождений по коду. Вместо `logger`.

**Задача:** T-1-004 «Замена print на structlog».

---

### INF-007. Нет CI

Нет `.github/workflows/`. Каждый push — ничего не проверяется.

**Задача:** T-1-005 «GitHub Actions: lint + test + build».

---

### INF-008. Nginx конфиг минимальный

**Файл:** `Config/nginx.conf` — 20 строк. Нет:
- gzip
- HTTPS (redirect 80→443)
- security headers (X-Frame-Options, CSP)
- client_max_body_size (фото экранов могут быть большими)
- access log ротация
- static files кэширование

**Задача:** T-4-xxx «Prod nginx config».

---

## Часть 4. Notifications

### NOT-001. Прямой `async_to_sync` во view

**Файл:** `application/utils.py:25, 62, 228`

```python
async_to_sync(presend_filters)(text=..., type_msg='create_application')
```

Это **внутри** request-handler блокирует ответ до:
1. Сходить в Redis
2. Получить `publish` acknowledgement
3. Вернуться

Если Redis упал — view падает. Если медленный — юзер ждёт.

**Решение:** использовать `transaction.on_commit(lambda: queue.enqueue(...))` + не ждать доставки, только факт попадания в очередь.

---

### NOT-002. Redis PubSub = без гарантий доставки

**Файл:** `sorting_message.py:14-17`

```python
async def send_tg_message_private_async(json_msg):
    await redis_client.publish('send_tg_private', json_msg)
```

PubSub: если consumer не слушал в момент publish — сообщение потерялось. Без персистентности, без повторов.

**Решение:** Redis Streams (`XADD` + `XREADGROUP`), pending list, DLQ.

**Задача:** T-5-001 «Перевод очереди уведомлений на Redis Streams».

---

### NOT-003. Телеграм заблокирован — нет fallback

Владелец пишет: «уведомления снова наёбнулись, видимо из-за того что блочат в россии не шлет сообщения бот».

Решение — отдельный документ `06-integrations/telegram-russia-workaround.md` + `max-bot.md`.

---

### NOT-004. `get_workers(type_msg)` — список ролей захардкожен

**Файл:** `sorting_message.py:19-36`

```python
if type_msg == 'create_application':
    workers = workers.filter(permission__in=('service', 'admin', ...))
elif type_msg == 'delete_application':
    workers = workers.filter(permission__in=('service', 'admin', ...))  # ← то же
```

Полторы копипасты. + нельзя настроить «я не хочу уведомления о daily_task».

**Решение:** `NotificationPreference` модель (см. domain-model.md).

---

### NOT-005. Статус доставки висит в памяти consumer-а

**Файл:** `sender_tg_message.py:49-61`

`telegram_person['status']` — это только для отправки отчёта админу. В БД не пишется. Диагностика — кому дошло, кому нет — невозможна без логов.

**Решение:** `Notification` модель, БД + индекс по `status='failed'`.

---

## Часть 5. Frontend (templates/JS)

### FE-001. Хардкод URL в fetch

**Файл:** `templates/html/panel_info_block.html:404`

```js
fetch('https://www.mstechnics.ru/api/panel/edit-comment', { ... })
```

Ломается на staging/dev. Должно быть относительным.

---

### FE-002. 28 полей заявки в одном шаблоне

**Файл:** `application/templates/application/application_block.html`

153 строки, 7 секций-копий (мониторинг, контроль принятие, контроль отправка, сервис принятие, сервис работа, сервис невозможно, архив). При рефакторинге модели → шаблон сам по себе пересобирается из `application.events`.

---

### FE-003. Inline styles в шаблонах

Особенно в `panel_info_block.html`:

```django
<div class="application-status-color"
     style="background-color: {{ application.status.color.hex_color }};
            width: 2rem;
            height: 2rem;
            display: flex;
            ...">
```

С одной стороны, динамические цвета — оправданно. Но рядом — статический layout, который должен быть в CSS.

---

### FE-004. Dropdown — hover через JS, не CSS

Не нашёл в исходниках, но из шаблонов видно, что есть и CSS, и JS. При миграции на React — это уходит в shadcn/ui DropdownMenu.

---

### FE-005. Modal загрузка через HTML-фрагменты

Текущая модель: фронт делает `fetch('/x/modal-xxx/', {method: POST, body: JSON})`, сервер возвращает HTML-фрагмент, фронт его вставляет в `innerHTML`.

- XSS-риск если `innerHTML`
- Нет разделения данных и представления
- Невозможно тестировать модалку изолированно

→ при переезде на SPA всё это уходит.

---

### FE-006. Emoji-хардкод в Python

**Файл:** `zip/views.py:156-162`

```python
smiles = {
    'moving': '🚚',
    'breakdown': '💥',
    ...
}
```

Владелец хочет: «во всей истории придумать всем разные смайлики».
Решение: Icon модель (см. domain-model.md), хранятся в БД, админ редактирует.

---

### FE-007. «Нажмите чтобы получить информацию о заявках» везде title

Все элементы имеют `title` — нативный HTML tooltip. Но:
- Не работает на мобильных
- Стилизация ограничена
- Работает с задержкой

Решение: React + shadcn/ui Tooltip.

---

### FE-008. Владелец хочет hover-превью заявки

> «при наведении на цвет заявки всплывает заявка вся поверх чтобы почитать»

В шаблоне `panel_info_block.html:200-240` частично уже сделано — `<div class="tooltip-content">` с вложенным `{% include 'application/application_block.html' %}`, раскрывается через JS. Но:
- Tooltip фиксированный в углу экрана, не следует за курсором
- Показывает всю 153-строчную портянку — не читабельно

Решение: в SPA — `<PanelApplicationPreview application={app} />` компонент.

---

### FE-009. Комментарий без `line-clamp`

> «коменты не в одну строку а переносился и обрезался до 3х строк а при наведении все строки»

Нет CSS `line-clamp`, комменты рендерятся целиком. Фикс на CSS:

```css
.comment-text {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.comment-text:hover { -webkit-line-clamp: unset; }
```

В React — отдельный компонент `<ClampedText lines={3}>{text}</ClampedText>`.

---

## Часть 6. Тесты

### TST-001. Тестов нет

Все `tests.py` — дефолтные 1-строчные файлы:
```python
from django.test import TestCase
# Create your tests here.
```

**Coverage = 0%.** Любой рефакторинг без тестов — рулетка. Поэтому **фаза 2 начинается** с написания regression-тестов на текущее поведение, а уже потом — рефакторинг моделей.

---

## Итоговая таблица

| Слой          | Найдено issues | Высокой критичности |
|---------------|----------------|---------------------|
| Безопасность  | 15             | 7                   |
| Модели        | 11             | 5                   |
| Views/логика  | 10             | 6                   |
| Инфра         | 8              | 4                   |
| Notifications | 5              | 3                   |
| Frontend      | 9              | 2                   |
| Тесты         | 1 (категория)  | 1                   |
| **Итого**     | **~60**        | **~28**             |

---

## Что НЕ является проблемой (хотя выглядит)

Список того, что при первом взгляде кажется багом, но на самом деле работает:

1. **UniqueConstraint на Cell.panel** с nullable — OK, Django/PostgreSQL правильно обрабатывают NULL != NULL.
2. **`on_delete=PROTECT`** в куче мест — осознанно, предотвращает случайное удаление.
3. **`get_time_setting_tz()`** вместо `timezone.now()` — чтобы выставлять строго `Asia/Yekaterinburg` независимо от USE_TZ. Костыльно, но понимаю зачем.
4. **`Display.slug`** `blank=True, null=True` — можно оставить, если слаг необязателен (но тогда в URL-ах использовать id).
