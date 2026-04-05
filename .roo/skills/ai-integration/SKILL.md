---
name: ai-integration
description: Guide LLM routing, prompt engineering, RAG pipeline, and model fallback chains for the CyberAI platform.
---

Use this skill for LLM inference configuration, prompt design, RAG retrieval tuning, model fallback logic, intent classification, and anti-hallucination validation.

Primary intent:
- Enforce reliable multi-model inference with graceful fallback chains and offline capability.
- Standardize prompt engineering, RAG context injection, and LLM output validation patterns.

Reference direction:
- Model router: `backend/services/model_router.py`
- Cloud LLM service: `backend/services/cloud_llm_service.py`
- RAG service: `backend/services/rag_service.py`
- Vector store: `backend/repositories/vector_store.py`
- Model guard: `backend/services/model_guard.py`
- Assessment helpers: `backend/services/assessment_helpers.py`
- Config: `backend/core/config.py`

## LLM routing

- Hybrid intent classification: semantic (ChromaDB in-memory `intent_classifier`, threshold 0.6) → keyword regex fallback.
- `INTENT_TEMPLATES` define semantic prototypes for security/search/general.
- Three routes:
  - `security` — `use_rag=true`, `SECURITY_MODEL_NAME`
  - `search` — `use_search=true`, `MODEL_NAME`
  - `general` — `MODEL_NAME`
- Add new intents by extending `INTENT_TEMPLATES` and keyword lists.

## Inference chain

- `PREFER_LOCAL=true` (default): LocalAI → Ollama → Cloud fallback.
- `PREFER_LOCAL=false`: Cloud → LocalAI fallback.
- `LOCAL_ONLY_MODE=true`: No cloud calls allowed.
- Ollama detection: models starting with `gemma3:`, `gemma3n:`, `gemma4:`, `phi4:`, `llama3:`, `mistral:`, `qwen3:`.
- LocalAI-to-Ollama mapping: `gemma-3-4b-it` → `gemma3:4b`, etc.
- Cloud models priority: `gemini-3-flash-preview` → `gemini-3-pro-preview` → `gpt-5-mini` → `claude-sonnet-4` → `gpt-5`.
- API key round-robin with 30s cooldown on 429 responses.
- Health checks: verify LocalAI/Ollama availability before routing.

## Prompt engineering

- System prompts defined per task type (chat, security analysis, report formatting).
- Assessment Phase 1 (GAP analysis): compact prompt with missing controls + system summary per category.
- Assessment Phase 2 (Report): compressed risk register (max 2500 chars) + weight breakdown.
- RAG context injection: prepend retrieved chunks to user message.
- Session history: last 10 messages as conversation context.
- Prompt injection detection before LLM call.

## RAG pipeline

- Document ingestion: header-aware chunking (600 chars, 150 overlap) with hierarchical context prefix.
- Domain-scoped collections: `iso_documents` (default), `iso27001`, `tcvn11930`, `nd13`, `nist_csf`, `pci_dss`, `hipaa`, `gdpr`, `soc2` + custom.
- Retrieval: `top_k=5`, confidence threshold 0.35 (cosine similarity).
- Multi-query expansion: Vietnamese synonym variants for ISO/TCVN queries.
- Deduplication by `source_chunk_index`.
- Embedding: ChromaDB built-in default (no external model dependency).
- Re-index endpoints: `GET /api/iso27001/reindex` (all docs), `GET /api/iso27001/reindex-domains` (per-standard).

## Model guard

- Validates required GGUF files exist in `MODELS_PATH`.
- `REQUIRED_MODEL_IDS`: `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`, `SecurityLLM-7B-Q4_K_M.gguf`.
- Thread-safe state cache, refreshed on startup.

## Anti-hallucination

- JSON output validation: reject control IDs not in valid set.
- Retry up to 3 times on invalid output.
- Fallback: `infer_gap_from_control()` generates gap from control metadata.
- Severity normalization: if >70% critical → redistribute proportionally.

## Rules

- Always validate LLM JSON output before using it.
- Always implement fallback chains (never rely on single model/provider).
- Never send raw user input to LLM without injection detection.
- Keep prompts under context window limits (8192 tokens default).
- Log `model_used`, `source` (local/cloud), `processing_time` for every inference.
- Test with `LOCAL_ONLY_MODE=true` to verify offline functionality.

Code quality policy:
- No verbose comments or tutorial-style explanations.
- No banner decorations.
- Only comment non-obvious architectural constraints or performance-sensitive logic.
