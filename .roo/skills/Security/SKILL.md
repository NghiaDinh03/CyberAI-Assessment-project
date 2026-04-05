---
name: security
description: Guide security practices including JWT auth, CORS, rate limiting, prompt injection defense, and API key management for the CyberAI platform.
---

Use this skill for authentication, authorization, CORS configuration, rate limiting, input validation, prompt injection defense, API key rotation, and production hardening.

Primary intent:
- Enforce defense-in-depth security across the CyberAI platform API, AI inference layer, and production infrastructure.
- Prevent credential leaks, prompt injection, and resource exhaustion.

Reference direction:
- Auth/CORS/rate-limit config: `backend/core/config.py` (Settings class)
- Exception handling: `backend/core/exceptions.py`
- Rate limiter setup: `backend/core/limiter.py`
- Chat service (prompt injection): `backend/services/chat_service.py`
- Cloud LLM key rotation: `backend/services/cloud_llm_service.py`
- Nginx hardening: `nginx/nginx.conf`
- Env template: `.env.example`

JWT authentication:
- Secret via `JWT_SECRET` env var (min 32 chars in production).
- Expiry: `JWT_EXPIRE_MINUTES` (default 60).
- Weak secrets blocked when `DEBUG=false`; warned in dev.
- Validation in `core/config.py` Settings class.

CORS:
- `CORS_ORIGINS` env var (comma-separated).
- `cors_origins_list` property splits and validates origins.
- Never use wildcard `*` in production.
- Default: `http://localhost:3000`.

Rate limiting:
- Library: slowapi, per-endpoint limits.
- Chat: `RATE_LIMIT_CHAT` = 10/minute.
- Assessment: `RATE_LIMIT_ASSESS` = 3/minute.
- Benchmark: `RATE_LIMIT_BENCHMARK` = 5/minute.
- Nginx (prod): 30 req/s burst 20 for `/api/`, 100 req/s burst 50 global.

Prompt injection defense:
- Detection in ChatService before LLM inference.
- Pattern matching for common injection vectors.
- Request body size guard: 2MB default (exempt: upload, validate, evidence endpoints).
- Evidence upload: max 10MB, allowed file types whitelist.

API key management:
- `CLOUD_API_KEYS` env var (comma-separated).
- `cloud_api_key_list` property deduplicates and filters placeholder values.
- Round-robin rotation across keys.
- 30-second cooldown per key on 429 rate limit response.
- Never log API keys; use masked format in debug output.

Request security:
- X-Request-ID propagation/generation (uuid4) for tracing.
- All error responses include request_id (stack traces server-side only).
- AppException → sanitized JSON (no internal details leaked).

Nginx security (production):
- TLS 1.2/1.3 hardening, HSTS.
- CSP headers, X-Frame-Options DENY, X-XSS-Protection, Referrer-Policy.
- Hidden files (.env, .git) denied.
- Client max body: 50MB.
- WebSocket upgrade support for SSE.

Rules:
- Never commit API keys, JWT secrets, or .env files.
- Always validate file uploads (type whitelist + size limit).
- Always sanitize error responses (no stack traces to clients).
- Always use request_id for distributed tracing.
- Rate limit all public-facing endpoints.
- Rotate API keys when any key is compromised.
- Use `MAX_CONCURRENT_REQUESTS` semaphore (default 3) to prevent resource exhaustion.

Code quality policy:
- No verbose security comments that explain the obvious.
- No banner decorations.
- Only comment non-obvious security constraints or threat-model rationale.
