# CyberAI Assessment Platform — Chiến lược Backup

> **Phiên bản:** 1.0
> **Cập nhật:** 2026-03-31
> **Chủ sở hữu:** DevSecOps / Platform Engineering

---

## Mục lục

1. [Cái gì được backup](#1-cái-gì-được-backup)
2. [Khuyến nghị tần suất backup](#2-khuyến-nghị-tần-suất-backup)
3. [Chính sách lưu giữ (Retention)](#3-chính-sách-lưu-giữ-retention)
4. [Chạy backup thủ công](#4-chạy-backup-thủ-công)
5. [Tự động hoá với Cron](#5-tự-động-hoá-với-cron)
6. [Restore từ backup](#6-restore-từ-backup)
7. [Lưu ý Docker Volume](#7-lưu-ý-docker-volume)
8. [Checklist Disaster Recovery](#8-checklist-disaster-recovery)

---

## 1. Cái gì được backup

Script backup ([`scripts/backup.sh`](../../scripts/backup.sh)) chụp lại
**toàn bộ dữ liệu stateful, không tái tạo được** phát sinh tại runtime.
Source code tĩnh **không** được backup — nó nằm trong Git.

| Thành phần | Đường dẫn | Mô tả |
|---|---|---|
| **Assessments** | `data/assessments/` | File JSON cho mỗi đánh giá ISO 27001 / multi-standard. Mỗi file chứa toàn bộ system info, báo cáo AI, JSON data, điểm compliance. Đây là bản ghi audit chính. |
| **Sessions** | `data/sessions/` | Lịch sử chat của user. Khôi phục context hội thoại. |
| **Knowledge Base** | `data/knowledge_base/` | Dataset fine-tune (JSONL), benchmark, control catalogs, training pair. Sinh lại tốn kém — phải backup. |
| **Vector Store** | `data/vector_store/` | ChromaDB persistent — vector index của toàn bộ ISO documents. Index lại từ markdown gốc được, nhưng mất thời gian. |

**KHÔNG backup (chủ ý):**

- Source code → dùng Git / GitHub
- Docker image → dùng container registry
- `.env` secret → dùng secrets manager (Vault, AWS SM, …)
- File evidence (`data/evidence/`) — thêm vào script nếu cần lưu lâu dài

---

## 2. Khuyến nghị tần suất backup

| Tier | Tần suất | Thời điểm | Lý do |
|------|-----------|-------------|-----------|
| **Incremental (hàng ngày)** | Mỗi 24 giờ | 02:00 giờ local | Bắt hoạt động đánh giá hàng ngày, overhead đĩa tối thiểu |
| **Full hàng tuần** | Mỗi Chủ Nhật | 03:00 giờ local | Snapshot point-in-time sạch cho test khôi phục |
| **Trước khi deploy** | Mỗi lần deploy production | Trong pipeline | Đảm bảo có rollback point trước khi migrate data |
| **On-demand** | Bất cứ khi nào | Trigger thủ công | Trước khi reindex, import lớn, đổi hạ tầng |

---

## 3. Chính sách lưu giữ (Retention)

| Tuổi archive | Hành động |
|-------------|--------|
| 0 – 30 ngày | **Giữ** — cửa sổ rolling mặc định |
| > 30 ngày | **Tự xoá** — `find … -mtime +30 -delete` (tuỳ chỉnh qua `--retention-days`) |

**Retention khuyến nghị theo môi trường:**

| Môi trường | Retention |
|-------------|-----------|
| Production | 90 ngày |
| Staging | 14 ngày |
| Development | 7 ngày |

Override mặc định:

```bash
./scripts/backup.sh --retention-days 90
```

---

## 4. Chạy backup thủ công

### Điều kiện

- Bash 4.x trở lên (Linux chuẩn; Windows dùng WSL)
- Quyền đọc `data/`
- Quyền ghi điểm đích backup

### Sử dụng cơ bản

```bash
# Mặc định: vào <repo_root>/backups/, retention 30 ngày
./scripts/backup.sh

# Tuỳ chỉnh đích và retention
./scripts/backup.sh --dest /mnt/nas/cyberai-backups --retention-days 90

# Kiểm tra archive
ls -lh backups/cyberai_backup_*.tar.gz

# Xem manifest không cần giải nén toàn bộ
tar -xzf backups/cyberai_backup_20260331_020000.tar.gz \
    cyberai_backup_20260331_020000/manifest.json -O
```

### Script sinh ra gì

```
backups/
└── cyberai_backup_20260331_020000.tar.gz
    └── cyberai_backup_20260331_020000/
        ├── manifest.json
        ├── assessments/
        ├── sessions/
        ├── knowledge_base/
        └── vector_store/
```

---

## 5. Tự động hoá với Cron

Thêm vào crontab của user chạy platform (`crontab -e`):

```cron
# CyberAI — backup incremental hàng ngày 02:00
0 2 * * * /bin/bash /opt/cyberai/scripts/backup.sh \
    --dest /mnt/backups/cyberai \
    --retention-days 30 \
    >> /var/log/cyberai-backup.log 2>&1

# CyberAI — backup full hàng tuần Chủ Nhật 03:00
0 3 * * 0 /bin/bash /opt/cyberai/scripts/backup.sh \
    --dest /mnt/backups/cyberai-weekly \
    --retention-days 90 \
    >> /var/log/cyberai-backup-weekly.log 2>&1
```

**Kiểm tra cron đang chạy:**

```bash
tail -20 /var/log/cyberai-backup.log
ls -lt /mnt/backups/cyberai/ | head -5
```

**Lựa chọn thay thế — systemd timer** (ưu tiên trên Linux hiện đại):

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

## 6. Restore từ backup

### Full restore

```bash
# 1. Dừng platform tránh ghi đè
docker compose down

# 2. Chọn archive
ARCHIVE="backups/cyberai_backup_20260331_020000.tar.gz"
RESTORE_DIR="/tmp/cyberai-restore"

# 3. Giải nén
mkdir -p "$RESTORE_DIR"
tar -xzf "$ARCHIVE" -C "$RESTORE_DIR"

# 4. Xác định thư mục giải nén
EXTRACTED=$(ls "$RESTORE_DIR")

# 5. Ghi backup data hiện tại cho chắc
cp -r data/assessments data/assessments.bak 2>/dev/null || true
cp -r data/sessions    data/sessions.bak    2>/dev/null || true
cp -r data/vector_store data/vector_store.bak 2>/dev/null || true

# 6. Khôi phục
cp -r "$RESTORE_DIR/$EXTRACTED/assessments"   data/assessments
cp -r "$RESTORE_DIR/$EXTRACTED/sessions"      data/sessions
cp -r "$RESTORE_DIR/$EXTRACTED/knowledge_base" data/knowledge_base
cp -r "$RESTORE_DIR/$EXTRACTED/vector_store"  data/vector_store

# 7. Khởi động lại
docker compose up -d

# 8. Kiểm tra health
curl -s http://localhost:8000/health
```

### Restore một phần (chỉ assessments)

```bash
tar -xzf "$ARCHIVE" --strip-components=1 \
    -C data/assessments \
    "${EXTRACTED}/assessments/"
```

### Kiểm tra sau restore

```bash
# So số assessment trước/sau
curl -s http://localhost:8000/api/v1/iso27001/assessments | python3 -c \
    "import sys, json; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]} assessments')"

# Kiểm vector store ChromaDB
curl -s http://localhost:8000/api/v1/iso27001/chromadb/stats
```

---

## 7. Lưu ý Docker Volume

Khi chạy Docker Compose, thư mục `data/` được bind-mount từ host. Script
backup chạy trực tiếp trên đường dẫn host — **không cần xử lý đặc biệt
cho Docker**.

Nếu chuyển sang named Docker volume, dùng mẫu sau:

```bash
# Backup named volume
docker run --rm \
  -v cyberai_data:/source:ro \
  -v "$(pwd)/backups":/dest \
  alpine tar -czf /dest/volume_backup_$(date +%Y%m%d).tar.gz -C /source .

# Restore named volume
docker run --rm \
  -v cyberai_data:/target \
  -v "$(pwd)/backups":/src \
  alpine tar -xzf /src/volume_backup_20260331.tar.gz -C /target
```

**Chú ý riêng ChromaDB:**
`PersistentClient` của ChromaDB ghi 1 SQLite (`chroma.sqlite3`) + các
file segment. Luôn backup và restore **toàn bộ** thư mục `vector_store/`
atomically. Restore một phần ChromaDB sẽ làm hỏng index.

Để backup zero-downtime, pause client ChromaDB (hoặc chỉ dừng container
backend) trong lúc snapshot:

```bash
docker compose stop backend
cp -r data/vector_store backups/vector_store_snapshot
docker compose start backend
```

---

## 8. Checklist Disaster Recovery

Dùng checklist sau sau bất cứ sự kiện mất dữ liệu / deploy hỏng.

### Phản ứng tức thì (0 – 15 phút)

- [ ] Dừng platform: `docker compose down`
- [ ] Xác định archive backup healthy gần nhất trong `backups/`
- [ ] Mở `manifest.json` trong archive để xác nhận ngày & component
- [ ] Báo incident owner / on-call

### Khôi phục assessment (15 – 30 phút)

- [ ] Giải nén archive ra staging
- [ ] So số assessment: `ls data/assessments/ | wc -l` vs backup
- [ ] Restore `assessments/`
- [ ] Restore `sessions/` nếu cần lịch sử chat
- [ ] Kiểm không có assessment đang `processing` lúc sự cố

### Khôi phục vector store (30 – 60 phút)

- [ ] Restore `vector_store/` từ backup **hoặc** trigger reindex full:
  ```bash
  curl -X POST http://localhost:8000/api/v1/iso27001/reindex
  curl -X POST http://localhost:8000/api/v1/iso27001/reindex-domains
  ```
- [ ] Xác nhận chunk count qua `/api/v1/iso27001/chromadb/stats`
- [ ] Chạy test RAG query kiểm chất lượng retrieval

### Khởi động và kiểm tra (60 – 90 phút)

- [ ] Khởi động platform: `docker compose up -d`
- [ ] `docker compose ps` — mọi container healthy
- [ ] `curl http://localhost:8000/health`
- [ ] `curl http://localhost:8000/metrics | grep cyberai`
- [ ] Submit test assessment — xác nhận end-to-end
- [ ] Ghi lại incident, nguyên nhân, bước khôi phục

### Hành động sau sự cố

- [ ] Xem lại tần suất backup — tăng nếu RPO bị vi phạm
- [ ] Test integrity backup hàng tháng: giải nén ngẫu nhiên, kiểm manifest
- [ ] Cập nhật doc này khi thêm stateful component mới
- [ ] Lịch diễn tập restore trong 30 ngày

---

*Doc này là một phần của runbook DevSecOps CyberAI. Hãy cập nhật mỗi khi
data model hoặc topo deploy thay đổi.*
