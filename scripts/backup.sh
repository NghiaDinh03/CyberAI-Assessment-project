#!/usr/bin/env bash
# =============================================================================
# CyberAI Assessment Platform — Production Backup Script
# =============================================================================
# Usage:
#   ./scripts/backup.sh
#   ./scripts/backup.sh --dest /backup/path --retention-days 30
#
# Options (positional or named):
#   --dest <path>            Destination directory for backup archives
#                            Default: <project_root>/backups
#   --retention-days <n>     Delete archives older than N days
#                            Default: 30
#
# Exit codes:
#   0  — success
#   1  — fatal error (backup not created)
# =============================================================================

set -euo pipefail

# ── Resolve directories ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Parse arguments ────────────────────────────────────────────────────────────
DEST="${PROJECT_ROOT}/backups"
RETENTION_DAYS=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST="$2"
      shift 2
      ;;
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    *)
      echo "[WARN] Unknown argument: $1 — ignoring" >&2
      shift
      ;;
  esac
done

# ── Derived variables ──────────────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="cyberai_backup_${TIMESTAMP}"
BACKUP_PATH="${DEST}/${BACKUP_NAME}"

# ── Ensure destination exists ──────────────────────────────────────────────────
mkdir -p "$BACKUP_PATH"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ═══════════════════════════════════════════"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting CyberAI backup: ${BACKUP_NAME}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Project root : ${PROJECT_ROOT}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Destination  : ${DEST}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Retention    : ${RETENTION_DAYS} days"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ───────────────────────────────────────────"

# ── 1. Assessments ─────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [1/5] Backing up assessments..."
if cp -r "${PROJECT_ROOT}/data/assessments" "${BACKUP_PATH}/assessments" 2>/dev/null; then
  COUNT=$(find "${BACKUP_PATH}/assessments" -name "*.json" | wc -l)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → ${COUNT} assessment file(s) copied"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → No assessments directory found — skipping"
  mkdir -p "${BACKUP_PATH}/assessments"
fi

# ── 2. Sessions ────────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [2/5] Backing up sessions..."
if cp -r "${PROJECT_ROOT}/data/sessions" "${BACKUP_PATH}/sessions" 2>/dev/null; then
  COUNT=$(find "${BACKUP_PATH}/sessions" -type f | wc -l)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → ${COUNT} session file(s) copied"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → No sessions directory found — skipping"
  mkdir -p "${BACKUP_PATH}/sessions"
fi

# ── 3. Knowledge base ──────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [3/5] Backing up knowledge base..."
if cp -r "${PROJECT_ROOT}/data/knowledge_base" "${BACKUP_PATH}/knowledge_base" 2>/dev/null; then
  COUNT=$(find "${BACKUP_PATH}/knowledge_base" -type f | wc -l)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → ${COUNT} knowledge base file(s) copied"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → No knowledge base directory found — skipping"
  mkdir -p "${BACKUP_PATH}/knowledge_base"
fi

# ── 4. Vector store (ChromaDB) ─────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [4/5] Backing up vector store (ChromaDB)..."
if cp -r "${PROJECT_ROOT}/data/vector_store" "${BACKUP_PATH}/vector_store" 2>/dev/null; then
  SIZE=$(du -sh "${BACKUP_PATH}/vector_store" 2>/dev/null | cut -f1)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → Vector store copied (${SIZE})"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → No vector store directory found — skipping"
  mkdir -p "${BACKUP_PATH}/vector_store"
fi

# ── 5. Backup manifest ─────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [5/5] Writing manifest..."
cat > "${BACKUP_PATH}/manifest.json" << EOF
{
  "schema_version": "1.0",
  "timestamp": "${TIMESTAMP}",
  "backup_name": "${BACKUP_NAME}",
  "project": "CyberAI Assessment Platform",
  "created_by": "backup.sh",
  "retention_days": ${RETENTION_DAYS},
  "components": [
    "assessments",
    "sessions",
    "knowledge_base",
    "vector_store"
  ],
  "restore_command": "tar -xzf ${BACKUP_NAME}.tar.gz"
}
EOF
echo "[$(date '+%Y-%m-%d %H:%M:%S')]       → manifest.json written"

# ── Compress archive ───────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Compressing archive..."
tar -czf "${DEST}/${BACKUP_NAME}.tar.gz" -C "${DEST}" "${BACKUP_NAME}"
rm -rf "${BACKUP_PATH}"

ARCHIVE_SIZE=$(du -sh "${DEST}/${BACKUP_NAME}.tar.gz" 2>/dev/null | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Backup complete: ${DEST}/${BACKUP_NAME}.tar.gz (${ARCHIVE_SIZE})"

# ── Cleanup old backups ────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up archives older than ${RETENTION_DAYS} days..."
DELETED=$(find "${DEST}" -name "cyberai_backup_*.tar.gz" -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] → ${DELETED} old archive(s) removed"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ═══════════════════════════════════════════"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup finished successfully."
