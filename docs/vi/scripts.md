# Tham chiếu thư mục `scripts/`

> Các script vận hành đi kèm CyberAI Assessment Platform. Mọi script đều
> chạy được từ thư mục gốc repo trên một bản clone mới.

| Script | Nền tảng | Mục đích |
|---|---|---|
| [`scripts/setup.sh`](../../scripts/setup.sh) | bash (Linux / macOS / WSL) | Setup lần đầu: env, JWT secret, folder, docker compose, chờ health |
| [`scripts/setup.bat`](../../scripts/setup.bat) | Windows `cmd.exe` | Bản gương của `setup.sh` |
| [`scripts/backup.sh`](../../scripts/backup.sh) | bash | Tar+gzip 4 thư mục dữ liệu stateful + manifest, dọn theo retention |
| [`scripts/download_models.py`](../../scripts/download_models.py) | Python 3.10+ | Tải weights GGUF từ HuggingFace về `models/llm/weights/` |

---

## 1. `setup.sh` — Bootstrap lần đầu (bash)

Nguồn: [`scripts/setup.sh:1-125`](../../scripts/setup.sh)

Pipeline 6 bước, đều idempotent:

| # | Bước | Hành vi |
|---|---|---|
| 1 | `.env` | Copy `.env.example` → `.env` nếu thiếu |
| 2 | `JWT_SECRET` | Thay literal `change-me-in-production` bằng `python3 -c "import secrets; print(secrets.token_hex(32))"` (fallback `openssl rand -hex 32`) |
| 3 | Folders | `mkdir -p` cho `data/{sessions,uploads,exports,evidence,assessments,standards,knowledge_base,iso_documents,vector_store,translations,models/huggingface}` và `models/llm` + `.gitkeep` |
| 4 | Check Docker | Báo lỗi nếu thiếu `docker` hoặc `docker compose v2` |
| 5 | Build & start | `docker compose up -d --build` |
| 6 | Chờ health | Poll `http://localhost:8000/health` ≤ 600 giây |

Trả mã khác 0 nếu Docker thiếu hoặc build fail. Chạy lại trên cài đặt
sẵn an toàn.

```bash
bash scripts/setup.sh
```

### `setup.bat` (Windows)

Nguồn: [`scripts/setup.bat:1-108`](../../scripts/setup.bat)

Tương đương chức năng bản bash. Việc thay JWT dùng PowerShell
(`Get-Content … | Set-Content`) nên chạy được trên Windows 10/11 mặc định
mà không cần WSL.

```cmd
scripts\setup.bat
```

---

## 2. `backup.sh` — Backup dữ liệu stateful

Nguồn: [`scripts/backup.sh:1-138`](../../scripts/backup.sh)

| Tham số | Mặc định | Ghi chú |
|---|---|---|
| `--dest <path>` | `<repo>/backups` | Thư mục đích (tự tạo nếu thiếu) |
| `--retention-days <n>` | `30` | `find … -mtime +n -delete` với `cyberai_backup_*.tar.gz` |

### Nội dung backup

```
cyberai_backup_<TIMESTAMP>.tar.gz
└── cyberai_backup_<TIMESTAMP>/
    ├── manifest.json     ← schema_version, components, restore_command
    ├── assessments/      ← data/assessments/*
    ├── sessions/         ← data/sessions/*
    ├── knowledge_base/   ← data/knowledge_base/*
    └── vector_store/     ← data/vector_store/* (toàn bộ folder ChromaDB)
```

Cấu trúc manifest — viết nguyên văn bởi
[`backup.sh:104-120`](../../scripts/backup.sh):

```json
{
  "schema_version": "1.0",
  "timestamp": "20260419_140000",
  "backup_name": "cyberai_backup_20260419_140000",
  "project": "CyberAI Assessment Platform",
  "created_by": "backup.sh",
  "retention_days": 30,
  "components": ["assessments", "sessions", "knowledge_base", "vector_store"],
  "restore_command": "tar -xzf cyberai_backup_20260419_140000.tar.gz"
}
```

