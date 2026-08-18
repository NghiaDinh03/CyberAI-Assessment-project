# CyberAI Assessment Platform — Deployment Guide

## 1. Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24+ | Latest stable |
| Docker Compose | v2 | v2.20+ |
| RAM | 16 GB | 32 GB |
| Disk | 20 GB (model files) | 40 GB+ |
| GPU | — | NVIDIA (optional, faster inference) |

> **Memory breakdown:** LocalAI alone requires 12 GB (dev) / 16 GB (prod) for loading GGUF models. Ollama needs an additional 12 GB. The backend and frontend add ~8 GB combined.

---

## 2. Quick Start (Development)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — at minimum set CLOUD_API_KEYS if you want cloud fallback

# 2. Start all containers
docker compose up -d

# 3. Verify
docker compose ps
```

**Service endpoints after startup:**

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3000 | Next.js dev server with hot reload |
| Backend API docs | http://localhost:8000/docs | Swagger UI |
| Backend ReDoc | http://localhost:8000/redoc | Alternative API docs |
| LocalAI | http://localhost:8080 | OpenAI-compatible API |
| Ollama | http://localhost:11434 | OpenAI-compatible API |

> **Note:** LocalAI takes up to 120 seconds to become ready (model loading). The backend container starts immediately but will fail inference calls until LocalAI passes its health check.

---

## 3. Model Download

GGUF model files for LocalAI must be downloaded before first use:

```bash
pip install huggingface_hub hf_transfer
python scripts/download_models.py --model llama --model security
```

### Available Models

| Model ID | File | Size | Description |
|----------|------|------|-------------|
| `llama` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | ~4.9 GB | General LLM (report formatting, chat) |
| `security` | `SecurityLLM-7B-Q4_K_M.gguf` | ~4.2 GB | Cybersecurity domain (GAP analysis) |
| `gemma-3-4b` | `google_gemma-3-4b-it-Q4_K_M.gguf` | ~2.5 GB | Fast, lightweight |
| `gemma-3-12b` | `google_gemma-3-12b-it-Q4_K_M.gguf` | ~7.3 GB | Balanced quality/speed |
| `gemma-4-31b` | `gemma-4-31B-it-Q4_K_M.gguf` | ~19 GB | Best quality, high RAM |
| `gemma-4-31b-q3` | `gemma-4-31B-it-Q3_K_M.gguf` | ~13.5 GB | Lighter quantization |

Models download to [`models/llm/weights/`](scripts/download_models.py:32) via HuggingFace Hub.

```bash
# Check download status
python scripts/download_models.py --status

# Download all models
python scripts/download_models.py --model all
```

**Ollama models:** Gemma 3n E4B is auto-pulled on container startup via the [entrypoint](docker-compose.yml:127). No manual download required.

---

## 4. Environment Variables

All configuration is via environment variables defined in [`.env.example`](.env.example). Copy to `.env` and customize.

### Model & LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCALAI_URL` | `http://localai:8080` | LocalAI service URL (internal Docker DNS) |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama service URL (internal Docker DNS) |
| `MODEL_NAME` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | Primary GGUF model for general chat/reports |
| `SECURITY_MODEL_NAME` | *(falls back to MODEL_NAME)* | Security-specific GGUF model for GAP analysis |
| `MAX_TOKENS` | `-1` | Max generation tokens (`-1` = model default) |
| `PREFER_LOCAL` | `true` | `true`: LocalAI/Ollama first, cloud fallback. `false`: cloud first |
| `LOCAL_ONLY_MODE` | `false` | `true`: never call cloud APIs |
| `THREADS` | `6` | CPU threads for LocalAI inference |
| `CONTEXT_SIZE` | `8192` | Context window size for LocalAI |
| `DEBUG` | `true` | Enable debug logging and relaxed JWT validation |

### Cloud LLM API

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUD_LLM_API_URL` | `https://open-claude.com/v1` | Open Claude gateway URL |
| `CLOUD_MODEL_NAME` | `gemini-3-flash-preview` | Default cloud model |
| `CLOUD_API_KEYS` | *(empty)* | Comma-separated API keys for round-robin rotation |

### Data Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `ISO_DOCS_PATH` | `/data/iso_documents` | Knowledge base markdown files |
| `VECTOR_STORE_PATH` | `/data/vector_store` | ChromaDB persistent storage |
| `DATA_PATH` | `/data` | Root data directory |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret (**must** be ≥32 chars in production) |
| `JWT_EXPIRE_MINUTES` | `60` | Token expiry in minutes |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

> **Important:** The application refuses to start in production (`DEBUG=false`) if `JWT_SECRET` is a known weak value or shorter than 32 characters. Generate a secure secret:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_CHAT` | `10/minute` | Chat endpoint rate limit |
| `RATE_LIMIT_ASSESS` | `3/minute` | Assessment endpoint rate limit |
| `RATE_LIMIT_BENCHMARK` | `5/minute` | Benchmark endpoint rate limit |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_TIMEOUT` | `300` | LocalAI/Ollama request timeout (seconds) |
| `CLOUD_TIMEOUT` | `60` | Cloud API request timeout (seconds) |
| `MAX_CONCURRENT_REQUESTS` | `3` | Semaphore limit for concurrent LLM requests |

