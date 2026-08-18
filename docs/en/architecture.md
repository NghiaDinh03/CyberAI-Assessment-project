# CyberAI Assessment Platform — System Architecture

## 1. Overview

The CyberAI Assessment Platform is an AI-powered cybersecurity assessment system built on a **4-container Docker architecture** (5 in production). It provides ISO 27001 compliance chatbot, GAP analysis, automated report generation, and multi-standard assessment through dual local inference engines (LocalAI + Ollama) with cloud LLM fallback.

**Core capabilities:**
- AI-powered chat with RAG (Retrieval-Augmented Generation) over 21+ security knowledge base documents
- Automated GAP analysis and structured assessment reports
- Multi-standard support (ISO 27001, NIST CSF, PCI DSS, GDPR, SOC 2, Vietnamese regulations)
- Hybrid local/cloud inference with intelligent model routing
- Prometheus observability and structured logging

---

## 2. Container Architecture

### System Topology

```mermaid
flowchart LR
    Browser(["🖥️ Browser"])

    subgraph PROD["⚡ Production Only"]
        Nginx["cyberai-nginx\nnginx:alpine\n:80 / :443"]
    end

    subgraph DOCKER["🐳 Docker Network"]
        Frontend["🎨 phobert-frontend\nNext.js 15.1\n:3000"]
        Backend["⚙️ phobert-backend\nFastAPI\n:8000"]
        LocalAI["🧠 phobert-localai\nLocalAI v2.24.2\n:8080"]
        Ollama["🦙 phobert-ollama\nOllama\n:11434"]
    end

    Cloud(["☁️ Cloud LLM\nOpen Claude"])

    Browser -- "HTTPS" --> Nginx
    Browser -- "HTTP dev" --> Frontend
    Nginx -- "proxy_pass" --> Frontend
    Nginx -- "/api/*" --> Backend
    Frontend -- "rewrite /api/*" --> Backend
    Backend -- "OpenAI API" --> LocalAI
    Backend -- "OpenAI API" --> Ollama
    Backend -. "Fallback" .-> Cloud

    style Nginx fill:#f59e0b,stroke:#d97706,color:#000
    style Frontend fill:#3b82f6,stroke:#2563eb,color:#fff
    style Backend fill:#10b981,stroke:#059669,color:#fff
    style LocalAI fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style Ollama fill:#ef4444,stroke:#dc2626,color:#fff
    style Cloud fill:#6366f1,stroke:#4f46e5,color:#fff
    style PROD fill:#fef3c7,stroke:#f59e0b
    style DOCKER fill:#dbeafe,stroke:#93c5fd
```

| Container | Image | Port | Memory Limit | Memory Reserved | Health Check |
|-----------|-------|------|-------------|-----------------|-------------|
| `phobert-backend` | Python 3.10-slim (FastAPI) | 8000 | 6 GB | 2 GB | `curl -f http://localhost:8000/health` every 30s |
| `phobert-frontend` | Node 20-alpine (Next.js 15.1) | 3000 | 2 GB (dev) / 1 GB (prod) | — | none |
| `phobert-localai` | `localai/localai:v2.24.2` | 8080 | 12 GB (dev) / 16 GB (prod) | 4 GB (dev) / 8 GB (prod) | `curl -f http://localhost:8080/readyz` every 30s, start\_period 120s |
| `phobert-ollama` | `ollama/ollama:latest` | 11434 | 12 GB | 2 GB | `curl -sf http://localhost:11434/api/tags` every 30s |
| `cyberai-nginx` *(prod only)* | `nginx:alpine` | 80, 443 | — | — | — |

**Network:**
- Development: [`phobert-network`](docker-compose.yml:156) (bridge driver)
- Production: [`cyberai-network`](docker-compose.prod.yml:129) (bridge driver)

**Volumes:**
- Development: bind mounts for hot reload (`./backend:/app`, `./frontend-next/src:/app/src`, etc.)
- Production: named volume `cyberai-data` for `/data`, `ollama_data` for Ollama model storage

---

## 3. Dual Local Inference Architecture

The platform runs **two independent local inference engines** to maximize model compatibility and avoid single-point-of-failure:

