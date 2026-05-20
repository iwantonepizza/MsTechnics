# T-1-002. Правка docker-compose: postgres в compose, env_files, сети

> **Тип:** infra
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Привести `docker-compose.yml` в состояние, в котором его можно поднять на любом dev-хосте без правок (postgres внутри compose, секреты из env, healthchecks).

---

## Контекст

Текущий `docker-compose.yml`:
- **Нет postgres-сервиса** — он поднят на хосте где-то
- `env_file: Config/.env` — Config/.env в репо, `.env` — в `.gitignore`. В задаче T-1-007 придём к `.env` в корне и `Config/` удалим.
- Нет healthcheck'ов; сервисы стартуют независимо от готовности друг друга
- Нет volumes для postgres — данные в контейнере
- `manage_control` и `daily_checker` стартуют одновременно с `web`, до миграций

---

## Зависимости

- **Блокируется:** T-1-001 (pyproject.toml)
- **Блокирует:** T-1-005 (CI гоняет compose-тесты)

---

## Что нужно сделать

1. Переписать `docker-compose.yml`:
   ```yaml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_DB: ${DATABASE_NAME}
         POSTGRES_USER: ${DATABASE_USER}
         POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
       volumes:
         - pgdata:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER}"]
         interval: 5s
         timeout: 3s
         retries: 10
       networks: [backend]
       restart: always

     redis:
       image: redis:7-alpine
       volumes:
         - redisdata:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 10
       networks: [backend]
       restart: always

     web:
       build: .
       image: mstechnics-web:${VERSION:-latest}
       volumes:
         - ./staticfiles:/app/staticfiles
         - ./media:/app/media
       ports:
         - "8000:8000"
       env_file: .env
       depends_on:
         db:
           condition: service_healthy
         redis:
           condition: service_healthy
       networks: [backend]
       restart: always
       command: >
         bash -c "python manage.py migrate --noinput &&
                  python manage.py collectstatic --noinput &&
                  gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --access-logfile -"

     tg_sender:
       build: .
       command: python3 sender_tg_message.py
       env_file: .env
       depends_on:
         redis:
           condition: service_healthy
         web:
           condition: service_started
       networks: [backend]
       restart: always

     manage_control:
       build: .
       command: python3 ManageControl.py
       env_file: .env
       depends_on:
         web:
           condition: service_started
       networks: [backend]
       restart: always

     daily_checker:
       build: .
       command: python3 daily_checker.py
       env_file: .env
       depends_on:
         web:
           condition: service_started
       networks: [backend]
       restart: always

   volumes:
     pgdata:
     redisdata:

   networks:
     backend:
   ```

2. Создать `docker-compose.override.yml` для dev:
   ```yaml
   services:
     web:
       volumes:
         - .:/app  # hot-reload кода
       command: python manage.py runserver 0.0.0.0:8000
   ```

3. Создать `.env.example` в корне с плейсхолдерами (не реальными значениями!):
   ```
   # Django
   DJANGO_SETTINGS_MODULE=config.settings.dev
   DJANGO_SECRET_KEY=change-me-in-production
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

   # Database
   DATABASE_NAME=mstechnics
   DATABASE_USER=mstechnics
   DATABASE_PASSWORD=change-me
   DATABASE_HOST=db
   DATABASE_PORT=5432

   # Redis
   REDIS_URL=redis://redis:6379/0

   # Telegram
   TELEGRAM_BOT_TOKEN=
   TELEGRAM_PROXY_URL=

   # Gmail
   GMAIL_USER=
   GMAIL_APP_PASSWORD=
   ```

4. Проверить что `docker compose up --build` работает с нуля на чистой машине (локально).

5. Обновить README: раздел «Локальная разработка».

---

## Критерии приёмки

- [ ] `docker compose up --build` работает из чистого репо (с `.env` скопированного из `.env.example`)
- [ ] Postgres поднимается, данные сохраняются в volume
- [ ] `web` стартует только после того как db/redis готовы (healthcheck)
- [ ] `tg_sender`, `manage_control`, `daily_checker` стартуют после `web`
- [ ] Hot-reload работает в dev override
- [ ] `.env.example` в репо, без реальных секретов
- [ ] `Config/.env` удалён из репо (проверь `git log -- Config/.env`; если был в истории — см. git-workflow.md раздел «Секрет в истории»)

---

## Что НЕ делать

- **НЕ пиши** production-оптимизированный compose с nginx-фронтом — это задача Фазы 5
- **НЕ ставь** `build: .` для `db` / `redis` — это official images
- **НЕ клади** креды в compose напрямую, только через `${VAR}`

---

## Вопросы

- [ ] Есть ли уже `pgdata` на проде, который мигрируем? Если да — нужна отдельная задача на экспорт и импорт.
