# Dataset Generator — Bộ dữ liệu fine-tune SecurityLM

> **Module:** [`backend/services/dataset_generator.py`](../../backend/services/dataset_generator.py)
> **API:** `POST /api/v1/dataset/generate`, `GET /api/v1/dataset/status` — xem [`backend/main.py:281-319`](../../backend/main.py)
> **Output:** `data/knowledge_base/finetune_iso27001.jsonl` (format Alpaca) + `data/knowledge_base/finetune_metadata.json`

---

## 1. Mục tiêu

Sinh bộ dữ liệu fine-tune dạy mô hình SecurityLM cục bộ (7B GGUF) làm
**Phase-1 GAP analysis** cho ISO 27001:2022 và TCVN 11930:2017. Pipeline
gom 2 nguồn bổ trợ:

1. **Assessment thực** đã hoàn thành trên platform
   (`data/assessments/*.json`) — nguồn chính, chất lượng cao.
2. **Kịch bản tổng hợp** do Cloud LLM (Gemini / GPT-5 / Claude) sinh tại
   thời điểm chạy, theo prompt co khung — nguồn phụ để lấp control hiếm.

Cả 2 luồng đều xuất **Alpaca JSONL** nên có thể nạp thẳng vào recipe
HuggingFace PEFT / QLoRA.

---

## 2. Tổng quan pipeline

```
┌────────────────────────┐     ┌────────────────────────┐
│ data/assessments/*.json│     │ Kịch bản hard-code     │
│ (nguồn chính)          │     │ (Startup/Bệnh viện/NH/ │
└─────────┬──────────────┘     │  CQNN/TMĐT)            │
          │                    └──────────┬─────────────┘
          ▼                               ▼
 generate_from_assessments()   generate_synthetic_pairs(count)
          │                               │  Cloud LLM
          │                               │  (task_type="iso_analysis")
          └────────────┬──────────────────┘
                       ▼
              export_to_jsonl(pairs)
                       │
                       ▼
   data/knowledge_base/finetune_iso27001.jsonl   ← Alpaca
   data/knowledge_base/finetune_metadata.json    ← metadata
```

Nguồn: [`backend/services/dataset_generator.py:209-248`](../../backend/services/dataset_generator.py)

---

## 3. API nội bộ

| Hàm | Vai trò | Vị trí |
|---|---|---|
| `generate_from_assessments() -> List[Dict]` | Biến mỗi assessment thành 1 training pair / category | `dataset_generator.py:53-140` |
| `generate_synthetic_pairs(count=20) -> List[Dict]` | Fan-out 5 kịch bản, gọi Cloud LLM, parse JSON | `dataset_generator.py:143-189` |
| `export_to_jsonl(pairs, output_path) -> int` | Ghi Alpaca JSONL, trả số dòng | `dataset_generator.py:192-206` |
| `run_full_pipeline(synthetic_count=10) -> Dict` | Orchestrate cả 3 + metadata | `dataset_generator.py:209-248` |
| `_cloud_generate(prompt, max_tokens=1000)` | Wrapper `CloudLLMService.chat_completion` với `task_type="iso_analysis"` | `dataset_generator.py:38-50` |

### Cấu trúc 1 dòng Alpaca

```json
{
  "instruction": "Phân tích GAP controls nhóm A.8 Công nghệ cho hệ thống sau:",
  "input":       "<mô tả hệ thống>",
  "output":      "[{\"id\":\"A.8.1\",\"severity\":\"high\",...}]"
}
```

---

## 4. Seed kịch bản (Synthetic)

List hard-code tại [`dataset_generator.py:145-151`](../../backend/services/dataset_generator.py):

| # | Kịch bản | Tiêu chuẩn | Category mục tiêu |
|---|---|---|---|
| 1 | Startup SaaS 30 người, AWS, không SIEM, AV cơ bản | `iso27001` | A.8 Công nghệ |
| 2 | Bệnh viện 500 nhân viên, HIS không mã hoá, Wi-Fi chung | `tcvn11930` | 2. Bảo đảm ATTT Máy chủ |
| 3 | Ngân hàng 2 000 nhân viên, Palo Alto HA, CrowdStrike, Splunk | `iso27001` | A.5 Tổ chức |
| 4 | Cơ quan nhà nước, FortiGate, BKAV, không có quy trình ứng cứu | `tcvn11930` | 5. Quản lý Vận hành |
| 5 | Công ty TMĐT, 50 server, Kaspersky, không WAF | `iso27001` | A.8 Công nghệ |

