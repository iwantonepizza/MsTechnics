# T-6-006. Encoding hygiene — UTF-8 без BOM enforcement

> **Тип задачи:** hygiene + infra
> **Приоритет:** P1 (репо потерял `03-tasks/README.md` из-за двойного UTF-8 mojibake — нужна страховка от повторения)
> **Оценка:** 1-2 часа
> **Фаза:** 6 (production)
> **Статус:** review
> **Исполнитель:** GPT-5 Codex

---

## Цель

После T-6-004 (filter-repo + force-push) один из критичных файлов — `ai-docs/03-tasks/README.md` — оказался испорчен: UTF-8 с BOM + двойное кодирование (кириллица закодирована в UTF-8, потом интерпретирована как Windows-1251 и снова в UTF-8). Архитектор восстановил файл вручную, но повторение возможно — нужна автопроверка, которая блокирует подобный коммит.

Архитектор реально видел в `Read`-выводе битую строку вместо `# 03-tasks — задачи для кодеров`. Поправил через `Write` в правильной кодировке.

Аналогичная история была раньше с `requirements.txt` (UTF-16 BOM), которую закрывал T-5-fix-002. Это второй случай — паттерн.

---

## Контекст

**Что произошло.** На Windows есть редакторы / PowerShell pipeline'ы, которые по умолчанию пишут файл в `Windows-1251` (или другую системную локаль) с UTF-8 BOM, или с двойным UTF-8 encoding. Если такой файл потом читать как «UTF-8», получим mojibake — текст внешне правильный, но байты битые.

**Чем чинить навсегда:**

1. **`.editorconfig`** — даёт редакторам единое правило `charset = utf-8`, `end_of_line = lf`. Большинство IDE (VSCode, PyCharm, Sublime, JetBrains) его уважают.
2. **`.gitattributes`** — даёт правило конкретно git'у: `* text=auto eol=lf working-tree-encoding=UTF-8`. Это не магически конвертирует, но помечает текстовые файлы.
3. **Pre-commit hook** — простой Python/bash скрипт, который проверяет, что все `*.md`, `*.py`, `*.txt` в staged changes:
   - не содержат UTF-8 BOM (`\xef\xbb\xbf` в начале),
   - валидно декодируются как UTF-8,
   - не содержат типичные mojibake-паттерны (например, битые строки после перекодировки UTF-8 через cp1251).
4. **CI check** (когда будет CI) — тот же скрипт в Actions.

---

## Зависимости

- **Блокируется:** ничем.
- **Блокирует:** ничего, но **обязательно до закрытия prod cutover** — иначе следующий раунд правок может снова сломать центральный документ.

---

## Что нужно сделать

### Шаг 1. Создать `.editorconfig`

В корне репо:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.md]
trim_trailing_whitespace = false
indent_size = 2

[*.{ts,tsx,js,jsx,json,yaml,yml}]
indent_size = 2

[Makefile]
indent_style = tab
```

### Шаг 2. Создать/обновить `.gitattributes`

В корне репо:

```
* text=auto eol=lf

*.md       text eol=lf
*.py       text eol=lf
*.txt      text eol=lf
*.yaml     text eol=lf
*.yml      text eol=lf
*.json     text eol=lf
*.ts       text eol=lf
*.tsx      text eol=lf
*.sh       text eol=lf

*.ps1      text eol=crlf

*.png      binary
*.jpg      binary
*.pdf      binary
*.dump     binary
```

### Шаг 3. Сканер mojibake — `scripts/check_encoding.py`

```python
#!/usr/bin/env python3
"""Detect UTF-8 BOM, invalid UTF-8, and double-UTF-8/cp1251 mojibake in text files.

Usage:
    python scripts/check_encoding.py [paths...]   # specific paths
    python scripts/check_encoding.py              # all tracked text files

Exit code 0 = чисто, 1 = найдены проблемы.
"""
import re
import subprocess
import sys
from pathlib import Path

UTF8_BOM = b"\xef\xbb\xbf"

# Сигнатуры двойного кодирования. Кириллица в UTF-8 (2 байта на букву) → cp1251 (1 байт)
# → UTF-8 (опять 2 байта). На выходе ловятся характерные mojibake-последовательности.
MOJIBAKE_MARKERS = [
    "Р°", "Р±", "Р²", "Р·", "Р¶", "С‡", "С€", "С‚",  # обычные двойные-encoded кириллические
    "mangled-dash", "mangled-quote", "mangled-ellipsis",                # mangled punctuation
    "mangled-status",                                                   # mangled "Статус"
]

