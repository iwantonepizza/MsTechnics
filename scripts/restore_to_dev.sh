#!/usr/bin/env bash
# restore_to_dev.sh — restore a PostgreSQL dump into dev/staging and run migrations.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  DATABASE_URL=postgres://... ./scripts/restore_to_dev.sh /path/to/mstechnics.dump
  DATABASE_NAME=... DATABASE_USER=... DATABASE_PASSWORD=... DATABASE_HOST=... DATABASE_PORT=... \
    ./scripts/restore_to_dev.sh /path/to/mstechnics.dump

Supports:
  *.dump -> pg_restore custom format

Optional env:
  MANAGE_PYTHON_BIN=/path/to/python
  SHOWMIGRATIONS_TAIL=60
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DUMP_FILE="${1:?Specify dump path: $0 <path/to/mstechnics.dump>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SHOWMIGRATIONS_TAIL="${SHOWMIGRATIONS_TAIL:-60}"

log() {
  printf '[restore_to_dev] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

select_python() {
  if [[ -n "${MANAGE_PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$MANAGE_PYTHON_BIN"
    return
  fi
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  printf 'Missing Python interpreter for manage.py\n' >&2
  exit 1
}

parse_database_url() {
  local python_bin="$1"
  mapfile -t parsed_database_url < <(
    "$python_bin" - "$DATABASE_URL" <<'PY'
from urllib.parse import unquote, urlparse
import sys

url = urlparse(sys.argv[1])
if url.scheme not in {"postgres", "postgresql"}:
    raise SystemExit(f"Unsupported DATABASE_URL scheme: {url.scheme!r}")
if not url.path or not url.path.lstrip("/"):
    raise SystemExit("DATABASE_URL must include the database name")
if not url.username:
    raise SystemExit("DATABASE_URL must include the database user")
if not url.hostname:
    raise SystemExit("DATABASE_URL must include the database host")

print(unquote(url.path.lstrip("/")))
print(unquote(url.username))
print(unquote(url.password or ""))
print(url.hostname)
print(url.port or 5432)
PY
  )

  DATABASE_NAME="${DATABASE_NAME:-${parsed_database_url[0]}}"
  DATABASE_USER="${DATABASE_USER:-${parsed_database_url[1]}}"
  DATABASE_PASSWORD="${DATABASE_PASSWORD:-${parsed_database_url[2]}}"
  DATABASE_HOST="${DATABASE_HOST:-${parsed_database_url[3]}}"
  DATABASE_PORT="${DATABASE_PORT:-${parsed_database_url[4]}}"
}

resolve_database_env() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    parse_database_url "$PYTHON_BIN"
  fi

  : "${DATABASE_NAME:?DATABASE_NAME is required when DATABASE_URL is not set}"
  : "${DATABASE_USER:?DATABASE_USER is required when DATABASE_URL is not set}"
  : "${DATABASE_PASSWORD:?DATABASE_PASSWORD is required when DATABASE_URL is not set}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is not set}"
  : "${DATABASE_PORT:?DATABASE_PORT is required when DATABASE_URL is not set}"

  export DATABASE_NAME DATABASE_USER DATABASE_PASSWORD DATABASE_HOST DATABASE_PORT
}

database_target_for_guard() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    printf '%s' "$DATABASE_URL"
    return
  fi
  printf '%s:%s/%s' "$DATABASE_HOST" "$DATABASE_PORT" "$DATABASE_NAME"
}

guard_target() {
  local target
  target="$(database_target_for_guard)"
  if [[ "$target" == *"mstechnics.ru"* ]] || [[ "$target" == *"185.251"* ]]; then
    printf 'Refusing restore to a target that looks like production: %s\n' "$target" >&2
    exit 1
  fi
}

run_psql() {
  PGPASSWORD="$DATABASE_PASSWORD" \
    psql \
      -v ON_ERROR_STOP=1 \
      -h "$DATABASE_HOST" \
      -p "$DATABASE_PORT" \
      -U "$DATABASE_USER" \
      "$DATABASE_NAME" \
      "$@"
}

run_pg_restore() {
  PGPASSWORD="$DATABASE_PASSWORD" \
    pg_restore \
      --clean \
      --if-exists \
      --no-owner \
      --no-privileges \
      -h "$DATABASE_HOST" \
      -p "$DATABASE_PORT" \
      -U "$DATABASE_USER" \
      -d "$DATABASE_NAME" \
      "$1"
}

if [[ ! -f "$DUMP_FILE" ]]; then
  printf 'Dump file not found: %s\n' "$DUMP_FILE" >&2
  exit 1
fi

case "$DUMP_FILE" in
  *.dump) ;;
  *)
    printf 'Unsupported dump format: %s (expected *.dump custom-format backup)\n' "$DUMP_FILE" >&2
    exit 1
    ;;
esac

require_command psql
require_command pg_restore
PYTHON_BIN="$(select_python)"
resolve_database_env
guard_target

cd "$REPO_ROOT"

log "Resetting public schema"
run_psql -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

log "Restoring dump from $DUMP_FILE"
run_pg_restore "$DUMP_FILE"

log "Current migration matrix"
"$PYTHON_BIN" manage.py showmigrations | tail -n "$SHOWMIGRATIONS_TAIL"

log "Applying migrations"
"$PYTHON_BIN" manage.py migrate --noinput

log "Running Django system checks"
"$PYTHON_BIN" manage.py check

log "Restore and migrate completed"