```mermaid
flowchart TB
    BE(["⚙️ phobert-backend\nFastAPI :8000"])

    subgraph LOCAL_AI["🧠 LocalAI :8080"]
        L1["Meta-Llama 3.1 8B\nQ4_K_M · ~4.9 GB\nReport formatting & Chat"]
        L2["SecurityLLM 7B\nQ4_K_M · ~4.2 GB\nGAP Analysis"]
    end

    subgraph OLLAMA["🦙 Ollama :11434"]
        O1["Gemma 3n E4B\nAuto-pull on startup"]
        O2["gemma3:4b / 12b\ngemma4:31b\nManual pull"]
    end

    subgraph CLOUD["☁️ Cloud Fallback — Open Claude"]
        direction TB
        C1["1. gemini-3-flash-preview"] --> C2["2. gemini-3-pro-preview"]
        C2 --> C3["3. gpt-5-mini"]
        C3 --> C4["4. claude-sonnet-4"]
        C4 --> C5["5. gpt-5"]
    end

    BE -- "OpenAI API" --> LOCAL_AI
    BE -- "OpenAI API" --> OLLAMA
    BE -. "Fallback on error" .-> CLOUD

    style BE fill:#10b981,stroke:#059669,color:#fff
    style LOCAL_AI fill:#ede9fe,stroke:#8b5cf6
    style OLLAMA fill:#fee2e2,stroke:#ef4444
    style CLOUD fill:#e0f2fe,stroke:#0ea5e9
```

### LocalAI (port 8080)

OpenAI-compatible API serving GGUF model files from [`models/llm/weights/`](models/llm/weights):

| Model | Quant | Size | Role |
|-------|-------|------|------|
| Meta-Llama 3.1 8B Instruct | Q4\_K\_M | ~4.9 GB | Report formatting, general chat |
| SecurityLLM 7B | Q4\_K\_M | ~4.2 GB | GAP analysis, security audit |

Configuration: [`THREADS`](.env.example:16)=6, [`CONTEXT_SIZE`](.env.example:17)=8192, `PARALLEL_REQUESTS=false`, `MMAP=true`.

### Ollama (port 11434)

OpenAI-compatible API with automatic model pulling on startup:

| Model | Pull Method |
|-------|-------------|
| Gemma 3n E4B | Auto-pulled via [entrypoint](docker-compose.yml:127): `ollama pull gemma3n:e4b` |
| gemma3:4b, gemma3:12b, gemma4:31b | Optional — manually pull or via download script |

The Ollama entrypoint starts `ollama serve`, waits 5 seconds, then pulls `gemma3n:e4b` before entering the ready state.

### Cloud Fallback

Open Claude API gateway at `https://open-claude.com/v1`:

**Fallback chain** (defined in [`FALLBACK_CHAIN`](backend/services/cloud_llm_service.py:22)):
1. `gemini-3-flash-preview`
2. `gemini-3-pro-preview`
3. `gpt-5-mini`
4. `claude-sonnet-4`
5. `gpt-5`

**Key rotation:** Round-robin across comma-separated [`CLOUD_API_KEYS`](.env.example:22) with 30-second cooldown per key on HTTP 429 rate-limit responses.

---

## 4. Model Routing Flow

The [`ModelRouter`](backend/services/model_router.py:173) uses **hybrid intent classification** — semantic first, keyword fallback:

### Step 1: Semantic Classification

ChromaDB in-memory [`intent_classifier`](backend/services/model_router.py:127) collection seeded with bilingual (Vietnamese + English) intent templates. Query returns top-3 nearest neighbors; votes are aggregated by intent with **confidence threshold 0.6**.

### Step 2: Keyword Fallback

If semantic confidence ≤ 0.6, regex matching runs against three keyword lists:
- [`ISO_KEYWORDS`](backend/services/model_router.py:61) — broad ISO/compliance terms (≥1 match → ISO candidate)
- [`ISO_STRICT_KEYWORDS`](backend/services/model_router.py:96) — strict security terms (≥2 matches → strong security signal)
- [`SEARCH_KEYWORDS`](backend/services/model_router.py:81) — real-time search intent markers

### Step 3: Route Decision

| Route | `use_rag` | `use_search` | Model | Trigger |
|-------|-----------|-------------|-------|---------|
| `security` | `true` | `false` | SecurityLLM | Semantic security intent OR ISO strict keyword match |
| `search` | `false` | `true` | General LLM | Semantic search intent OR search keywords present |
| `general` | `false` | `false` | General LLM | Default fallback |

### Inference Priority

Controlled by environment variables in [`CloudLLMService.chat_completion()`](backend/services/cloud_llm_service.py:302):

| Setting | Behavior |
|---------|----------|
| [`PREFER_LOCAL=true`](.env.example:4) | LocalAI/Ollama first → Cloud fallback on failure |
| `PREFER_LOCAL=false` | Cloud first → LocalAI fallback |
| [`LOCAL_ONLY_MODE=true`](backend/core/config.py:53) | No cloud API calls; fails if local models unavailable |

