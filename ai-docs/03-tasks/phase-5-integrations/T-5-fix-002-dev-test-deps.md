# T-5-fix-002. dev/test зависимости в .venv + UTF-8 requirements.txt

> **Тип задачи:** infra
> **Приоритет:** P1 (нужно до T-5-fix-001 или вместе с ним, чтобы прогнать pytest и ruff)
> **Оценка:** 1 час
> **Фаза:** 5 (hotfix перед deploy)
> **Статус:** done
> **Исполнитель:** GPT-5 / Codex

---

## Цель

Привести dev-окружение в состояние, когда `pytest`, `ruff`, `black`, `mypy`, `factory-boy`, `freezegun` доступны из `.venv` и реально запускаются. Без этого регрессии не ловятся, отчёты T-5-* не могут указать backend coverage, pre-commit hooks висят молча. Параллельно — починить `requirements.txt`, который сейчас в UTF-16 BOM (нечитаем для `pip install -r` на linux-host).

---

## Контекст

В `pyproject.toml` зависимости разнесены по группам:

```toml
[project]
dependencies = [...]            # минимум для прод-сервера

[project.optional-dependencies]
dev = ["ruff>=0.5", "black>=24.4", "mypy>=1.10", "django-stubs[...]", ...]
test = ["pytest>=8.2", "pytest-django>=4.8", "pytest-cov>=5.0", "factory-boy>=3.3", "freezegun>=1.5", ...]
```

В каждом T-5-* отчёте кодер пишет «Полный pytest не запускался, в проекте есть известные legacy system check blockers» и «ruff не установлен». Первое чинит T-5-fix-001. Второе чинит **установка `[dev,test]` extras** в `.venv`.

Параллельно: `requirements.txt` в репо имеет **UTF-16 BOM** (видно по тому, как Read рендерит null-byte между каждым символом). На macOS/Windows pip'у это иногда сходит с рук, на linux-host (`pip install -r requirements.txt` в Dockerfile или Gunicorn деплое) → ParseError.

---

## Зависимости

- **Блокируется:** ничем.
- **Блокирует:** `pytest`-этап в T-5-fix-001 (если эту задачу делать первой, удобно).

Эти задачи можно делать в любом порядке, но **PR на T-5-fix-002 ушёл первым** упрощает T-5-fix-001 (там сразу прогоняется pytest).

---

## Что нужно сделать

### Шаг 1. Установить extras в `.venv`

```bash
# Активировать venv
.venv/Scripts/activate         # Windows / git-bash
# или
source .venv/bin/activate      # Linux/Mac (если когда-нибудь)

# Установить dev + test extras (в режиме editable, чтобы код apps был автодоступен)
pip install -e ".[dev,test]"

# Проверить, что появилось
pip list | grep -Ei "pytest|ruff|black|mypy|factory|freezegun|django-stubs"
```

Ожидание: `pytest 8.x`, `pytest-django 4.x`, `pytest-cov 5.x`, `factory-boy 3.3+`, `freezegun 1.5+`, `ruff 0.5+`, `black 24.4+`, `mypy 1.10+`, `django-stubs 5.x`, `djangorestframework-stubs 3.15+`.

### Шаг 2. Перезаписать `requirements.txt` в UTF-8

Сейчас файл в UTF-16 BOM. Перезаписать так, чтобы:
- кодировка была UTF-8 без BOM,
- содержимое соответствовало `requirements.lock` (чтобы prod-Dockerfile получил тот же набор),
- в нём остались **только runtime** зависимости (без `[dev,test]` extras — они только для разработки).

Можно сгенерировать через pip-compile или вручную сделать UTF-8 копию `requirements.lock`. Цель: `python -c "open('requirements.txt', 'rb').read().decode('utf-8')"` не падает.

После — проверить:

```bash
pip install -r requirements.txt --dry-run    # чисто
file requirements.txt                          # ASCII text / UTF-8 (не UTF-16)
```

### Шаг 3. Прогнать ruff

```bash
ruff check apps/ shared/ Config/
```

- Если 0 ошибок — отлично.
- Если 5-20 ошибок — фиксы в этой же задаче, **только** автоматически фиксируемые: `ruff check --fix` + ручная проверка диффа.
- Если **больше 20 ошибок или нужны крупные правки** — НЕ фикси здесь. Зафиксируй число и категории в отчёте, заведи follow-up задачу `T-5-fix-002-followup-ruff`. Цель этой задачи — иметь работающий ruff, не вылизать кодовую базу.

### Шаг 4. Прогнать pytest (best effort до T-5-fix-001)

```bash
pytest -x --no-cov   # без cov, чтобы не тратить время на coverage пока migration graph не починен
```

**Если падает на `SystemCheckError: legacy duplicate models`** — это ожидаемо, **это закрывает T-5-fix-001**. Зафиксируй в отчёте: «pytest blocked by T-5-fix-001 system check, see report». Не фикси ничего связанного с моделями здесь.

**Если падает по другой причине** (ImportError, missing module и т.д.) — это, наоборот, могла быть проблема dev-deps. Зафиксируй и почини в этой же задаче, **если фикс мелкий**.

