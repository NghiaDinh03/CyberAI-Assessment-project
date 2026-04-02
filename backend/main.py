"""CyberAI Assessment API v2.0 — FastAPI with CORS, rate limiting, and custom error handlers."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.exceptions import AppException

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from core.limiter import limiter, _has_rate_limit
except ImportError:
    limiter = None
    _has_rate_limit = False
    logger.warning("slowapi not installed — rate limiting disabled")


# ── Lifespan: startup + graceful shutdown (Improvement 6) ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ────────────────────────────────────────────────────────────
    logger.info("CyberAI Platform starting up...")

    # Validate settings; emit warnings for any soft issues
    for w in settings.validate():
        logger.warning(w)

    logger.info(f"  App       : {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Cloud LLM : {settings.CLOUD_LLM_API_URL} (model: {settings.CLOUD_MODEL_NAME})")
    logger.info(f"  API keys  : {len(settings.cloud_api_key_list)} configured")
    logger.info(f"  LocalAI   : {settings.LOCALAI_URL}")
    logger.info(f"  CORS      : {settings.cors_origins_list}")
    logger.info(f"  PREFER_LOCAL: {settings.PREFER_LOCAL}")
    logger.info(f"  DEBUG     : {settings.DEBUG}")

    from services.model_guard import ModelGuard
    ModelGuard.refresh()

    try:
        from repositories.session_store import SessionStore
        cleaned = SessionStore().cleanup_expired()
        if cleaned:
            logger.info(f"  Cleaned {cleaned} expired sessions on startup")
    except Exception as exc:
        logger.warning(f"Session cleanup error on startup: {exc}")

    # Hand control to the application
    yield

    # ── SHUTDOWN ───────────────────────────────────────────────────────────
    logger.info("Graceful shutdown initiated...")

    try:
        from repositories.vector_store import VectorStore
        vs = VectorStore()
        # chromadb.PersistentClient does not expose an explicit .close() in all
        # versions; call it only when the method exists to stay version-agnostic.
        client = getattr(vs, "client", None)
        if client is not None:
            if hasattr(client, "close"):
                client.close()
                logger.info("  ChromaDB client closed.")
            elif hasattr(client, "reset"):
                # reset() clears in-memory state without deleting persisted data
                client.reset()
                logger.info("  ChromaDB client reset.")
    except Exception as exc:
        logger.warning(f"  ChromaDB shutdown error (non-fatal): {exc}")

    logger.info("Shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        f"AI-powered ISO 27001 compliance chatbot with "
        f"{settings.CLOUD_MODEL_NAME} via Open Claude"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

if _has_rate_limit:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: Prometheus metrics (Phase 5) ───────────────────────────────
@app.middleware("http")
async def record_metrics(request: Request, call_next):
    """Track request count and duration for every HTTP request.

    Skips the /metrics endpoint itself to avoid self-referential cardinality.
    Uses the raw path (without query string) as the endpoint label to keep
    cardinality bounded even with dynamic path segments.
    """
    path = request.url.path
    start = time.perf_counter()
    response = await call_next(request)
    if path != "/metrics":
        try:
            from api.routes.metrics import REQUEST_COUNT, REQUEST_DURATION
            duration = time.perf_counter() - start
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=path,
                status=str(response.status_code),
            ).inc()
            REQUEST_DURATION.labels(endpoint=path).observe(duration)
        except Exception:
            # Never let metrics instrumentation crash the request
            pass
    return response


# ── Middleware: Request ID (Improvement 1) ─────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Propagate or generate a unique request ID for every HTTP request.

    - Reads ``X-Request-ID`` from the incoming headers (pass-through pattern).
    - Falls back to a fresh ``uuid4`` when the header is absent.
    - Stores the value in ``request.state.request_id`` for use by route
      handlers and exception handlers.
    - Echoes the value back in the ``X-Request-ID`` response header.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Middleware: Request body size guard ────────────────────────────────────
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Allow larger uploads for documents, standards, and evidence files
    exempt_prefixes = [
        "/api/documents/upload",
        "/api/standards/upload",
        "/api/standards/validate",
        "/api/iso27001/evidence/",
        "/api/v1/documents/upload",
        "/api/v1/standards/upload",
        "/api/v1/standards/validate",
        "/api/v1/iso27001/evidence/",
    ]
    if not any(request.url.path.startswith(p) for p in exempt_prefixes):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2 * 1024 * 1024:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "max_size": "2MB",
                    "request_id": request_id,
                },
            )
    return await call_next(request)


# ── Exception handlers: sanitized responses (Improvement 3) ───────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle all first-party AppException subclasses with sanitized output."""
    request_id = getattr(request.state, "request_id", "unknown")
    content: dict = {
        "error": exc.message,
        "status_code": exc.status_code,
        "request_id": request_id,
    }
    # Include structured details only when they are explicitly provided and
    # contain no raw exception data (the caller's responsibility).
    if exc.details is not None:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return sanitized JSON for every FastAPI/Starlette HTTPException."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — never leaks internal details to API consumers.

    Stack traces and raw exception messages are logged server-side only.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception [request_id=%s] %s %s",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Resource not found",
            "request_id": request_id,
        },
    )