**Ollama detection:** Models starting with any of these prefixes are routed to Ollama instead of LocalAI (defined in [`OLLAMA_MODEL_PREFIXES`](backend/services/cloud_llm_service.py:310)):
`gemma3:`, `gemma3n:`, `gemma4:`, `phi4:`, `llama3:`, `mistral:`, `qwen3:`

Additionally, LocalAI Gemma IDs (`gemma-3-4b-it`, `gemma-3-12b-it`, `gemma-4-31b-it`) are mapped to their Ollama equivalents via [`_LOCALAI_TO_OLLAMA`](backend/services/cloud_llm_service.py:32).

---

## 5. Backend Architecture

### Framework

[FastAPI 0.115+](backend/requirements.txt) with Pydantic v2, async lifespan management, and versioned API routes.

**API versioning:** Dual-mounted routers at `/api/v1/...` (versioned) and `/api/...` (legacy backward-compatible), defined in [`main.py`](backend/main.py:254).

### Middleware Stack

Order matters — outermost middleware executes first:

| # | Middleware | Location | Purpose |
|---|-----------|----------|---------|
| 1 | Request body size guard | [`limit_request_size()`](backend/main.py:159) | 2 MB limit; exempt: upload/validate/evidence endpoints |
| 2 | Request ID | [`add_request_id()`](backend/main.py:141) | Propagates `X-Request-ID` header or generates UUID4 |
| 3 | Prometheus metrics | [`record_metrics()`](backend/main.py:113) | `cyberai_requests_total`, `cyberai_request_duration_seconds` |
| 4 | CORS | [`CORSMiddleware`](backend/main.py:103) | Configurable origins via [`CORS_ORIGINS`](.env.example:33) |
| 5 | Rate limiting | [`slowapi`](backend/core/limiter.py) | Per-endpoint limits (chat: 10/min, assess: 3/min, benchmark: 5/min) |

### Service Layer

| Service | File | Responsibility |
|---------|------|---------------|
| **ChatService** | [`chat_service.py`](backend/services/chat_service.py) | Singleton VectorStore/SessionStore, prompt injection detection, session memory (10 messages for LLM context), SSE streaming |
| **CloudLLMService** | [`cloud_llm_service.py`](backend/services/cloud_llm_service.py) | Round-robin API keys, rate-limit cooldown (30s), model fallback chain, LocalAI/Ollama/Cloud routing |
| **RAGService** | [`rag_service.py`](backend/services/rag_service.py) | Multi-query search, confidence threshold 0.35, Prometheus counter (`hit`/`miss`) |
| **ModelRouter** | [`model_router.py`](backend/services/model_router.py) | Hybrid semantic + keyword intent classification |
| **AssessmentHelpers** | [`assessment_helpers.py`](backend/services/assessment_helpers.py) | Chunked prompts, JSON validation (anti-hallucination), severity normalization |
| **StandardService** | [`standard_service.py`](backend/services/standard_service.py) | JSON/YAML upload, validation (max 500 controls), ChromaDB domain-scoped indexing |
| **WebSearch** | [`web_search.py`](backend/services/web_search.py) | DuckDuckGo via `ddgs`, retry logic, Vietnamese region |
| **ModelGuard** | [`model_guard.py`](backend/services/model_guard.py) | GGUF file presence check at startup |

### Repository Layer

| Repository | File | Responsibility |
|-----------|------|---------------|
| **VectorStore** | [`vector_store.py`](backend/repositories/vector_store.py) | ChromaDB `PersistentClient`, domain-scoped collections, header-aware chunking (600 chars, 150 overlap), cosine similarity |
| **SessionStore** | [`session_store.py`](backend/repositories/session_store.py) | File-based JSON in `/data/sessions/`, TTL 24h (86400s), max 20 messages per session |

---

## 6. Frontend Architecture