---

## 5. Production Deployment

Production uses [`docker-compose.prod.yml`](docker-compose.prod.yml) which overrides the base configuration:

### Key Differences from Development

| Aspect | Development | Production |
|--------|-------------|------------|
| Nginx | Not included | [`cyberai-nginx`](docker-compose.prod.yml:12) with TLS |
| Volumes | Bind mounts (hot reload) | Named volume `cyberai-data` |
| Backend | Single uvicorn worker | [`WORKERS=2`](docker-compose.prod.yml:50) |
| Frontend | `Dockerfile.dev` (dev server) | `Dockerfile` (production build, standalone) |
| LocalAI image | `localai/localai:v2.24.2` | `localai/localai:latest` |
| LocalAI memory | 12 GB / 4 GB reserved | 16 GB / 8 GB reserved |
| Frontend memory | 2 GB | 1 GB |
| Backend memory | 6 GB / 2 GB reserved | 4 GB / 1 GB reserved |
| DEBUG | `true` | `false` |
| LOG_LEVEL | `INFO` | `WARNING` |
| Container prefix | `phobert-*` | `cyberai-*` |
| Network | `phobert-network` | `cyberai-network` |

### Deploy Command

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### SSL Certificates

Place TLS certificates in [`nginx/certs/`](nginx/nginx.conf:82):

```
nginx/certs/
├── fullchain.pem    # Certificate chain
└── privkey.pem      # Private key
```

The [Nginx configuration](nginx/nginx.conf) includes:
- **TLS hardening:** TLSv1.2 + TLSv1.3 only, modern cipher suites, OCSP stapling
- **Rate limiting:** 30 req/s per IP on `/api/` (burst 20), 100 req/s global (burst 50)
- **Security headers:** HSTS, CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff
- **WebSocket support:** Connection upgrade headers for SSE streaming
- **Hidden file denial:** Blocks access to `.env`, `.git`, etc.
- **Let's Encrypt:** ACME challenge support at `/.well-known/acme-challenge/`
- **Gzip compression:** Enabled for text, JSON, CSS, JS, SVG

---

## 6. Health Checks

| Service | Endpoint | Method | Expected Response | Notes |
|---------|----------|--------|-------------------|-------|
| Backend | `GET /health` | HTTP | `{"status": "healthy"}` | 30s interval, 30s start\_period |
| LocalAI | `GET /readyz` | HTTP | 200 OK | 30s interval, **120s start\_period** (model loading) |
| Ollama | `GET /api/tags` | HTTP | 200 OK with model list | 30s interval, 60s start\_period |
| AI Status | `GET /api/system/ai-status` | HTTP | JSON with model status | Comprehensive LLM health (LocalAI + Ollama + Cloud) |

### Checking Health Manually

```bash
# Backend
curl -f http://localhost:8000/health

# LocalAI
curl -f http://localhost:8080/readyz

# Ollama
curl -sf http://localhost:11434/api/tags

# Full AI status
curl http://localhost:8000/api/system/ai-status
```

---

## 7. Data Persistence

### Development (Bind Mounts)

In development, [`docker-compose.yml`](docker-compose.yml:33) mounts host directories directly into the backend container for live editing:

```yaml
volumes:
  - ./backend:/app                          # Source code (hot reload)
  - ./data/iso_documents:/data/iso_documents
  - ./data/vector_store:/data/vector_store
  - ./data/assessments:/data/assessments
  - ./data/evidence:/data/evidence
  - ./data/exports:/data/exports
  - ./data/sessions:/data/sessions
  - ./data/standards:/data/standards
  - ./data/knowledge_base:/data/knowledge_base
  - ./data/uploads:/data/uploads
```

Frontend source is also bind-mounted for hot reload via `WATCHPACK_POLLING=true`.

### Production (Named Volumes)

In production, [`docker-compose.prod.yml`](docker-compose.prod.yml:54) uses a single named volume:

```yaml
volumes:
  - cyberai-data:/data    # All persistent data
```

Ollama model storage uses a separate named volume in both environments:

```yaml
volumes:
  - ollama_data:/root/.ollama
```

---

## 8. Backup & Restore

The platform includes a production backup script at [`scripts/backup.sh`](scripts/backup.sh):

```bash
# Default: backs up to ./backups/ with 30-day retention
./scripts/backup.sh

# Custom destination and retention
./scripts/backup.sh --dest /backup/path --retention-days 30
```

### What Gets Backed Up

| Component | Source Path | Content |
|-----------|------------|---------|
| Assessments | `data/assessments/` | Assessment JSON records |
| Sessions | `data/sessions/` | Chat session history (JSON) |
| Knowledge Base | `data/knowledge_base/` | Benchmark + controls data |
| Vector Store | `data/vector_store/` | ChromaDB persistent index |

