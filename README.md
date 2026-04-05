# CyberAI Assessment Platform

> AI-powered cybersecurity assessment platform with multi-model inference, RAG-enhanced analysis, and ISO 27001 / TCVN 11930 compliance evaluation.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Table of Contents

- [Features](#features)
  - [AI Chatbot](#-ai-chatbot)
  - [ISO 27001 / TCVN 11930 Assessment](#-iso-27001--tcvn-11930-assessment)
  - [RAG Pipeline](#-rag-pipeline)
  - [Standards Management](#-standards-management)
  - [Web Search](#-web-search)
  - [Dual Local Inference](#️-dual-local-inference)
  - [Monitoring](#-monitoring)
  - [Security](#-security)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Model Infrastructure](#model-infrastructure)
  - [Cloud Fallback Chain](#cloud-fallback-chain)
  - [Resource Requirements](#resource-requirements)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
  - [Example: Chat Request](#example-chat-request)
  - [Example: Assessment Request](#example-assessment-request)
- [AI Pipeline Details](#ai-pipeline-details)
  - [2-Phase Assessment Pipeline](#2-phase-assessment-pipeline)
  - [Weighted Compliance Scoring](#weighted-compliance-scoring)
  - [RAG Retrieval Strategy](#rag-retrieval-strategy)
  - [Prompt Injection Detection](#prompt-injection-detection)
- [Prometheus Metrics](#prometheus-metrics)
- [Documentation](#documentation)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### 🤖 AI Chatbot

Multi-model chat with **18+ models** across **5 providers** (OpenAI, Google, Anthropic, Ollama, LocalAI). Key capabilities:

- **SSE streaming** — real-time token-by-token responses via `POST /chat/stream`
- **Session memory** — persistent conversation context stored in JSON files under `data/sessions/`
- **Smart routing** — hybrid intent classifier (semantic ChromaDB + keyword fallback) auto-selects between SecurityLLM, Llama, or cloud models
- **Markdown rendering** — full GFM support via `react-markdown` + `remark-gfm`
- **Prompt injection detection** — regex-based blocking of `ignore previous instructions`, `system:` prefix, special token injection

**Example chat flow:**
```
User: "Đánh giá rủi ro cho hệ thống có 50 servers"
  → Intent classifier: "security" (confidence 0.87)
  → Model selected: SecurityLLM-7B-Q4_K_M.gguf
  → RAG retrieves: iso27001_annex_a.md, nist_csf_2.md (cosine ≥ 0.35)
  → Response streamed with source attribution
```

### 📋 ISO 27001 / TCVN 11930 Assessment

4-step wizard with a **2-phase AI pipeline**:

| Step | UI Component | Description |
|------|-------------|-------------|
| 1 | System Info | Organization name, size, industry, infrastructure details |
| 2 | Control Checklist | Select implemented controls (93 for ISO 27001, 34 for TCVN 11930) |
| 3 | Evidence Upload | Attach files per control (PDF/PNG/DOCX/XLSX, max 10 MB each) |
| 4 | AI Analysis | 2-phase pipeline generates GAP analysis + formatted report |

**Scoring example (ISO 27001):**
```
Organization: Acme Corp (200 employees, 50 servers)
Implemented: 62/93 controls → 66.7% compliance
Weighted score: 148/268 points → 55.2% (critical gaps in A.8 Technology)

Risk Register output:
| # | Control | Severity | L | I | Risk | Recommendation |
|---|---------|----------|---|---|------|----------------|
| 1 | A.8.8   | 🔴 Critical | 4 | 5 | 20 | Deploy vulnerability scanning |
| 2 | A.8.9   | 🔴 Critical | 4 | 4 | 16 | Implement CIS hardening |
| 3 | A.5.24  | 🟠 High     | 3 | 4 | 12 | Create incident response plan |
```

### 📚 RAG Pipeline

**21 security standards** as knowledge base with intelligent retrieval:

| Category | Documents | Examples |
|----------|-----------|----------|
| International | 8 | ISO 27001 Annex A, ISO 27002:2022, NIST CSF 2.0, NIST SP 800-53 |
| Industry | 4 | PCI DSS 4.0, HIPAA Security Rule, SOC 2, OWASP Top 10 |
| Regional | 2 | NIS2 Directive, GDPR Compliance |
| Vietnamese | 4 | TCVN 11930:2017, Luật An ninh mạng 2018, Nghị định 13/2023, Nghị định 85/2016 |
| Internal | 3 | Assessment criteria, GAP analysis patterns, Infrastructure guide |

**Technical parameters:**
- Chunking: 600 chars with 150-char overlap, header-aware (preserves `# > ## > ###` hierarchy)
- Embedding: ChromaDB default (all-MiniLM-L6-v2), cosine similarity
- Confidence threshold: `score ≥ 0.35` (distance ≤ 0.65)
- Multi-query expansion: auto-generates Vietnamese synonyms (`đánh giá` → `kiểm toán`)
- Batch indexing: 100 chunks/batch for memory efficiency

### 📁 Standards Management

Upload custom standards (JSON/YAML, up to 500 controls), auto-indexed to ChromaDB.

**Built-in standards:**

| Standard | Controls | Weight Distribution |
|----------|----------|-------------------|
| ISO 27001:2022 | 93 | 15 critical, 30 high, 28 medium, 20 low |
| TCVN 11930:2017 | 34 | 8 critical, 12 high, 10 medium, 4 low |

**Custom standard JSON format:**
```json
{
  "standard_name": "Company Security Policy v2",
  "categories": [
    {
      "category": "Access Control",
      "controls": [
        { "id": "AC-01", "label": "MFA for all users", "weight": "critical" },
        { "id": "AC-02", "label": "Password rotation policy", "weight": "high" }
      ]
    }
  ]
}
```

### 🔍 Web Search

DuckDuckGo integration for real-time information retrieval when the knowledge base doesn't cover the query. Triggered automatically by the intent classifier when search keywords are detected (`latest`, `recent`, `news`, `tìm kiếm`, `tin tức`).

### 🖥️ Dual Local Inference

**LocalAI** (Llama 3.1 8B + SecurityLLM 7B) + **Ollama** (Gemma 3n E4B) with automatic cloud fallback.

```
Request flow:
  1. PREFER_LOCAL=true → try LocalAI first
  2. LocalAI timeout/error → try Ollama (gemma3n:e4b)
  3. Ollama unavailable → Cloud fallback chain
  4. All cloud models failed → Return graceful error
```

### 📊 Monitoring

Prometheus-compatible metrics at `GET /metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `cyberai_requests_total` | Counter | HTTP requests by method, endpoint, status |
| `cyberai_request_duration_seconds` | Histogram | Latency distribution (11 buckets: 5ms → 10s) |
| `cyberai_active_sessions` | Gauge | Current active chat sessions |
| `cyberai_rag_queries_total` | Counter | RAG queries by result (`hit` / `miss`) |
| `cyberai_assessments_total` | Gauge | Total persisted assessments |

System stats via `GET /system/stats`: CPU usage, RAM usage, disk usage (powered by `psutil`).

### 🔒 Security

| Layer | Mechanism | Configuration |
|-------|-----------|---------------|
| Rate limiting | SlowAPI | `10/min` chat, `3/min` assess, `5/min` benchmark |
| Authentication | JWT (HS256) | ≥32-char secret, 60-min expiry, enforced in prod |
| CORS | FastAPI middleware | Configurable origins (default: `localhost:3000`) |
| Input validation | Pydantic v2 | `max_length=2000` on chat, safe path IDs on file ops |
| Prompt injection | Regex detection | Blocks `ignore previous`, `system:`, special tokens |
| Request size | Evidence upload | 10 MB/file, allowed extensions whitelist |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ Frontend   │  │ Backend   │  │ LocalAI   │  │ Ollama   │ │
│  │ Next.js 15 │  │ FastAPI   │  │ v2.24.2   │  │ latest   │ │
│  │ React 19   │  │ Pydantic  │  │ GGUF      │  │ Gemma 3n │ │
│  │ :3000      │→ │ :8000     │→ │ :8080     │  │ :11434   │ │
│  │ (2 GB)     │  │ (6 GB)    │  │ (12 GB)   │  │ (12 GB)  │ │
│  └───────────┘  └─────┬─────┘  └───────────┘  └──────────┘ │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │    ChromaDB     │                             │
│              │  (embedded)     │                             │
│              │  cosine HNSW    │                             │
│              │  21 docs →      │                             │
│              │  ~500 chunks    │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │   Cloud APIs    │                             │
│              │   Open Claude   │                             │
│              │   gateway       │                             │
│              │  (fallback)     │                             │
│              └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

**Data flow — Assessment pipeline:**
```
Frontend (Step 1-3)           Backend                        AI Models
──────────────────           ───────                        ─────────
SystemInfo + Controls  →  /iso27001/assess
                              │
                              ├─ Calculate weighted score
                              ├─ Chunk controls by category
                              ├─ RAG: retrieve relevant standards
                              │
                              ├─ Phase 1: SecurityLLM (GAP analysis)
                              │    └─ Per-category JSON gap items
                              │    └─ Validate + anti-hallucination filter
                              │    └─ Severity normalization (≤70% critical)
                              │
                              ├─ Phase 2: Llama 3.1 (Report formatting)
                              │    └─ Risk Register markdown table
                              │    └─ Executive summary
                              │
                              └─ Return: { report, gaps, score, pdf_url }
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/your-org/phobert-chatbot-project.git
cd phobert-chatbot-project

# Configure
cp .env.example .env
# Edit .env — set CLOUD_API_KEYS if using cloud fallback

# Download models (optional — for local inference)
pip install huggingface_hub hf_transfer
python scripts/download_models.py --model llama --model security

# Start
docker compose up -d

# Access
# Frontend:    http://localhost:3000
# Backend API: http://localhost:8000
# API Docs:    http://localhost:8000/docs
# LocalAI:     http://localhost:8080
# Ollama:      http://localhost:11434
```

> **Note:** Ollama auto-pulls `gemma3n:e4b` on first start — no manual download required.

**Verify everything is running:**
```bash
# Check all containers
docker compose ps

# Health check
curl http://localhost:8000/health

# Check LocalAI model readiness
curl http://localhost:8080/readyz

# Check Ollama models
curl http://localhost:11434/api/tags
```

---

## Model Infrastructure

| Provider | Model | Quantization | Size | Port | Role |
|----------|-------|-------------|------|------|------|
| LocalAI | Meta-Llama-3.1-8B-Instruct | Q4_K_M | ~4.9 GB | 8080 | Report formatting, general chat |
| LocalAI | SecurityLLM-7B | Q4_K_M | ~4.2 GB | 8080 | GAP analysis, security audit |
| Ollama | Gemma 3n E4B | native | ~2 GB | 11434 | Chat, assessment (auto-pulled) |
| Cloud | gemini-3-flash-preview | — | — | — | Primary cloud fallback |
| Cloud | gpt-5-mini | — | — | — | Secondary fallback |
| Cloud | claude-sonnet-4 | — | — | — | Tertiary fallback |

### Cloud Fallback Chain

When local models are unavailable or produce errors:

```
gemini-3-flash-preview → gemini-3-pro-preview → gpt-5-mini → claude-sonnet-4 → gpt-5
```

Each model is tried with all available API keys (round-robin with 30s rate-limit cooldown per key).

### Resource Requirements

| Component | RAM (min) | RAM (recommended) | CPU |
|-----------|-----------|-------------------|-----|
| Frontend | 512 MB | 2 GB | 1 core |
| Backend | 2 GB | 6 GB | 2 cores |
| LocalAI | 4 GB | 12 GB | 6 threads (`THREADS=6`) |
| Ollama | 2 GB | 12 GB | 4 cores |
| **Total** | **8.5 GB** | **32 GB** | **4+ cores** |

**Model download options:**
```bash
# Check status of all models
python scripts/download_models.py --status

# Download individual models
python scripts/download_models.py --model llama        # 4.9 GB
python scripts/download_models.py --model security     # 4.2 GB
python scripts/download_models.py --model gemma-3-4b   # 2.5 GB
python scripts/download_models.py --model gemma-3-12b  # 7.3 GB
python scripts/download_models.py --model gemma-4-31b  # 19 GB

# Download all models at once
python scripts/download_models.py --model all
```

---

## Environment Variables

Key variables — see [`.env.example`](.env.example) for the full list with comments.

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | Primary LocalAI model (Phase 2 — report) |
| `SECURITY_MODEL_NAME` | `SecurityLLM-7B-Q4_K_M.gguf` | Security model (Phase 1 — GAP analysis) |
| `LOCALAI_URL` | `http://localai:8080` | LocalAI endpoint |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama endpoint |
| `PREFER_LOCAL` | `true` | Prefer local inference over cloud |
| `CLOUD_LLM_API_URL` | `https://open-claude.com/v1` | Cloud LLM gateway URL |
| `CLOUD_MODEL_NAME` | `gemini-3-flash-preview` | Default cloud model |
| `CLOUD_API_KEYS` | — | Comma-separated API keys for cloud fallback |
| `JWT_SECRET` | — | JWT signing secret (≥32 chars, required in prod) |
| `JWT_EXPIRE_MINUTES` | `60` | JWT token expiry in minutes |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `RATE_LIMIT_CHAT` | `10/minute` | Chat endpoint rate limit |
| `RATE_LIMIT_ASSESS` | `3/minute` | Assessment endpoint rate limit |
| `RATE_LIMIT_BENCHMARK` | `5/minute` | Benchmark endpoint rate limit |
| `INFERENCE_TIMEOUT` | `300` | LocalAI request timeout (seconds) |
| `CLOUD_TIMEOUT` | `60` | Cloud API request timeout (seconds) |
| `CONTEXT_SIZE` | `8192` | LocalAI context window |
| `THREADS` | `6` | LocalAI CPU threads |
| `MAX_CONCURRENT_REQUESTS` | `3` | Backend concurrency limit |
| `ISO_DOCS_PATH` | `/data/iso_documents` | RAG knowledge base directory |
| `VECTOR_STORE_PATH` | `/data/vector_store` | ChromaDB persistence directory |
| `DATA_PATH` | `/data` | Root data directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `true` | Debug mode (relaxes JWT validation) |

---

## Project Structure

```
phobert-chatbot-project/
├── backend/                        # FastAPI application
│   ├── main.py                     # App entry, lifespan hooks, middleware
│   ├── core/
│   │   ├── config.py               # Settings with JWT validation
│   │   ├── exceptions.py           # Custom exception classes
│   │   └── limiter.py              # SlowAPI rate limiter setup
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py             # POST /chat, /chat/stream, /chat/history
│   │   │   ├── iso27001.py         # POST /iso27001/assess (794 lines)
│   │   │   ├── standards.py        # GET/POST /standards/
│   │   │   ├── document.py         # POST /documents/upload
│   │   │   ├── health.py           # GET /health
│   │   │   ├── metrics.py          # GET /metrics (Prometheus)
│   │   │   ├── system.py           # GET /system/stats
│   │   │   └── benchmark.py        # GET /benchmark
│   │   └── schemas/
│   │       ├── chat.py             # ChatRequest, ChatResponse
│   │       └── document.py         # Document schemas
│   ├── services/
│   │   ├── chat_service.py         # Conversation routing, SSE (820 lines)
│   │   ├── cloud_llm_service.py    # Cloud/Local/Ollama with fallback (498 lines)
│   │   ├── model_router.py         # Intent-based model selection (214 lines)
│   │   ├── model_guard.py          # Model availability checker
│   │   ├── rag_service.py          # RAG pipeline, confidence filter
│   │   ├── standard_service.py     # Custom standard upload & indexing
│   │   ├── web_search.py           # DuckDuckGo search integration
│   │   ├── assessment_helpers.py   # 2-phase pipeline, scoring, prompts
│   │   ├── controls_catalog.py     # ISO 27001 + TCVN 11930 definitions
│   │   ├── document_service.py     # Document processing
│   │   └── dataset_generator.py    # Training data generation
│   ├── repositories/
│   │   ├── vector_store.py         # ChromaDB wrapper, chunking, search
│   │   └── session_store.py        # JSON session persistence
│   └── tests/                      # pytest test suite
│       ├── test_chat_service.py
│       ├── test_iso27001_routes.py
│       └── test_rag_service.py
├── frontend-next/                  # Next.js 15 frontend
│   └── src/
│       ├── app/
│       │   ├── chatbot/            # AI chat interface
│       │   ├── form-iso/           # 4-step assessment wizard
│       │   ├── standards/          # Standards management UI
│       │   ├── analytics/          # Monitoring dashboard
│       │   ├── landing/            # Landing page
│       │   └── templates/          # Report templates
│       ├── components/             # Navbar, StepProgress, SystemStats, Toast
│       ├── data/
│       │   ├── standards.js        # ISO 27001 (93) + TCVN 11930 (34) controls
│       │   ├── controlDescriptions.js
│       │   └── templates.js
│       └── lib/api.js              # Backend API client
├── data/
│   ├── iso_documents/              # 21 security standard documents (markdown)
│   ├── knowledge_base/             # Control catalogs, training pairs (JSON)
│   ├── vector_store/               # ChromaDB persistence
│   ├── assessments/                # Saved assessment JSON results
│   ├── evidence/                   # Uploaded evidence files
│   ├── exports/                    # Generated PDF reports
│   ├── sessions/                   # Chat session files
│   ├── standards/                  # Custom uploaded standards
│   └── uploads/                    # General uploads
├── docs/
│   ├── en/                         # English documentation
│   │   ├── architecture.md
│   │   ├── deployment.md
│   │   ├── api.md
│   │   ├── chatbot_rag.md
│   │   ├── iso_assessment_form.md
│   │   ├── chromadb_guide.md
│   │   ├── analytics_monitoring.md
│   │   ├── backup_strategy.md
│   │   └── markdown_rag_standard.md
│   └── vi/                         # Vietnamese documentation
│       ├── architecture.md
│       ├── deployment.md
│       ├── api.md
│       ├── chatbot_rag.md
│       ├── iso_assessment_form.md
│       ├── chromadb_guide.md
│       └── analytics_monitoring.md
├── scripts/
│   └── download_models.py          # HuggingFace model downloader (6 models)
├── nginx/nginx.conf                # Production reverse proxy
├── docker-compose.yml              # Development stack (4 services)
├── docker-compose.prod.yml         # Production stack
└── .env.example                    # Environment variable reference
```

---

## API Overview

The backend exposes a RESTful API at `http://localhost:8000`. Interactive documentation is available at [`/docs`](http://localhost:8000/docs) (Swagger UI) and [`/redoc`](http://localhost:8000/redoc) (ReDoc).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | AI chat (synchronous response) |
| `/chat/stream` | POST | SSE streaming chat |
| `/chat/history/{session_id}` | GET | Retrieve session history |
| `/iso27001/assess` | POST | Run ISO 27001 / TCVN 11930 assessment |
| `/iso27001/assessments` | GET | List saved assessments |
| `/iso27001/assessments/{id}` | GET | Get specific assessment |
| `/iso27001/export/{id}` | GET | Export assessment as PDF |
| `/iso27001/evidence/{id}` | POST | Upload evidence files |
| `/standards/` | GET | List available standards |
| `/standards/` | POST | Upload custom standard |
| `/documents/upload` | POST | Upload documents for RAG indexing |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/system/stats` | GET | CPU, RAM, disk statistics |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Giải thích Annex A.8.8 về quản lý lỗ hổng kỹ thuật",
    "session_id": "user-001",
    "model": "gemini-3-flash-preview",
    "prefer_cloud": true
  }'
```

**Response:**
```json
{
  "response": "**A.8.8 — Quản lý lỗ hổng kỹ thuật**\n\nĐây là biện pháp kiểm soát ...",
  "model": "gemini-3-flash-preview",
  "session_id": "user-001",
  "provider": "cloud",
  "rag_used": true,
  "sources": [
    { "file": "iso27001_annex_a.md", "title": "ISO 27001:2022 Annex A", "score": 0.72 }
  ]
}
```

### Example: Assessment Request

```bash
curl -X POST http://localhost:8000/iso27001/assess \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_standard": "iso27001",
    "org_name": "Acme Corp",
    "org_size": "medium",
    "industry": "fintech",
    "servers": 50,
    "employees": 200,
    "implemented_controls": ["A.5.1", "A.5.2", "A.5.15", "A.8.1"],
    "model_mode": "hybrid"
  }'
```

For full API reference, see [`docs/en/api.md`](docs/en/api.md).

---

## AI Pipeline Details

### 2-Phase Assessment Pipeline

The ISO assessment uses a specialized 2-phase approach:

**Phase 1 — GAP Analysis (SecurityLLM 7B)**
- Input: controls chunked by category + RAG context + evidence
- Output: JSON array per category with `{ id, severity, likelihood, impact, risk, gap, recommendation }`
- Anti-hallucination: validates control IDs against known catalog, rejects unknown IDs
- Severity normalization: if >70% marked critical, redistributes to realistic distribution (~25% critical, 25% high, 30% medium, 20% low)
- Few-shot examples embedded in prompt for consistent JSON output

**Phase 2 — Report Generation (Llama 3.1 8B)**
- Input: aggregated gap items + system info + weighted scores
- Output: formatted markdown report with Risk Register table, executive summary
- Risk scoring: `Risk = Likelihood × Impact` (each 1–5 scale, max risk = 25)

### Weighted Compliance Scoring

Controls are weighted by criticality:

| Weight | Score | Examples |
|--------|-------|---------|
| Critical | 4 pts | A.5.1 Security policy, A.5.15 Access control, A.8.1 Endpoint security |
| High | 3 pts | A.5.9 Asset inventory, A.6.1 Background check, A.7.1 Physical perimeter |
| Medium | 2 pts | A.5.7 Threat intelligence, A.7.6 Secure work areas, A.8.6 Capacity |
| Low | 1 pt | A.5.6 Expert liaison, A.5.11 Asset return, A.7.7 Clear desk |

**Formula:** `Weighted Score = Σ(implemented control weights) / Σ(all control weights) × 100%`

**Example:** 62/93 controls implemented, but mostly low/medium → weighted score could be 55.2% despite 66.7% simple count.

### RAG Retrieval Strategy

```
User query
    │
    ├─ Multi-query expansion
    │   "đánh giá iso 27001" → ["đánh giá iso 27001", "tiêu chuẩn đánh giá iso 27001"]
    │   "đánh giá rủi ro" → ["đánh giá rủi ro", "kiểm toán rủi ro"]
    │
    ├─ ChromaDB cosine search (per expanded query, top_k=5)
    │   └─ Deduplicate by (source, chunk_index)
    │
    ├─ Confidence filter (score ≥ 0.35)
    │   └─ Track hit/miss via Prometheus counter
    │
    └─ Return context + source attribution
        └─ Sources: [{ file, title, score }]
```

### Prompt Injection Detection

The chat service blocks messages matching:
- `ignore previous instructions`, `disregard all prior`
- `you are now`, `act as`, `forget everything`
- Special tokens: `<|im_start|>`, `<|im_end|>`, `<|eot_id|>`
- `system:` prefix at message start

Blocked requests return HTTP 400 with a generic error (no details leaked).

---

## Prometheus Metrics

Configure Prometheus to scrape the backend:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: cyberai
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 30s
```

**Available metrics:**

| Metric | Type | Labels |
|--------|------|--------|
| `cyberai_requests_total` | Counter | `method`, `endpoint`, `status` |
| `cyberai_request_duration_seconds` | Histogram | `endpoint` |
| `cyberai_active_sessions` | Gauge | — |
| `cyberai_rag_queries_total` | Counter | `result` (`hit` / `miss`) |
| `cyberai_assessments_total` | Gauge | — |

**Histogram buckets:** 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/en/architecture.md) | System design, service interactions, data flow |
| [Deployment Guide](docs/en/deployment.md) | Production deployment, Nginx, resource planning |
| [API Reference](docs/en/api.md) | Complete endpoint documentation |
| [Chatbot & RAG](docs/en/chatbot_rag.md) | Chat pipeline, RAG strategy, prompt design |
| [ISO Assessment](docs/en/iso_assessment_form.md) | Assessment wizard, 2-phase pipeline, scoring |
| [ChromaDB Guide](docs/en/chromadb_guide.md) | Vector store setup, collection management |
| [Analytics & Monitoring](docs/en/analytics_monitoring.md) | Prometheus metrics, dashboard setup |

Vietnamese versions available: [`docs/vi/`](docs/vi/)

---

## Tech Stack

| Layer | Technology | Details |
|-------|------------|---------|
| **Backend** | Python 3.10, FastAPI 0.115+, Pydantic v2 | Uvicorn ASGI, async support |
| **Vector Store** | ChromaDB 0.5+ | Embedded PersistentClient, cosine HNSW |
| **Frontend** | Next.js 15.1, React 19 | CSS Modules, lucide-react, react-markdown |
| **Local AI** | LocalAI v2.24.2 | GGUF inference, MMAP enabled, 8192 context |
| **Local AI** | Ollama (latest) | Gemma 3n architecture, auto-pull |
| **Cloud AI** | Open Claude gateway | Multi-model routing (Gemini, GPT, Claude) |
| **Search** | DuckDuckGo Search 6.2+ | Real-time web information |
| **Metrics** | Prometheus Client 0.20+ | Counter, Gauge, Histogram |
| **Security** | SlowAPI, JWT (HS256) | Rate limiting, token auth |
| **Infrastructure** | Docker Compose | 4 services, health checks, resource limits |
| **Production** | Nginx reverse proxy | TLS termination, static caching |
| **PDF Export** | WeasyPrint 62+ | HTML → PDF conversion |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please ensure all tests pass before submitting:

```bash
cd backend && python -m pytest tests/ -v
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