- **Framework:** Next.js 15.1 (App Router), React 19, [`standalone`](frontend-next/next.config.js:3) output mode
- **API proxy:** [`next.config.js`](frontend-next/next.config.js:4) rewrites `/api/:path*` → `http://backend:8000/api/:path*`
- **Dev Dockerfile:** [`Dockerfile.dev`](frontend-next/Dockerfile.dev) with `WATCHPACK_POLLING=true` for hot reload

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | [`/`](frontend-next/src/app/page.js) | Platform overview and system status |
| AI Chat | [`/chatbot`](frontend-next/src/app/chatbot/page.js) | RAG-powered cybersecurity chatbot |
| Assessment | [`/form-iso`](frontend-next/src/app/form-iso/page.js) | ISO 27001 GAP analysis form |
| Standards | [`/standards`](frontend-next/src/app/standards/page.js) | Custom standard management |
| Analytics | [`/analytics`](frontend-next/src/app/analytics/page.js) | Assessment analytics and metrics |

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Navbar | [`Navbar.js`](frontend-next/src/components/Navbar.js) | Theme toggle, multi-timezone clock, backend status dot |
| SystemStats | [`SystemStats.js`](frontend-next/src/components/SystemStats.js) | Real-time system metrics display |
| StepProgress | [`StepProgress.js`](frontend-next/src/components/StepProgress.js) | Multi-step form progress indicator |
| Skeleton | [`Skeleton.js`](frontend-next/src/components/Skeleton.js) | Loading placeholder animations |
| ThemeProvider | [`ThemeProvider.js`](frontend-next/src/components/ThemeProvider.js) | Dark/light theme context |
| Toast | [`Toast.js`](frontend-next/src/components/Toast.js) | Notification system |

---

## 7. Data Flow Diagrams

### Chat Request Flow

```mermaid
flowchart TD
    User(["\u{1F464} User Input"])
    User --> FE

    FE["\u{1F3A8} Frontend\nNext.js :3000"]
    FE -- "/api/chat (SSE)" --> BE

    BE["\u2699\uFE0F Backend\nFastAPI :8000"]
    BE --> Router["\u{1F500} ModelRouter\nintent + keyword"]

    subgraph CONTEXT["Context Building"]
        RAG["\u{1F4DA} RAG Service\nChromaDB"]
        WS["\u{1F310} Web Search\nDuckDuckGo"]
        MEM["\u{1F4BE} Session Memory\n10 messages"]
        SEC["\u{1F6E1}\uFE0F Prompt Injection\nDetection"]
    end

    Router --> RAG
    Router --> WS
    Router --> MEM
    Router --> SEC

    RAG & WS & MEM --> LLM

    subgraph LLM["\u2601\uFE0F CloudLLM Service \u2014 Inference Routing"]
        LAI["\u{1F9E0} LocalAI :8080\nGGUF models"]
        OLL["\u{1F999} Ollama :11434\nGemma 3n"]
        CLD["\u2601\uFE0F Open Claude\nCloud Fallback"]
    end

    LLM -- "SSE stream" --> FE

    style User fill:#fbbf24,stroke:#f59e0b,color:#000
    style FE fill:#3b82f6,stroke:#2563eb,color:#fff
    style BE fill:#10b981,stroke:#059669,color:#fff
    style Router fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style CONTEXT fill:#f0fdf4,stroke:#86efac
    style LLM fill:#dbeafe,stroke:#93c5fd
    style CLD fill:#6366f1,stroke:#4f46e5,color:#fff
```

### Assessment Pipeline

```mermaid
flowchart TD
    Submit(["\u{1F4DD} Form Submit\nISO 27001 controls list"])
    Submit --> P1A

    subgraph Phase1["\u{1F50D} Phase 1 \u2014 GAP Analysis"]
        P1A["Chunked prompts"]
        P1B["SecurityLLM 7B\nvia LocalAI :8080"]
        P1C["JSON validation per chunk"]
        P1D["Severity normalization\nCritical / High / Medium / Low"]
        P1E["Anti-hallucination checks"]
        P1A --> P1B --> P1C --> P1D --> P1E
    end

    P1E --> P2A

    subgraph Phase2["\u{1F4CA} Phase 2 \u2014 Report Generation"]
        P2A["Meta-Llama 3.1 8B\nvia LocalAI :8080"]
        P2B["Executive summary"]
        P2C["Recommendations"]
        P2D["Structured JSON output"]
        P2A --> P2B --> P2C --> P2D
    end

    P2D --> O1
    P2D --> O2

    O1["\u{1F4C4} /data/assessments\n{uuid}.json"]
    O2["\u{1F4E6} /data/exports\nPDF / HTML"]

    style Submit fill:#fbbf24,stroke:#f59e0b,color:#000
    style Phase1 fill:#fee2e2,stroke:#fca5a5
    style Phase2 fill:#dbeafe,stroke:#93c5fd
    style O1 fill:#d1fae5,stroke:#6ee7b7
    style O2 fill:#d1fae5,stroke:#6ee7b7
```

### RAG Retrieval Flow

