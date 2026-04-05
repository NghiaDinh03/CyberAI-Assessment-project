---
name: backend
description: Guide FastAPI backend development patterns, service layer architecture, error handling, and logging for the CyberAI platform.
---

Use this skill for route creation, service implementation, schema design, middleware configuration, error handling, logging, and backend architecture decisions.

Primary intent:
- Enforce clean layered architecture with clear dependency flow across routes, services, and repositories.
- Standardize error handling, logging, and configuration patterns for production reliability.

Reference direction:
- Routes: `backend/api/routes/`
- Schemas: `backend/api/schemas/`
- Services: `backend/services/`
- Repositories: `backend/repositories/`
- Config: `backend/core/config.py`
- Exceptions: `backend/core/exceptions.py`
- Rate limiter: `backend/core/limiter.py`
- Logger: `backend/utils/logger.py`
- Entrypoint: `backend/main.py`

## Framework

- FastAPI 0.115+ with Pydantic v2.
- Python 3.10 (Docker) / 3.11 (CI).
- Uvicorn with 2 workers (production).

## Architecture layers

1. **Routes** (`api/routes/`) — HTTP handlers, request validation, response formatting.
2. **Schemas** (`api/schemas/`) — Pydantic models for request/response.
3. **Services** (`services/`) — business logic, external API calls, AI inference.
4. **Repositories** (`repositories/`) — data persistence (ChromaDB, file-based sessions).
5. **Core** (`core/`) — config, exceptions, rate limiter.
6. **Utils** (`utils/`) — helpers, logger.

## Service patterns

- Singleton pattern: VectorStore and SessionStore initialized once (thread-safe lazy init in ChatService).
- Dependency injection: pass services via function params, not global imports where possible.
- Async: use `async def` for routes, `httpx.AsyncClient` for external calls.
- Background tasks: use FastAPI `BackgroundTasks` for long-running operations (assessment, dataset generation).
- Semaphore: `MAX_CONCURRENT_REQUESTS` limits parallel inference calls.

## Error handling

- Custom `AppException` in `core/exceptions.py` with `status_code` and `detail`.
- All routes should catch service exceptions and return appropriate HTTP status.
- Never expose stack traces to clients — log server-side, return sanitized error + `request_id`.
- 404 handler returns JSON (not HTML).
- Request ID: `X-Request-ID` header propagation/generation for distributed tracing.

## Logging

- Use `utils/logger.py` — structured logging with `request_id` context.
- Log levels: ERROR for failures, WARNING for degraded service, INFO for request flow, DEBUG for inference details.
- `LOG_LEVEL` env var (default INFO).
- Never log sensitive data (API keys, JWT tokens, user PII).

## Configuration

- `core/config.py` — Pydantic Settings class with env var binding.
- Validation: `validate()` method checks JWT secret strength, CORS config, API keys.
- Properties: `cors_origins_list`, `cloud_api_key_list` parse comma-separated env vars.

## Middleware stack (order matters — applied bottom-up)

1. Request body size guard (2MB).
2. Request ID.
3. Prometheus metrics.
4. CORS.
5. Rate limiting (slowapi).

## API versioning

- Mount routes at both `/api/v1/...` and `/api/...` for backward compatibility.
- All route modules registered in `api/routes/__init__.py`.

## Rules

- Every route must have Pydantic schema for request/response validation.
- Services must not import from routes (dependency flows: routes → services → repositories).
- All external HTTP calls must use timeouts (`INFERENCE_TIMEOUT=300`, `CLOUD_TIMEOUT=60`).
- Background tasks must handle their own exceptions (don't crash the worker).
- File I/O operations should use absolute paths from config (`DATA_PATH`, `ISO_DOCS_PATH`, `VECTOR_STORE_PATH`).
- Rate limit annotation required on all public-facing endpoints.

Code quality policy:
- No verbose comments or tutorial-style explanations.
- No banner decorations.
- Only comment non-obvious architectural constraints or performance-sensitive logic.
