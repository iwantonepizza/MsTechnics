# T-1-008. Prod logging: JSON в stdout + опционально Sentry

> **Тип:** infra
> **Приоритет:** P2
> **Оценка:** 1.5 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

В проде логи должны быть JSON-строками в stdout — это читается любым агрегатором (Loki, ELK, CloudWatch). Ошибки дополнительно шлются в Sentry для алертов.

---

## Зависимости

- **Блокируется:** T-1-004 (structlog)

---

## Что нужно сделать

### Часть 1: JSON в stdout на проде

Уже сделано в T-1-004. Убедиться:
1. `config/settings/prod.py`:
   ```python
   LOGGING["handlers"]["default"]["formatter"] = "json"
   LOGGING["loggers"][""]["level"] = "INFO"
   ```
2. Gunicorn `--access-logfile -` — чтобы access-логи тоже шли в stdout.
3. Проверить в docker-compose: `web` сервис имеет `logging` driver `json-file` (дефолт) — stdout автоматически собирается.

### Часть 2: Sentry

1. Добавить `sentry-sdk` в deps:
   ```toml
   # pyproject.toml, prod-only
   "sentry-sdk[django]>=2.3",
   ```

2. `config/settings/prod.py`:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration
   from sentry_sdk.integrations.redis import RedisIntegration
   from sentry_sdk.integrations.logging import LoggingIntegration

   SENTRY_DSN = env("SENTRY_DSN", default=None)
   if SENTRY_DSN:
       sentry_sdk.init(
           dsn=SENTRY_DSN,
           integrations=[
               DjangoIntegration(),
               RedisIntegration(),
               LoggingIntegration(
                   level=logging.INFO,     # breadcrumbs с уровня INFO
                   event_level=logging.ERROR,  # события только с ERROR
               ),
           ],
           traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
           send_default_pii=False,
           environment=env("DJANGO_ENV", default="prod"),
           release=env("RELEASE_VERSION", default=None),
       )
   ```

3. Добавить переменные в `.env.example`:
   ```
   # Sentry
   SENTRY_DSN=
   SENTRY_TRACES_SAMPLE_RATE=0.1
   ```

4. Инициализировать и для воркеров:
   ```python
   # sender_tg_message.py, daily_checker.py, ManageControl.py
   import os
   if os.environ.get("SENTRY_DSN"):
       import sentry_sdk
       sentry_sdk.init(
           dsn=os.environ["SENTRY_DSN"],
           environment=os.environ.get("DJANGO_ENV", "prod"),
       )
   ```

5. Прокинуть `user_id` и `request_id` в Sentry scope через middleware:
   ```python
   # shared/middleware.py (расширить существующий RequestIDMiddleware)
   import sentry_sdk

   def __call__(self, request):
       request_id = ...
       if request.user.is_authenticated:
           with sentry_sdk.configure_scope() as scope:
               scope.set_user({"id": request.user.id, "username": request.user.username})
               scope.set_tag("request_id", request_id)
       ...
   ```

### Часть 3: Log rotation в Docker

В `docker-compose.yml` для prod — ограничить размер json-log'ов:
```yaml
services:
  web:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

Иначе контейнер может съесть диск.

---

## Критерии приёмки

- [x] В prod — JSON логи в stdout при `DEBUG=False` через structlog JSONRenderer
- [x] Sentry SDK инициализируется, если `SENTRY_DSN` задан
- [ ] Тестовая ошибка (`raise Exception("test sentry")`) в view — требует реальный `SENTRY_DSN`
- [x] В Sentry/log context прокидываются `user_id`, `request_id`; `send_default_pii=False`
- [ ] Воркеры тоже пишут в Sentry при падении — отдельные legacy workers удалены, management commands покрываются Django settings
- [x] Docker log rotation настроен для `web`

---

## Что НЕ делать

- **НЕ включай** Sentry PII (`send_default_pii=True`) — риск утечки персональных данных. Прокидываем только ID явно.
- **НЕ шли** DEBUG-логи в Sentry — засорит quota.
- **НЕ настраивай** performance monitoring на 100% — начинаем с 10% sample rate.

---

## Известные сложности

- Sentry free-tier имеет квоту на события. Если приложение шумное (много exception'ов) — квота кончится. Митигация: в первый месяц — внимательно смотреть, вычистить noisy errors.
- `sentry-sdk` автоматически ловит unhandled exceptions в Django, но **не в async-тасках**. Для async — обернуть в `try/except` + `sentry_sdk.capture_exception`.
