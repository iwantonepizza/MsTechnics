#!/usr/bin/env bash
# dump_prod.sh — снять дамп с прод-БД
# Использование: PROD_DATABASE_URL="postgres://user:pass@host:5432/db" ./scripts/dump_prod.sh
set -euo pipefail

: "${PROD_DATABASE_URL:?Нужна переменная PROD_DATABASE_URL=postgres://user:pass@host/db}"

DUMP_DIR="${DUMP_DIR:-./dumps}"
mkdir -p "$DUMP_DIR"
TS="$(date -u +%Y%m%d-%H%M%S)"
OUT="$DUMP_DIR/prod-$TS.sql.gz"

echo "Снимаем дамп..."
pg_dump --no-owner --no-acl --format=plain "$PROD_DATABASE_URL" \
  | gzip -9 > "$OUT"

echo "Готово: $OUT"
echo "Размер: $(du -h "$OUT" | cut -f1)"
