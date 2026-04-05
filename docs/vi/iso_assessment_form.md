# Form Đánh Giá ISO 27001 — Phân Tích Kỹ Thuật

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-ISO_Assessment-blue?style=flat-square)](iso_assessment_form.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Đánh_giá_ISO-red?style=flat-square)](iso_assessment_form_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Sơ Đồ Luồng Đầu Cuối](#2-sơ-đồ-luồng-đầu-cuối)
3. [Cấu Trúc Form — Wizard 4 Bước](#3-cấu-trúc-form--wizard-4-bước)
4. [Đánh Giá Async — BackgroundTasks](#4-đánh-giá-async--backgroundtasks)
5. [Pipeline Phân Tích AI](#5-pipeline-phân-tích-ai)
6. [Cơ Sở Kiến Thức — Tài Liệu ISO](#6-cơ-sở-kiến-thức--tài-liệu-iso)
7. [Định Dạng Kết Quả Đánh Giá](#7-định-dạng-kết-quả-đánh-giá)
8. [Cơ Chế Polling](#8-cơ-chế-polling)
9. [Hỗ Trợ Đa Tiêu Chuẩn](#9-hỗ-trợ-đa-tiêu-chuẩn)
10. [Lưu Trữ Dữ Liệu](#10-lưu-trữ-dữ-liệu)

---

## 1. Tổng Quan

Module Đánh Giá ISO 27001 đánh giá mức độ tuân thủ bảo mật thông tin của tổ chức theo các controls ISO 27001:2022 (và TCVN 14423). Hệ thống hoạt động **bất đồng bộ** — người dùng gửi form và nhận ngay job ID; phân tích AI chạy trong luồng nền và kết quả được polling.

| Tính năng | Chi tiết |
|---------|---------|
| Tiêu chuẩn | ISO 27001:2022 (mặc định), TCVN 14423 (tùy chọn) |
| Model AI | `gemini-2.5-pro` qua Open Claude (task_type=`iso_analysis`) |
| Thực thi | FastAPI `BackgroundTasks` (async, không chặn) |
| Lưu trữ | File JSON: `/data/assessments/{uuid4}.json` |
| Polling | Frontend poll `GET /api/iso27001/assessments/{id}` mỗi 3s |
| Kiến thức | ChromaDB `iso_documents` — 7 tài liệu ISO/pháp lý |

---

## 2. Sơ Đồ Luồng Đầu Cuối

```
Người dùng điền form 4 bước
           │
           ▼
POST /api/iso27001/assess  { system_info, controls[], standard_id }
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│  iso27001.py — assess()                                      │
│                                                              │
│  1. assessment_id = str(uuid4())                             │
│  2. Lưu JSON { id, status:"pending", data:{...} }            │
│     → /data/assessments/{id}.json                            │
│  3. background_tasks.add_task(process_assessment_bg, id)     │
│  4. Trả về HTTP 202 { id, status:"pending" }                 │
└──────────────────────────┬───────────────────────────────────┘
                           │ phản hồi ngay lập tức cho frontend
                           │
         ┌─────────────────┘
         │  [Luồng Nền — FastAPI BackgroundTasks]
         ▼
┌──────────────────────────────────────────────────────────────┐
│  process_assessment_bg(assessment_id)                        │
│                                                              │
│  1. Load JSON từ /data/assessments/{id}.json                 │
│  2. ChatService.assess_system(system_data)                   │
│     a. VectorStore.search(query, top_k=5)                    │
│        → Truy xuất controls ISO liên quan từ ChromaDB        │
│     b. Xây dựng system_prompt + user_prompt chi tiết         │
│     c. CloudLLMService.chat_completion(                      │
│           task_type="iso_analysis"                           │
│        )  → gemini-2.5-pro qua Open Claude                   │
│           → LocalAI dự phòng nếu Open Claude thất bại        │
│  3. Cập nhật JSON { status:"done", result:{...} }            │
└──────────────────────────────────────────────────────────────┘
         │
         │  [Frontend poll mỗi 3 giây]
         ▼
GET /api/iso27001/assessments/{id}
→ { id, status:"pending" }   (đang xử lý)
→ { id, status:"done", result:{...} }  (hoàn thành)
```

---

## 3. Cấu Trúc Form — Wizard 4 Bước

File: [`frontend-next/src/app/form-iso/page.js`](../frontend-next/src/app/form-iso/page.js)

### Bước 1 — Tiêu Chuẩn & Thông Tin Công Ty

```
┌──────────────────────────────────────────────────────┐
│  Chọn tiêu chuẩn:  [ISO 27001:2022] [TCVN 14423]    │
│                                                       │
│  Tên công ty:      [____________________]             │
│  Lĩnh vực:         [____________________]             │
│  Mô tả hệ thống:   [____________________]             │
└──────────────────────────────────────────────────────┘
```

### Bước 2 — Chọn Controls Bảo Mật

Tổ chức theo danh mục control (miền Annex A):

```
┌──────────────────────────────────────────────────────────────┐
│  A.5 Chính sách an toàn thông tin         [Chọn tất cả]      │
│  ☑ A.5.1 Chính sách an toàn thông tin                        │
│  ☑ A.5.2 Vai trò và trách nhiệm bảo mật                      │
│                                                              │
│  A.9 Kiểm soát truy cập                   [Chọn tất cả]      │
│  ☑ A.9.1 Yêu cầu nghiệp vụ về kiểm soát truy cập            │
│  ☐ A.9.2 Quản lý truy cập người dùng                        │
└──────────────────────────────────────────────────────────────┘
```

### Bước 3 — Tình Trạng Bảo Mật Hiện Tại

Câu hỏi nhị phân/ba giá trị về các controls hiện có:

| Trường | Tùy chọn |
|--------|---------|
| `firewall` | yes / no |
| `antivirus` | yes / no |
| `backup` | yes / partial / no |
| `patch_management` | yes / no |
| `incident_response` | yes / no |
| `access_control` | yes / partial / no |
| `encryption` | yes / partial / no |
| `employee_training` | yes / no |
| `physical_security` | yes / no |
| `risk_assessment` | yes / partial / no |

### Bước 4 — Xem Lại & Gửi

Hiển thị tóm tắt tất cả controls đã chọn và thông tin hệ thống trước khi gửi.

---

## 4. Đánh Giá Async — BackgroundTasks

File: [`backend/api/routes/iso27001.py`](../backend/api/routes/iso27001.py)

### Route Handler

```python
@router.post("/iso27001/assess")
async def assess(data: SystemInfo, background_tasks: BackgroundTasks):
    assessment_id = str(uuid4())

    assessment_data = {
        "id": assessment_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "data": data.dict()
    }
    save_assessment(assessment_id, assessment_data)

    background_tasks.add_task(process_assessment_bg, assessment_id, data.dict())

    return {"id": assessment_id, "status": "pending"}
```

### Processor Nền

```python
def process_assessment_bg(assessment_id: str, system_data: dict):
    data = load_assessment(assessment_id)
    try:
        result = ChatService.assess_system(system_data)
        data["status"] = "done"
        data["result"] = result
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
    finally:
        save_assessment(assessment_id, data)
```

### Lưu File

```python
ASSESSMENTS_DIR = "/data/assessments"

def save_assessment(assessment_id, data):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 5. Pipeline Phân Tích AI

File: [`backend/services/chat_service.py`](../backend/services/chat_service.py)

### `ChatService.assess_system(system_data)`

```python
@staticmethod
def assess_system(system_data: Dict) -> Dict:
    vs = ChatService.get_vector_store()

    # 1. Xây dựng query tìm kiếm từ dữ liệu hệ thống
    query = (
        f"{system_data.get('standard_id', 'ISO 27001')} "
        f"{system_data.get('industry', '')} "
        f"{' '.join(system_data.get('controls', []))}"
    )

    # 2. Truy xuất context ISO liên quan
    context_docs = vs.search(query, top_k=5)
    context = "\n\n---\n\n".join([d["document"] for d in context_docs])

    # 3. Xây dựng AI prompt
    system_prompt = f"""Bạn là kiểm toán viên ISO 27001 chuyên nghiệp.
Phân tích thông tin hệ thống được cung cấp theo các controls ISO 27001:2022.
Tham chiếu context cơ sở kiến thức sau trong phân tích:

{context}

Cung cấp:
1. Điểm tuân thủ tổng thể (0-100)
2. Mức độ tuân thủ (Không tuân thủ / Một phần / Phần lớn / Hoàn toàn)
3. Các gap nghiêm trọng tìm thấy
4. Khuyến nghị cụ thể cho mỗi gap
5. Phân tích từng control đã chọn"""

    # 4. Gọi AI
    result = CloudLLMService.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2,
        task_type="iso_analysis"    # → gemini-2.5-pro
    )

    return {"analysis": result["content"], "model": result["model"], "provider": result["provider"]}
```

---

## 6. Cơ Sở Kiến Thức — Tài Liệu ISO

Lưu tại `data/iso_documents/` và được index vào ChromaDB (collection `iso_documents`):

| File | Nội dung | Chunks (xấp xỉ) |
|------|---------|-----------------|
| `iso27001_annex_a.md` | Toàn bộ Annex A — 93 controls với mô tả | ~120 |
| `assessment_criteria.md` | Tiêu chí đánh giá và tuân thủ | ~25 |
| `checklist_danh_gia_he_thong.md` | Checklist đánh giá hệ thống tiếng Việt | ~30 |
| `luat_an_ninh_mang_2018.md` | Luật An ninh Mạng Việt Nam 2018 | ~40 |
| `network_infrastructure.md` | Hướng dẫn và thực hành tốt nhất bảo mật mạng | ~35 |
| `nghi_dinh_13_2023_bvdlcn.md` | Nghị định 13/2023 bảo vệ dữ liệu cá nhân | ~30 |
| `tcvn_11930_2017.md` | Tiêu chuẩn CNTT TCVN 11930:2017 | ~35 |

**Tổng cộng: ~315 chunks** được index với cosine similarity, chunk_size=600, overlap=150.

---

## 7. Định Dạng Kết Quả Đánh Giá

```json
{
  "id": "7e0b008d-34d9-4c5b-bf9a-f3de2d53658e",
  "status": "done",
  "created_at": "2025-03-24T09:00:00",
  "data": {
    "company_name": "ACME Corp",
    "industry": "Tài chính",
    "controls": ["A.5.1", "A.9.1", "A.9.2"],
    "firewall": "yes",
    "patch_management": "no"
  },
  "result": {
    "analysis": "## Đánh Giá Tuân Thủ ISO 27001:2022\n\n**Điểm tổng thể: 62/100**\n\n**Mức độ tuân thủ: Một phần**\n\n### Các Gap Nghiêm Trọng:\n1. Chưa có quy trình quản lý vá lỗi...\n2. Chưa có kế hoạch ứng phó sự cố...\n\n### Khuyến Nghị:\n1. **Quản lý vá lỗi (A.12.6.1)**: Triển khai quản lý vá lỗi tự động...\n\n### Phân Tích Control:\n- **A.5.1** Chính sách bảo mật: ✅ Tuân thủ\n- **A.9.1** Chính sách kiểm soát truy cập: ⚠️ Một phần\n- **A.9.2** Quản lý truy cập người dùng: ❌ Không tuân thủ",
    "model": "gemini-2.5-pro",
    "provider": "open_claude"
  }
}
```

---

## 8. Cơ Chế Polling

### Frontend Polling (form-iso/page.js)

```js
const submit = async () => {
  const res = await fetch('/api/iso27001/assess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form)
  })
  const { id } = await res.json()

  // Bắt đầu polling
  setResult({ status: 'pending', id })
  const interval = setInterval(async () => {
    const poll = await fetch(`/api/iso27001/assessments/${id}`)
    const data = await poll.json()
    if (data.status !== 'pending') {
      clearInterval(interval)
      setResult(data)
    }
  }, 3000)   // Poll mỗi 3 giây
}
```

### Luồng Trạng Thái

```
submit()    → status: "pending"  → hiện spinner
poll()×n    → status: "pending"  → giữ spinner
poll()      → status: "done"     → hiện kết quả
poll()      → status: "error"    → hiện thông báo lỗi
```

---

## 9. Hỗ Trợ Đa Tiêu Chuẩn

File: [`frontend-next/src/data/standards.js`](../frontend-next/src/data/standards.js)

Form hỗ trợ nhiều tiêu chuẩn. Mỗi tiêu chuẩn định nghĩa bộ controls riêng:

```js
export const STANDARDS = [
  {
    id: "iso27001_2022",
    name: "ISO 27001:2022",
    categories: [
      {
        name: "A.5 Chính sách an toàn thông tin",
        controls: [
          { id: "A.5.1", name: "Chính sách an toàn thông tin" },
          { id: "A.5.2", name: "Vai trò và trách nhiệm" },
          ...
        ]
      },
      ...  // 4 danh mục, 93 controls tổng
    ]
  },
  {
    id: "tcvn14423",
    name: "TCVN 14423",
    categories: [...]
  }
]
```

### Xử Lý Đổi Tiêu Chuẩn

Khi người dùng đổi tiêu chuẩn giữa chừng, controls đã chọn bị reset:

```js
const handleStandardChange = (newStandardId) => {
  setForm(prev => ({
    ...prev,
    standard_id: newStandardId,
    controls: []           // reset lựa chọn controls
  }))
}
```

---

## 10. Lưu Trữ Dữ Liệu

### Lưu Trữ Đánh Giá

```
/data/assessments/
├── 7e0b008d-34d9-4c5b-bf9a-f3de2d53658e.json   ← status: done
├── 71789587-a7cd-4de2-94ed-09a540de90f7.json   ← status: done
└── {uuid4}.json                                  ← status: pending|done|error
```

### Load Lịch Sử (trang Analytics)

Trang analytics (`/analytics`) load tóm tắt tất cả đánh giá qua:

```
GET /api/iso27001/assessments  (list endpoint)
→ [{ id, status, created_at, company_name }, ...]
```

Nhấn vào mục để load kết quả đầy đủ:

```
GET /api/iso27001/assessments/{id}
→ { id, status, data, result }
```

### Tái Sử Dụng Đánh Giá

Nút "Tái sử dụng" trên trang analytics điền sẵn form với dữ liệu gửi ban đầu:

```js
const handleReuse = () => {
  router.push(`/form-iso?prefill=${encodeURIComponent(JSON.stringify(selectedDetail.data))}`)
}
```
