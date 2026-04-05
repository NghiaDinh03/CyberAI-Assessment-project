---
name: database
description: Guide ChromaDB vector store patterns, data persistence, and backup strategy for the CyberAI platform.
---

Use this skill for vector store configuration, collection management, document chunking, file-based storage layout, data persistence strategy, and backup/restore operations.

Primary intent:
- Enforce consistent ChromaDB collection patterns with domain-scoped isolation and proper lifecycle management.
- Standardize file-based storage layout, persistence strategy, and backup procedures.

Reference direction:
- Vector store: `backend/repositories/vector_store.py`
- Session store: `backend/repositories/session_store.py`
- RAG service: `backend/services/rag_service.py`
- Standard service: `backend/services/standard_service.py`
- Backup script: `scripts/backup.sh`
- Config: `backend/core/config.py`
- Compose (dev): `docker-compose.yml`
- Compose (prod): `docker-compose.prod.yml`

## ChromaDB

- `PersistentClient` with configurable path (`VECTOR_STORE_PATH`, default `/data/vector_store`).
- Cosine similarity (`hnsw:space: cosine`).
- Domain-scoped collections: `iso_documents`, `iso27001`, `tcvn11930`, `nd13`, `nist_csf`, `pci_dss`, `hipaa`, `gdpr`, `soc2`, custom standards.
- Embedding: ChromaDB built-in default (no external model).
- Graceful shutdown in FastAPI lifespan handler.

## Document chunking

- Header-aware: tracks `#`, `##`, `###` hierarchically.
- Chunk size: 600 chars, overlap: 150 chars.
- Context prefix: `[Context: # > ## > ###]` for orphan chunks.
- Metadata per chunk: source file, `chunk_index`, headers.

## Collection management

- `index_documents()` — reads all `*.md` from `ISO_DOCS_PATH`, chunks, stores.
- `index_domain_documents()` — indexes specific files into domain collection.
- `search(query, top_k=5, domain)` — ensures indexed, queries ChromaDB.
- Custom standards auto-indexed on upload into `{standard_id}` collection.

## File-based storage

- Sessions: `/data/sessions/` — JSON files, TTL 24h, max 20 messages per session.
- Assessments: `/data/assessments/` — JSON files, one per assessment UUID.
- Evidence: `/data/evidence/` — uploaded files organized by `control_id`.
- Exports: `/data/exports/` — PDF/HTML export files.
- Standards: `/data/standards/` — custom uploaded JSON/YAML standards.
- Knowledge base: `/data/knowledge_base/` — benchmark data, controls JSON.
- Uploads: `/data/uploads/` — general document uploads.

## Data persistence

- Dev: bind mounts map host directories to container paths.
- Prod: named volume `cyberai-data:/data`.
- Ollama models: named volume `ollama_data:/root/.ollama`.

## Backup

- Script: `scripts/backup.sh --dest /backup/path --retention-days 30`.
- Backs up: assessments, sessions, knowledge_base, vector_store.
- Creates `tar.gz` with manifest JSON.
- Retention: 30 days (configurable `--retention-days`).

## Rules

- Always use domain-scoped collections for standard-specific queries.
- Never delete the default `iso_documents` collection.
- Always call graceful shutdown on ChromaDB client in lifespan handler.
- Session files must respect TTL (24h) — clean up expired sessions.
- Evidence files must validate type whitelist before storage.
- Backup before any re-index operation that could corrupt data.
- Custom standards limited to 500 controls per upload.

Code quality policy:
- No verbose comments or tutorial-style explanations.
- No banner decorations.
- Only comment non-obvious architectural constraints or performance-sensitive logic.
