---
name: docker
description: Guide Docker container management, compose patterns, volume strategy, and health checks for the CyberAI platform.
---

Use this skill for Dockerfile authoring, compose configuration, volume management, health check design, container networking, and resource limits.

Primary intent:
- Ensure consistent, secure, production-ready container architecture for the CyberAI platform.
- Standardize compose patterns across dev and prod environments.

Reference direction:
- Dev compose: `docker-compose.yml`
- Prod compose: `docker-compose.prod.yml`
- Backend Dockerfile: `backend/Dockerfile`
- Frontend Dockerfiles: `frontend-next/Dockerfile` (prod), `frontend-next/Dockerfile.dev` (dev)
- Nginx config: `nginx/nginx.conf`
- Model configs: `models/llm/*.yaml`

Container architecture:
- backend: FastAPI on :8000
- frontend: Next.js on :3000
- localai: v2.24.2 on :8080
- ollama: latest on :11434
- nginx (prod only): alpine on :80, :443

Networks:
- Dev: `phobert-network`
- Prod: `cyberai-network`

Compose patterns:
- Dev: bind mounts for hot reload, `Dockerfile.dev` for frontend.
- Prod: named volumes (`cyberai-data`), multi-stage builds, no source mounts.
- Always use `docker compose` (v2), never `docker-compose` (v1).

Volume strategy:
- Dev bind mounts: `./backend:/app`, `./data/*:/data/*` (10 subdirectories).
- Prod named volume: `cyberai-data:/data`.
- Ollama model storage: `ollama_data:/root/.ollama` (named volume, both envs).
- Model files: `./models:/build/models` (prod).

Health checks:
- backend: `curl -f http://localhost:8000/health` interval 30s
- localai: `curl -f http://localhost:8080/readyz` interval 30s, start_period 120s (model loading)
- ollama: `curl -sf http://localhost:11434/api/tags` interval 30s

Memory limits:
- backend: 6GB limit, 2GB reservation
- frontend: 2GB limit (dev), 1GB limit (prod)
- localai: 12GB limit / 4GB reserved (dev), 16GB limit / 8GB reserved (prod)
- ollama: 12GB limit, 2GB reservation

Dockerfile patterns:
- Backend: `python:3.10-slim`, install curl for health checks, `pip install -r requirements.txt`, uvicorn with 2 workers.
- Frontend: multi-stage `node:20-alpine` — deps stage → build stage → runner stage. Non-root user, standalone output mode.

Rules:
- Never run containers as root in production.
- Always set memory limits and reservations.
- Always define health checks with appropriate start_period for slow-starting services.
- Use `.dockerignore` to exclude: node_modules, __pycache__, .git, .env.
- Ollama entrypoint must auto-pull models: `ollama serve & sleep 5 && ollama pull gemma3n:e4b; wait`.
- Validate compose config in CI: `docker compose config --quiet` for both files.

Code quality policy:
- No verbose comments in Dockerfiles or compose files.
- No banner decorations.
- Only comment non-obvious build constraints or security-sensitive directives.
