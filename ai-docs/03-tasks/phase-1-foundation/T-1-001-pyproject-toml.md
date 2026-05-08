# T-1-001. Перевод зависимостей в pyproject.toml + lock-файл

> **Тип:** infra
> **Приоритет:** P0
> **Оценка:** 1.5 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Заменить рукописный `requirements.txt` (в UTF-16, без версий части зависимостей) на `pyproject.toml` + lock-файл. Это фундамент: без воспроизводимой среды дальнейшие задачи не имеют смысла.

---

## Контекст

Сейчас в корне проекта:
- `requirements.txt` — **в кодировке UTF-16**, нечитаемо в обычных редакторах, не генерит `pip freeze`. Проверить: `file requirements.txt`.
- Ряд зависимостей без pinned-версии (`Django` вместо `Django==5.1.4`).
- Нет разделения prod / dev / test.

---

## Зависимости

- **Блокируется:** нет
- **Блокирует:** все остальные задачи фазы 1 (линтеры, тесты)

---

## Что нужно сделать

1. Прочитать существующий `requirements.txt` (учти UTF-16):
   ```bash
   iconv -f UTF-16 -t UTF-8 requirements.txt > /tmp/reqs.txt
   ```
   Проверить что получилось читаемо.

2. Создать `pyproject.toml` в корне:
   ```toml
   [build-system]
   requires = ["setuptools>=65", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "mstechnics"
   version = "0.1.0"
   requires-python = ">=3.12,<3.13"
   dependencies = [
       "django>=5.1,<5.2",
       "djangorestframework>=3.15,<3.16",
       "djangorestframework-simplejwt>=5.3",
       "django-environ>=0.11",
       "django-cors-headers>=4.3",
       "django-colorfield>=0.11",
       "psycopg[binary]>=3.2",
       "redis>=5.0",
       "structlog>=24.1",
       "python-telegram-bot>=21.0",
       "httpx>=0.27",
       "google-auth>=2.30",
       "google-auth-oauthlib>=1.2",
       "google-api-python-client>=2.130",
       "gunicorn>=22.0",
       "pillow>=10.3",
       "python-slugify>=8.0",
   ]

   [project.optional-dependencies]
   dev = [
       "ruff>=0.5",
       "black>=24.4",
       "mypy>=1.10",
       "django-stubs[compatible-mypy]>=5.0",
       "djangorestframework-stubs>=3.15",
       "pre-commit>=3.7",
   ]
   test = [
       "pytest>=8.2",
       "pytest-django>=4.8",
       "pytest-cov>=5.0",
       "factory-boy>=3.3",
       "freezegun>=1.5",
       "httpx>=0.27",
   ]

   [tool.ruff]
   target-version = "py312"
   line-length = 100

   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "B", "C4", "DJ", "N", "UP", "RET", "ARG", "SIM", "RUF"]
   ignore = ["E501"]  # black handles line length

   [tool.black]
   line-length = 100
   target-version = ["py312"]

   [tool.mypy]
   python_version = "3.12"
   plugins = ["mypy_django_plugin.main", "mypy_drf_plugin.main"]
   strict = true
   disallow_untyped_defs = true
   exclude = ["migrations/", "build/"]

   [tool.django-stubs]
   django_settings_module = "config.settings.dev"

   [tool.pytest.ini_options]
   DJANGO_SETTINGS_MODULE = "config.settings.test"
   python_files = "test_*.py tests.py"
   addopts = "--cov=apps --cov=shared --cov-report=term-missing --cov-fail-under=70"
   ```

3. Сгенерировать lock: `pip install uv` → `uv pip compile pyproject.toml -o requirements.lock`.

4. Добавить в `.gitignore`: `.venv/`, `__pycache__/`, `*.pyc` (если нет).

5. Удалить старый `requirements.txt`. Обновить `Dockerfile`:
   ```dockerfile
   FROM python:3.12-slim
   ...
   COPY pyproject.toml requirements.lock ./
   RUN pip install --no-cache-dir -r requirements.lock
   ...
   ```

6. Обновить README: инструкция как поднять:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev,test]"
   ```

---

## Критерии приёмки

- [ ] `pyproject.toml` создан и валиден (`python -m build --check` OK)
- [ ] `requirements.lock` сгенерирован, все версии pinned
- [ ] `Dockerfile` обновлён, образ собирается
- [ ] `pip install -e ".[dev,test]"` работает на чистом venv
- [ ] `ruff check .` — проходит (возможны warnings, это пофиксим в T-1-003)
- [ ] Удалён `requirements.txt`
- [ ] Обновлён README

---

## Что НЕ делать

- **НЕ добавляй Celery** — его в проекте не будет (см. AGENTS.md)
- **НЕ добавляй django-fsm** — FSM пишем сами
- **НЕ переделывай структуру settings.py** в этой задаче — это T-1-007

---

## Вопросы для архитектора

- [ ]
