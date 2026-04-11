# CyberAI Platform — Chatbot & RAG Pipeline

---

## 🎯 Quick Introduction — What Does This Project Do?

> **New to AI/Chatbot?** Read this section first.

### CyberAI Chatbot works like a virtual cybersecurity expert

Imagine you have an **ISO 27001 consultant** available 24/7. You ask any security question, and the consultant will:

1. **Search** 21+ security standard documents (ISO, NIST, PCI DSS, Vietnamese regulations...) for relevant information
2. **Synthesize** information from multiple sources
3. **Answer** in plain language, with citations to source documents

This is **RAG (Retrieval-Augmented Generation)** — in simple terms, "AI with a reference library."

### Real-World Example — 3 Chat Modes

| You ask | Chatbot auto-selects | What happens behind the scenes |
|---------|---------------------|-------------------------------|
| *"What does ISO 27001 A.9 say about access control?"* | 🔒 **Security** | Searches 21+ ISO documents → finds 5 most relevant passages → AI synthesizes into a response |
| *"Latest ransomware news?"* | 🌐 **Search** | Searches DuckDuckGo → gets top 5 results → AI summarizes |
| *"Hello, what can you do?"* | 💬 **General** | No search needed → AI responds directly |

> 💡 **The chatbot automatically detects question type** — you don't need to manually select a mode.

### What is RAG? — Simple Explanation

Think about the difference between two types of AI:

| | Standard AI (e.g., ChatGPT alone) | AI + RAG (CyberAI Chatbot) |
|---|---|---|
| **Real-world analogy** | An expert with general knowledge but **no reference books** | An expert **with a library of 21+ specialized books** — searches before answering |
| **When asked about ISO 27001** | Answers from "memory" → may be wrong or outdated | Searches actual ISO 27001 documents → cites specific clauses |
| **When asked about local laws** | May fabricate non-existent laws | Searches real Vietnamese Cybersecurity Law 2018, Decree 13/2023 → cites specific articles |
| **Reliability** | ⚠️ May "hallucinate" (invent facts) | ✅ Cites sources, minimizes hallucination |

### SSE Streaming — Why Does Text Appear Word by Word?

When you chat, the response appears **word by word** (like ChatGPT). This technique is called **SSE (Server-Sent Events)**:
- ⏱️ You see a response **immediately** — no waiting 10-30 seconds
- 📖 You can read the beginning while AI is still writing the rest
- 🔄 If the response is wrong, you can stop early without wasting time

---

## 1. Chatbot Architecture

### Multi-Model Support

18+ models across 5 providers, selectable per request via the `model` field or frontend dropdown (grouped by provider):

| Provider | Examples |
|----------|----------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-3.5-turbo |
| **Google** | gemini-1.5-pro, gemini-1.5-flash |
| **Anthropic** | claude-3.5-sonnet, claude-3-haiku |
| **Ollama** | llama3, mistral, phi3 |
| **LocalAI** | SecurityLLM 7B, Meta-Llama 8B |

Model list is composed from built-in defaults merged with [`models.json`](models.json) at startup.

### Session Management

Handled by [`SessionStore`](backend/repositories/session_store.py) — file-based JSON persistence under `data/sessions/`.

| Parameter | Value |
|-----------|-------|
| Storage format | JSON file per session |
| TTL | 24 hours |
| Max messages stored | 20 per session |
| Context window sent to LLM | 10 most recent messages |
| Session ID | Auto-generated `uuid4` if not provided |

### Security

- **Prompt injection detection** performed inside [`ChatService`](backend/services/chat_service.py) before forwarding to LLM
- [`ModelGuard`](backend/services/model_guard.py) health exposed via `/api/chat/health`

### Streaming

SSE streaming implemented via `sse-starlette`. The `/api/chat/stream` endpoint emits `text/event-stream` tokens:

```
data: {"token": "partial ", "done": false}
data: {"token": "", "done": true, "metadata": {...}}
```

---

## 2. Model Routing

[`ModelRouter`](backend/services/model_router.py) classifies each incoming message into one of three intents using a **hybrid semantic + keyword** approach.

### Classification Pipeline

```
User message
  │
  ├─ Semantic: ChromaDB in-memory collection "intent_classifier"
  │   └─ Populated from INTENT_TEMPLATES at startup
  │   └─ Cosine similarity against intent exemplars
  │
  ├─ Confidence ≥ 0.6 → use semantic result
  │
  └─ Confidence < 0.6 → fallback to keyword regex matching
```

