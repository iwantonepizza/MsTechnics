#!/usr/bin/env bash
# backup-db.sh — снять операционный backup PostgreSQL с ротацией и optional off-host sync.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  DATABASE_URL=postgres://... ./scripts/backup-db.sh
  # или через DATABASE_* из Config/.env

Optional env:
  BACKUP_DIR=/var/backups/mstechnics
  BACKUP_BASENAME=mstechnics
  BACKUP_RETENTION_COUNT=14
  BACKUP_REMOTE_TARGET=backup-vps:/var/backups/mstechnics/
  BACKUP_ENCRYPTION_PASSPHRASE=...
  BACKUP_ALLOW_PLAINTEXT_REMOTE=1
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

log() {
  printf '[backup-db] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

BACKUP_DIR="${BACKUP_DIR:-/var/backups/mstechnics}"
BACKUP_BASENAME="${BACKUP_BASENAME:-mstechnics}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
BACKUP_REMOTE_TARGET="${BACKUP_REMOTE_TARGET:-}"
BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE:-}"
BACKUP_ALLOW_PLAINTEXT_REMOTE="${BACKUP_ALLOW_PLAINTEXT_REMOTE:-0}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
PLAIN_DUMP_FILE="$BACKUP_DIR/${BACKUP_BASENAME}_${TIMESTAMP}.dump"
FINAL_FILE="$PLAIN_DUMP_FILE"

require_command pg_dump
require_command sha256sum

if [[ -n "$BACKUP_REMOTE_TARGET" ]]; then
  require_command rsync
  if [[ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]] && [[ "$BACKUP_ALLOW_PLAINTEXT_REMOTE" != "1" ]]; then
    printf 'Refusing off-host sync without BACKUP_ENCRYPTION_PASSPHRASE or BACKUP_ALLOW_PLAINTEXT_REMOTE=1\n' >&2
    exit 1
  fi
fi

if [[ -n "$BACKUP_ENCRYPTION_PASSPHRASE" ]]; then
  require_command openssl
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
umask 077

run_pg_dump() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    pg_dump --format=custom --no-owner --no-privileges --file="$PLAIN_DUMP_FILE" "$DATABASE_URL"
    return
  fi

  if [[ -n "${PROD_DATABASE_URL:-}" ]]; then
    pg_dump --format=custom --no-owner --no-privileges --file="$PLAIN_DUMP_FILE" "$PROD_DATABASE_URL"
    return
  fi

  : "${DATABASE_NAME:?DATABASE_NAME is required when DATABASE_URL is not set}"
  : "${DATABASE_USER:?DATABASE_USER is required when DATABASE_URL is not set}"
  : "${DATABASE_PASSWORD:?DATABASE_PASSWORD is required when DATABASE_URL is not set}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is not set}"
  : "${DATABASE_PORT:?DATABASE_PORT is required when DATABASE_URL is not set}"

  PGPASSWORD="$DATABASE_PASSWORD" \
    pg_dump \
      --format=custom \
      --no-owner \
      --no-privileges \
      --file="$PLAIN_DUMP_FILE" \
      -h "$DATABASE_HOST" \
      -p "$DATABASE_PORT" \
      -U "$DATABASE_USER" \
      "$DATABASE_NAME"
}

rotate_backups() {
  shopt -s nullglob
  local files=(
    "$BACKUP_DIR"/"${BACKUP_BASENAME}"_*.dump
    "$BACKUP_DIR"/"${BACKUP_BASENAME}"_*.dump.enc
  )
  local sorted=()
  local old_file

  if (( ${#files[@]} <= BACKUP_RETENTION_COUNT )); then
    return
  fi

  mapfile -t sorted < <(ls -1t "${files[@]}")
  for old_file in "${sorted[@]:BACKUP_RETENTION_COUNT}"; do
    rm -f -- "$old_file" "$old_file.sha256"
  done
}

log "Creating PostgreSQL backup in $BACKUP_DIR"
run_pg_dump

if [[ -n "$BACKUP_ENCRYPTION_PASSPHRASE" ]]; then
  FINAL_FILE="${PLAIN_DUMP_FILE}.enc"
  log "Encrypting backup artifact"
  openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in "$PLAIN_DUMP_FILE" \
    -out "$FINAL_FILE" \
    -pass env:BACKUP_ENCRYPTION_PASSPHRASE
  rm -f -- "$PLAIN_DUMP_FILE"
fi

sha256sum "$FINAL_FILE" > "${FINAL_FILE}.sha256"

if [[ -n "$BACKUP_REMOTE_TARGET" ]]; then
  log "Syncing backup off-host to $BACKUP_REMOTE_TARGET"
  rsync -az --chmod=F600,D700 "$FINAL_FILE" "${FINAL_FILE}.sha256" "$BACKUP_REMOTE_TARGET"
fi

rotate_backups

log "Backup completed: $FINAL_FILE"
log "Checksum written: ${FINAL_FILE}.sha256"
