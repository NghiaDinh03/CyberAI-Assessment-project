# ModelGuard — Kiểm tra GGUF cục bộ & Sức khoẻ LocalAI

> **Module:** `backend/services/model_guard.py`
> **Gọi lúc:** Lifespan FastAPI khởi động — `backend/main.py:55-56`
> **Endpoint trạng thái:** `GET /health/ready`, `GET /health` (xem `backend/api/routes/health.py`)

---

## 1. Mục đích

`ModelGuard` là một registry nhẹ, thread-safe trả lời câu hỏi
**"Các file GGUF mà platform cần có thực sự nằm trên đĩa hay không?"**.

Nó chạy 1 lần lúc start, cache trong RAM dưới `threading.Lock`, và có thể
được làm mới theo nhu cầu. Nó **không phải** engine inference — chỉ kiểm
tra sự tồn tại của file weights và là nguồn duy nhất mà readiness probe
dùng trước khi backend chấp nhận bất cứ request chat / assessment nào.

---

## 2. Hợp đồng class

Nguồn: [`backend/services/model_guard.py:10-45`](../../backend/services/model_guard.py)

| Thành phần | Loại | Vai trò |
|---|---|---|
| `_lock` | `threading.Lock` | Tuần tự hoá cập nhật `_state` |
| `_state` | `Dict[str, str]` | Cờ từng model: `"present"` hoặc `"missing"` |
| `refresh()` | `@classmethod` | Duyệt `settings.required_model_ids`, kiểm tra filesystem, ghi đè `_state`, trả snapshot mới |
| `status()` | `@classmethod` | Trả **bản copy** của `_state`; tự động gọi `refresh()` lần đầu |
| `is_ready()` | `@classmethod` | `True` nếu **mọi** model đều `"present"` |
| `_resolve_model_path(base_dir, model_id)` | `@staticmethod` | Thử 2 đường dẫn ứng viên, trả về cái đầu tiên tồn tại hoặc `""` |

---

## 3. Thuật toán resolve path

```
base_dir = os.getenv("MODELS_PATH", "./models")

for model_id in settings.required_model_ids:
    candidates = [
        f"{base_dir}/{model_id}",                  # full id, ví dụ ./models/llama/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
        f"{base_dir}/{os.path.basename(model_id)}" # tên phẳng, ví dụ ./models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
    ]
    first_existing = next((p for p in candidates if os.path.exists(p)), "")
    summary[model_id] = "present" if first_existing else "missing"
```

Tham chiếu: [`backend/services/model_guard.py:36-45`](../../backend/services/model_guard.py)

Hai ứng viên là cố ý — cho phép vận hành xếp file GGUF dưới sub-folder do
[`scripts/download_models.py`](../../scripts/download_models.py) tạo (ví dụ
`models/llama/…`, `models/security/…`) **hoặc** xếp phẳng trong `models/`
sau khi tải tay.

---

## 4. Cấu hình

| Biến | Mặc định | Nơi đọc |
|---|---|---|
| `MODELS_PATH` | `./models` | Env host, đọc trong `refresh()` |
| `REQUIRED_MODEL_IDS` | list cách bằng dấu phẩy | `backend/core/config.py:55-58` |

`settings.required_model_ids` được build bằng cách `split(",")` rồi
`strip()`. List rỗng đồng nghĩa ModelGuard luôn báo ready (hữu ích khi chạy
chế độ cloud-only).

---

## 5. Vòng đời

1. **Startup** — `backend/main.py:55-56` gọi `ModelGuard.refresh()` trong
   `lifespan` context. Kết quả được log để vận hành phát hiện thiếu GGUF
   trước khi user request đầu tiên đến.
2. **Runtime** — `/health` và `/health/ready` gọi `status()` /
   `is_ready()` (xem `backend/api/routes/health.py`). Các call này
   **không** chạm đĩa lại; chúng dùng map cache.
3. **Refresh thủ công** — hiện chưa có endpoint quét lại; vận hành thả
   GGUF mới vào host nên restart container backend để buộc scan lại.

---

## 6. Tương tác với LocalAI và Ollama

ModelGuard là kiểm tra **tĩnh** (file có không?). Kiểm tra **động** (LocalAI
có thật sự load được không?) nằm ở
[`backend/services/cloud_llm_service.py:252-275`](../../backend/services/cloud_llm_service.py)
qua `CloudLLMService.localai_health_check()` — gọi
`POST /v1/chat/completions` với prompt 1 token và cache kết quả.

| Kiểm tra | Tầng | Đo |
|---|---|---|
| `ModelGuard.is_ready()` | Filesystem | GGUF binary có trên đĩa |
| `CloudLLMService.localai_health_check()` | HTTP | LocalAI daemon up & load được model |
| `CloudLLMService.ollama_health_check()` | HTTP | Ollama daemon trả `/api/tags` |

Cả 3 phải pass thì platform mới trả lời chat ở chế độ local thuần. Nếu một
trong số chúng fail, fallback chain ở
[`cloud_llm_service.py:24-30`](../../backend/services/cloud_llm_service.py)
nhảy vào.

---

## 7. Công thức vận hành

### Xem trạng thái hiện tại

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/health/ready
```

### Tải về model còn thiếu

```bash
python scripts/download_models.py --key llama --key security
```

(Các key registry được liệt kê trong
[`scripts/download_models.py:185-222`](../../scripts/download_models.py).)

### Buộc rescan

```bash
docker compose restart backend
```

---

## 8. Chế độ lỗi & chẩn đoán

| Triệu chứng | Nguyên nhân khả dĩ | Fix |
|---|---|---|
| `is_ready() == False` lúc start | Thiếu file GGUF | Chạy `scripts/download_models.py` hoặc thả file vào `MODELS_PATH` |
| `status()` trả về `{}` rỗng | `REQUIRED_MODEL_IDS` chưa set / rỗng | Set env hoặc chấp nhận chế độ cloud-only |
| File có nhưng LocalAI vẫn fail | GGUF hỏng / sai quant | Tải lại; check SHA trên trang HF |
| `/health/ready` chớp nháy ready/not | Race với job backup chạm `models/` | Backup nên skip `models/` (xem [`scripts/backup.sh`](../../scripts/backup.sh)) |

---

## 9. Xem thêm

- [`docs/vi/architecture.md`](architecture.md) — vị trí ModelGuard trong
  trình tự khởi động.
- [`docs/vi/deployment.md`](deployment.md) — bind-mount `MODELS_PATH` cho
  Docker Compose.
- [`docs/vi/analytics_monitoring.md`](analytics_monitoring.md) — các counter
  `cyberai_*` Prometheus liên quan tới readiness.
