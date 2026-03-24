# Context — CyberAI Platform

> File này để tham khảo nhanh khi hỏi đáp, lên plan, hoặc code. Cập nhật liên tục theo tiến độ.

---

## 1. Tech Stack

| Tầng | Công nghệ |
|------|----------|
| Frontend | Next.js 14 (App Router), React, CSS Modules |
| Backend | FastAPI (Python 3.11), Uvicorn |
| AI chính | Open Claude (round-robin nhiều API key) |
| AI dự phòng | LocalAI (self-hosted, tương thích OpenAI) |
| Vector DB | ChromaDB (collection `iso_documents`, cosine, chunk_size=600) |
| TTS | Microsoft Edge TTS (giọng `vi-VN-HoaiMyNeural`) |
| Tìm kiếm web | DuckDuckGo (thư viện `ddgs`) |
| Container | Docker Compose (backend:8000, frontend:3000) |

---

## 2. Định Tuyến Model AI

```python
TASK_MODEL_MAP = {
    "news_translate": "gemini-2.5-pro",        # Dịch toàn bộ bài báo
    "news_summary":   "gemini-3-flash-preview", # Tóm tắt nhanh
    "iso_analysis":   "gemini-2.5-pro",         # Phân tích ISO GAP
    "complex":        "gemini-2.5-pro",          # Chat phức tạp
    "chat":           "gemini-3-pro-preview",    # Chat thông thường
    "default":        "gemini-3-pro-preview",    # Mặc định
}
# Chuỗi dự phòng: Open Claude → LocalAI (KHÔNG có OpenRouter)
```

---

## 3. Chat Router (3 route)

- **security** → RAG với ChromaDB `iso_documents`
- **search** → Tìm kiếm web DuckDuckGo
- **general** → Gọi LLM trực tiếp

Phân loại hybrid: ngữ nghĩa (ChromaDB `intent_classifier`, confidence > 0.6) → keyword fallback

---

## 4. Session Memory

- Lưu tối đa: 20 tin nhắn/session
- Gửi lên LLM: `history[-10:]` (10 tin nhắn cuối)
- TTL: 86400s (24 giờ)
- Lưu tại: `/data/sessions/{session_id}.json`

---

## 5. Cơ Chế Chấm Điểm ISO Assessment

### Logic hiện tại (`backend/services/chat_service.py`)

```python
score = len(implemented_controls)   # đếm số controls đã tick
max_score = 93   # ISO 27001:2022
# max_score = 34  # TCVN 11930:2017
percentage = round((score / max_score) * 100, 1)
```

**Chỉ là đếm số lượng** — mỗi control tích = 1 điểm, không có trọng số.

### 2 Phase AI tạo báo cáo
- **Phase 1** (task `iso_analysis` → gemini-2.5-pro): AI Auditor tìm GAP/rủi ro từ dữ liệu thô
- **Phase 2** (task `default` → gemini-3-pro-preview): Định dạng thành báo cáo Markdown gồm:
  1. ĐÁNH GIÁ TỔNG QUAN (Executive Summary + %)
  2. PHÂN TÍCH LỖ HỔNG (GAP Analysis)
  3. KHUYẾN NGHỊ ƯU TIÊN (Action Plan)

### Tiêu chuẩn hỗ trợ
| Tiêu chuẩn | Max Controls | Giá trị field |
|------------|-------------|---------------|
| ISO 27001:2022 | 93 | `assessment_standard = "iso27001"` |
| TCVN 11930:2017 | 34 | `assessment_standard = "tcvn11930"` |

### Luồng API
```
POST /api/iso27001/assess
→ HTTP 202 { status:"accepted", id }   ← trả ngay lập tức
→ BackgroundTasks chạy process_assessment_bg()
→ Trạng thái: pending → processing → completed/failed

GET /api/iso27001/assessments/{id}
→ { status, result.report, result.model_used }

Frontend poll mỗi 10s (POLL_INTERVAL = 10000ms)
```

---

## 6. Form ISO — Wizard 4 Bước

| Bước | Nội dung |
|------|---------|
| 1 | Chọn tiêu chuẩn + Thông tin tổ chức (tên, quy mô, ngành, nhân viên, trạng thái ISO) |
| 2 | Hạ tầng (server, firewall, cloud, antivirus, backup, SIEM, VPN, sự cố) |
| 3 | Checklist controls (accordion theo category, chọn-tất-cả, panel thông tin) |
| 4 | Mô tả topology mạng + ghi chú + tóm tắt trước khi gửi |

State quan trọng: `form.implemented_controls` = mảng các control ID đã tích

---

## 7. Kết quả Tab — Đã Cải Thiện (24/03/2025)

### Những gì đã sửa:
1. ✅ **Score Hero Card** — hiển thị % to, badge mức độ tuân thủ, stats 3 cột
2. ✅ **Trạng thái xử lý** — animated spinner card với 3 bước progress thay vì text đơn giản
3. ✅ **Action bar** — nút Sao chép / In / Đánh giá mới
4. ✅ **Model chips** — hiển thị inline gần score, không bị chôn xuống dưới
5. ✅ **Fix `[Ngày hiện tại]`** — backend inject ngày thực vào prompt Phase 2
6. ✅ **Markdown đẹp hơn** — h2 có border trái xanh, blockquote styled, hr separator
7. ✅ **Print styles** — ẩn navigation khi in

### Các mức điểm:
| % | Màu | Badge |
|---|-----|-------|
| < 25% | Đỏ | 🔴 Không tuân thủ |
| 25–49% | Cam/Vàng | 🟠 Tuân thủ thấp |
| 50–79% | Xanh dương | 🟡 Tuân thủ một phần |
| ≥ 80% | Xanh lá | ✅ Tuân thủ cao |

---

## 8. Map File Quan Trọng

| File | Mục đích |
|------|---------|
| `frontend-next/src/app/form-iso/page.js` | Form + result + history (770+ dòng) |
| `frontend-next/src/app/form-iso/page.module.css` | Toàn bộ style (1450+ dòng) |
| `frontend-next/src/data/standards.js` | ASSESSMENT_STANDARDS — danh sách controls |
| `frontend-next/src/data/controlDescriptions.js` | Nội dung panel chi tiết theo control |
| `backend/api/routes/iso27001.py` | API routes (assess, list, get, delete, reindex) |
| `backend/services/chat_service.py` | `assess_system()` — 2-phase AI report |
| `backend/repositories/vector_store.py` | ChromaDB (iso_documents, chunk=600) |

---

## 9. Biến CSS Quan Trọng (globals.css)

```css
--bg-card, --bg-subtle, --bg-muted
--text-primary, --text-secondary, --text-dim, --text-muted
--accent-blue, --accent-green, --accent-red, --accent-yellow, --accent-purple
--blue-subtle, --green-subtle, --red-subtle, --yellow-subtle
--border, --border-active, --shadow-md, --shadow-lg
```

---

## 10. TODO Tiếp Theo (Gợi ý)

- [ ] Weighted scoring: phân loại controls theo mức độ quan trọng (Critical/High/Medium/Low)
- [ ] Export PDF thực sự thay vì chỉ window.print()
- [ ] History tab: thêm cột % điểm tuân thủ
- [ ] Thêm animation gauge tròn SVG thực thay vì border CSS hack
