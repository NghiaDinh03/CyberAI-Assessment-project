# Hướng Dẫn ChromaDB Vector Store

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-ChromaDB_Guide-blue?style=flat-square)](chromadb_guide.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Hướng_dẫn_ChromaDB-red?style=flat-square)](chromadb_guide_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Cấu Hình Collection](#2-cấu-hình-collection)
3. [Chunking Tài Liệu — Nhận Biết Header](#3-chunking-tài-liệu--nhận-biết-header)
4. [Pipeline Indexing](#4-pipeline-indexing)
5. [API Tìm Kiếm](#5-api-tìm-kiếm)
6. [Tìm Kiếm Đa Query](#6-tìm-kiếm-đa-query)
7. [Collection Intent Classifier](#7-collection-intent-classifier)
8. [Thao Tác Quản Trị](#8-thao-tác-quản-trị)
9. [Cấu Trúc Thư Mục Dữ Liệu](#9-cấu-trúc-thư-mục-dữ-liệu)
10. [Xử Lý Sự Cố](#10-xử-lý-sự-cố)

---

## 1. Tổng Quan

ChromaDB được sử dụng theo hai cách khác nhau trong dự án:

| Collection | Mục đích | Lưu trữ |
|-----------|---------|--------|
| `iso_documents` | Cơ sở kiến thức ISO để truy xuất RAG | Bền vững: `/data/vector_store/` |
| `intent_classifier` | Ví dụ intent cho model router | In-memory (xây lại khi khởi động) |

Collection `iso_documents` index **7 file markdown** tổng cộng ~315 chunks, hỗ trợ tìm kiếm ngữ nghĩa với cosine similarity cho cả pipeline RAG chatbot và tra cứu kiến thức đánh giá ISO.

---

## 2. Cấu Hình Collection

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

```python
self.client = chromadb.PersistentClient(
    path=persist_dir or "/data/vector_store"
)

self.collection = self.client.get_or_create_collection(
    name="iso_documents",
    metadata={"hnsw:space": "cosine"}   # metric khoảng cách cosine
)
```

### Tham Số

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Tên collection | `iso_documents` | Cố định — dùng bởi cả RAG và ISO assessment |
| Metric khoảng cách | cosine | 0 = giống hệt, 1 = trực giao, 2 = đối lập |
| Thư mục lưu | `/data/vector_store` | Tồn tại qua các lần khởi động container |
| Embedding function | Mặc định ChromaDB | `sentence-transformers/all-MiniLM-L6-v2` |

---

## 3. Chunking Tài Liệu — Nhận Biết Header

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `_chunk_text()`

### Tham Số

```python
def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 150) -> list:
```

| Tham số | Giá trị |
|---------|---------|
| `chunk_size` | 600 ký tự |
| `overlap` | 150 ký tự |

### Theo Dõi Context Header

Khi quét text, phân cấp markdown heading hiện tại được theo dõi và thêm vào đầu mỗi chunk:

```python
header_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
current_headers = {1: "", 2: "", 3: ""}

for match in header_pattern.finditer(text):
    level = len(match.group(1))    # 1, 2, hoặc 3
    title = match.group(2).strip()
    current_headers[level] = title
    # Xóa sub-headers khi parent thay đổi
    for sub in range(level+1, 4):
        current_headers[sub] = ""
```

### Định Dạng Tiền Tố Context

```
[Context: # <h1> > ## <h2> > ### <h3>]
```

**Ví dụ:**

```
[Context: # ISO 27001:2022 > ## Annex A Controls > ### A.9 Kiểm soát truy cập]
A.9.1.1 Chính sách kiểm soát truy cập
Cần thiết lập, lập tài liệu chính sách kiểm soát truy cập, được phê duyệt
bởi ban quản lý, công bố và truyền đạt tới nhân viên và các bên liên quan...
```

### Tại Sao Điều Này Quan Trọng

Không có context header, chunk `"A.9.1.1 — Cần thiết lập chính sách kiểm soát truy cập..."` không có chỉ báo thuộc tiêu chuẩn hay mục nào. Với tiền tố:

```
[Context: # ISO 27001:2022 > ## Annex A > ### A.9]
A.9.1.1 Cần thiết lập chính sách kiểm soát truy cập...
```

Model embedding thấy được toàn bộ ngữ cảnh phân cấp, cải thiện đáng kể độ chính xác truy xuất cho các query như "ISO 27001 access control" so với "TCVN 11930 access control".

---

## 4. Pipeline Indexing

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `index_documents()`

### Auto-Index Khi Khởi Động

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

Chỉ index nếu collection rỗng — không index trùng khi khởi động lại.

### Quy Trình Index Đầy Đủ

```python
def index_documents(self, docs_dir=None):
    docs_dir = docs_dir or "/data/iso_documents"
    documents, metadatas, ids = [], [], []

    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = self._chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{i}"
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_index": i})
            ids.append(doc_id)

    # Upsert theo lô vào ChromaDB
    self.collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"[VectorStore] Indexed {len(ids)} chunks from {docs_dir}")
```

### Buộc Re-index

```
POST /api/iso27001/reindex
```

Xóa và xây lại toàn bộ collection:

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

## 5. API Tìm Kiếm

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `search()`

### Tìm Kiếm Cơ Bản

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

### Định Dạng Kết Quả

```python
[
  {
    "id":       "iso27001_annex_a.md_42",
    "document": "[Context: # ISO 27001 > ## Annex A > ### A.9]\nA.9.1.1 Chính sách...",
    "metadata": { "source": "iso27001_annex_a.md", "chunk_index": 42 },
    "distance": 0.12     # thấp hơn = tương tự hơn
  },
  ...
]
```

### Diễn Giải Khoảng Cách

| Khoảng cách | Ý nghĩa |
|-------------|---------|
| 0.0–0.2 | Độ liên quan rất cao |
| 0.2–0.4 | Độ liên quan cao |
| 0.4–0.6 | Độ liên quan trung bình |
| 0.6–1.0 | Độ liên quan thấp |
| > 1.0 | Không liên quan |

---

## 6. Tìm Kiếm Đa Query

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py) — `multi_query_search()`

Với các query phức tạp, tạo nhiều biến thể để cải thiện recall:

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

    # Sắp xếp theo distance, trả về top_k
    merged = sorted(seen_ids.values(), key=lambda x: x["distance"])
    return merged[:top_k]
```

**Khi nào dùng:** Pipeline ISO assessment dùng `multi_query_search` để tối đa độ phủ truy xuất kiến thức trên tất cả controls liên quan.

---

## 7. Collection Intent Classifier

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

Collection ChromaDB **in-memory** riêng biệt được dùng để phân loại intent chat người dùng.

### Thiết Lập

```python
_client = chromadb.Client()   # in-memory, không bền vững

def _get_intent_collection():
    collection = _client.get_or_create_collection(
        name="intent_classifier",
        metadata={"hnsw:space": "cosine"}
    )
    if collection.count() == 0:
        _seed_examples(collection)
    return collection
```

### Ví Dụ Seed

```python
def _seed_examples(collection):
    examples = [
        # Ví dụ route security
        ("ISO 27001 Annex A controls là gì?",            "security"),
        ("Giải thích yêu cầu chính sách kiểm soát truy cập", "security"),
        ("Cách triển khai mã hóa theo ISO 27001?",       "security"),
        # Ví dụ route search
        ("Tin tức ransomware mới nhất hôm nay",          "search"),
        ("Sự kiện an ninh mạng gần đây tuần này",        "search"),
        # Ví dụ route general
        ("HTTPS hoạt động như thế nào?",                 "general"),
        ("Sự khác biệt giữa IDS và IPS là gì?",          "general"),
    ]
    collection.upsert(
        documents=[e[0] for e in examples],
        metadatas=[{"route": e[1]} for e in examples],
        ids=[f"ex_{i}" for i in range(len(examples))]
    )
```

### Phân Loại

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

## 8. Thao Tác Quản Trị

### Endpoint Thống Kê

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

### Endpoint Tìm Kiếm

```
POST /api/iso27001/chromadb/search
{ "query": "kiểm soát truy cập", "top_k": 5 }
```

Có thể dùng từ giao diện ChromaDB Explorer trên trang Analytics.

### Endpoint Re-index

```
POST /api/iso27001/reindex
```

Xóa và xây lại collection `iso_documents`. Dùng khi file tài liệu ISO được cập nhật.

---

## 9. Cấu Trúc Thư Mục Dữ Liệu

```
data/
├── vector_store/                   ← Thư mục lưu ChromaDB
│   ├── chroma.sqlite3              ← metadata + index embeddings
│   └── {collection-uuid}/
│       ├── data_level0.bin         ← HNSW graph level 0
│       ├── header.bin
│       ├── length.bin
│       └── link_lists.bin
│
└── iso_documents/                  ← File markdown nguồn
    ├── iso27001_annex_a.md
    ├── assessment_criteria.md
    ├── checklist_danh_gia_he_thong.md
    ├── luat_an_ninh_mang_2018.md
    ├── network_infrastructure.md
    ├── nghi_dinh_13_2023_bvdlcn.md
    └── tcvn_11930_2017.md
```

---

## 10. Xử Lý Sự Cố

### Collection rỗng (không có kết quả tìm kiếm)

```bash
# Buộc re-index qua API
curl -X POST http://localhost:8000/api/iso27001/reindex

# Hoặc kiểm tra số file
docker exec <backend_container> ls -la /data/iso_documents/
```

### Số chunk sai sau khi cập nhật tài liệu

Sau khi chỉnh sửa file trong `data/iso_documents/`, buộc re-index:

```
POST /api/iso27001/reindex
```

### Lỗi SQLite lock ChromaDB

Xảy ra khi hai process cùng truy cập `PersistentClient`. Backend là single-process (Uvicorn), không nên xảy ra. Nếu có:

```bash
docker restart <backend_container>
```

### Xác Minh Nội Dung Collection

```bash
# Kiểm tra thống kê
curl http://localhost:8000/api/iso27001/chromadb/stats

# Test tìm kiếm ngữ nghĩa
curl -X POST http://localhost:8000/api/iso27001/chromadb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "chính sách kiểm soát truy cập", "top_k": 3}'
```

### Giá Trị Distance Cao > 0.9 (truy xuất kém)

Cho thấy embedding không khớp tốt. Kiểm tra:
1. Ngôn ngữ query khớp ngôn ngữ tài liệu (hầu hết tài liệu là tiếng Việt+Anh hỗn hợp)
2. Tài liệu được chunk đúng (kiểm tra `chunk_index` trong metadata)
3. Thử re-index: `POST /api/iso27001/reindex`
