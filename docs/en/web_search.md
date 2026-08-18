# Web Search Service — DuckDuckGo Integration

> **Module:** [`backend/services/web_search.py`](../../backend/services/web_search.py)
> **Trigger:** Hybrid intent classifier in [`backend/services/model_router.py:173-213`](../../backend/services/model_router.py) routes a message to `intent="search"` → `ChatService` calls `WebSearch.search()` and injects `WebSearch.format_context()` into the LLM prompt.

---

## 1. Why a Search Service?

CyberAI is built around an offline RAG corpus (`data/iso_documents/`) but
some user questions need fresh web context (CVE advisories, vendor news,
"latest version of …"). To stay zero-cost and zero-API-key, the platform
calls DuckDuckGo via the **`ddgs`** Python package (with
**`duckduckgo-search`** as a backwards-compatible fallback).

---

## 2. Public API

```python
class WebSearch:
    @staticmethod
    def search(query: str, max_results: int = 5, retries: int = 2) -> List[Dict[str, str]]
    @staticmethod
    def format_context(results: List[Dict[str, str]]) -> str
```

Source: [`backend/services/web_search.py:14-64`](../../backend/services/web_search.py)

### Result schema

```json
[
  { "title": "…", "url": "https://…", "snippet": "…" }
]
```

---

## 3. Algorithm

```
1. Try `from ddgs import DDGS`.
   On ImportError, try `from duckduckgo_search import DDGS`.
   If both fail → log error, return [].

2. For attempt in range(retries + 1):
     with DDGS(headers={"User-Agent": USER_AGENT}) as ddgs:
         raw = list(ddgs.text(query, max_results=max_results, region="vn-vi"))
     if raw:
         return [ {title, url, snippet} for item in raw ]
     else:
         sleep(1) and retry
   On exception → log warning, sleep(2), retry.

3. After retries → log warning, return [].
```

| Knob | Value | Where |
|---|---|---|
| `region` | `vn-vi` | Hard-coded — biases results toward Vietnamese sources |
| `max_results` | `5` (default) | Tunable per call |
| `retries` | `2` (default) → 3 attempts total | Tunable per call |
| `User-Agent` | Chrome 120 desktop string | `web_search.py:7-11` to dodge bot-walls |
| Back-off | `1s` between empty results, `2s` after exception | Linear, no jitter |

---

## 4. Library Resolution Order

| Package | Status | Behaviour |
|---|---|---|
| `ddgs` | **preferred** — modern fork | Listed in `backend/requirements.txt` as `ddgs` (alias) and `duckduckgo-search>=6.2` |
| `duckduckgo-search` | legacy fallback | Same `DDGS` symbol; ddgs is its successor |

If both packages are absent the call returns `[]` rather than raising — the
caller (`ChatService`) falls back to a no-context generation so chat never
blocks on a missing optional dep.

---

## 5. Context Formatting

`format_context()` joins results into the exact block shape the chat
prompt expects:

```
[1] <title>
URL: <url>
<snippet>

---

[2] <title>
URL: <url>
<snippet>
```

This is appended to the system prompt under the heading produced by
[`ChatService._build_messages`](../../backend/services/chat_service.py)
(see lines 208-258). The numbered prefix lets the LLM cite sources back to
the user (e.g. "according to [2] …").

---

## 6. Routing — When Web Search Fires

The decision is made by the **hybrid router** in
[`backend/services/model_router.py:173-213`](../../backend/services/model_router.py):

1. Semantic classification against the `intent_collection` ChromaDB
   collection seeded with `INTENT_TEMPLATES`.
2. If semantic confidence ≥ 0.6 → use semantic intent.
3. Otherwise, keyword fallback against `SEARCH_KEYWORDS` (e.g. "tìm",
   "search", "google", "tin tức", "news", "cve", "cập nhật").
4. Final intent ∈ `{"security", "search", "general"}`. Only `search`
   triggers `WebSearch.search()`.

This means RAG-eligible cyber-security questions **stay local** and never
touch the public internet.

---

## 7. Operational Notes

| Topic | Notes |
|---|---|
| **No API key** | DuckDuckGo HTML/JSON scrape — usage is best-effort, not SLA-backed |
| **Rate limiting** | DDG can return 202/empty under load — the retry+backoff loop is the only mitigation |
| **Privacy** | Only the user's verbatim query is sent; no session/PII attached |
| **Egress** | Outbound HTTPS to `duckduckgo.com`. Allow this in nginx/firewall if you run in a hardened environment |
| **Disable** | Drop `ddgs` and `duckduckgo-search` from `backend/requirements.txt` — `WebSearch.search()` will safely return `[]` |

---

## 8. Failure Modes

| Symptom | Likely cause | Mitigation |
|---|---|---|
| Always returns `[]` | DDG temporarily blocking the egress IP | Wait, or proxy egress through a residential exit |
| `ImportError` log on first call | Neither `ddgs` nor `duckduckgo-search` installed | `pip install ddgs` |
| Stale or off-topic results | `region="vn-vi"` over-filters English sources | Pass an English query or relax region (requires code change) |
| Long latency | DDG slow + 2 retries × 2s back-off | Lower `retries` for latency-sensitive flows |

---

## 9. See Also

- [`docs/en/algorithms.md`](algorithms.md) — full hybrid intent classifier
  algorithm.
- [`docs/en/chatbot_rag.md`](chatbot_rag.md) — how search context blends
  with RAG context inside the prompt.
- [`docs/en/architecture.md`](architecture.md) — egress topology in
  Docker/nginx deployments.
