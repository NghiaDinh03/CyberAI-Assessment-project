---
name: deployment
description: Guide production deployment, nginx configuration, SSL setup, and scaling strategy for the CyberAI platform.
---

Use this skill for production deployment, nginx reverse proxy configuration, SSL/TLS setup, scaling decisions, pre-deployment checks, backup strategy, and model provisioning.

Primary intent:
- Enforce secure production deployment with proper nginx hardening, SSL, and health verification.
- Standardize scaling patterns, backup procedures, and pre-deployment checklists.

Reference direction:
- Prod compose: `docker-compose.prod.yml`
- Dev compose: `docker-compose.yml`
- Nginx config: `nginx/nginx.conf`
- Backup script: `scripts/backup.sh`
- Model download: `scripts/download_models.py`
- Config: `backend/core/config.py`
- Model guard: `backend/services/model_guard.py`

## Production compose

- `docker-compose.prod.yml` overlays `docker-compose.yml`.
- Adds `nginx:alpine` container (`:80`, `:443`).
- Uses named volumes instead of bind mounts.
- No source code mounts (pre-built images).
- Uvicorn with 2 workers.
- Higher memory limits for LocalAI (16GB limit, 8GB reserved).
- Network: `cyberai-network`.

Deploy command:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Nginx configuration

- HTTP → HTTPS redirect with ACME challenge support.
- TLS 1.2/1.3 with strong cipher suites.
- Security headers: HSTS, CSP, X-Frame-Options DENY, X-XSS-Protection, Referrer-Policy.
- Rate limiting: `/api/` 30 req/s burst 20; global 100 req/s burst 50.
- Proxy: `/api/` → `backend:8000`, `/_next/static/` → cached 365d, `/` → `frontend:3000`.
- WebSocket upgrade for SSE streaming.
- Client max body: 50MB.
- Hidden files denied (`.env`, `.git`).
- SSL certs: `nginx/certs/` directory.

## SSL setup

- Place `cert.pem` and `key.pem` in `nginx/certs/`.
- For Let's Encrypt: use certbot with ACME challenge path (`/.well-known/acme-challenge/`).
- Nginx config supports both self-signed and CA-signed certs.

## Scaling strategy

- Uvicorn workers: increase for CPU-bound tasks (default 2).
- `MAX_CONCURRENT_REQUESTS` semaphore: controls parallel inference (default 3).
- Horizontal: run multiple backend instances behind nginx load balancer.
- LocalAI: single instance per host (GPU-bound), scale by adding hosts.
- Ollama: single instance per host, scale similarly.
- ChromaDB: embedded (not clustered) — scale by data partitioning.

## Pre-deployment checklist

- Set `DEBUG=false`.
- Set strong `JWT_SECRET` (min 32 chars).
- Set specific `CORS_ORIGINS` (no wildcards).
- Configure `CLOUD_API_KEYS` (valid keys, not placeholders).
- Set `LOG_LEVEL=WARNING` or `INFO`.
- Verify model files exist (ModelGuard check).
- Run backup before deployment.
- Test with `docker compose config --quiet`.

## Backup strategy

- Script: `scripts/backup.sh --dest /backup/path --retention-days 30`.
- Components: assessments, sessions, knowledge_base, vector_store.
- Schedule: daily cron job recommended.
- Restore: extract `tar.gz` to `/data` directory, restart containers.

## Model download for production

- Pre-download GGUF files to `models/llm/weights/`.
- Mount as `./models:/build/models` in prod compose.
- Ollama models auto-pulled on startup.
- Script: `python scripts/download_models.py --model llama --model security`.

## Rules

- Never deploy with `DEBUG=true`.
- Never use default `JWT_SECRET` in production.
- Always run `docker compose config --quiet` before deploying.
- Always backup data before deployments.
- Always verify health checks pass after deployment.
- Use named volumes in production (not bind mounts).
- Keep nginx rate limits in sync with backend rate limits.
- Monitor disk space for model files + vector store growth.

Code quality policy:
- No verbose comments or tutorial-style explanations.
- No banner decorations.
- Only comment non-obvious architectural constraints or performance-sensitive logic.
