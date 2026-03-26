#!/usr/bin/env bash
# PostgreSQL PITR Backup Script
# Supports base backups and WAL archiving to S3/MinIO.
#
# Usage:
#   ./pg_backup.sh --full          # Take a full base backup
#   ./pg_backup.sh --wal-archive   # Archive a single WAL file (called by archive_command)
#
# Environment variables:
#   PGHOST           PostgreSQL host (default: localhost)
#   PGPORT           PostgreSQL port (default: 5432)
#   PGUSER           PostgreSQL superuser (default: postgres)
#   PGPASSWORD       PostgreSQL password
#   BACKUP_BUCKET    S3/MinIO bucket name (required)
#   BACKUP_PREFIX    Key prefix inside the bucket (default: ddos-platform/backups)
#   WAL_PATH         Path to WAL file (used with --wal-archive, passed by PostgreSQL)
#   WAL_NAME         WAL file name (used with --wal-archive, passed by PostgreSQL)
#   S3_ENDPOINT_URL  Custom S3 endpoint for MinIO (optional)

set -euo pipefail

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGUSER:=postgres}"
: "${BACKUP_PREFIX:=ddos-platform/backups}"

if [[ -z "${BACKUP_BUCKET:-}" ]]; then
    echo "ERROR: BACKUP_BUCKET environment variable is required" >&2
    exit 1
fi

S3_BASE="s3://${BACKUP_BUCKET}/${BACKUP_PREFIX}"

# Build optional aws endpoint args
AWS_EXTRA_ARGS=()
if [[ -n "${S3_ENDPOINT_URL:-}" ]]; then
    AWS_EXTRA_ARGS+=("--endpoint-url" "${S3_ENDPOINT_URL}")
fi

do_full_backup() {
    local ts
    ts="$(date -u '+%Y%m%dT%H%M%SZ')"
    local local_dir="/tmp/pg_basebackup_${ts}"
    local archive_name="basebackup_${ts}.tar.gz"
    local s3_key="${S3_BASE}/base/${archive_name}"

    log "Starting full base backup → ${s3_key}"

    pg_basebackup \
        --host="${PGHOST}" \
        --port="${PGPORT}" \
        --username="${PGUSER}" \
        --format=tar \
        --gzip \
        --wal-method=stream \
        --checkpoint=fast \
        --pgdata="${local_dir}"

    log "Base backup complete; uploading to S3..."
    aws s3 cp "${local_dir}/base.tar.gz" "${s3_key}" "${AWS_EXTRA_ARGS[@]}"
    rm -rf "${local_dir}"
    log "Full backup finished: ${s3_key}"
}

do_wal_archive() {
    if [[ -z "${WAL_PATH:-}" || -z "${WAL_NAME:-}" ]]; then
        echo "ERROR: WAL_PATH and WAL_NAME must be set for --wal-archive" >&2
        exit 1
    fi
    local s3_key="${S3_BASE}/wal/${WAL_NAME}"
    log "Archiving WAL segment ${WAL_NAME} → ${s3_key}"
    aws s3 cp "${WAL_PATH}" "${s3_key}" "${AWS_EXTRA_ARGS[@]}"
    log "WAL archive complete: ${s3_key}"
}

case "${1:-}" in
    --full)
        do_full_backup
        ;;
    --wal-archive)
        do_wal_archive
        ;;
    *)
        echo "Usage: $0 {--full|--wal-archive}" >&2
        echo "  --full         Take a full pg_basebackup and upload to S3" >&2
        echo "  --wal-archive  Archive a WAL segment (set WAL_PATH and WAL_NAME)" >&2
        exit 1
        ;;
esac
