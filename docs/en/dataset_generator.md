# Dataset Generator — SecurityLM Fine-Tuning Dataset

> **Module:** [`backend/services/dataset_generator.py`](../../backend/services/dataset_generator.py)
> **API:** `POST /api/v1/dataset/generate`, `GET /api/v1/dataset/status` — see [`backend/main.py:281-319`](../../backend/main.py)
> **Output:** `data/knowledge_base/finetune_iso27001.jsonl` (Alpaca format) + `data/knowledge_base/finetune_metadata.json`

---

## 1. Goal

Produce a fine-tuning dataset that teaches the local SecurityLM (7B GGUF)
to perform **Phase-1 GAP analysis** for ISO 27001:2022 and TCVN
11930:2017. The pipeline mines two complementary data sources:

1. **Real assessments** already completed on the platform
   (`data/assessments/*.json`) — primary, high-quality source.
2. **Synthetic scenarios** generated on-demand by the Cloud LLM (Gemini /
   GPT-5 / Claude) following a tightly-scoped prompt — secondary filler
   to cover rare controls.

Both streams are serialised to **Alpaca JSONL** so they can be consumed
directly by HuggingFace PEFT / QLoRA recipes.

---

## 2. Pipeline Overview

```
┌────────────────────────┐     ┌────────────────────────┐
│ data/assessments/*.json│     │ Hard-coded scenarios   │
│ (primary)              │     │ (Startup/Hospital/Bank/│
└─────────┬──────────────┘     │  Gov/E-commerce)       │
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
   data/knowledge_base/finetune_metadata.json    ← run info
```

Source: [`backend/services/dataset_generator.py:209-248`](../../backend/services/dataset_generator.py)

---

## 3. Public API

| Function | Purpose | Source |
|---|---|---|
| `generate_from_assessments() -> List[Dict]` | Convert each assessment into one training pair per category | `dataset_generator.py:53-140` |
| `generate_synthetic_pairs(count=20) -> List[Dict]` | Fan-out over 5 hard-coded scenarios, call Cloud LLM, parse JSON | `dataset_generator.py:143-189` |
| `export_to_jsonl(pairs, output_path) -> int` | Write Alpaca JSONL and return row count | `dataset_generator.py:192-206` |
| `run_full_pipeline(synthetic_count=10) -> Dict` | Orchestrate all three + metadata | `dataset_generator.py:209-248` |
| `_cloud_generate(prompt, max_tokens=1000) -> Optional[str]` | Thin wrapper around `CloudLLMService.chat_completion` with `task_type="iso_analysis"` | `dataset_generator.py:38-50` |

### Alpaca row shape

```json
{
  "instruction": "Phân tích GAP controls nhóm A.8 Công nghệ cho hệ thống sau:",
  "input":       "<system description>",
  "output":      "[{\"id\":\"A.8.1\",\"severity\":\"high\",...}]"
}
```

---

## 4. Scenario Seeds (Synthetic)

Hard-coded list at [`dataset_generator.py:145-151`](../../backend/services/dataset_generator.py):

| # | Scenario | Standard | Target Category |
|---|---|---|---|
| 1 | Startup SaaS 30 employees, AWS, no SIEM, basic AV | `iso27001` | A.8 Technology |
| 2 | Hospital 500 staff, unencrypted HIS, shared Wi-Fi | `tcvn11930` | 2. Server Security |
| 3 | Bank 2 000 staff, Palo Alto HA, CrowdStrike, Splunk | `iso27001` | A.5 Organisational |
| 4 | Government agency, FortiGate, BKAV, no IR plan | `tcvn11930` | 5. Operational Management |
| 5 | E-commerce, 50 servers, Kaspersky, no WAF | `iso27001` | A.8 Technology |

The synthetic prompt asks the Cloud LLM to emit a strict JSON blob
containing `system_input`, `missing_controls`, and a `gap_analysis`
array with `{id, severity, likelihood, impact, risk, gap, recommendation}`
per control. A regex (`r'\{.*\}'` with `re.DOTALL`) extracts the first
JSON object; rows that fail to parse are silently dropped.

---

## 5. Metadata File

Written atomically by `run_full_pipeline()` — see
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

Both endpoints live directly on `backend/main.py` (not in a router
sub-module) — see [`backend/main.py:281-319`](../../backend/main.py).

### `POST /api/v1/dataset/generate`

```bash
curl -X POST "http://localhost:8000/api/v1/dataset/generate?synthetic_count=10"
```

Runs `run_full_pipeline()` in a `BackgroundTask`; returns `202 Accepted`
immediately so the caller does not block on Cloud LLM calls.

### `GET /api/v1/dataset/status`

```bash
curl -s http://localhost:8000/api/v1/dataset/status | jq
```

Returns `{ exists, path, size_bytes, total_pairs, breakdown, generated_at }`
by reading `finetune_metadata.json`.

---

## 7. Consuming the JSONL

Because the output is strict Alpaca, any HF-compatible trainer works:

```python
from datasets import load_dataset
ds = load_dataset(
    "json",
    data_files="data/knowledge_base/finetune_iso27001.jsonl",
    split="train",
)
```

The metadata field `fine_tune_method` deliberately pins **QLoRA 4-bit,
`lora_r=16`** — this is the recipe the repo validates against; using
full-rank LoRA or higher ranks is supported but not tested.

---

## 8. Operational Notes

| Topic | Notes |
|---|---|
| **Cost** | Each synthetic pair costs roughly one Cloud LLM call at `max_tokens=1000` |
| **Idempotency** | `export_to_jsonl` **overwrites** the JSONL on every run |
| **Reproducibility** | Synthetic pairs are non-deterministic (Cloud LLM); for regression tests pin `synthetic_count=0` |
| **ISO_CONTROLS_FLAT** | List of 93 ISO + 34 TCVN IDs at [`dataset_generator.py:18-35`](../../backend/services/dataset_generator.py) — used to validate that generated controls land in the known universe |
| **Assessment parsing** | Only files ending in `.json` inside `data/assessments/` are read; malformed files are skipped with a log warning |

---

## 9. See Also

- [`docs/en/algorithms.md`](algorithms.md) — Phase-1 GAP analysis prompt
  shape.
- [`docs/en/benchmark.md`](benchmark.md) — how to measure fine-tuned
  SecurityLM quality afterwards.
- [`data/knowledge_base/sample_training_pairs.jsonl`](../../data/knowledge_base/sample_training_pairs.jsonl) —
  seed pairs that ship with the repo.