### Mẹo vận hành

- Vòng dọn retention chạy **sau** khi archive mới được ghi, nên archive
  vừa tạo không thể bị xoá cùng lần chạy.
- Script dùng `cp -r` (không `rsync`); nên pause backend trước khi snap
  `data/vector_store/` nếu không chấp nhận snapshot Chroma bị xé.
- Recipe restore + cron + systemd chi tiết nằm ở
  [`docs/vi/backup_strategy.md`](backup_strategy.md).

---

## 3. `download_models.py` — Trình tải GGUF

Nguồn: [`scripts/download_models.py:1-333`](../../scripts/download_models.py)

Tải weights GGUF (lượng tử) về `models/llm/weights/` để LocalAI mount qua
các tham chiếu YAML `model: weights/<file>.gguf` trong `models/llm/*.yaml`.

### Registry (đã verify `repo_id` + `hf_filename`)

Nguồn: [`scripts/download_models.py:36-88`](../../scripts/download_models.py)

| Key | Filename | Repo | Size | Ghi chú |
|---|---|---|---|---|
| `gemma-3-4b` | `google_gemma-3-4b-it-Q4_K_M.gguf` | `bartowski/google_gemma-3-4b-it-GGUF` | 2.5 GB | Nhanh, ~3 GB RAM |
| `gemma-3-12b` | `google_gemma-3-12b-it-Q4_K_M.gguf` | `bartowski/google_gemma-3-12b-it-GGUF` | 7.3 GB | Cân bằng, ~8 GB RAM |
| `gemma-4-31b` | `gemma-4-31B-it-Q4_K_M.gguf` | `unsloth/gemma-4-31B-it-GGUF` | 19.0 GB | Tốt nhất, ~20 GB RAM |
| `gemma-4-31b-q3` | `gemma-4-31B-it-Q3_K_M.gguf` | `unsloth/gemma-4-31B-it-GGUF` | 13.5 GB | Nhẹ hơn, ~14 GB RAM |
| `llama` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | 4.9 GB | LLM tổng quát |
| `security` | `SecurityLLM-7B-Q4_K_M.gguf` | `QuantFactory/SecurityLLM-GGUF` | 4.2 GB | Domain bảo mật |

Tất cả entry đều `auth: False` — không cần `HF_TOKEN`.

### Thuật toán tải

1. Ưu tiên **`huggingface_hub.hf_hub_download`** (kèm tăng tốc tuỳ chọn
   `hf_transfer`) — xem `download_via_hf_hub()` tại
   `download_models.py:141-182`.
2. Fallback **urllib** stream với progress bar console —
   `download_direct()` tại `download_models.py:104-138`.
3. Đổi tên atomically: ghi vào `<file>.tmp` rồi `os.replace()` sang đường
   dẫn cuối, nên transfer đứt giữa chừng không phá huỷ bản tốt cũ.

### Lệnh hay dùng

```bash
# Xem model nào đang có + check LocalAI thấy weight chưa
python scripts/download_models.py --status

# Tải 1 model
python scripts/download_models.py --model llama
python scripts/download_models.py --model security

# Tải toàn bộ registry
python scripts/download_models.py --model all
```

Cờ `--status` thêm bước probe `http://localhost:8080/v1/models` để xác
nhận LocalAI daemon thấy file weight (xem `check_status()` tại
`download_models.py:225-253`).

---

## 4. Tham chiếu chéo

- **Trình tự bootstrap** (sau `setup.sh`): tải model →
  `docker compose restart backend` → `ModelGuard.refresh()` (tự động lúc
  start) → `/health/ready` trả `200`.
- **Kỷ luật backup:** xem [`docs/vi/backup_strategy.md`](backup_strategy.md)
  cho cron / systemd recipe và checklist DR.
- **Tầng model:** xem [`docs/vi/model_guard.md`](model_guard.md) — backend
  xác nhận GGUF đã tải có được pick up không.
