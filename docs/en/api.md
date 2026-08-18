# CyberAI Platform — API Reference

All endpoints are available at both **`/api/v1/...`** (versioned) and **`/api/...`** (legacy backward-compatible).

Base URL: `http://localhost:8000` (default development)

---

## Chat Endpoints

| Method | Path | Description | Rate Limit |
|--------|------|-------------|------------|
| POST | `/api/chat` | Send message, get response | 10/min |
| POST | `/api/chat/stream` | SSE streaming response | 10/min |
| GET | `/api/chat/history/{session_id}` | Get chat history | — |
| DELETE | `/api/chat/history/{session_id}` | Clear session history | — |
| GET | `/api/chat/health` | Chat service health + ModelGuard status | — |

### Request Body

Defined in [`ChatRequest`](backend/api/schemas/chat.py):

```json
{
  "message": "string (required)",
  "session_id": "string (optional, auto-generated uuid4)",
  "model": "string (optional, defaults to MODEL_NAME env var)",
  "mode": "string (optional: 'local' | 'cloud' | 'hybrid')"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | LLM-generated answer |
| `session_id` | string | Session identifier (reuse for continuity) |
| `model_used` | string | Actual model that served the request |
| `source` | string | `"local"` or `"cloud"` |
| `rag_used` | bool | Whether RAG context was injected |
| `search_used` | bool | Whether web search was triggered |
| `processing_time` | float | End-to-end latency in seconds |

### SSE Stream Format

`POST /api/chat/stream` returns `text/event-stream`:

```
data: {"token": "The ", "done": false}
data: {"token": "answer ", "done": false}
data: {"token": "is...", "done": false}
data: {"token": "", "done": true, "metadata": {"model_used": "...", "source": "local", "rag_used": true, "search_used": false, "processing_time": 1.23}}
```

---

## ISO 27001 Assessment Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/iso27001/assess` | Submit assessment (background task) |
| GET | `/api/iso27001/assessments` | List all assessments (paginated) |
| GET | `/api/iso27001/assessments/{id}` | Get assessment by ID |
| DELETE | `/api/iso27001/assessments/{id}` | Delete assessment |
| POST | `/api/iso27001/reindex` | Re-index all ISO docs into default collection |
| POST | `/api/iso27001/reindex-domains` | Re-index per-standard domain collections |
| GET | `/api/iso27001/chromadb/stats` | ChromaDB stats (all domain collections) |
| POST | `/api/iso27001/chromadb/search` | Search ChromaDB `{query, top_k}` |
| POST | `/api/iso27001/assessments/{id}/export-pdf` | Export PDF (weasyprint) or HTML fallback |

### Pagination — List Assessments

```
GET /api/iso27001/assessments?page=1&page_size=50&flat=false
```

| Param | Default | Description |
|-------|---------|-------------|
| `page` | 1 | Page number |
| `page_size` | 50 | Results per page |
| `flat` | false | Flatten nested structure |

---

## Evidence Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/iso27001/evidence/{control_id}` | Upload evidence file (max 10 MB) |
| GET | `/api/iso27001/evidence/{control_id}` | List evidence files for control |
| GET | `/api/iso27001/evidence/{control_id}/{filename}` | Download evidence file |
| DELETE | `/api/iso27001/evidence/{control_id}/{filename}` | Delete evidence file |
| GET | `/api/iso27001/evidence/{control_id}/{filename}/preview` | Preview evidence content |
| GET | `/api/iso27001/evidence-summary` | Summary of all evidence across controls |

### Allowed File Types

`PDF`, `PNG`, `JPG`, `DOC`, `DOCX`, `XLSX`, `CSV`, `TXT`, `LOG`, `CONF`, `XML`, `JSON`

---

## Standards Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/standards` | List all standards (built-in + custom) |
| GET | `/api/standards/sample` | Download sample standard JSON template |
| GET | `/api/standards/{id}` | Get standard detail (frontend-compatible) |
| POST | `/api/standards/upload` | Upload JSON/YAML standard (max 2 MB) |
| POST | `/api/standards/validate` | Validate file without saving |
| POST | `/api/standards/{id}/index` | Re-index standard into ChromaDB |
| DELETE | `/api/standards/{id}` | Delete custom standard |

---

## Document Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/documents/upload` | Upload document for processing |

---

## System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/stats` | CPU, memory, disk, uptime (psutil) |
| GET | `/api/system/cache-stats` | Sessions + exports directory sizes |
| GET | `/api/system/ai-status` | LocalAI/Cloud health, mode label, ModelGuard status |
| GET | `/api/models` | List all available models (built-in + models.json) |

---

## Health Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | `{"status": "healthy"}` |
| GET | `/health` | Root-level health (same) |
| GET | `/` | Service info + version |

---

## Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metrics` | Prometheus text format (mounted at root, not `/api/`) |

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `cyberai_requests_total` | Counter | Total HTTP requests |
| `cyberai_request_duration_seconds` | Histogram | Request latency distribution |
| `cyberai_active_sessions` | Gauge | Currently active chat sessions |
| `cyberai_rag_queries_total` | Counter | Total RAG queries executed |
| `cyberai_assessments_total` | Gauge | Total assessments stored |

---

## Benchmark & Dataset Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/benchmark/test-cases` | List benchmark test cases |
| POST | `/api/benchmark/run` | Run benchmark (compare modes) |
| GET | `/api/benchmark/scoring-guide` | Scoring criteria docs |
| POST | `/api/dataset/generate` | Trigger fine-tuning dataset generation (background) |
| GET | `/api/dataset/status` | Check dataset generation status |

---

## Error Handling

All error responses return JSON with a `request_id` field for tracing.

| Source | Behavior |
|--------|----------|
| `AppException` | Sanitized JSON response |
| `HTTPException` | Sanitized JSON response |
| Unhandled exception | HTTP 500 with `request_id` (stack trace server-side only) |
| 404 Not Found | Custom JSON handler |

Response shape:

```json
{
  "error": "Human-readable message",
  "request_id": "uuid4",
  "status_code": 400
}
```

---

## Examples

### Send a Chat Message

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key controls in ISO 27001 Annex A.5?",
    "mode": "hybrid"
  }'
```

### Submit an ISO 27001 Assessment

```bash
curl -X POST http://localhost:8000/api/iso27001/assess \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "ACME Corp",
    "standard_id": "iso27001",
    "scope": "full",
    "controls": {"A.5.1": true, "A.5.2": false},
    "ai_mode": "hybrid"
  }'
```

### Upload Evidence for a Control

```bash
curl -X POST http://localhost:8000/api/iso27001/evidence/A.5.1 \
  -F "file=@./firewall_policy.pdf"
```
