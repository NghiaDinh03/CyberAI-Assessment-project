# `scripts/` Reference

> Operational helpers shipped with the CyberAI Assessment Platform.
> All scripts are runnable from the repository root on a fresh clone.

| Script | Platform | Purpose |
|---|---|---|
| [`scripts/setup.sh`](../../scripts/setup.sh) | bash (Linux / macOS / WSL) | First-run setup: env, JWT secret, folders, docker compose, health-wait |
| [`scripts/setup.bat`](../../scripts/setup.bat) | Windows `cmd.exe` | Mirror of `setup.sh` |
| [`scripts/backup.sh`](../../scripts/backup.sh) | bash | Tar+gzip the four stateful data folders + manifest, retention sweep |
| [`scripts/download_models.py`](../../scripts/download_models.py) | Python 3.10+ | Pull GGUF weights from HuggingFace into `models/llm/weights/` |

---

## 1. `setup.sh` — First-Run Bootstrap (bash)

Source: [`scripts/setup.sh:1-125`](../../scripts/setup.sh)

Six-step pipeline, all idempotent:

| # | Step | Behaviour |
|---|---|---|
| 1 | `.env` | Copies `.env.example` → `.env` if missing |
| 2 | `JWT_SECRET` | Replaces literal `change-me-in-production` with `python3 -c "import secrets; print(secrets.token_hex(32))"` (or `openssl rand -hex 32` fallback) |
| 3 | Folders | `mkdir -p` for `data/{sessions,uploads,exports,evidence,assessments,standards,knowledge_base,iso_documents,vector_store,translations,models/huggingface}` and `models/llm` + `.gitkeep` files |
| 4 | Docker check | Aborts unless both `docker` and `docker compose v2` exist |
| 5 | Build & start | `docker compose up -d --build` |
| 6 | Health wait | Polls `http://localhost:8000/health` for ≤ 600 seconds |

Exit non-zero if Docker is missing or build fails. Re-running on an
existing install is safe.

```bash
bash scripts/setup.sh
```

### `setup.bat` (Windows)

Source: [`scripts/setup.bat:1-108`](../../scripts/setup.bat)

Functional parity with the bash version. JWT replacement uses PowerShell
(`Get-Content … | Set-Content`) so it works on default Windows 10/11
without WSL.

```cmd
scripts\setup.bat
```

---

## 2. `backup.sh` — Stateful Data Backup

Source: [`scripts/backup.sh:1-138`](../../scripts/backup.sh)

| Argument | Default | Notes |
|---|---|---|
| `--dest <path>` | `<repo>/backups` | Destination directory (created if missing) |
| `--retention-days <n>` | `30` | `find … -mtime +n -delete` against `cyberai_backup_*.tar.gz` |

### Backup contents

```
cyberai_backup_<TIMESTAMP>.tar.gz
└── cyberai_backup_<TIMESTAMP>/
    ├── manifest.json     ← schema_version, components, restore_command
    ├── assessments/      ← data/assessments/*
    ├── sessions/         ← data/sessions/*
    ├── knowledge_base/   ← data/knowledge_base/*
    └── vector_store/     ← data/vector_store/* (entire ChromaDB folder)
```

Manifest layout — written verbatim by
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

### Operational tips

- Retention sweep runs **after** the new archive is written, so a freshly
  created archive can never be deleted in the same invocation.
- The script uses `cp -r` (no `rsync`); pause the backend before snapping
  `data/vector_store/` if you cannot tolerate a torn ChromaDB snapshot.
- Detailed restore + cron + systemd recipes live in
  [`docs/en/backup_strategy.md`](backup_strategy.md).

---

## 3. `download_models.py` — GGUF Fetcher

Source: [`scripts/download_models.py:1-333`](../../scripts/download_models.py)

Downloads **GGUF** quantised weights into `models/llm/weights/` so
LocalAI can mount them via the YAML `model: weights/<file>.gguf`
references in `models/llm/*.yaml`.

### Registry (verified `repo_id` + `hf_filename`)

Source: [`scripts/download_models.py:36-88`](../../scripts/download_models.py)

| Key | Filename | Repo | Size | Notes |
|---|---|---|---|---|
| `gemma-3-4b` | `google_gemma-3-4b-it-Q4_K_M.gguf` | `bartowski/google_gemma-3-4b-it-GGUF` | 2.5 GB | Fast, ~3 GB RAM |
| `gemma-3-12b` | `google_gemma-3-12b-it-Q4_K_M.gguf` | `bartowski/google_gemma-3-12b-it-GGUF` | 7.3 GB | Balanced, ~8 GB RAM |
| `gemma-4-31b` | `gemma-4-31B-it-Q4_K_M.gguf` | `unsloth/gemma-4-31B-it-GGUF` | 19.0 GB | Best quality, ~20 GB RAM |
| `gemma-4-31b-q3` | `gemma-4-31B-it-Q3_K_M.gguf` | `unsloth/gemma-4-31B-it-GGUF` | 13.5 GB | Lighter, ~14 GB RAM |
| `llama` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF` | 4.9 GB | General LLM |
| `security` | `SecurityLLM-7B-Q4_K_M.gguf` | `QuantFactory/SecurityLLM-GGUF` | 4.2 GB | Cybersecurity domain |

All entries set `auth: False` — no `HF_TOKEN` required.

### Download algorithm

1. Prefer **`huggingface_hub.hf_hub_download`** (with optional
   `hf_transfer` accelerator) — see `download_via_hf_hub()` at
   `download_models.py:141-182`.
2. Fall back to a plain **urllib** streaming download with a console
   progress bar — `download_direct()` at `download_models.py:104-138`.
3. Atomic rename: write to `<file>.tmp` then `os.replace()` to final
   path so an interrupted transfer never corrupts a previous good copy.

### Common invocations

```bash
# Show which models are present + LocalAI visibility check
python scripts/download_models.py --status

# Pull a single model
python scripts/download_models.py --model llama
python scripts/download_models.py --model security

# Pull everything in the registry
python scripts/download_models.py --model all
```

`--status` additionally probes `http://localhost:8080/v1/models` to
confirm the running LocalAI daemon actually sees each weight file (see
`check_status()` at `download_models.py:225-253`).

---

## 4. Cross-references

- **Bootstrap order** (after `setup.sh`): download models →
  `docker compose restart backend` → `ModelGuard.refresh()` (auto on
  start) → `/health/ready` returns `200`.
- **Backup discipline:** see [`docs/en/backup_strategy.md`](backup_strategy.md)
  for cron / systemd recipes and disaster recovery checklist.
- **Model layer:** see [`docs/en/model_guard.md`](model_guard.md) for how
  the backend confirms a downloaded GGUF is actually picked up.