TEXT_SUFFIXES = {".md", ".py", ".txt", ".yaml", ".yml", ".json", ".ts", ".tsx", ".sh", ".ini", ".cfg", ".toml"}


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def check_file(path: Path) -> list[str]:
    problems = []
    try:
        raw = path.read_bytes()
    except OSError as e:
        return [f"unreadable: {e}"]

    if raw.startswith(UTF8_BOM):
        problems.append("starts with UTF-8 BOM (\\xef\\xbb\\xbf)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        problems.append(f"not valid UTF-8: {e}")
        return problems

    for marker in MOJIBAKE_MARKERS:
        if marker in text:
            problems.append(f"mojibake marker found: {marker!r}")
            break  # один маркер достаточно

    return problems


def collect_paths(args: list[str]) -> list[Path]:
    if args:
        return [Path(a) for a in args]
    # tracked files in git
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(p) for p in out.splitlines()]


def main() -> int:
    paths = [p for p in collect_paths(sys.argv[1:]) if is_text(p)]
    total = 0
    for p in paths:
        if not p.exists():
            continue
        problems = check_file(p)
        if problems:
            print(f"FAIL {p}")
            for prob in problems:
                print(f"     - {prob}")
            total += 1
    if total:
        print(f"\n{total} file(s) with encoding issues.")
        return 1
    print(f"OK {len(paths)} text files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Шаг 4. Подключить к `.pre-commit-config.yaml`

Добавить локальный hook:

```yaml
  - repo: local
    hooks:
      - id: check-encoding
        name: Check files for UTF-8 BOM and mojibake
        entry: python scripts/check_encoding.py
        language: system
        pass_filenames: true
        files: '\.(md|py|txt|yaml|yml|json|ts|tsx|sh|ini|cfg|toml)$'
```

После — `pre-commit install` (один раз на каждом dev/server clone'е).

### Шаг 5. Прогнать сейчас по всему репо

```bash
python scripts/check_encoding.py
```

Если найдены ещё файлы (помимо `03-tasks/README.md`, который архитектор уже починил) — починить через перезапись в UTF-8 без BOM. Для `requirements.txt` это уже было сделано в T-5-fix-002, для `03-tasks/README.md` — в этой архитектурной сессии.

### Шаг 6. Документировать в `04-conventions/`

В `ai-docs/04-conventions/code-style.md` (или новый `encoding-conventions.md`):

```markdown
## Кодировка файлов

Все текстовые файлы в репо — **UTF-8 без BOM, LF line endings**.

- `.editorconfig` в корне — глобально для всех редакторов.
- `.gitattributes` — для git.
- Pre-commit hook `check-encoding` блокирует коммит при mojibake.

Windows-разработчикам: убедиться, что PowerShell профиль выставляет
`$OutputEncoding = [System.Text.Encoding]::UTF8` и редактор не сохраняет с BOM.
```

---

## Критерии приёмки

- [x] `.editorconfig` в корне.
- [x] `.gitattributes` в корне.
- [x] `scripts/check_encoding.py` создан, исполняется, exit 0 на чистом репо.
- [x] `.pre-commit-config.yaml` содержит hook `check-encoding`.
- [x] `pre-commit run check-encoding --all-files` зелёный.
- [x] `04-conventions/code-style.md` дополнен или создан `encoding-conventions.md`.
- [x] Отчёт в `08-reports/T-6-006.md`.

---

## Что НЕ нужно делать

- Не переписывать массово всю кодовую базу через `iconv` или подобное «на всякий случай». Сканер должен показать конкретные файлы, чинить точечно.
- Не подключать сложные `chardet`/`charset-normalizer` зависимости — достаточно простого декода в UTF-8 + список mojibake-маркеров.
- Не делать `git filter-repo` для «починки» истории — мы её только что переписали. Mojibake-файлы чинятся новым коммитом.

---

## Отчёт

- Статус переведён в `review`.
- Добавлены `.editorconfig`, `.gitattributes`, `scripts/check_encoding.py` и local pre-commit hook `check-encoding`.
- Сканер подтверждён на всём репо: `OK 624 text files checked.`
- Убраны UTF-8 BOM из 54 markdown task cards в `ai-docs/03-tasks/`.
- Дополнительно восстановлен реально битый файл `ai-docs/03-tasks/phase-5-integrations/T-6-001-production-cutover-runbook.md` из cp1251-mojibake.
- Подробный отчёт: `ai-docs/08-reports/T-6-006.md`.
