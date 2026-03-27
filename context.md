# CyberAI Assessment Platform — Dev Context (27/03/2026)

## Tech Stack
- **Frontend**: Next.js 15 App Router, CSS Modules, ReactMarkdown
- **Backend**: FastAPI Python 3.11
- **AI Local**: LocalAI v2.24.2 — SecurityLM 7B (Phase 1) + Meta-Llama 8B (Phase 2)
- **AI Cloud**: Open Claude API (Gemini) — primary for news/chat, fallback for assessment
- **Vector DB**: ChromaDB cosine similarity, 221 chunks từ 21 `.md` tài liệu
- **Proxy**: Next.js rewrites `/api/*` → `http://backend:8000/api/*`

---

## LocalAI Model Config (quan trọng)
```
MODEL_NAME=Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf     # Phase 2 + chat — ~5GB RAM
SECURITY_MODEL_NAME=SecurityLLM-7B-Q4_K_M.gguf         # Phase 1 GAP — ~4GB RAM
INFERENCE_TIMEOUT=300                                    # 300s cho chunked analysis
```
Container limit: 12GB. Tổng 2 models = ~9GB → vừa đủ.
**KHÔNG dùng 70B** — cần 40GB RAM, sẽ crash với `rpc error: Canceled`.

---

## AI Routing
| task_type | Model | Ghi chú |
|-----------|-------|---------|
| `iso_local` | SecurityLM 7B | Phase 1 — chunked GAP per category. Priority=True, preempts news |
| `iso_analysis` | Cloud (gemini-2.5-pro) | Phase 2 — format full report |
| `news_translate` | gemini-2.5-pro | EN→VI translation |
| `news_summary` | gemini-3-flash | Tóm tắt bài viết |
| `chat` | gemini-3-pro | Chat chung |

---

## Assessment Pipeline (2-Phase)

```
[Form submit] → BackgroundTask → poll 10s
    ↓
[Health check] localai_health_check(15s)
    FAIL → local→hybrid, hybrid→cloud auto-fallback
    ↓
[Phase 1 — SecurityLM 7B] Chunked per ISO category
    Per category: compact prompt ~800 tokens
        = sys_summary[:400] + RAG context[:350] + missing controls list
    Output: JSON array [{id, severity, likelihood, impact, risk, gap, recommendation}]
    Validate → retry ×2 → fallback infer_gap_from_control if all fail
    ↓
[Aggregate] gap_items_to_markdown() → Risk Register markdown
    compress_for_phase2() if > 2500 chars
    ↓
[Phase 2 — Meta-Llama 8B / Cloud] Format full report
    5 sections: Tổng quan / Risk Register / GAP Analysis / Action Plan / Executive Summary
    ↓
[json_data] _build_structured_json() → dashboard: risk_summary, weight_breakdown, top_gaps
```

### Điểm yếu LocalAI SecurityLM 7B — Nguyên nhân và Giải pháp

**Vấn đề cốt lõi:**
1. **Input quá lớn** — SecurityLM 7B context window = 4096 tokens. Prompt cũ > 2000 tokens → model "cắt đầu" input, quên system context
2. **Model không "khôn"** — 7B Q4 quantized: 4-bit precision, knowledge bị nén mạnh → reasoning về ISO 27001 kém
3. **Format mismatch** — Model không được fine-tune cho JSON output → hay trả markdown bảng thay vì JSON array
4. **Severity hallucination** — Mọi GAP đều "critical" vì model không hiểu risk scoring

**Đã fix:**
- Compact prompt < 800 tokens/chunk (sys_summary[:400] + RAG[:350] + 15 controls max)
- Few-shot examples: 2 JSON mẫu đúng format trực tiếp trong prompt
- Control ID whitelist: loại bỏ IDs không thuộc tiêu chuẩn
- Retry × 2 + validate_chunk_output() + infer_gap_from_control() fallback

**Giải pháp tiếp theo để tăng output quality:**

| Giải pháp | Cách làm | Khả thi? | Lợi ích |
|-----------|---------|---------|---------|
| **Fine-tune với sample_training_pairs.jsonl** | QLoRA Llama-3-8B, 10 pairs mẫu + generated pairs | ✅ Có dataset sẵn | Output chuẩn format, đúng control IDs |
| **Prompt engineering nâng cao** | Chain-of-thought: "Think step by step before outputting JSON" | ✅ Ngay bây giờ | Tăng reasoning 20-30% |
| **Temperature thấp hơn** | 0.1 thay vì 0.2 → ít creative, nhiều deterministic | ✅ Ngay bây giờ | Ít hallucinate hơn |
| **2-pass approach** | Pass 1: list control IDs → Pass 2: analyze từng ID riêng | ⚠️ 2× API calls | Chính xác hơn nhưng 2× thời gian |
| **Rule-based fallback** | Nếu severity=critical rate > 80% → normalize distribution | ✅ Backend code | Realistic risk distribution |

---

## Chatbot RAG Pipeline

```
User message → model_router.py (keyword + semantic intent)
    ↓
[RAG] ChromaDB search(query, top_k=5) → inject context
[Web] DuckDuckGo search if search_intent detected
    ↓
Cloud LLM (primary) / LocalAI (fallback)
    ↓
Session history stored in /data/sessions/ (24h TTL)
```

**ChromaDB**: 221 chunks, 21 tài liệu — ISO 27001, TCVN 11930, NIST CSF/800-53, PCI-DSS, SOC 2, HIPAA, NIS2, GDPR, OWASP, CIS Controls, ND 85/2016, gap_analysis_patterns, author_profile

---

## News Pipeline

