#!/usr/bin/env bash
# restore-db.sh — восстановить PostgreSQL из backup-db.sh артефакта.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  DATABASE_URL=postgres://... ./scripts/restore-db.sh /path/to/backup.dump
  DATABASE_URL=postgres://... BACKUP_ENCRYPTION_PASSPHRASE=... ./scripts/restore-db.sh /path/to/backup.dump.enc

Supports:
  *.dump      -> pg_restore custom format
  *.dump.enc  -> openssl decrypt + pg_restore
  *.sql       -> psql
  *.sql.gz    -> gunzip | psql
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

BACKUP_FILE="${1:?Specify backup path: $0 <backup.dump|backup.dump.enc|backup.sql|backup.sql.gz>}"

log() {
  printf '[restore-db] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

if [[ ! -f "$BACKUP_FILE" ]]; then
  printf 'Backup file not found: %s\n' "$BACKUP_FILE" >&2
  exit 1
fi

require_command psql
require_command pg_restore

if [[ "$BACKUP_FILE" == *.enc ]]; then
  require_command openssl
fi
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  require_command sha256sum
fi

run_psql() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    psql "$DATABASE_URL" "$@"
    return
  fi

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
      "$@"
}

run_pg_restore() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$DATABASE_URL" "$1"
    return
  fi

  : "${DATABASE_NAME:?DATABASE_NAME is required when DATABASE_URL is not set}"
  : "${DATABASE_USER:?DATABASE_USER is required when DATABASE_URL is not set}"
  : "${DATABASE_PASSWORD:?DATABASE_PASSWORD is required when DATABASE_URL is not set}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is not set}"
  : "${DATABASE_PORT:?DATABASE_PORT is required when DATABASE_URL is not set}"

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

database_target_for_guard() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    printf '%s' "$DATABASE_URL"
    return
  fi
  printf '%s:%s/%s' "${DATABASE_HOST:-}" "${DATABASE_PORT:-}" "${DATABASE_NAME:-}"
}

guard_target="$(database_target_for_guard)"
if [[ "$guard_target" == *"mstechnics.ru"* ]] || [[ "$guard_target" == *"185.251"* ]]; then
  printf 'Refusing restore to a target that looks like production: %s\n' "$guard_target" >&2
  exit 1
fi

TEMP_FILE=""
cleanup() {
  if [[ -n "$TEMP_FILE" ]] && [[ -f "$TEMP_FILE" ]]; then
    rm -f -- "$TEMP_FILE"
  fi
}
trap cleanup EXIT

if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  log "Verifying checksum"
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

RESTORE_MODE=""
RESTORE_SOURCE="$BACKUP_FILE"

case "$BACKUP_FILE" in
  *.dump.enc)
    : "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE is required for encrypted backup restore}"
    TEMP_FILE="$(mktemp "${TMPDIR:-/tmp}/mstechnics-restore-XXXXXX.dump")"
    log "Decrypting encrypted backup"
    openssl enc -d -aes-256-cbc -pbkdf2 \
      -in "$BACKUP_FILE" \
      -out "$TEMP_FILE" \
      -pass env:BACKUP_ENCRYPTION_PASSPHRASE
    RESTORE_MODE="pg_restore"
    RESTORE_SOURCE="$TEMP_FILE"
    ;;
  *.dump)
    RESTORE_MODE="pg_restore"
    ;;
  *.sql.gz)
    require_command gunzip
    RESTORE_MODE="sql_gzip"
    ;;
  *.sql)
    RESTORE_MODE="sql"
    ;;
  *)
    printf 'Unsupported backup format: %s\n' "$BACKUP_FILE" >&2
    exit 1
    ;;
esac

log "Resetting public schema"
run_psql -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

case "$RESTORE_MODE" in
  pg_restore)
    run_pg_restore "$RESTORE_SOURCE"
    ;;
  sql_gzip)
    gunzip -c "$BACKUP_FILE" | run_psql -v ON_ERROR_STOP=1
    ;;
  sql)
    run_psql -v ON_ERROR_STOP=1 -f "$BACKUP_FILE"
    ;;
esac

log "Restore completed"