### Шаг 5. Обновить `scripts/bootstrap_dev.sh` и Makefile (если есть)

Чтобы в следующий раз новый кодер не наступал на те же грабли:

- В `scripts/bootstrap_dev.sh` (или `Makefile` target `dev-setup`) — после `pip install -r requirements.txt` добавить:

  ```bash
  pip install -e ".[dev,test]"
  ```

- В `ai-docs/04-conventions/code-style.md` (или README.md) — короткая ремарка «Для разработки нужны extras: `pip install -e \".[dev,test]\"`».

### Шаг 6. Проверить, что pre-commit реально что-то делает

```bash
pre-commit run --all-files
```

Если падает на ruff/black/mypy — фикси автогенерируемые правки. Если падает с какой-то странной ошибкой типа «hook not found» — обнови `.pre-commit-config.yaml` под актуальные ruff/black версии.

---

## Критерии приёмки

- [ ] `.venv/Scripts/python -c "import pytest, ruff, factory" && echo ok` — выводит `ok`.
- [ ] `ruff check apps/ shared/ Config/` — exit 0 или количество ошибок ≤ 5 (документированы в отчёте) с follow-up задачей.
- [ ] `pytest --collect-only` — собирает тесты без ImportError (даже если они потом фейлятся на T-5-fix-001).
- [ ] `requirements.txt` — UTF-8 без BOM, читается `pip install -r requirements.txt --dry-run` без ошибок.
- [ ] `scripts/bootstrap_dev.sh` или `Makefile dev-setup` ставит extras.
- [ ] Отчёт в `ai-docs/08-reports/T-5-fix-002.md`.

---

## Что НЕ нужно делать

- **Не апгрейдить версии** существующих runtime-зависимостей (Django, DRF, psycopg, redis) в этой задаче — только установка dev/test и перезапись `requirements.txt` в UTF-8.
- **Не подключать coverage gate** в pytest (cov-fail-under=70). Это будет следующая задача после того, как pytest начнёт реально проходить целиком.
- **Не фиксить migration-related ошибки** в pytest здесь — это T-5-fix-001.
- **Не править `pyproject.toml` секцию `[project.optional-dependencies]`** — она правильная, проблема в том, что её не установили.

---

## Вопросы для архитектора (если есть)

- [ ] Если `pip install -e ".[dev,test]"` тянет несовместимые версии (например, `mypy 1.10` конфликтует с уже установленной 0.971) — обновлять или фиксировать минимум? — Ответ: обновляй до тех, что в `pyproject.toml`. Эти версии уже зафиксированы архитектором.
- [ ] Pre-commit hook падает, но фикс требует изменения 50+ файлов — как быть? — Ответ: оставь как есть, заведи follow-up. Цель этой задачи — работающие инструменты, не вылизанная кодовая база.

---

## Отчёт по выполнению

(Заполняет кодер при переводе в review/done.)

### Что сделано
- `pip install -e ".[dev,test]"` восстановлен: в `pyproject.toml` добавлен корректный `setuptools.find`, editable install больше не падает.
- `requirements.txt` переписан в UTF-8 без BOM по содержимому `requirements.lock`.
- `scripts/bootstrap_dev.sh` и `Makefile` (`dev-setup`) теперь ставят `.[dev,test]` extras перед дальнейшими шагами.
- Для pytest-cov 7 убран сломанный `--cov-omit` из `pyproject.toml`, добавлен `.coveragerc`.
- `pytest --collect-only` теперь поднимает Django и собирает тесты без ImportError.
- В `ai-docs/04-conventions/code-style.md` добавлена ремарка про обязательный `pip install -e ".[dev,test]"`.

### Отклонения от плана
- Пришлось править `pyproject.toml`: исходно extras были описаны, но проект не устанавливался в editable-режиме из-за отсутствия package discovery config.
- `pytest` не просто "best effort": пришлось отдельно чинить конфиг pytest-cov под актуальную версию 7.x, иначе collect падал до старта тестов.
- `ruff`, `black` и `mypy` теперь запускаются, но baseline намного хуже лимита задачи; массовую зачистку не делал, завёл follow-up.

### Что показал ruff/pytest
- `ruff check apps shared Config`: 291 ошибок. Основные категории: import order, unused imports, django-style (`DJ001/DJ012`), ambiguous unicode (`RUF00x`), typing/style warnings.
- `black --check apps shared Config`: 96 файлов требуют форматирования.
- `mypy apps`: 16 ошибок в 12 файлах.
- `pytest --collect-only -q`: 79 тестов собираются.
- Точечный прогон `apps.notifications.tests.test_channels` + `apps.integrations.max.tests.test_webhook`: 9 тестов, всё зелёное.

### Измеренное время
- Оценка: 1 час
- Фактически: ~1.5 часа

### Дальнейшие шаги
- Продолжать `T-5-fix-001`: runtime duplicate-model blocker снят, но migration state drift ещё надо дочистить.
- Отдельной задачей разобрать lint/type baseline: `T-5-fix-002-followup-ruff.md`.
