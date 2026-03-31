"""CyberAI Assessment API v2.0 — FastAPI with CORS, rate limiting, and custom error handlers."""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    _has_rate_limit = True
except ImportError:
    limiter = None
    _has_rate_limit = False
    logger.warning("slowapi not installed — rate limiting disabled")

app = FastAPI(
    title=settings.APP_NAME,
    description=f"AI-powered ISO 27001 compliance chatbot with {settings.CLOUD_MODEL_NAME} via Open Claude",
    version=settings.APP_VERSION,
    docs_url="/docs", redoc_url="/redoc",
)

if _has_rate_limit:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={
        "error": "Not found", "detail": str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(status_code=500, content={
        "error": "Internal server error", "detail": "Đã xảy ra lỗi hệ thống. Vui lòng thử lại."})


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Allow larger uploads for documents, standards, and evidence files
    exempt_prefixes = ["/api/documents/upload", "/api/standards/upload", "/api/standards/validate", "/api/iso27001/evidence/"]
    if not any(request.url.path.startswith(p) for p in exempt_prefixes):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"error": "Request body too large", "max_size": "2MB"})
    return await call_next(request)


from api.routes import chat, document, health, iso27001, system, standards, benchmark

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(document.router, prefix="/api", tags=["Documents"])
app.include_router(iso27001.router, prefix="/api", tags=["ISO27001"])
app.include_router(standards.router, prefix="/api", tags=["Standards"])
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(benchmark.router, prefix="/api", tags=["Benchmark"])


# ── Dataset generation endpoint ────────────────────────
from fastapi import BackgroundTasks as _BT

@app.post("/api/dataset/generate", tags=["Dataset"])
async def generate_dataset(background_tasks: _BT, synthetic_count: int = 10):
    """Trigger fine-tuning dataset generation in background.
    Sources: completed assessments + synthetic Cloud AI pairs.
    Produces /data/knowledge_base/finetune_iso27001.jsonl (Alpaca format).
    """
    def _run():
        from services.dataset_generator import run_full_pipeline
        run_full_pipeline(synthetic_count=synthetic_count)

    background_tasks.add_task(_run)
    return {"status": "accepted", "message": f"Dataset generation started (synthetic={synthetic_count})"}


@app.get("/api/dataset/status", tags=["Dataset"])
async def dataset_status():
    """Check generated dataset status."""
    import os, json
    meta_path = os.path.join(os.getenv("DATA_PATH", "./data"), "knowledge_base", "finetune_metadata.json")
    jsonl_path = os.path.join(os.getenv("DATA_PATH", "./data"), "knowledge_base", "finetune_iso27001.jsonl")
    if not os.path.exists(meta_path):
        return {"status": "not_generated", "message": "Run POST /api/dataset/generate first"}
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    size_kb = round(os.path.getsize(jsonl_path) / 1024, 1) if os.path.exists(jsonl_path) else 0
    meta["file_size_kb"] = size_kb
    return {"status": "ready", **meta}


@app.on_event("startup")
def on_startup():
    for w in settings.validate():
        logger.warning(w)

    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"   Cloud LLM: {settings.CLOUD_LLM_API_URL} (model: {settings.CLOUD_MODEL_NAME})")
    logger.info(f"   Cloud API keys: {len(settings.cloud_api_key_list)}")
    logger.info(f"   LocalAI: {settings.LOCALAI_URL}")
    logger.info(f"   CORS origins: {settings.cors_origins_list}")
    logger.info(f"   PREFER_LOCAL: {settings.PREFER_LOCAL}")

    from services.model_guard import ModelGuard
    ModelGuard.refresh()

    try:
        from repositories.session_store import SessionStore
        cleaned = SessionStore().cleanup_expired()
        if cleaned:
            logger.info(f"Cleaned {cleaned} expired sessions on startup")
    except Exception as e:
        logger.warning(f"Session cleanup error: {e}")


@app.get("/")
def root():
    return {
        "status": "running", "service": settings.APP_NAME, "version": settings.APP_VERSION,
        "ai_model": settings.CLOUD_MODEL_NAME, "ai_provider": f"Open Claude ({settings.CLOUD_MODEL_NAME})",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
