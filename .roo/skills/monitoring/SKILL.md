---
name: monitoring
description: Guide Prometheus metrics, health checks, log aggregation, and alerting for the CyberAI platform.
---

Use this skill for metrics instrumentation, health check endpoints, structured logging, system resource monitoring, Docker health checks, and alerting configuration.

Primary intent:
- Enforce consistent observability with Prometheus metrics, structured logging, and health checks across all services.
- Standardize alerting thresholds and monitoring patterns for production reliability.

Reference direction:
- Metrics middleware: `backend/main.py`
- Metrics route: `backend/api/routes/metrics.py`
- Health route: `backend/api/routes/health.py`
- System route: `backend/api/routes/system.py`
- Logger: `backend/utils/logger.py`
- Model guard: `backend/services/model_guard.py`
- Docker compose: `docker-compose.yml`
- Prod compose: `docker-compose.prod.yml`
- Frontend stats: `frontend-next/src/components/SystemStats.js`

## Prometheus metrics

Defined in `backend/main.py` middleware:
- `cyberai_requests_total` — Counter(method, endpoint, status_code).
- `cyberai_request_duration_seconds` — Histogram(endpoint).
- `cyberai_active_sessions` — Gauge.
- `cyberai_rag_queries_total` — Counter(result: hit|miss).
- `cyberai_assessments_total` — Gauge.
- Endpoint: `GET /metrics` (Prometheus text format, mounted at root).

## Health checks

- Backend: `GET /health` → `{"status": "healthy"}`.
- Backend: `GET /api/chat/health` → includes ModelGuard status.
- System: `GET /api/system/ai-status` → LocalAI/Cloud health, mode label.
- System: `GET /api/system/stats` → CPU, memory, disk, uptime (psutil).
- System: `GET /api/system/cache-stats` → session + export directory sizes.
- LocalAI: `GET :8080/readyz` (Docker health check).
- Ollama: `GET :11434/api/tags` (Docker health check).

## Logging

- Structured logging via `utils/logger.py`.
- Request ID propagation (`X-Request-ID`) for distributed tracing.
- Log levels: ERROR (failures), WARNING (degraded), INFO (request flow), DEBUG (inference).
- `LOG_LEVEL` env var (default INFO).
- Never log: API keys, JWT tokens, user PII, full prompt content.

## System monitoring

- `psutil` for CPU, memory, disk usage.
- Endpoint: `GET /api/system/stats` returns real-time metrics.
- Frontend `SystemStats` component polls and displays.

## Docker health checks

- Backend: curl every 30s, timeout 10s, retries 3, start_period 10s.
- LocalAI: curl every 30s, timeout 10s, retries 5, start_period 120s.
- Ollama: curl every 30s, timeout 10s, retries 5, start_period 60s.

## Alerting recommendations

- Alert when LocalAI health check fails for >5 minutes.
- Alert when cloud API fallback rate exceeds 50% (indicates local model issues).
- Alert when assessment processing time exceeds 300s (`INFERENCE_TIMEOUT`).
- Alert when disk usage exceeds 80% (vector store growth).
- Alert when rate limit hits spike (potential abuse).

## Scrape config

Prometheus scrape configuration:
```yaml
scrape_configs:
  - job_name: 'cyberai-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

## Rules

- Every new endpoint must increment request counter and duration histogram.
- Every external service call must have a health check.
- Log `request_id` in all log messages for tracing.
- Never expose `/metrics` to public internet (restrict to internal network).
- Monitor RAG hit/miss ratio — low hit rate indicates knowledge base gaps.
- Set up alerts before going to production.

Code quality policy:
- No verbose comments or tutorial-style explanations.
- No banner decorations.
- Only comment non-obvious architectural constraints or performance-sensitive logic.
