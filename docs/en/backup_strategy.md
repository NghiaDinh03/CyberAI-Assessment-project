# CyberAI Assessment Platform — Backup Strategy

> **Version:** 1.0  
> **Last Updated:** 2026-03-31  
> **Owner:** DevSecOps / Platform Engineering

---

## Table of Contents

1. [What Is Backed Up](#1-what-is-backed-up)
2. [Backup Frequency Recommendations](#2-backup-frequency-recommendations)
3. [Retention Policy](#3-retention-policy)
4. [Running a Manual Backup](#4-running-a-manual-backup)
5. [Automating with Cron](#5-automating-with-cron)
6. [Restoring from Backup](#6-restoring-from-backup)
7. [Docker Volume Backup Considerations](#7-docker-volume-backup-considerations)
8. [Disaster Recovery Checklist](#8-disaster-recovery-checklist)

---

## 1. What Is Backed Up

The backup script (`scripts/backup.sh`) captures all stateful, irreplaceable data produced at runtime. Static source code is excluded — it lives in version control.

| Component | Path | Description |
|-----------|------|-------------|
| **Assessments** | `data/assessments/` | JSON files for every ISO 27001 / multi-standard assessment. Each file contains the full system info, AI report, JSON data, and compliance score. These are the primary audit records. |
| **Sessions** | `data/sessions/` | Chat session history files. Used to restore conversation context for active users. |
| **Knowledge Base** | `data/knowledge_base/` | Fine-tuning datasets (JSONL), benchmark files, control catalogs, and any generated training pairs. Regeneration is expensive — back these up. |
| **Vector Store** | `data/vector_store/` | ChromaDB persistent storage — the embedded vector index for all ISO documents. Re-indexing from source markdown is possible but takes significant time. |

**Not backed up (by design):**

- Source code → use Git / GitHub
- Docker images → use a container registry
- `.env` secrets → use a secrets manager (Vault, AWS Secrets Manager, etc.)
- Uploaded evidence files (`data/evidence/`) — add to the script if long-term evidence retention is required

---

## 2. Backup Frequency Recommendations

| Tier | Frequency | When to Run | Rationale |
|------|-----------|-------------|-----------|
| **Incremental (daily)** | Every 24 hours | 02:00 local time | Captures daily assessment activity with minimal disk overhead |
| **Full weekly** | Every Sunday | 03:00 local time | Guaranteed clean point-in-time snapshot for recovery testing |
| **Pre-deployment** | Before every production deploy | Part of deploy pipeline | Ensures a rollback point exists before any schema or data migration |
| **On-demand** | Any time | Manual trigger | Before bulk reindexing, large data imports, or infrastructure changes |

---

## 3. Retention Policy

| Archive Age | Action |
|-------------|--------|
| 0 – 30 days | **Keep** — rolling window, default |
| > 30 days | **Auto-delete** — `find … -mtime +30 -delete` (configurable via `--retention-days`) |

**Recommended retention by environment:**

| Environment | Retention |
|-------------|-----------|
| Production | 90 days |
| Staging | 14 days |
| Development | 7 days |

Override the default with:

```bash
./scripts/backup.sh --retention-days 90
```

---

## 4. Running a Manual Backup

### Prerequisites

- Bash 4.x or later (standard on Linux; use WSL on Windows)
- Read access to `data/` directory
- Write access to the backup destination

### Basic usage

```bash
# Default: backs up to <project_root>/backups/, 30-day retention
./scripts/backup.sh

# Custom destination and retention
./scripts/backup.sh --dest /mnt/nas/cyberai-backups --retention-days 90

# Verify the created archive
ls -lh backups/cyberai_backup_*.tar.gz

# Inspect manifest without fully extracting
tar -xzf backups/cyberai_backup_20260331_020000.tar.gz \
    cyberai_backup_20260331_020000/manifest.json -O
```

### What the script produces

```
backups/
└── cyberai_backup_20260331_020000.tar.gz   ← compressed archive
    └── cyberai_backup_20260331_020000/
        ├── manifest.json                   ← metadata + restore instructions
        ├── assessments/                    ← JSON assessment records
        ├── sessions/                       ← session history files
        ├── knowledge_base/                 ← JSONL datasets + control catalogs
        └── vector_store/                   ← ChromaDB persistent data
```

---

## 5. Automating with Cron

Add to the crontab of the user running the platform (`crontab -e`):

```cron
# CyberAI — daily incremental backup at 02:00
0 2 * * * /bin/bash /opt/cyberai/scripts/backup.sh \
    --dest /mnt/backups/cyberai \
    --retention-days 30 \
    >> /var/log/cyberai-backup.log 2>&1

# CyberAI — weekly full backup every Sunday at 03:00
0 3 * * 0 /bin/bash /opt/cyberai/scripts/backup.sh \
    --dest /mnt/backups/cyberai-weekly \
    --retention-days 90 \
    >> /var/log/cyberai-backup-weekly.log 2>&1
```

**Verify cron is running:**

```bash
# Check last log entry
tail -20 /var/log/cyberai-backup.log

# Confirm latest archive exists
ls -lt /mnt/backups/cyberai/ | head -5
```

**Systemd timer alternative** (preferred on modern Linux):

```ini
# /etc/systemd/system/cyberai-backup.service
[Unit]
Description=CyberAI Platform Backup
After=network.target

[Service]
Type=oneshot
User=cyberai
ExecStart=/bin/bash /opt/cyberai/scripts/backup.sh \
    --dest /mnt/backups/cyberai --retention-days 30
StandardOutput=journal
StandardError=journal

# /etc/systemd/system/cyberai-backup.timer
[Unit]
Description=CyberAI Platform Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now cyberai-backup.timer
systemctl status cyberai-backup.timer
```

---

## 6. Restoring from Backup

### Full restore

```bash
# 1. Stop the running platform to prevent writes during restore
docker compose down

# 2. Choose the archive to restore
ARCHIVE="backups/cyberai_backup_20260331_020000.tar.gz"
RESTORE_DIR="/tmp/cyberai-restore"

# 3. Extract
mkdir -p "$RESTORE_DIR"
tar -xzf "$ARCHIVE" -C "$RESTORE_DIR"

# 4. Identify the extracted folder name
EXTRACTED=$(ls "$RESTORE_DIR")

# 5. Replace live data (backup current data first just in case)
cp -r data/assessments data/assessments.bak 2>/dev/null || true
cp -r data/sessions    data/sessions.bak    2>/dev/null || true
cp -r data/vector_store data/vector_store.bak 2>/dev/null || true

# 6. Restore components
cp -r "$RESTORE_DIR/$EXTRACTED/assessments"   data/assessments
cp -r "$RESTORE_DIR/$EXTRACTED/sessions"      data/sessions
cp -r "$RESTORE_DIR/$EXTRACTED/knowledge_base" data/knowledge_base
cp -r "$RESTORE_DIR/$EXTRACTED/vector_store"  data/vector_store

# 7. Restart
docker compose up -d

# 8. Verify health
curl -s http://localhost:8000/health
```

### Partial restore (assessments only)

```bash
tar -xzf "$ARCHIVE" --strip-components=1 \
    -C data/assessments \
    "${EXTRACTED}/assessments/"
```

### Post-restore validation

```bash
# Check assessment count matches pre-restore
curl -s http://localhost:8000/api/v1/iso27001/assessments | python3 -c \
    "import sys, json; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]} assessments')"

# Verify ChromaDB vector store is healthy
curl -s http://localhost:8000/api/v1/iso27001/chromadb/stats
```

---

## 7. Docker Volume Backup Considerations

When running with Docker Compose, the `data/` directory is bind-mounted from the host. The backup script works directly on the host path and requires **no special Docker handling**.

However, if you migrate to named Docker volumes, use the following pattern:

```bash
# Backup a named Docker volume
docker run --rm \
  -v cyberai_data:/source:ro \
  -v "$(pwd)/backups":/dest \
  alpine tar -czf /dest/volume_backup_$(date +%Y%m%d).tar.gz -C /source .

# Restore a named Docker volume
docker run --rm \
  -v cyberai_data:/target \
  -v "$(pwd)/backups":/src \
  alpine tar -xzf /src/volume_backup_20260331.tar.gz -C /target
```

**ChromaDB-specific note:**  
ChromaDB's `PersistentClient` writes a SQLite database (`chroma.sqlite3`) plus segment files. Always back up and restore the **entire** `vector_store/` directory atomically. Partial restores of ChromaDB will corrupt the index.

For zero-downtime backups, pause the ChromaDB client (or stop only the backend container) during the vector store snapshot:

```bash
docker compose stop backend
cp -r data/vector_store backups/vector_store_snapshot
docker compose start backend
```

---

## 8. Disaster Recovery Checklist

Use this checklist after any data loss event or failed deployment.

### Immediate response (0 – 15 minutes)

- [ ] Stop the platform: `docker compose down`
- [ ] Identify the most recent healthy backup archive in `backups/`
- [ ] Check the `manifest.json` inside the archive to confirm the backup date and components
- [ ] Notify the incident owner / on-call engineer

### Assessment data recovery (15 – 30 minutes)

- [ ] Extract backup archive to a staging path
- [ ] Diff assessment count: compare `ls data/assessments/ | wc -l` against backup
- [ ] Restore `assessments/` directory
- [ ] Restore `sessions/` directory if conversation history is required
- [ ] Verify no active assessments were mid-processing (status: `processing`) during the incident

### Vector store recovery (30 – 60 minutes)

- [ ] Restore `vector_store/` from backup **or** trigger a full re-index:
  ```bash
  curl -X POST http://localhost:8000/api/v1/iso27001/reindex
  curl -X POST http://localhost:8000/api/v1/iso27001/reindex-domains
  ```
- [ ] Confirm chunk counts via `/api/v1/iso27001/chromadb/stats`
- [ ] Run a test RAG query to verify retrieval quality

### Platform restart and validation (60 – 90 minutes)

- [ ] Restart the platform: `docker compose up -d`
- [ ] Confirm all containers are healthy: `docker compose ps`
- [ ] Verify API health: `curl http://localhost:8000/health`
- [ ] Check Prometheus metrics: `curl http://localhost:8000/metrics | grep cyberai`
- [ ] Submit a test assessment to confirm end-to-end flow
- [ ] Document the incident, root cause, and recovery steps

### Post-incident actions

- [ ] Review backup frequency — consider increasing if RPO was violated
- [ ] Test backup integrity monthly: extract a random archive and validate manifest
- [ ] Update this document if new stateful components were added
- [ ] Schedule a backup restore drill within 30 days

---

*This document is part of the CyberAI Assessment Platform DevSecOps runbook. Keep it updated whenever the platform's data model or deployment topology changes.*