```mermaid
flowchart LR
    Query(["\u{1F50D} User Query"])
    Query --> MQ

    MQ["\u{1F4DD} Multi-Query Expansion\nVectorStore.multi_query_search"]
    MQ --> DB

    DB["\u{1F5C4}\uFE0F ChromaDB\nCosine Similarity\n\u00B7 Domain-scoped collections\n\u00B7 Header-aware chunking\n\u00B7 600 chars / 150 overlap\n\u00B7 Top-K results"]
    DB --> CF

    CF{"\u2696\uFE0F Confidence \u2265 0.35?\nscore = 1 \u2212 distance"}
    CF -- "\u2705 hit" --> CTX
    CF -- "\u274C miss" --> PROM

    CTX["\u{1F4CE} Context Injection\n\u00B7 Source attribution\n\u00B7 Inject into LLM prompt"]
    PROM["\u{1F4CA} Prometheus\ncyberai_rag_queries_total\nlabel: miss"]

    style Query fill:#fbbf24,stroke:#f59e0b,color:#000
    style DB fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style CF fill:#f59e0b,stroke:#d97706,color:#000
    style CTX fill:#10b981,stroke:#059669,color:#fff
    style PROM fill:#6366f1,stroke:#4f46e5,color:#fff
```

---

## 8. Data Storage

| Path | Purpose |
|------|---------|
| `/data/iso_documents/` | 21+ markdown knowledge base files (ISO 27001, NIST, PCI DSS, Vietnamese regulations, etc.) |
| `/data/vector_store/` | ChromaDB persistent storage (cosine similarity index) |
| `/data/assessments/` | Assessment JSON records (`{uuid}.json`) |
| `/data/evidence/` | Uploaded evidence files |
| `/data/exports/` | PDF/HTML exports |
| `/data/sessions/` | Chat session JSON files (TTL 24h, auto-cleanup on startup) |
| `/data/standards/` | Custom uploaded standards (JSON/YAML) |
| `/data/knowledge_base/` | Benchmark + controls JSON (`benchmark_iso27001.json`, `controls.json`, etc.) |
| `/data/uploads/` | Document uploads |
| `ollama_data` *(named volume)* | Ollama model storage (`/root/.ollama`) |

---

## 9. Security Architecture

### Authentication & Authorization
- JWT authentication with configurable secret ([`JWT_SECRET`](.env.example:38), minimum 32 characters)
- 60-minute token expiry ([`JWT_EXPIRE_MINUTES`](.env.example:39))
- Weak secret detection: startup refuses in production (`DEBUG=false`), warns in development

### Rate Limiting
Per-endpoint rate limiting via [`slowapi`](backend/core/limiter.py):

| Endpoint | Limit |
|----------|-------|
| Chat | [`10/minute`](.env.example:42) |
| Assessment | [`3/minute`](.env.example:43) |
| Benchmark | [`5/minute`](.env.example:44) |

### Request Protection
- Request body size limit: **2 MB** default, exempt for upload/validate/evidence endpoints
- Evidence upload: **10 MB** via endpoint-specific exemption
- CORS with configurable origins ([`CORS_ORIGINS`](.env.example:33))
- `X-Request-ID` propagation for traceability
- Prompt injection detection in [`ChatService`](backend/services/chat_service.py)

### Nginx (Production)
Defined in [`nginx.conf`](nginx/nginx.conf):
- TLS 1.2 / TLS 1.3 with modern cipher suites, OCSP stapling
- HSTS: `max-age=63072000; includeSubDomains; preload`
- Content-Security-Policy: `default-src 'self'`, `frame-ancestors 'none'`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- Hidden file denial (`location ~ /\.` → `deny all`)
- Rate limiting: 30 req/s per IP on `/api/` (burst 20), 100 req/s global (burst 50)

---

## 10. Prometheus Metrics

All metrics are defined in [`metrics.py`](backend/api/routes/metrics.py) and exposed at `GET /metrics`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `cyberai_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests processed |
| `cyberai_request_duration_seconds` | Histogram | `endpoint` | Request processing duration (buckets: 5ms–10s) |
| `cyberai_active_sessions` | Gauge | — | Number of active chat sessions |
| `cyberai_rag_queries_total` | Counter | `result` (`hit` / `miss`) | RAG vector-store query outcomes |
| `cyberai_assessments_total` | Gauge | — | Total assessment records on disk |

Metrics middleware in [`main.py`](backend/main.py:113) instruments every HTTP request except `/metrics` itself to avoid self-referential cardinality.