Prompt synthetic yêu cầu Cloud LLM xuất JSON nghiêm ngặt gồm
`system_input`, `missing_controls`, và mảng `gap_analysis` với
`{id, severity, likelihood, impact, risk, gap, recommendation}` / control.
Regex `r'\{.*\}'` (flag `re.DOTALL`) trích object JSON đầu tiên; dòng
parse lỗi được drop im lặng.

---

## 5. File metadata

Ghi atomically bởi `run_full_pipeline()` — xem
[`dataset_generator.py:234-245`](../../backend/services/dataset_generator.py):

```json
{
  "generated_at": "2026-04-19T14:00:00+00:00",
  "total_pairs": 137,
  "breakdown": {
    "assessments": 120,
    "synthetic": 17,
    "total": 137,
    "output": "./data/knowledge_base/finetune_iso27001.jsonl"
  },
  "format": "alpaca_jsonl",
  "target_model": "meta-llama/Llama-3-8B-Instruct",
  "fine_tune_method": "QLoRA 4-bit (lora_r=16)",
  "output_file": "./data/knowledge_base/finetune_iso27001.jsonl"
}
```

---

## 6. REST API

Cả 2 endpoint nằm trực tiếp trong `backend/main.py` (không thuộc router
con) — xem [`backend/main.py:281-319`](../../backend/main.py).

### `POST /api/v1/dataset/generate`

```bash
curl -X POST "http://localhost:8000/api/v1/dataset/generate?synthetic_count=10"
```

Chạy `run_full_pipeline()` trong `BackgroundTask`; trả `202 Accepted`
ngay để caller không block do Cloud LLM.

### `GET /api/v1/dataset/status`

```bash
curl -s http://localhost:8000/api/v1/dataset/status | jq
```

Trả `{ exists, path, size_bytes, total_pairs, breakdown, generated_at }`
đọc từ `finetune_metadata.json`.

---

## 7. Tiêu thụ JSONL

Vì output đúng chuẩn Alpaca nên mọi trainer HF-compatible đều dùng được:

```python
from datasets import load_dataset
ds = load_dataset(
    "json",
    data_files="data/knowledge_base/finetune_iso27001.jsonl",
    split="train",
)
```

Trường metadata `fine_tune_method` cố ý pin **QLoRA 4-bit, `lora_r=16`** —
đây là recipe repo validate; full-rank LoRA hoặc rank cao hơn vẫn chạy
nhưng chưa test.

---

## 8. Ghi chú vận hành

| Chủ đề | Ghi chú |
|---|---|
| **Chi phí** | Mỗi synthetic pair ~ 1 call Cloud LLM với `max_tokens=1000` |
| **Idempotency** | `export_to_jsonl` **ghi đè** JSONL mỗi lần chạy |
| **Tính tái lập** | Synthetic pair không deterministic; test hồi quy nên `synthetic_count=0` |
| **ISO_CONTROLS_FLAT** | List 93 ISO + 34 TCVN ID tại [`dataset_generator.py:18-35`](../../backend/services/dataset_generator.py) — dùng để validate control sinh ra có trong vũ trụ biết trước |
| **Parse assessment** | Chỉ file `.json` trong `data/assessments/` được đọc; file hỏng bị skip kèm log warning |

---

## 9. Xem thêm

- [`docs/vi/algorithms.md`](algorithms.md) — cấu trúc prompt Phase-1 GAP.
- [`docs/vi/benchmark.md`](benchmark.md) — cách đo chất lượng SecurityLM
  sau khi fine-tune.
- [`data/knowledge_base/sample_training_pairs.jsonl`](../../data/knowledge_base/sample_training_pairs.jsonl) —
  seed pair đi kèm repo.
