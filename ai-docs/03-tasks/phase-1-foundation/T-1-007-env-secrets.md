# T-1-007. django-environ, .env.example, отзыв утекших секретов

> **Тип:** security / infra
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Вывести все секреты из репо, вычистить историю git, отозвать утекшие токены.

---

## Контекст

В репо обнаружены утечки (см. `ai-docs/01-current-state/security-issues.md`):

1. **SEC-001 (critical):** `Config/client_secret.json` содержит реальный Google OAuth client secret `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`. Он **уже скомпрометирован**, отозвать немедленно.
2. **SEC-002:** `SECRET_KEY` без фоллбека — если env не прочитался, Django падает в рантайме (не в старте). Fail-fast нужен.
3. **SEC-003:** `DEBUG = os.environ.get('DEBUG')` — строка `"False"` truthy, прод может работать в debug-mode.
4. **SEC-004:** `ALLOWED_HOSTS` захардкожен с IP `185.251.88.121`.

---

## Зависимости

- **Блокируется:** T-1-001 (django-environ в deps)

---

## Что нужно сделать

### Часть 1: Отзыв утекших секретов (сделать ПЕРВЫМ)

1. Зайти в Google Cloud Console → проект `ms-contol-cloud` → Credentials.
2. Удалить OAuth client `320806079726-dck3103ahc67t845tlfvieffvq8ogm0u`.
3. Создать новый OAuth client. Скачать JSON, сохранить в **локальный** `.env` (не в репо!).
4. Записать в отчёт: «Отозван SECRET: GOCSPX-tKt..., создан новый: [хэш нового]». Хэш, не сам секрет.

**Параллельно:** проверить в `git log --all`, когда этот файл появился. Если больше 30 дней — сервис **мог** быть использован для спама. Проверить в Google Cloud Console квоты и логи использования. Если видно аномалии — уведомить владельца.

### Часть 2: Вычистить из истории git

```bash
# Установить git-filter-repo (безопаснее filter-branch)
pip install git-filter-repo

# Бэкап!
git clone . /tmp/mstechnics-backup

# Удалить файл из истории
git filter-repo --invert-paths --path Config/client_secret.json --path Config/token.pickle

# Force-push (ОБЯЗАТЕЛЬНО предупредив команду заранее)
git push --force --all
git push --force --tags
```

Все работающие клоны репо должны сделать свежий `git clone`. Перечислить в отчёте кого предупредили.

### Часть 3: django-environ и settings

1. Создать структуру `config/settings/`:
   ```
   config/
   ├── __init__.py
   ├── asgi.py
   ├── wsgi.py
   ├── urls.py
   └── settings/
       ├── __init__.py
       ├── base.py
       ├── dev.py
       ├── prod.py
       └── test.py
   ```

   Переименовать `MsServiceControl/` → `config/`. Обновить все импорты:
   ```bash
   grep -rn "MsServiceControl" --include="*.py" . 
   # заменить на config
   ```

2. `config/settings/base.py`:
   ```python
   import environ
   from pathlib import Path

   BASE_DIR = Path(__file__).resolve().parent.parent.parent
   env = environ.Env()
   environ.Env.read_env(BASE_DIR / ".env")

   SECRET_KEY = env("DJANGO_SECRET_KEY")  # без default — fail if missing
   DEBUG = env.bool("DJANGO_DEBUG", default=False)  # строгое приведение
   ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

   DATABASES = {
       "default": env.db("DATABASE_URL", default="postgres://localhost/mstechnics"),
   }

   REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
   CACHES = {
       "default": {
           "BACKEND": "django.core.cache.backends.redis.RedisCache",
           "LOCATION": REDIS_URL,
       }
   }

   TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default=None)
   TELEGRAM_PROXY_URL = env("TELEGRAM_PROXY_URL", default=None)

   GMAIL_USER = env("GMAIL_USER", default=None)
   GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD", default=None)

   # ... остальное из существующего settings.py без изменений
   ```

3. `config/settings/dev.py`:
   ```python
   from .base import *  # noqa

   DEBUG = True
   ALLOWED_HOSTS = ["*"]
   ```

4. `config/settings/prod.py`:
   ```python
   from .base import *  # noqa

   DEBUG = False
   if not env.list("DJANGO_ALLOWED_HOSTS"):
       raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in prod")

   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   X_FRAME_OPTIONS = "DENY"
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   ```

5. `config/settings/test.py`:
   ```python
   from .base import *  # noqa

   DEBUG = False
   DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///:memory:")}
   EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
   PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # быстро в тестах
   ```

6. Обновить `manage.py`, `config/wsgi.py`, `config/asgi.py`:
   ```python
   os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
   ```

7. Убрать `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` из `mail/views.py` — перенести в `config/settings/dev.py` (SEC-006):
   ```python
   # dev.py, только для локальной разработки!
   import os
   os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
   ```

8. Удалить `Config/` директорию после миграции.

### Часть 4: .gitignore и .env.example

1. `.gitignore` убедиться что есть:
   ```
   .env
   .env.*
   !.env.example
   **/token.pickle
   **/client_secret.json
   ```

2. `.env.example` — полный список переменных (см. T-1-002 — уже создан там).

---

## Критерии приёмки

- [ ] Google OAuth secret отозван в Google Cloud Console (скриншот / запись в отчёт)
- [ ] `Config/client_secret.json` удалён из текущего коммита И из истории
- [ ] `git log --all -- Config/client_secret.json` — пусто
- [ ] `git log --all -p | grep "GOCSPX-"` — пусто
- [ ] `django-environ` в deps, читает `.env`
- [ ] `DJANGO_SECRET_KEY` из env, без default — fail-fast если не задан
- [ ] `DEBUG = env.bool(...)` — "False" корректно даёт False
- [ ] `ALLOWED_HOSTS` из env, в prod — обязательно не пустой
- [ ] settings разделены на dev / prod / test
- [ ] MsServiceControl переименован в config
- [ ] `OAUTHLIB_INSECURE_TRANSPORT` только в dev-settings
- [ ] `.env.example` актуален
- [ ] Прод переразвёрнут с новым `.env`, система работает

---

## Что НЕ делать

- **НЕ коммить** реальный `.env`
- **НЕ вкладывай** реальные креды в `.env.example`
- **НЕ меняй** домены ALLOWED_HOSTS пока не согласовал с владельцем
- **НЕ удаляй** из истории что-то ещё (не .env), на эту задачу только secrets