```
RSS → scrape (trafilatura/BS4) → _is_noise_paragraph() filter
    → content cutoff at "Related Articles" markers (max 12000 chars)
    → Cloud AI translate/edit → summary_vi (full text)
    → Edge-TTS vi-VN-HoaiMyNeural → MP3
    → Cache JSON + MP3 in /data/summaries/
```

**Storage**: JSON ~5KB/bài, MP3 ~200KB/bài. ~130MB/7 ngày. Không auto-delete.

---

## Files Structure quan trọng
```
backend/services/
├── chat_service.py          # Chat + Assessment orchestration
├── controls_catalog.py      # ISO 27001 + TCVN 11930 control lists (server-side)
├── assessment_helpers.py    # build_chunk_prompt, validate_chunk_output, infer_gap_from_control
├── cloud_llm_service.py     # LLM routing, LocalAI health check, priority bypass
├── summary_service.py       # News scrape + translate + TTS
├── model_guard.py           # Check GGUF files present before assessment
└── news_service.py          # RSS + background workers + ai_status

frontend-next/src/
├── app/form-iso/page.js     # Assessment form — 4 steps + result + history + templates
├── app/chatbot/page.js      # Chat UI với RAG + web search
├── app/news/page.js         # News + 7-day history tab
├── app/analytics/page.js    # Dashboard + Standards + Benchmark AI tab
├── data/controls_catalog.js # Frontend control lists (mirrors backend)
└── data/templates.js        # 6 real-org templates (bank, hospital, startup, govt...)
```

---

## TODO Nâng cấp (ưu tiên cao → thấp)

### 🔴 Quan trọng — LocalAI quality
| # | Cải tiến | Lý do cần thiết | Output |
|---|----------|-----------------|--------|
| 1 | **Few-shot examples in chunk prompt** — thêm 2-3 ví dụ JSON đúng format | SecurityLM 7B hay sai format | Giảm 50% malformed JSON, ít retry hơn |
| 2 | **Control ID whitelist validation** — nếu SecurityLM trả control ID không có trong tiêu chuẩn, loại bỏ | Hallucination control IDs | Risk Register chính xác hơn |
| 3 | **TTS dedicated summary** — thêm bước tạo 3-5 câu tóm tắt riêng cho audio (thay vì đọc full translation) | Audio hiện tại 5-15 phút/bài, quá dài | Audio 1-2 phút, dễ nghe hơn |
| 4 | **Assessment progress SSE** — frontend nhận update real-time: "Đang phân tích A.5...", "Đang phân tích A.6..." | User không biết tiến trình trong 3-5 phút | Progress bar per-category |

### 🟠 Trung bình
| # | Cải tiến | Phản biện | Quyết định |
|---|----------|-----------|-----------|
| 5 | **Per-control individual scoring** — gửi từng control riêng lẻ | 93 API calls = 93×45s = 70 phút → quá chậm | ❌ Không khả thi với LocalAI |
| 6 | **Parallel category chunks** — gửi 4 chunks song song | LocalAI single-threaded, sẽ queue/crash | ❌ LocalAI không hỗ trợ concurrent |
| 7 | **Control embedding ChromaDB** — embed control labels, semantic match | Tăng accuracy RAG; cần rebuild ChromaDB | ✅ Có giá trị, làm sau |
| 8 | **Re-assessment diff** — so sánh 2 lần đánh giá | Useful nhưng phức tạp UI | ⏳ Backlog |

### 🟡 Thấp — không cần thiết ngay
| # | Cải tiến | Phản biện |
|---|----------|-----------|
| 9 | LocalAI streaming | LocalAI không stable streaming → skip |
| 10 | MP3 archive cũ | Chỉ cần nếu disk > 80% |
| 11 | Fine-tune SecurityLM | Cần dataset + GPU → out of scope |

---

## Thay đổi đã làm (tóm tắt)

### Assessment
- [x] Chunked analysis (4 categories per assessment, ~800 tokens/chunk)
- [x] JSON output validation + retry ×2 + `infer_gap_from_control` fallback
- [x] RAG per-category (ChromaDB lookup cho từng nhóm control)
- [x] Health check + auto-fallback (local→hybrid→cloud)
- [x] `controls_catalog.py` — server-side ISO 27001 + TCVN 11930 authoritative data
- [x] `assessment_helpers.py` — tách helper functions ra module riêng
- [x] Benchmark API (`/api/benchmark/run`) + scoring 15 điểm
- [x] Benchmark AI tab trong Analytics (model comparison UI)

### Chatbot
- [x] Suggestion chips: TCVN 11930 đúng, thêm "Tác giả CyberAI là ai?"
- [x] 21 ChromaDB documents: NIST, PCI-DSS, SOC 2, HIPAA, NIS2, GDPR, OWASP, author_profile

### News
- [x] History tab inline (thay sidebar) với date filter default = hôm nay
- [x] `_is_noise_paragraph()` mở rộng: related articles, tags, cookie banners
- [x] Content cutoff tại "Related Articles" markers trước khi gửi AI
- [x] Text truncate từ 30,000 → 12,000 chars

### UI/UX
- [x] Form ISO: auto-save draft localStorage, scope definition (full/department/system)
- [x] History tab grid layout (3 cột CSS grid thay flex)
- [x] Processing card: numbered steps với animation
- [x] Standards page: FormatGuidePanel modal (JSON/YAML/ChromaDB diff)

### Infra
- [x] `.gitignore`: runtime data, context.md, summaries, assessments excluded
- [x] `docker-compose.prod.yml`: Nginx, healthchecks, resource limits
- [x] `.env`: MODEL_NAME=8B (fix 70B OOM), INFERENCE_TIMEOUT=300s
- [x] Benchmark dataset: 4 test cases với expected output criteria
