# Web Search Service — Tích hợp DuckDuckGo

> **Module:** [`backend/services/web_search.py`](../../backend/services/web_search.py)
> **Kích hoạt:** Hybrid intent classifier trong [`backend/services/model_router.py:173-213`](../../backend/services/model_router.py) phân loại câu hỏi vào `intent="search"` → `ChatService` gọi `WebSearch.search()` rồi nhét `WebSearch.format_context()` vào prompt LLM.

---

## 1. Vì sao cần Web Search?

CyberAI lấy gốc từ corpus RAG offline (`data/iso_documents/`) nhưng có
những câu hỏi cần ngữ cảnh web tươi (CVE mới, tin nhà cung cấp, "phiên
bản mới nhất của …"). Để giữ zero-cost và không cần API-key, platform gọi
DuckDuckGo qua package **`ddgs`** (với fallback ngược về
**`duckduckgo-search`**).

---

## 2. API công khai

```python
class WebSearch:
    @staticmethod
    def search(query: str, max_results: int = 5, retries: int = 2) -> List[Dict[str, str]]
    @staticmethod
    def format_context(results: List[Dict[str, str]]) -> str
```

Nguồn: [`backend/services/web_search.py:14-64`](../../backend/services/web_search.py)

### Schema kết quả

```json
[
  { "title": "…", "url": "https://…", "snippet": "…" }
]
```

---

## 3. Thuật toán

```
1. Thử `from ddgs import DDGS`.
   Nếu ImportError → thử `from duckduckgo_search import DDGS`.
   Nếu cả 2 fail → log error, trả về [].

2. For attempt in range(retries + 1):
     with DDGS(headers={"User-Agent": USER_AGENT}) as ddgs:
         raw = list(ddgs.text(query, max_results=max_results, region="vn-vi"))
     Nếu raw → trả [ {title, url, snippet} for item in raw ]
     Nếu không → sleep(1), retry.
   Nếu exception → log warning, sleep(2), retry.

3. Hết retries → log warning, trả [].
```

| Thông số | Giá trị | Vị trí |
|---|---|---|
| `region` | `vn-vi` | Hard-code — ưu tiên nguồn tiếng Việt |
| `max_results` | `5` (mặc định) | Tuỳ chỉnh từng call |
| `retries` | `2` (mặc định) → tổng 3 lần | Tuỳ chỉnh từng call |
| `User-Agent` | Chuỗi Chrome 120 desktop | `web_search.py:7-11` để né bot-wall |
| Back-off | `1s` khi rỗng, `2s` sau exception | Tuyến tính, không jitter |

---

## 4. Thứ tự resolve thư viện

| Package | Trạng thái | Hành vi |
|---|---|---|
| `ddgs` | **ưu tiên** — fork mới | Trong `backend/requirements.txt` |
| `duckduckgo-search` | fallback cũ | Cùng symbol `DDGS`; ddgs là phiên bản kế thừa |

Nếu cả 2 đều thiếu, hàm trả `[]` thay vì raise — caller (`ChatService`)
sẽ fall back về sinh không-context, chat không bị chặn vì thiếu dep tuỳ
chọn.

---

## 5. Định dạng context

`format_context()` ghép kết quả thành block đúng cấu trúc mà prompt chat
mong đợi:

```
[1] <title>
URL: <url>
<snippet>

---

[2] <title>
URL: <url>
<snippet>
```

Đoạn này được nối vào system prompt dưới tiêu đề mà
[`ChatService._build_messages`](../../backend/services/chat_service.py)
(dòng 208-258) tạo ra. Tiền tố đánh số cho phép LLM trích dẫn ngược về
người dùng (ví dụ "theo [2] …").

---

## 6. Routing — khi nào Web Search được gọi

Quyết định nằm ở **hybrid router**
[`backend/services/model_router.py:173-213`](../../backend/services/model_router.py):

1. Semantic classification với collection ChromaDB `intent_collection`
   được seed từ `INTENT_TEMPLATES`.
2. Nếu confidence ≥ 0.6 → dùng semantic intent.
3. Ngược lại → keyword fallback với `SEARCH_KEYWORDS` ("tìm", "search",
   "google", "tin tức", "news", "cve", "cập nhật" …).
4. Intent cuối cùng ∈ `{"security", "search", "general"}`. Chỉ `search`
   mới gọi `WebSearch.search()`.

Nghĩa là câu hỏi an ninh thuộc phạm vi RAG **giữ ở local**, không bao giờ
chạm internet công cộng.

---

## 7. Ghi chú vận hành

| Chủ đề | Ghi chú |
|---|---|
| **Không API-key** | DDG scrape HTML/JSON — best-effort, không có SLA |
| **Rate limit** | DDG có thể trả 202/rỗng khi tải cao — vòng retry+backoff là biện pháp duy nhất |
| **Quyền riêng tư** | Chỉ truy vấn nguyên văn được gửi; không kèm session/PII |
| **Egress** | HTTPS ra `duckduckgo.com`. Cần allow ở nginx/firewall nếu môi trường hardened |
| **Tắt** | Bỏ `ddgs` và `duckduckgo-search` khỏi `backend/requirements.txt` — `WebSearch.search()` sẽ trả `[]` an toàn |

---

## 8. Chế độ lỗi

| Triệu chứng | Nguyên nhân | Khắc phục |
|---|---|---|
| Luôn trả `[]` | DDG tạm block IP egress | Đợi, hoặc proxy egress qua residential exit |
| Log `ImportError` lần gọi đầu | Chưa cài `ddgs`/`duckduckgo-search` | `pip install ddgs` |
| Kết quả lệch chủ đề / cũ | `region="vn-vi"` lọc quá tay nguồn EN | Truy vấn bằng EN hoặc nới region (phải đổi code) |
| Latency cao | DDG chậm + 2 retry × 2s | Hạ `retries` cho luồng nhạy độ trễ |

---

## 9. Xem thêm

- [`docs/vi/algorithms.md`](algorithms.md) — toàn bộ hybrid intent
  classifier.
- [`docs/vi/chatbot_rag.md`](chatbot_rag.md) — cách context search hoà
  với context RAG trong prompt.
- [`docs/vi/architecture.md`](architecture.md) — topo egress trong Docker/nginx.
