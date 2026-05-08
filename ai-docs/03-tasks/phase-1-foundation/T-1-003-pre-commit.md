# T-1-003. Pre-commit hooks: ruff + black + mypy + проверка секретов

> **Тип:** infra
> **Приоритет:** P1
> **Оценка:** 1.5 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Кодер не должен запушить в main невалидный или небезопасный код. Pre-commit ловит 90% проблем до коммита — быстрее чем CI.

---

## Зависимости

- **Блокируется:** T-1-001 (pyproject.toml с конфигом ruff/black/mypy)

---

## Что нужно сделать

1. Создать `.pre-commit-config.yaml`:
   ```yaml
   default_language_version:
     python: python3.12

   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.6.0
       hooks:
         - id: trailing-whitespace
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-json
         - id: check-added-large-files
           args: ["--maxkb=500"]
         - id: check-merge-conflict
         - id: detect-private-key
         - id: debug-statements

     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.5.0
       hooks:
         - id: ruff
           args: [--fix, --exit-non-zero-on-fix]
         - id: ruff-format

     - repo: https://github.com/psf/black
       rev: 24.4.2
       hooks:
         - id: black
           language_version: python3.12

     - repo: https://github.com/pre-commit/mirrors-mypy
       rev: v1.10.0
       hooks:
         - id: mypy
           additional_dependencies:
             - django-stubs[compatible-mypy]
             - djangorestframework-stubs
           args: [--config-file=pyproject.toml]
           exclude: "(^migrations/|^tests/)"

     - repo: https://github.com/gitleaks/gitleaks
       rev: v8.18.4
       hooks:
         - id: gitleaks

     - repo: https://github.com/Riverside-Healthcare/djLint
       rev: v1.34.1
       hooks:
         - id: djlint-django
           files: \.(html)$
   ```

2. Добавить `.gitleaks.toml` в корень:
   ```toml
   [allowlist]
   paths = [
       "ai-docs/",  # там могут быть примеры фейковых токенов
       ".*\\.example$",
   ]
   ```

3. Установить и активировать:
   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit install --hook-type commit-msg  # для commitlint, см. T-1-005
   ```

4. Прогнать по всему репо один раз:
   ```bash
   pre-commit run --all-files
   ```
   Это сгенерирует кучу правок. Закоммить их одним коммитом `chore(style): apply pre-commit formatters to existing code`.

5. Задокументировать в README раздел «Contributing»:
   ```markdown
   ## Контрибуция
   ```bash
   pre-commit install
   ```
   ```

---

## Критерии приёмки

- [ ] `.pre-commit-config.yaml` в репо
- [ ] `pre-commit run --all-files` проходит (после одноразовой нормализации)
- [ ] При попытке закоммить что-то с `print(` / трейлинг-вайтспейсом / секретом — хуки блокируют
- [ ] В README добавлен раздел как устанавливать
- [ ] CI позже будет гонять `pre-commit run --all-files --show-diff-on-failure` (отдельной задачей T-1-005)

---

## Что НЕ делать

- **НЕ отключай mypy-hook** потому что «много ошибок». Эти ошибки — задачи. Либо фиксим в рамках этой задачи, либо добавляем `# type: ignore[code]` с комментарием-tracker-ID.
- **НЕ добавляй** `--no-verify` в командах в README. Если pre-commit блокирует — это правильно.

---

## Известные сложности

- `mypy` может сыпать на существующем коде сотнями ошибок. Подход: в этой задаче — **НЕ фикси все**, добавь `pyproject.toml` ограничение:
  ```toml
  [[tool.mypy.overrides]]
  module = ["mail.*", "control.*", "monitoring.*", "service.*", "zip.*", "departure.*"]
  ignore_errors = true
  ```
  И задачу на исправление модулей — по одному на фазу 2.
- `djlint-django` может ругаться на ручной HTML в шаблонах — настрой `.djlintrc`:
  ```json
  {
    "profile": "django",
    "ignore": "H006,H013,H030,H031",
    "max_line_length": 120
  }
  ```