### Backup Output

- Creates a timestamped `tar.gz` archive (e.g., `cyberai_backup_20260405_143700.tar.gz`)
- Includes a `manifest.json` with schema version, timestamp, and component list
- Automatically cleans up archives older than the retention period

### Restore

```bash
# Extract archive
tar -xzf cyberai_backup_20260405_143700.tar.gz

# Copy data back to project
cp -r cyberai_backup_20260405_143700/assessments/ data/assessments/
cp -r cyberai_backup_20260405_143700/sessions/ data/sessions/
cp -r cyberai_backup_20260405_143700/knowledge_base/ data/knowledge_base/
cp -r cyberai_backup_20260405_143700/vector_store/ data/vector_store/

# Restart backend to pick up restored data
docker compose restart backend
```

---

## 9. Troubleshooting

### LocalAI Slow Start

**Symptom:** Backend returns "LocalAI connection error" for the first ~2 minutes.

**Cause:** LocalAI loads GGUF models into memory at startup. The health check has a 120-second `start_period` to accommodate this.

**Fix:** Wait for the health check to pass:
```bash
docker compose ps   # Check health status column
docker logs phobert-localai --tail 20   # Watch model loading progress
```

### Model Not Found

**Symptom:** `"could not load model"` or `"rpc error"` in logs.

**Fix:**
1. Verify GGUF files exist in `models/llm/weights/`:
   ```bash
   ls -la models/llm/weights/*.gguf
   ```
2. Re-download if missing:
   ```bash
   python scripts/download_models.py --model llama --model security
   ```
3. Verify `MODEL_NAME` and `SECURITY_MODEL_NAME` in `.env` match the filenames.

### Out of Memory (OOM)

**Symptom:** Container killed by Docker or `Canceled` errors in logs.

**Fix:**
- Ensure the host has sufficient RAM (16 GB minimum).
- Only use 8B-parameter models with the default 12 GB LocalAI memory limit.
- Do **not** set `MODEL_NAME` to a 70B model — it requires ~40 GB RAM.
- Reduce `CONTEXT_SIZE` from 8192 to 4096 if RAM is tight.

### CORS Errors

**Symptom:** Browser console shows `Access-Control-Allow-Origin` errors.

**Fix:** Set `CORS_ORIGINS` in `.env` to include your frontend URL:
```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Cloud API Key Issues

**Symptom:** `"[OpenClaude] No API key configured"` or all keys rate-limited.

**Fix:**
1. Set `CLOUD_API_KEYS` in `.env` with one or more valid keys (comma-separated).
2. If all keys are in cooldown (429 rate limit), wait 30 seconds or add more keys.
3. Check key validity at `https://open-claude.com`.
4. If cloud is not needed, set `LOCAL_ONLY_MODE=true`.

### Ollama Model Not Pulling

**Symptom:** Ollama container is running but `gemma3n:e4b` is not available.

**Fix:**
```bash
# Check Ollama logs
docker logs phobert-ollama --tail 30

# Manually pull the model
docker exec phobert-ollama ollama pull gemma3n:e4b

# Verify
curl http://localhost:11434/api/tags
```

---

## 10. Scaling Considerations

### Uvicorn Workers

Production uses [`WORKERS=2`](docker-compose.prod.yml:50) (set in the backend environment). Increase for higher throughput on multi-core machines:

```yaml
environment:
  - WORKERS=4
```

> **Caveat:** Each worker loads its own in-memory VectorStore and SessionStore. File-based session storage ensures consistency across workers.

### Concurrent Request Semaphore

[`MAX_CONCURRENT_REQUESTS=3`](.env.example:51) limits simultaneous LLM inference calls to prevent memory exhaustion. Increase only if the host has sufficient RAM:

```bash
MAX_CONCURRENT_REQUESTS=5
```

### Memory Allocation per Container

Tune memory limits in [`docker-compose.yml`](docker-compose.yml) based on available host RAM:

| Container | Dev Default | Light (16 GB host) | Full (64 GB host) |
|-----------|-------------|--------------------|--------------------|
| Backend | 6 GB | 4 GB | 8 GB |
| Frontend | 2 GB | 1 GB | 2 GB |
| LocalAI | 12 GB | 8 GB* | 24 GB |
| Ollama | 12 GB | 8 GB | 16 GB |

\* With 8 GB, only load one model at a time (set `PARALLEL_REQUESTS=false`).

### Horizontal Scaling

The current architecture is designed for single-node deployment. For horizontal scaling:
- **Backend:** Stateless except for file-based sessions. Move sessions to Redis for multi-node.
- **ChromaDB:** Currently uses `PersistentClient` (local disk). Migrate to ChromaDB server mode for shared access.
- **LocalAI/Ollama:** Each instance loads models into RAM. Use a dedicated inference node.
