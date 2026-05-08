#!/usr/bin/env bash
# restore_to_dev.sh — залить дамп в dev-БД
# Использование: DATABASE_URL="postgres://..." ./scripts/restore_to_dev.sh dumps/prod-20260424.sql.gz
set -euo pipefail

DUMP_FILE="${1:?Укажи файл дампа: $0 <dump.sql.gz>}"
: "${DATABASE_URL:?Нужна переменная DATABASE_URL=postgres://user:pass@host/db}"

# Безопасность: не даём перезаписать прод
if [[ "$DATABASE_URL" == *"mstechnics.ru"* ]] || [[ "$DATABASE_URL" == *"185.251"* ]]; then
  echo "ОТКАЗАНО: DATABASE_URL выглядит как прод. Останавливаемся." >&2
  exit 1
fi

echo "Очищаем dev-БД..."
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" --quiet

echo "Восстанавливаем из $DUMP_FILE..."
gunzip -c "$DUMP_FILE" | psql "$DATABASE_URL" --quiet

echo "Готово. Схема восстановлена."
