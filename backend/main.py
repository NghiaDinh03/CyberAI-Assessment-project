from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat, document, health, iso27001, system, news

app = FastAPI(
    title="PhoBERT ISO27001 API",
    description="AI-powered ISO 27001 compliance chatbot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(document.router, prefix="/api", tags=["Documents"])
app.include_router(iso27001.router, prefix="/api", tags=["ISO27001"])
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(news.router, prefix="/api", tags=["News"])


@app.on_event("startup")
def on_startup():
    from services.news_service import start_bg_worker
    start_bg_worker()

@app.get("/")
def root():
    return {
        "status": "running",
        "service": "PhoBERT ISO27001 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
