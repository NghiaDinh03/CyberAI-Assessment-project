# ModelGuard — Local GGUF Availability & LocalAI Health

> **Module:** `backend/services/model_guard.py`
> **Invoked at:** FastAPI lifespan startup — `backend/main.py:55-56`
> **Status source:** `GET /health/ready` and `GET /health` (see `backend/api/routes/health.py`)

---

## 1. Purpose

`ModelGuard` is a lightweight thread-safe registry that answers the question
**"Do the GGUF model files the platform needs actually exist on disk?"**.

It is evaluated once at process start, cached in-memory under a
`threading.Lock`, and re-evaluated on demand. It is **not** an inference
engine; it only verifies presence of binary weights and is the single source
of truth used by readiness probes before any chat / assessment request is
accepted.

---

## 2. Class Contract

Source: [`backend/services/model_guard.py:10-45`](../../backend/services/model_guard.py)

| Member | Kind | Purpose |
|---|---|---|
| `_lock` | `threading.Lock` | Serialises mutations of `_state` |
| `_state` | `Dict[str, str]` | Per-model flag: `"present"` or `"missing"` |
| `refresh()` | `@classmethod` | Walk `settings.required_model_ids`, test filesystem, replace `_state`, return the new snapshot |
| `status()` | `@classmethod` | Return a **copy** of `_state`; auto-calls `refresh()` on first use |
| `is_ready()` | `@classmethod` | `True` iff every required model reports `"present"` |
| `_resolve_model_path(base_dir, model_id)` | `@staticmethod` | Probe two candidate paths, return the first that exists or `""` |

---

## 3. Path Resolution Algorithm

```
base_dir = os.getenv("MODELS_PATH", "./models")

for model_id in settings.required_model_ids:
    candidates = [
        f"{base_dir}/{model_id}",                 # full relative id, e.g. ./models/llama/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
        f"{base_dir}/{os.path.basename(model_id)}" # flat name fallback,   e.g. ./models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
    ]
    first_existing = next((p for p in candidates if os.path.exists(p)), "")
    summary[model_id] = "present" if first_existing else "missing"
```

Reference: [`backend/services/model_guard.py:36-45`](../../backend/services/model_guard.py)

The two-candidate probe is intentional — it lets operators organise GGUF
binaries either under the registry sub-folders produced by
[`scripts/download_models.py`](../../scripts/download_models.py) (e.g.
`models/llama/…`, `models/security/…`) **or** flat in `models/` after a
manual download.

---

## 4. Configuration

| Knob | Default | Where |
|---|---|---|
| `MODELS_PATH` | `./models` | Host env var read inside `refresh()` |
| `REQUIRED_MODEL_IDS` | comma-separated list | `backend/core/config.py:55-58` |

`settings.required_model_ids` is a list built by splitting the env var on
commas and trimming whitespace. An empty list means ModelGuard always
reports ready (useful when running in pure-cloud mode).

---

## 5. Lifecycle

1. **Startup** — `backend/main.py:55-56` calls `ModelGuard.refresh()` inside
   the `lifespan` context manager. The result is logged so operators can
   catch a missing GGUF before the first user request lands.
2. **Runtime** — `/health` and `/health/ready` endpoints call `status()` /
   `is_ready()` (see `backend/api/routes/health.py`). These calls do **not**
   re-hit the disk; they reuse the cached map.
3. **Manual refresh** — there is no public re-scan endpoint today; operators
   who drop a new GGUF file onto the host should restart the backend
   container to force a fresh scan.

---

## 6. Interaction with LocalAI and Ollama

ModelGuard is the **static** check (do files exist?). The **dynamic** check
(is LocalAI actually loading them?) lives in
[`backend/services/cloud_llm_service.py:252-275`](../../backend/services/cloud_llm_service.py)
as `CloudLLMService.localai_health_check()`. That call hits
`POST /v1/chat/completions` with a one-token prompt and caches the result.

| Check | Layer | Measures |
|---|---|---|
| `ModelGuard.is_ready()` | Filesystem | GGUF binary is on disk |
| `CloudLLMService.localai_health_check()` | HTTP | LocalAI daemon is up and can load the model |
| `CloudLLMService.ollama_health_check()` | HTTP | Ollama daemon responds to `/api/tags` |

All three must pass before the platform will answer a chat request in pure
local mode. If any fail, the fallback chain in
[`cloud_llm_service.py:24-30`](../../backend/services/cloud_llm_service.py)
takes over.

---

## 7. Operational Recipes

### Inspect current state

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/health/ready
```

### Download the missing models

```bash
python scripts/download_models.py --key llama --key security
```

(Registry keys are enumerated in
[`scripts/download_models.py:185-222`](../../scripts/download_models.py).)

### Force a rescan

```bash
docker compose restart backend
```

---

## 8. Failure Modes & Diagnostics

| Symptom | Likely cause | Fix |
|---|---|---|
| `is_ready() == False` at startup | Missing GGUF file | Run `scripts/download_models.py` or drop the file manually into `MODELS_PATH` |
| `status()` returns empty `{}` | `REQUIRED_MODEL_IDS` env var is unset/empty | Set the env var or accept cloud-only mode |
| Model file is present but LocalAI still fails | GGUF corrupt / wrong quant | Re-download; check SHA against the HF page |
| `/health/ready` flips between ready/not-ready | Race with a long-running backup that touches `models/` | Backups should skip `models/` (see [`scripts/backup.sh`](../../scripts/backup.sh)) |

---

## 9. See Also

- [`docs/en/architecture.md`](architecture.md) — where ModelGuard sits in
  the startup sequence.
- [`docs/en/deployment.md`](deployment.md) — `MODELS_PATH` bind-mounts for
  Docker Compose.
- [`docs/en/analytics_monitoring.md`](analytics_monitoring.md) — the
  `cyberai_*` Prometheus counters that correlate with readiness.
