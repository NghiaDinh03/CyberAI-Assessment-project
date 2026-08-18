# ChromaDB Vector Store Guide

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-ChromaDB_Guide-blue?style=flat-square)](chromadb_guide.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Hướng_dẫn_ChromaDB-red?style=flat-square)](chromadb_guide_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [Collection Configuration](#2-collection-configuration)
3. [Document Chunking — Header-Aware](#3-document-chunking--header-aware)
4. [Indexing Pipeline](#4-indexing-pipeline)
5. [Search API](#5-search-api)
6. [Multi-Query Search](#6-multi-query-search)
7. [Intent Classifier Collection](#7-intent-classifier-collection)
8. [Admin Operations](#8-admin-operations)
9. [Data Directory Layout](#9-data-directory-layout)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

ChromaDB is used in two distinct ways in this project:

| Collection | Purpose | Storage |
|-----------|---------|---------|
| `iso_documents` | ISO knowledge base for RAG retrieval | Persisted: `/data/vector_store/` |
| `intent_classifier` | Model router intent examples | In-memory (rebuilt on startup) |

The `iso_documents` collection indexes **7 markdown files** totalling ~315 chunks, and supports semantic search with cosine similarity for both the chatbot RAG pipeline and the ISO assessment knowledge lookup.

---

## 2. Collection Configuration

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

```python
self.client = chromadb.PersistentClient(
    path=persist_dir or "/data/vector_store"
)

self.collection = self.client.get_or_create_collection(
    name="iso_documents",
    metadata={"hnsw:space": "cosine"}   # cosine distance metric
)
```

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Collection name | `iso_documents` | Fixed — used by both RAG and ISO assessment |
| Distance metric | cosine | 0 = identical, 1 = orthogonal, 2 = opposite |
| Persist directory | `/data/vector_store` | Survives container restarts |
| Embedding function | ChromaDB default | `sentence-transformers/all-MiniLM-L6-v2` |

---

## 3. Document Chunking — Header-Aware

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `_chunk_text()`

### Parameters

```python
def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 150) -> list:
```

| Parameter | Value |
|-----------|-------|
| `chunk_size` | 600 characters |
| `overlap` | 150 characters |

### Header Context Tracking

As the text is scanned, the current markdown heading hierarchy is tracked and prepended to each chunk:

```python
header_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
current_headers = {1: "", 2: "", 3: ""}

for match in header_pattern.finditer(text):
    level = len(match.group(1))    # 1, 2, or 3
    title = match.group(2).strip()
    current_headers[level] = title
    # Clear sub-headers when parent changes
    for sub in range(level+1, 4):
        current_headers[sub] = ""
```

### Context Prefix Format

```
[Context: # <h1> > ## <h2> > ### <h3>]
```

**Example:**

```
[Context: # ISO 27001:2022 > ## Annex A Controls > ### A.9 Access Control]
A.9.1.1 Access control policy
An access control policy shall be established, documented, approved by
management, published and communicated to employees and relevant
external parties. The access control policy shall address...
```

### Chunking Algorithm

```python
def _chunk_text(self, text, chunk_size=600, overlap=150):
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            # Build context prefix from current headers
            context = self._build_context_prefix(current_headers)
            chunks.append(f"{context}\n{current.strip()}" if context else current.strip())

            # Overlap: keep last `overlap` chars of current chunk
            current = current[-overlap:] + "\n\n" + para
        else:
            current += ("\n\n" if current else "") + para

    # Final chunk
    if current.strip():
        context = self._build_context_prefix(current_headers)
        chunks.append(f"{context}\n{current.strip()}" if context else current.strip())

    return chunks
```

### Why This Matters

Without header context, a chunk like `"A.9.1.1 — An access control policy shall be..."` has no indication which standard or section it belongs to. With the prefix:

```
[Context: # ISO 27001:2022 > ## Annex A > ### A.9]
A.9.1.1 An access control policy shall be...
```

The embedding model sees the full hierarchical context, significantly improving retrieval precision for queries like "ISO 27001 access control" vs "TCVN 11930 access control".

---

## 4. Indexing Pipeline

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `index_documents()`

### Auto-Index on Startup

```python
@app.on_event("startup")
def on_startup():
    VectorStore().ensure_indexed()
```

```python
def ensure_indexed(self):
    if self.collection.count() == 0:
        self.index_documents()
```

Only indexes if the collection is empty — no duplicate indexing on restart.

### Full Index Process

```python
def index_documents(self, docs_dir=None):
    docs_dir = docs_dir or "/data/iso_documents"
    documents, metadatas, ids = [], [], []

    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = self._chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{i}"
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_index": i})
            ids.append(doc_id)

    # Batch upsert to ChromaDB
    self.collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"[VectorStore] Indexed {len(ids)} chunks from {docs_dir}")
```

### Force Re-index

```
POST /api/iso27001/reindex
```

Drops and rebuilds the entire collection:

```python
@router.post("/iso27001/reindex")
async def reindex():
    vs = VectorStore()
    vs.client.delete_collection("iso_documents")
    vs.collection = vs.client.create_collection(
        name="iso_documents",
        metadata={"hnsw:space": "cosine"}
    )
    vs.index_documents()
    return {"status": "ok", "indexed": vs.collection.count()}
```

---

## 5. Search API

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `search()`

### Basic Search

```python
def search(self, query: str, top_k: int = 5) -> list:
    results = self.collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id":       results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output
```

### Result Format

```python
[
  {
    "id":       "iso27001_annex_a.md_42",
    "document": "[Context: # ISO 27001 > ## Annex A > ### A.9]\nA.9.1.1 Access control...",
    "metadata": { "source": "iso27001_annex_a.md", "chunk_index": 42 },
    "distance": 0.12     # lower = more similar
  },
  ...
]
```

### Distance Interpretation

| Distance | Meaning |
|----------|---------|
| 0.0–0.2 | Very high relevance |
| 0.2–0.4 | High relevance |
| 0.4–0.6 | Moderate relevance |
| 0.6–1.0 | Low relevance |
| > 1.0 | Not relevant (cosine distance can exceed 1 for negative similarity) |

---

## 6. Multi-Query Search

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `multi_query_search()`

For complex queries, generate multiple variations to improve recall:

```python
def multi_query_search(self, query: str, top_k: int = 5) -> list:
    queries = [
        query,
        f"ISO 27001 {query}",
        f"security control {query}"
    ]

    seen_ids = {}
    for q in queries:
        results = self.search(q, top_k=top_k)
        for r in results:
            if r["id"] not in seen_ids or r["distance"] < seen_ids[r["id"]]["distance"]:
                seen_ids[r["id"]] = r

    # Sort by distance, return top_k
    merged = sorted(seen_ids.values(), key=lambda x: x["distance"])
    return merged[:top_k]
```

**When used:** The ISO assessment pipeline uses `multi_query_search` to maximize knowledge retrieval coverage across all relevant controls.

---

## 7. Intent Classifier Collection

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

A separate **in-memory** ChromaDB collection is used for classifying user chat intent.

### Setup

```python
_client = chromadb.Client()   # in-memory, not persisted

def _get_intent_collection():
    collection = _client.get_or_create_collection(
        name="intent_classifier",
        metadata={"hnsw:space": "cosine"}
    )
    if collection.count() == 0:
        _seed_examples(collection)
    return collection
```

### Seed Examples

```python
def _seed_examples(collection):
    examples = [
        # Security route examples
        ("What are ISO 27001 Annex A controls?",         "security"),
        ("Explain the access control policy requirement", "security"),
        ("How to implement encryption under ISO 27001?", "security"),
        ("CVE vulnerability assessment requirements",    "security"),
        # Search route examples
        ("Latest ransomware news today",                 "search"),
        ("Recent cybersecurity incidents this week",     "search"),
        ("Current stock market trends",                  "search"),
        # General route examples
        ("How does HTTPS work?",                         "general"),
        ("Explain what a firewall does",                 "general"),
        ("What is the difference between IDS and IPS?",  "general"),
    ]
    collection.upsert(
        documents=[e[0] for e in examples],
        metadatas=[{"route": e[1]} for e in examples],
        ids=[f"ex_{i}" for i in range(len(examples))]
    )
```

### Classification

```python
def _semantic_classify(message: str) -> Dict:
    collection = _get_intent_collection()
    result = collection.query(query_texts=[message], n_results=1)
    distance   = result["distances"][0][0]
    confidence = 1 - distance
    route      = result["metadatas"][0][0]["route"]
    return {"route": route, "confidence": confidence}
```

---

## 8. Admin Operations

### Stats Endpoint

```
GET /api/iso27001/chromadb/stats
```

```json
{
  "collection": "iso_documents",
  "count": 312,
  "persist_dir": "/data/vector_store",
  "metadata": { "hnsw:space": "cosine" }
}
```

### Search Endpoint

```
POST /api/iso27001/chromadb/search
{ "query": "access control", "top_k": 5 }
```

Available from the Analytics page's ChromaDB Explorer UI.

### Re-index Endpoint

```
POST /api/iso27001/reindex
```

Drops and rebuilds the `iso_documents` collection. Use when ISO document files are updated.

---

## 9. Data Directory Layout

```
data/
├── vector_store/                   ← ChromaDB persist directory
│   ├── chroma.sqlite3              ← metadata + embeddings index
│   └── {collection-uuid}/
│       ├── data_level0.bin         ← HNSW graph level 0
│       ├── header.bin
│       ├── length.bin
│       └── link_lists.bin
│
└── iso_documents/                  ← Source markdown files
    ├── iso27001_annex_a.md
    ├── assessment_criteria.md
    ├── checklist_danh_gia_he_thong.md
    ├── luat_an_ninh_mang_2018.md
    ├── network_infrastructure.md
    ├── nghi_dinh_13_2023_bvdlcn.md
    └── tcvn_11930_2017.md
```

---

## 10. Troubleshooting

### Collection is empty (no search results)

```bash
# Force re-index via API
curl -X POST http://localhost:8000/api/iso27001/reindex

# Or check file count
docker exec <backend_container> ls -la /data/iso_documents/
```

### Wrong chunk count after updating documents

After editing any file in `data/iso_documents/`, force re-index:

```
POST /api/iso27001/reindex
```

### ChromaDB SQLite lock error

Occurs if two processes access the same `PersistentClient` path simultaneously. The backend is single-process (Uvicorn), so this shouldn't happen. If it does:

```bash
docker restart <backend_container>
```

### Verify collection contents

```bash
# Check stats
curl http://localhost:8000/api/iso27001/chromadb/stats

# Test semantic search
curl -X POST http://localhost:8000/api/iso27001/chromadb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "access control policy", "top_k": 3}'
```

### Distance values all > 0.9 (poor retrieval)

Indicates embeddings are not matching well. Check:
1. Query language matches document language (most docs are Vietnamese+English mixed)
2. Documents were chunked correctly (verify `chunk_index` in metadata)
3. Try re-indexing: `POST /api/iso27001/reindex`
