# Deployment Guide

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Deployment-blue?style=flat-square)](deployment.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Triển_khai-red?style=flat-square)](deployment_vi.md)

</div>

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Variables](#2-environment-variables)
3. [Quick Start (Docker Compose)](#3-quick-start-docker-compose)
4. [Docker Compose Reference](#4-docker-compose-reference)
5. [Backend Dockerfile](#5-backend-dockerfile)
6. [Frontend Dockerfile](#6-frontend-dockerfile)
7. [Data Directory Setup](#7-data-directory-setup)
8. [LocalAI Setup (Optional)](#8-localai-setup-optional)
9. [Production Checklist](#9-production-checklist)
10. [Common Issues](#10-common-issues)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | ≥ 24.0 | Required |
| Docker Compose | ≥ 2.20 | Required (v2 syntax) |
| Open Claude API key(s) | — | Primary AI provider |
| LocalAI (optional) | — | Fallback AI, self-hosted |
| Disk space | ≥ 5 GB | For audio cache + models |
| RAM | ≥ 4 GB | 8 GB recommended |

**No Python or Node.js installation required** — everything runs inside Docker containers.

---

## 2. Environment Variables

Create a `.env` file in the project root:

```bash
# ── Open Claude (Primary AI) ─────────────────────────────────
# Comma-separated for round-robin key rotation
OPEN_CLAUDE_API_KEY=sk-xxx1,sk-xxx2,sk-xxx3
OPEN_CLAUDE_API_BASE=https://api.openai.com/v1   # or compatible endpoint

# ── LocalAI (Fallback AI) ────────────────────────────────────
LOCAL_AI_BASE_URL=http://localai:8080             # internal Docker DNS
LOCAL_AI_MODEL=llama3                             # model name served by LocalAI

# ── Backend ──────────────────────────────────────────────────
BACKEND_URL=http://backend:8000                   # used by Next.js proxy
LOG_LEVEL=INFO

# ── Frontend ─────────────────────────────────────────────────
NEXT_PUBLIC_APP_NAME=CyberAI Platform
```

### Key rotation

Supply multiple API keys as a comma-separated list. The backend uses round-robin rotation:

```
OPEN_CLAUDE_API_KEY=key1,key2,key3
# Request 1 → key1
# Request 2 → key2
# Request 3 → key3
# Request 4 → key1 (wraps around)
```

---

## 3. Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/phobert-chatbot-project.git
cd phobert-chatbot-project

# 2. Create environment file
cp .env.example .env
# Edit .env — fill in OPEN_CLAUDE_API_KEY at minimum

# 3. Create required data directories
mkdir -p data/sessions data/summaries/audio data/assessments \
         data/vector_store data/translations data/uploads

# 4. Build and start all services
docker compose up --build -d

# 5. Verify services are running
docker compose ps

# 6. Check logs
docker compose logs -f backend
docker compose logs -f frontend
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

---

## 4. Docker Compose Reference

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPEN_CLAUDE_API_KEY=${OPEN_CLAUDE_API_KEY}
      - OPEN_CLAUDE_API_BASE=${OPEN_CLAUDE_API_BASE}
      - LOCAL_AI_BASE_URL=${LOCAL_AI_BASE_URL}
      - LOCAL_AI_MODEL=${LOCAL_AI_MODEL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/data                  # persistent data
      - /proc:/host/proc:ro           # host system stats (read-only)
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend-next
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
      - NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME:-CyberAI Platform}
    depends_on:
      - backend
    restart: unless-stopped
```

---

## 5. Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for audio generation and web scraping
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories
RUN mkdir -p /data/sessions /data/summaries/audio \
    /data/assessments /data/vector_store \
    /data/translations /data/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### Key Python Dependencies

```
# requirements.txt (key packages)
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.0

chromadb>=0.4.22           # vector store
sentence-transformers       # embeddings

requests>=2.31
beautifulsoup4>=4.12
trafilatura>=1.8
newspaper3k>=0.2            # article scraping

edge-tts>=6.1               # Microsoft Neural TTS

duckduckgo-search>=5.0      # web search (ddgs)

httpx>=0.26
python-dotenv>=1.0
```

---

## 6. Frontend Dockerfile

```dockerfile
# frontend-next/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

### Development Mode

For hot-reload during development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

```yaml
# docker-compose.dev.yml (override)
services:
  frontend:
    build:
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend-next:/app
      - /app/node_modules
      - /app/.next
    environment:
      - WATCHPACK_POLLING=true
```

---

## 7. Data Directory Setup

All persistent data lives under `./data/` on the host, mounted into the backend container at `/data/`:

```
data/
├── iso_documents/          ← ISO knowledge base markdown files (ship with repo)
│   ├── iso27001_annex_a.md
│   ├── assessment_criteria.md
│   └── ...
├── knowledge_base/         ← Structured JSON knowledge (ship with repo)
│   ├── controls.json
│   ├── iso27001.json
│   └── tcvn14423.json
├── vector_store/           ← ChromaDB index (auto-created on startup)
│   ├── chroma.sqlite3
│   └── {uuid}/
├── sessions/               ← Chat session files (auto-created)
├── summaries/              ← Article summary JSON cache (auto-created)
│   └── audio/              ← MP3 audio files (auto-created)
├── assessments/            ← ISO assessment JSON files (auto-created)
├── translations/           ← Title translation cache (auto-created)
├── articles_history.json   ← News article history (auto-created)
└── uploads/                ← File uploads placeholder
```

### Backup Important Directories

```bash
# Backup all user data (assessments, cache, vector store)
tar czf backup-$(date +%Y%m%d).tar.gz data/

# Restore
tar xzf backup-20250324.tar.gz
```

---

## 8. LocalAI Setup (Optional)

LocalAI is the **fallback AI** when Open Claude is unavailable. It's self-hosted and serves any GGUF/GGML model with an OpenAI-compatible API.

### Add to docker-compose.yml

```yaml
services:
  localai:
    image: localai/localai:latest-aio-cpu
    ports:
      - "8080:8080"
    volumes:
      - ./localai-models:/models
    environment:
      - MODELS_PATH=/models
    restart: unless-stopped
```

### Download a Model

```bash
# Example: LLaMA-3 8B Q4
mkdir -p localai-models
cd localai-models
wget https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
```

### Create Model Config

```yaml
# localai-models/llama3.yaml
name: llama3
parameters:
  model: Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
  context_size: 8192
template:
  chat: llama3-instruct
```

### Configure Backend

```bash
LOCAL_AI_BASE_URL=http://localai:8080
LOCAL_AI_MODEL=llama3
```

---

## 9. Production Checklist

### Security

- [ ] Set `OPEN_CLAUDE_API_KEY` from environment secrets (not committed to git)
- [ ] Configure CORS in `backend/main.py` to restrict allowed origins:
  ```python
  app.add_middleware(CORSMiddleware, allow_origins=["https://yourdomain.com"])
  ```
- [ ] Add HTTPS via reverse proxy (Nginx/Caddy/Traefik)
- [ ] Set `LOG_LEVEL=WARNING` in production
- [ ] Restrict `/proc` mount to read-only (already configured in compose)

### Reverse Proxy (Nginx example)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_read_timeout 120s;        # long for AI generation
        proxy_set_header Host $host;
    }
}
```

### Performance

- [ ] Set `--workers 2` for Uvicorn if CPU-bound (note: ChromaDB is not fork-safe — use `--workers 1` with async)
- [ ] Pre-warm ChromaDB on startup (auto-handled by `ensure_indexed()`)
- [ ] Monitor disk usage — audio files accumulate (~1.5–2 MB per article)

### Monitoring

```bash
# Health check
curl http://localhost:8000/

# System stats
curl http://localhost:8000/api/system/stats

# AI service health
curl http://localhost:8000/api/system/cache-stats
```

---

## 10. Common Issues

### Backend won't start — missing API key

```
ValueError: OPEN_CLAUDE_API_KEY is not set
```

**Fix:** Set the environment variable in `.env` or Docker Compose environment section.

### ChromaDB index not found / empty results

```bash
# Re-index via API
curl -X POST http://localhost:8000/api/iso27001/reindex
```

### Audio files not playing

Check if the audio directory is accessible and MP3 was generated:

```bash
docker exec <backend> ls /data/summaries/audio/
curl http://localhost:8000/api/news/audio/<hash>.mp3 -I
```

### `/host/proc` stats showing zeros

The `/proc:/host/proc:ro` volume mount is missing or the host doesn't support it.

```bash
# Verify mount
docker exec <backend> ls /host/proc/stat
```

### Edge-TTS timeout / connection error

Edge-TTS requires internet access to Microsoft's TTS servers. Verify:

```bash
docker exec <backend> curl -I https://speech.microsoft.com
```

### DuckDuckGo search returns empty

DuckDuckGo rate-limits aggressive scrapers. The service retries 2 times with a 1s delay. If persistent:

```bash
# Check from inside container
docker exec <backend> python3 -c "
from duckduckgo_search import DDGS
with DDGS() as d:
    print(list(d.text('test', max_results=1)))
"
```

### Frontend can't reach backend

Verify the `BACKEND_URL` env var is set to the internal Docker DNS name:

```bash
# Should be http://backend:8000 (not localhost!)
docker exec <frontend> env | grep BACKEND_URL
```