# ── Routers (Improvement 2: /api/v1 + legacy /api for backward compat) ─────
from api.routes import chat, document, health, iso27001, system, standards, benchmark  # noqa: E402
from api.routes.metrics import router as metrics_router  # noqa: E402

# Prometheus scrape endpoint — mounted at root so it's at /metrics (not /api/metrics)
app.include_router(metrics_router, prefix="", tags=["Observability"])

# Versioned routes  — /api/v1/…
app.include_router(health.router,     prefix="/api/v1", tags=["Health v1"])
app.include_router(chat.router,       prefix="/api/v1", tags=["Chat v1"])
app.include_router(document.router,   prefix="/api/v1", tags=["Documents v1"])
app.include_router(iso27001.router,   prefix="/api/v1", tags=["ISO27001 v1"])
app.include_router(standards.router,  prefix="/api/v1", tags=["Standards v1"])
app.include_router(system.router,     prefix="/api/v1", tags=["System v1"])
app.include_router(benchmark.router,  prefix="/api/v1", tags=["Benchmark v1"])

# Legacy routes — /api/… (backward compatibility, no deprecation break)
app.include_router(health.router,     prefix="/api", tags=["Health"])
app.include_router(chat.router,       prefix="/api", tags=["Chat"])
app.include_router(document.router,   prefix="/api", tags=["Documents"])
app.include_router(iso27001.router,   prefix="/api", tags=["ISO27001"])
app.include_router(standards.router,  prefix="/api", tags=["Standards"])
app.include_router(system.router,     prefix="/api", tags=["System"])
app.include_router(benchmark.router,  prefix="/api", tags=["Benchmark"])


# ── Dataset generation endpoints ───────────────────────────────────────────
from fastapi import BackgroundTasks as _BT  # noqa: E402


@app.post("/api/v1/dataset/generate", tags=["Dataset v1"])
@app.post("/api/dataset/generate",    tags=["Dataset"])
async def generate_dataset(background_tasks: _BT, synthetic_count: int = 10):
    """Trigger fine-tuning dataset generation in background.

    Sources: completed assessments + synthetic Cloud AI pairs.
    Produces ``/data/knowledge_base/finetune_iso27001.jsonl`` (Alpaca format).
    """
    def _run():
        from services.dataset_generator import run_full_pipeline
        run_full_pipeline(synthetic_count=synthetic_count)

    background_tasks.add_task(_run)
    return {
        "status": "accepted",
        "message": f"Dataset generation started (synthetic={synthetic_count})",
    }


@app.get("/api/v1/dataset/status", tags=["Dataset v1"])
@app.get("/api/dataset/status",    tags=["Dataset"])
async def dataset_status():
    """Check generated dataset status."""
    import os
    import json

    meta_path = os.path.join(
        os.getenv("DATA_PATH", "./data"), "knowledge_base", "finetune_metadata.json"
    )
    jsonl_path = os.path.join(
        os.getenv("DATA_PATH", "./data"), "knowledge_base", "finetune_iso27001.jsonl"
    )
    if not os.path.exists(meta_path):
        return {"status": "not_generated", "message": "Run POST /api/dataset/generate first"}
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    size_kb = round(os.path.getsize(jsonl_path) / 1024, 1) if os.path.exists(jsonl_path) else 0
    meta["file_size_kb"] = size_kb
    return {"status": "ready", **meta}


# ── Root + health shortcuts ────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ai_model": settings.CLOUD_MODEL_NAME,
        "ai_provider": f"Open Claude ({settings.CLOUD_MODEL_NAME})",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}
