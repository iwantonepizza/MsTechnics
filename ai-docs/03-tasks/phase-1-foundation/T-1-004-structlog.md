# T-1-004. Заменить print() на structlog, настроить структурное логирование

> **Тип:** infra / refactor
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Логи должны быть машиночитаемыми (JSON), структурированными, с контекстом. `print(...)` — только отладочный инструмент, не код для прода.

---

## Контекст

Сейчас в проекте:
- `print(queryset.count(), department_name)` в `service/templatetags/panel_tags.py:36` — попало в прод, засоряет stdout
- `print('Message received:', message['data'])` в `sender_tg_message.py`, `daily_checker.py`, `ManageControl.py`
- `LOGGING` в `settings.py` не настроен — Django дефолт
- Нет JSON-вывода
- Нет `request_id` в логах — невозможно коррелировать

---

## Зависимости

- **Блокируется:** T-1-001

---

## Что нужно сделать

1. Настроить `structlog` в `settings.py`:
   ```python
   import structlog

   LOGGING = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "json": {
               "()": structlog.stdlib.ProcessorFormatter,
               "processor": structlog.processors.JSONRenderer(),
           },
           "console": {
               "()": structlog.stdlib.ProcessorFormatter,
               "processor": structlog.dev.ConsoleRenderer(colors=True),
           },
       },
       "handlers": {
           "default": {
               "class": "logging.StreamHandler",
               "formatter": "json" if not DEBUG else "console",
           },
       },
       "loggers": {
           "": {
               "handlers": ["default"],
               "level": "INFO",
           },
           "django.server": {
               "handlers": ["default"],
               "level": "INFO",
               "propagate": False,
           },
           "django.db.backends": {  # чтобы не спамило SQL в dev
               "handlers": ["default"],
               "level": "WARNING",
               "propagate": False,
           },
       },
   }

   structlog.configure(
       processors=[
           structlog.contextvars.merge_contextvars,
           structlog.processors.add_log_level,
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
       ],
       logger_factory=structlog.stdlib.LoggerFactory(),
       wrapper_class=structlog.stdlib.BoundLogger,
       cache_logger_on_first_use=True,
   )
   ```

2. Middleware для `request_id`:
   ```python
   # shared/middleware.py
   import uuid
   import structlog

   class RequestIDMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response

       def __call__(self, request):
           request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
           structlog.contextvars.clear_contextvars()
           structlog.contextvars.bind_contextvars(
               request_id=request_id,
               user_id=request.user.id if request.user.is_authenticated else None,
               path=request.path,
               method=request.method,
           )
           response = self.get_response(request)
           response["X-Request-ID"] = request_id
           return response
   ```

   Подключить в `MIDDLEWARE` первым.

3. Найти все `print(...)`:
   ```bash
   grep -rn --include="*.py" "print(" . | grep -v migrations | grep -v __pycache__
   ```

4. Заменить каждый `print(...)` на `logger.info(...)` с осмысленным сообщением и полями:
   ```python
   # было:
   print(queryset.count(), department_name)

   # стало:
   logger.debug("panel_queryset_built",
                count=queryset.count(),
                department=department_name)
   ```

   Где `logger = structlog.get_logger(__name__)` в начале файла.

5. Отдельно обработать воркеры (`sender_tg_message.py`, `daily_checker.py`, `ManageControl.py`):
   - Добавить `structlog.configure(...)` на старте процесса (т.к. они не проходят через Django middleware)
   - Биндить `worker=tg_sender` / `worker=daily_checker` в contextvars

6. Проверить что работает:
   ```bash
   # dev — цветной консольный вывод
   DJANGO_DEBUG=True python manage.py runserver

   # prod-симуляция — JSON
   DJANGO_DEBUG=False python manage.py runserver
   ```

---

## Критерии приёмки

- [ ] Ни одного `print(` в коде (кроме `scripts/` если такая папка появится — ручные скрипты)
- [ ] `logger = structlog.get_logger(__name__)` в начале каждого модуля, где нужны логи
- [ ] В dev — человекочитаемый вывод (structlog.dev.ConsoleRenderer)
- [ ] В prod (DEBUG=False) — JSON в stdout
- [ ] В каждом запросе — `request_id`, прокидывается в response header `X-Request-ID`
- [ ] Воркеры (tg_sender, daily_checker) шлют JSON-логи с `worker=<name>` полем
- [ ] Pre-commit hook блокирует `print(` (добавить в ruff правило `T201` через `select`)

---

## Что НЕ делать

- **НЕ переписывай** всю бизнес-логику «пока руки в этом файле». Только replace `print` → `logger`.
- **НЕ настраивай** Sentry в этой задаче — T-1-008.
- **НЕ удаляй** `# TODO` комментарии рядом с `print` — переделай их в задачи через tracker.

---

## Ожидаемый diff

~30-50 `print()` → `logger.*` замен по проекту. Если найдёшь больше 70 — напиши в отчёте количественную оценку.