### Intent Routes

| Intent | Action | Flag |
|--------|--------|------|
| `security` | RAG lookup against ISO/cybersecurity documents | `use_rag=true` |
| `search` | Web search via DuckDuckGo | `use_search=true` |
| `general` | Direct LLM response (no augmentation) | — |

---

## 3. RAG Pipeline

### Document Ingestion

**Source:** 21+ markdown files in [`/data/iso_documents/`](data/iso_documents/).

**Standards covered:**

- ISO 27001:2022, ISO 27002:2022
- TCVN 11930:2017
- NIST CSF 2.0, NIST SP 800-53
- PCI DSS 4.0
- HIPAA Security Rule
- GDPR
- SOC 2 Trust Criteria
- CIS Controls v8
- OWASP Top 10 2021
- NIS2 Directive
- Vietnamese Cybersecurity Law 2018, Nghị định 13/2023 (BVDLCN), Nghị định 85/2016

**Chunking strategy** (in [`VectorStore`](backend/repositories/vector_store.py)):

| Parameter | Value |
|-----------|-------|
| Chunk size | 600 characters |
| Overlap | 150 characters |
| Header tracking | `#`, `##`, `###` tracked hierarchically |
| Context prefix | `[Context: # > ## > ###]` prepended to each chunk |

### Domain-Scoped Collections

Each standard family is indexed into its own ChromaDB collection for scoped retrieval:

| Domain | Source Files |
|--------|-------------|
| `iso_documents` | All markdown files (default collection) |
| `iso27001` | `iso27001_annex_a.md`, `iso27002_2022.md` |
| `tcvn11930` | `tcvn_11930_2017.md`, `nd85_2016_cap_do_httt.md` |
| `nd13` | `nghi_dinh_13_2023_bvdlcn.md`, `luat_an_ninh_mang_2018.md` |
| `nist_csf` | `nist_csf_2.md`, `nist_sp800_53.md` |
| `pci_dss` | `pci_dss_4.md` |
| `hipaa` | `hipaa_security_rule.md` |
| `gdpr` | `gdpr_compliance.md` |
| `soc2` | `soc2_trust_criteria.md` |
| Custom | Auto-indexed on upload into `{standard_id}` collection |

### Retrieval Flow

```
VectorStore.search(query, top_k=5, domain)
  │
  ├─ 1. Ensure collection is indexed (lazy init)
  ├─ 2. Query ChromaDB with cosine similarity
  ├─ 3. Score = 1 - cosine_distance (higher = more similar)
  │
  └─ RAGService post-processing:
       ├─ 4. Apply RAG_CONFIDENCE_THRESHOLD = 0.35
       ├─ 5. Multi-query expansion (Vietnamese synonym variants for ISO/TCVN queries)
       ├─ 6. Sort by score, deduplicate by source_chunk_index
       └─ 7. Return ranked context chunks
```

Implemented in [`RAGService`](backend/services/rag_service.py) and [`VectorStore`](backend/repositories/vector_store.py).

### Embedding

ChromaDB built-in default embedding function — no separate `sentence-transformers` dependency required.

Storage: ChromaDB `PersistentClient` under `data/vector_store/`.

---

## 4. Web Search Integration

Implemented in [`web_search.py`](backend/services/web_search.py).

| Parameter | Value |
|-----------|-------|
| Library | `duckduckgo_search` (`ddgs`) |
| Retry logic | 2 retries on failure |
| Region | `vn-vi` (Vietnamese) |
| Trigger | `ModelRouter` classifies intent as `search` |

Results are injected into the prompt as additional context alongside any RAG results.

---

## 5. Chat Flow

```
User message
  │
  ▼
ModelRouter.classify(message)
  │
  ├── intent: security ──► RAGService.search(query, domain) ──► context chunks
  ├── intent: search   ──► WebSearch.search(query)           ──► search results
  └── intent: general  ──► (no augmentation)
  │
  ▼
Prompt Construction
  ├── System prompt
  ├── RAG context / search results (if any)
  └── Session history (last 10 messages)
  │
  ▼
LLM Inference
  ├── LocalAI / Ollama (local mode)
  ├── OpenAI / Google / Anthropic (cloud mode)
  └── Hybrid: local first, cloud fallback
  │
  ▼
Response + Metadata
  ├── response text
  ├── model_used, source, rag_used, search_used
  └── processing_time
```
