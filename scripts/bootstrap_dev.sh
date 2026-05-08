#!/usr/bin/env bash
# bootstrap_dev.sh — полный bootstrap dev-окружения из прод-дампа
# Использование: DATABASE_URL="postgres://..." ./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP_FILE="${1:?Укажи файл дампа: $0 <dump.sql.gz>}"

echo "=== 1/3 Восстанавливаем дамп ==="
"$SCRIPT_DIR/restore_to_dev.sh" "$DUMP_FILE"

echo "=== 2/3 Очищаем PII ==="
psql "$DATABASE_URL" -f "$SCRIPT_DIR/scrub_pii.sql"

echo "=== 3/3 Применяем миграции ==="
cd "$SCRIPT_DIR/.."
pip install -e ".[dev,test]"
python manage.py migrate --noinput

echo ""
echo "✅ Dev DB готова. Для входа: логин из admin, пароль: devpassword"
