#!/usr/bin/env bash
# bootstrap_dev.sh — full dev bootstrap from a production dump copy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP_FILE="${1:?Specify dump path: $0 <path/to/mstechnics.dump>}"

echo "=== 1/3 Restore dump + run migrations ==="
"$SCRIPT_DIR/restore_to_dev.sh" "$DUMP_FILE"

echo "=== 2/3 Scrub PII ==="
if [[ -n "${DATABASE_URL:-}" ]]; then
  psql "$DATABASE_URL" -f "$SCRIPT_DIR/scrub_pii.sql"
else
  : "${DATABASE_NAME:?DATABASE_NAME is required when DATABASE_URL is not set}"
  : "${DATABASE_USER:?DATABASE_USER is required when DATABASE_URL is not set}"
  : "${DATABASE_PASSWORD:?DATABASE_PASSWORD is required when DATABASE_URL is not set}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is not set}"
  : "${DATABASE_PORT:?DATABASE_PORT is required when DATABASE_URL is not set}"

  PGPASSWORD="$DATABASE_PASSWORD" \
    psql \
      -h "$DATABASE_HOST" \
      -p "$DATABASE_PORT" \
      -U "$DATABASE_USER" \
      "$DATABASE_NAME" \
      -f "$SCRIPT_DIR/scrub_pii.sql"
fi

echo "=== 3/3 Re-run migrate after scrub ==="
cd "$SCRIPT_DIR/.."
pip install -e ".[dev,test]"
python manage.py migrate --noinput

echo ""
echo "Dev DB is ready. Login password after scrub: devpassword"
