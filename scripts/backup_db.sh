#!/usr/bin/env bash
# scripts/backup_db.sh — PostgreSQL database backup for T1D Companion
#
# Usage:
#   ./scripts/backup_db.sh                    # backup to ./backups/ with timestamp
#   ./scripts/backup_db.sh --output /path     # backup to custom directory
#   ./scripts/backup_db.sh --compress         # gzip the dump
#   ./scripts/backup_db.sh --retain 30        # keep last 30 backups (default: 14)
#
# Environment variables (or set in .env):
#   DATABASE_URL — full PostgreSQL connection URL
#                 e.g. postgresql://user:pass@host:5432/dbname

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────
OUTPUT_DIR="./backups"
COMPRESS=false
RETAIN=14
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# ── Parse args ────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)   OUTPUT_DIR="$2";   shift 2 ;;
    --compress) COMPRESS=true;     shift ;;
    --retain)   RETAIN="$2";       shift 2 ;;
    -h|--help)
      sed -n '2,15p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Load .env if present ──────────────────────────────────────────
if [ -f ".env" ]; then
  set -a; source .env; set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL not set. Set it in .env or environment."
  exit 1
fi

# ── Parse connection URL ──────────────────────────────────────────
# postgresql://user:pass@host:5432/dbname
DB_USER=$(echo "$DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')
DB_PASS=$(echo "$DATABASE_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$DATABASE_URL" | sed -E 's|.*/([^/?]+).*|\1|')

# Handle asyncpg URLs
DB_HOST=$(echo "$DB_HOST" | sed 's/\+asyncpg//')

mkdir -p "$OUTPUT_DIR"

DUMP_FILE="${OUTPUT_DIR}/t1d_backup_${TIMESTAMP}.sql"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  T1D Companion — Database Backup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Host:     ${DB_HOST}:${DB_PORT}"
echo "  Database: ${DB_NAME}"
echo "  User:     ${DB_USER}"
echo "  Output:   ${DUMP_FILE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

export PGPASSWORD="$DB_PASS"

pg_dump \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --dbname="$DB_NAME" \
  --format=plain \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --file="$DUMP_FILE"

if [ "$COMPRESS" = true ]; then
  gzip "$DUMP_FILE"
  DUMP_FILE="${DUMP_FILE}.gz"
  echo "  Compressed: ${DUMP_FILE}"
fi

FILE_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "  Size: ${FILE_SIZE}"
echo "  ✅ Backup complete: ${DUMP_FILE}"

# ── Retention cleanup ─────────────────────────────────────────────
BACKUP_COUNT=$(find "$OUTPUT_DIR" -name "t1d_backup_*.sql*" -type f | wc -l)

if [ "$BACKUP_COUNT" -gt "$RETAIN" ]; then
  REMOVE_COUNT=$((BACKUP_COUNT - RETAIN))
  echo "  Cleaning up ${REMOVE_COUNT} old backup(s) (retaining last ${RETAIN})..."
  find "$OUTPUT_DIR" -name "t1d_backup_*.sql*" -type f -printf '%T@ %p\n' \
    | sort -n \
    | head -n "$REMOVE_COUNT" \
    | cut -d' ' -f2- \
    | xargs rm -f
  echo "  ✅ Retention cleanup complete."
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
