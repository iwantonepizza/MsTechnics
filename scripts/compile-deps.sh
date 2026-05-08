#!/usr/bin/env bash
# Регенерирует requirements.lock из pyproject.toml
# Требует: pip install uv
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Компилируем зависимости..."
uv pip compile pyproject.toml --output-file requirements.lock
echo "Готово. Закоммить requirements.lock."
