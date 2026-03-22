<div align="center">
  <h1>PhoBERT AI Platform v2.0</h1>
  <p>Enterprise RAG, ISO 27001 Assessment & AI News Aggregator</p>
  <p>
    <a href="README.md">🇬🇧 English</a> | <a href="README_vi.md">🇻🇳 Tiếng Việt</a>
  </p>
</div>

## Table of Contents
- [Overview](#overview)
- [What's New in v2.0](#whats-new-in-v20)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [AI Models Integration](#ai-models-integration)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [License](#license)

## Overview
PhoBERT AI Platform is a comprehensive, on-premise AI system featuring **ISO 27001:2022 & TCVN 11930** compliance assessment, Retrieval-Augmented Generation (RAG) capabilities, and Automated News Aggregation. Designed to run completely via Docker Compose, the system utilizes a Multi-Tier Fallback architecture to guarantee maximum High Availability (HA).

---

## 🆕 What's New in v2.0

### 🔄 Unified Cloud LLM Service (Open Claude + Multi-Tier Fallback)
- **New Primary API**: Replaced scattered API integrations with a unified `CloudLLMService` powered by **Open Claude** (`gemini-3-pro-preview` model).
- **3-Tier Smart Fallback Chain**: Open Claude → OpenRouter → LocalAI (on-premise). If any cloud provider fails, the system seamlessly cascades to the next.
- **Multi-Key Round-Robin**: Supports multiple API keys per provider with automatic rotation. When a key hits Rate Limit (HTTP 429), it enters a 60-second cooldown and the system switches to the next available key.
- **Exponential Backoff Retry**: Intelligent retry logic across all providers.

### 🧠 Conversation Memory (Session-Based Context)
- **Before**: Each chat message was a standalone request — the AI had zero memory of previous messages.
- **Now**: Full session-based conversation memory storing up to **20 recent messages per session**.
- **Persistent Storage**: File-based JSON sessions survive container restarts.
- **Auto-Cleanup**: Sessions expire after **24 hours** (configurable TTL).
- **New API Endpoints**: `GET /api/chat/history/{session_id}` and `DELETE /api/chat/history/{session_id}`.

### 🔍 Enhanced RAG Pipeline
- **Semantic Chunking**: Respects Markdown structure (headers, tables, lists) instead of naive character splitting.
- **Header Hierarchy Tracking**: Prepends parent header context to each chunk for better relevance.
- **Increased Overlap**: 150-character overlap between chunks for improved context preservation.
- **Multi-Query Search**: Generates Vietnamese query variations to increase recall from the vector store.
- **Cosine Similarity Scoring**: Results are sorted by relevance score.
- **Source Attribution**: RAG responses now include which documents were used as references.

### ⚡ CPU Performance Optimization
| Technique | Description |
|-----------|-------------|
| PyTorch Thread Control | `torch.set_num_threads()` configurable via `TORCH_THREADS` env var |
| JIT Optimization | `torch.jit.optimize_for_inference()` for faster CPU inference |
| Semaphore Throttling | Limits concurrent AI requests to prevent CPU overload |
| Cloud-First Strategy | Prioritizes Cloud APIs to offload CPU from local model inference |
| Batch Chunking | Processes translation in batches of 8 titles to prevent OOM |
| Aggressive Caching | File-based persistent cache with TTL management |
| Request Size Limit | Middleware caps request body at 2MB |
| Docker Memory Limits | Backend: 4GB, LocalAI: 8GB, Frontend: 1GB |

### 🛡️ Security & Stability Hardening
| Feature | Details |
|---------|---------|
| CORS Whitelist | Configurable via `CORS_ORIGINS` env var (no more wildcard `*`) |
| Rate Limiting | Per-endpoint rate limiting via `slowapi` (e.g., `10/minute` for chat) |
| Request Size Limit | 2MB middleware to prevent abuse |
| Input Validation | Pydantic schemas with `min_length=1, max_length=2000` |
| Error Boundaries | Custom 404/500 handlers with graceful degradation |
| Config Validation | `settings.validate()` runs on startup to catch misconfigurations |
| Docker Health Checks | Automated health monitoring for Backend & LocalAI containers |

### 🏗️ Intelligent Model Router
- **Before**: Simple regex-based question classification.
- **Now**: Keyword-weighted semantic classification across **7 route categories**: `iso`, `security`, `legal`, `technical`, `news`, `general`, `greeting`.
- Each route triggers a custom system prompt and dedicated RAG context for higher accuracy.

### 🔧 RAG Service v2.0
- New dedicated `rag_service.py` module providing a clean interface for Retrieval-Augmented Generation.
- Uses `CloudLLMService` instead of direct LocalAI calls for faster response times.
- Supports `retrieve_with_sources()` for full source attribution in answers.
- Relevance threshold checking via `is_relevant()` method.

### 🧹 Code Cleanup — Production-Ready Codebase
- **Removed** all decorative section separators and redundant inline comments across the entire backend.
- **Streamlined** docstrings to concise one-liners at file level only.
- **Eliminated** obvious comments (e.g., `# Check cooldown`, `# Build messages array`) that added no value.
- **Retained** only meaningful comments explaining business logic and edge cases.
- **Result**: ~25-40% code reduction across 10+ core files while maintaining full functionality. The codebase now reads like a professional production project.

### 🦙 Upgraded LocalAI Model — Llama 3.1 70B
- **Before**: Llama 3.1 8B Instruct (Q4_K_M) — decent but limited reasoning for complex ISO assessments.
- **Now**: **Llama 3.1 70B Instruct (Q4_K_M)** — significantly smarter for chatbot conversations, ISO gap analysis, and security auditing.
- Docker memory limits raised: Backend **6GB**, LocalAI **12GB**, Frontend **2GB**.
- Inference timeout increased to **180s** to accommodate larger model.
- Fallback: If machine has <16GB RAM, switch to 8B model in `.env`.

### 📰 Enhanced News Pipeline — Full-Content Translation
- **Before**: Articles were truncated to 6000 chars and summarized. Cloud API and VinAI handled translation separately.
- **Now**: Cloud API handles **full translation + editorial rewrite** in a single pass (up to 12000 chars, no content truncation).
- **Prompts upgraded** to enforce 100% factual accuracy: all names, statistics, CVE codes, dates, and technical specs must be preserved verbatim.
- **No summarization** — articles are fully translated/rewritten in broadcast-quality Vietnamese, ready for Text-to-Speech.
- Added more pronunciation fixes for TTS: DDoS, VPN, SSL, TLS, ransomware, blockchain, crypto.
- `max_tokens` raised to **16000** to prevent output truncation on long articles.

---

## System Architecture

The project leverages a modern Client-Server model powered by various AI models distributed across dedicated Docker containers.

### 1. 🖥️ Frontend (Next.js 15)
- **Ultra-fast SPA:** Single Page Application design eliminating page reloads. Includes modular tabs (Analytics, Chat, Form ISO, News).
- **Client-Side Caching:** Built-in caching (React state/ref) for the News module to persistently store tabs without refetching, reducing bandwidth and latency.
- **Smart Audio Control:** A modern audio interface that provides text-to-speech for news summaries directly on articles or via the History Panel.

### 2. ⚙️ Backend (FastAPI - Python)
A high-performance backend processing requests via multi-threading and robust routing:
- **`cloud_llm_service.py`** 🆕: Unified Cloud LLM client supporting Open Claude (primary), OpenRouter (fallback), and LocalAI (last resort) with multi-key round-robin and auto-cooldown.
- **`chat_service.py`:** Manages conversation routing with **session-based memory**, interacts with Cloud LLM first, then queries the Vector Database via RAG.
- **`model_router.py`:** Keyword-weighted semantic classification routing tasks across 7 categories to the appropriate AI model and system prompt.
- **`rag_service.py`** 🆕: Enhanced RAG pipeline with multi-query search, source attribution, and Cloud LLM integration.
- **`summary_service.py`:** The core of the news summarization engine featuring a **3-Tier Fallback & Round-Robin mechanism**:
  1. **Open Claude (gemini-3-pro-preview)**: Primary cloud API with multi-key rotation and 60s cooldown on rate limit.
  2. **OpenRouter**: Cascades here if all Open Claude keys fail.
  3. **LocalAI (On-premise)**: Final fallback using local AI if all cloud APIs are unavailable or quotas are exhausted.
- **`news_service.py`:** Fetches RSS feeds from major cybersecurity sources (The Hacker News, Dark Reading, etc.) and manages a 7-day lifecycle cleanup for `articles_history.json`.
- **`translation_service.py`:** Utilizes the `VinAI Translate` model (135M parameters) for direct CPU-based title translation, optimized with PyTorch JIT and configurable thread control.
- **`session_store.py`** 🆕: File-based persistent session storage for conversation memory with 24h TTL and auto-cleanup.

### 3. 💾 Data Persistent Storage (`data/` Directory)
Mounted into Docker to safely retain configurations, logic, and databases:
- **`data/iso_documents/`**: Drop your `.md` files here. ChromaDB converts them into a Knowledge Base for the ISO auditing bot.
- **`data/vector_store/`**: Contains the ChromaDB SQLite Vector Database.
- **`data/summaries/`**: Stores JSON Cache for content and the `data/summaries/audio/` directory.
  - **Audio Caching Mechanism:** URLs are hashed (MD5). Edge-TTS converts Vietnamese text to static `hash.mp3` files. Cached audio files persist for 7 days to eliminate redundant TTS API calls and reduce RAM/Disk usage.
- **`data/sessions/`** 🆕: Persistent conversation session files (JSON) with auto-expiry.
- **`data/assessments/`**: Stores historical generated ISO reports.

## Key Features

### 🏠 Dashboard
- Live 4-timezone world clock.
- Quick navigation to core system features.

### 💬 AI Chat (ISO RAG) — *Enhanced in v2.0*
- Employs Retrieval-Augmented Generation (RAG) with **semantic chunking** and **multi-query search**.
- **Conversation Memory**: The AI remembers your previous messages within a session (up to 20 messages).
- **Cloud-First Strategy**: Prioritizes fast cloud AI (Open Claude) and falls back to LocalAI when needed.
- **Source Attribution**: Answers cite which documents were used as references.
- **Session Management**: View chat history or clear sessions via API.

### 📊 Analytics & Monitoring
- Ultimate dashboard tracking hardware health (CPU, RAM).
- Maps container metrics and AI Model statuses (Idle/Busy).
- Manage ChromaDB (Clear, Reload) and System History seamlessly.
- **Cloud LLM Health Check** 🆕: Monitor status of Open Claude, OpenRouter, and LocalAI providers.

### 📝 ISO Assessment Form
- Rapid 20+ question survey regarding Enterprise Network Infrastructure.
- Automatically generates comprehensive Action Plan reports using Llama 3.1 & SecurityLLM.
- Analyzes gaps for ISO 27001:2022 and TCVN 11930 standards.

### 📰 AI News Aggregator
- 3 main cybersecurity news categories continuously fetched.
- One-click **🔊 Listen** immediately triggers the summarize -> MP3 generation -> play flow (Plays from cache on subsequent listens).
- **7-Day History Sidebar:** Revisit old articles and listen to cached static audio without consuming API tokens.

## AI Models Integration

| # | Model | Provider | Role |
|---|-------|----------|------|
| 1 | **gemini-3-pro-preview** 🆕 | Open Claude (Cloud) | Primary brain for chat, RAG, and summarization via unified Cloud LLM |
| 2 | **Llama 3.1 Instruct (70B)** 🆕 | LocalAI (On-premise) | Upgraded fallback — smarter reasoning for chat, ISO assessment, and local inference |
| 3 | **SecurityLLM (7B)** | LocalAI (On-premise) | Cybersecurity expert for auditing internal networks |
| 4 | **Gemini 2.5 Flash / OpenRouter** | Cloud API | Fallback cloud provider for fast summarization |
| 5 | **VinAI Translate (135M)** | HuggingFace Transformers | 100% on-server Vietnamese translator (CPU-optimized with JIT) |
| 6 | **all-MiniLM-L6-v2** | ChromaDB | Embeds markdown text into mathematical vectors |
| 7 | **Edge-TTS** | Microsoft Service | Natural, fluent Text-to-Speech output |

## Quick Start

The architecture deployment is highly streamlined via `docker-compose`. All DNS/Network routing issues are pre-configured.

### 1. Clone & Setup Environment
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
cp .env.example .env
```

### 2. Configure API Keys
Open the `.env` file and configure the following:

```env
# Primary Cloud LLM (Open Claude)
CLOUD_API_KEYS=your_key_1,your_key_2,your_key_3
CLOUD_LLM_API_URL=https://open-claude.com/v1
CLOUD_MODEL_NAME=gemini-3-pro-preview

# (Optional) OpenRouter as fallback
OPENROUTER_API_KEYS=your_openrouter_key

# (Optional) Legacy Gemini keys
GEMINI_API_KEYS=key1,key2,key3
```

> ⚠️ **Note:** The system requires at least **one** Cloud API key (Open Claude OR OpenRouter) for chat to work. Keys support comma-separated format for automatic Round-Robin load balancing!

### 3. Build & Run
```bash
docker-compose up --build -d
```
*This command pulls required images, downloads GGUF models into `/models`, installs libraries, and spins up `phobert-frontend`, `phobert-backend`, and `phobert-localai` containers with memory limits and health checks.*

### 4. Access
Open your browser and navigate to **http://localhost:3000**

### 5. (Optional) Performance Tuning
For CPU-constrained environments, adjust these in `.env`:
```env
TORCH_THREADS=4          # PyTorch threads for translation
MAX_CONCURRENT_REQUESTS=3 # Max concurrent AI requests
INFERENCE_TIMEOUT=120     # LocalAI timeout (seconds)
CLOUD_TIMEOUT=60          # Cloud API timeout (seconds)
```

## Documentation
The project includes deep functional and technical documentation inside the `docs/` directory:
- 📖 **[Architecture Details](./docs/architecture.md)**
- 📖 **[API References](./docs/api.md)**
- 📖 **[Deployment Guide](./docs/deployment.md)**
- 📖 **[ChromaDB Implementation](./docs/chromadb_guide.md)**
- 📖 **[RAG & PICO Markdown Formatting Standard](./docs/markdown_rag_standard.md)**
- 📖 **[Analytics & Monitoring Guide](./docs/analytics_monitoring.md)**
- 📖 **[News Aggregator Architecture](./docs/news_aggregator.md)**
- 📖 **[ISO Assessment Form Flow](./docs/iso_assessment_form.md)**

## v2.0 Performance Comparison

| Metric | v1.0 | v2.0 | Improvement |
|--------|------|------|-------------|
| Chat Response (Cloud) | N/A | ~2-5s | 🆕 New |
| Chat Response (LocalAI) | 15-30s | 15-30s (fallback only) | Cloud-first strategy |
| Translation Batch | No chunking | 8 titles/batch | More stable |
| Session Persistence | In-memory (lost on restart) | File-based (persistent) | ✅ Persistent |
| Conversation Context | None | 20 messages/session | ✅ New |
| RAG Chunk Quality | Basic split | Semantic + headers | More accurate |
| API Security | CORS `*` | Whitelist + rate limit | ✅ Secured |
| Error Recovery | Crash | Graceful fallback chain | ✅ Stable |

## License
This project is proprietary and built for enterprise network assessment purposes.
*Focused on premium end-user experiences, data security, memory overflow protection, and multi-tier robust fallback systems.*
