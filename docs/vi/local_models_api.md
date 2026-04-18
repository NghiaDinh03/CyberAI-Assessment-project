# Hướng dẫn sử dụng Local Models API (Tiếng Việt)

> Tài liệu này mô tả chi tiết cách gọi các mô hình local (Ollama — Gemma 4, Gemma 3n) từ một máy khác qua API để thực hiện **phân tích log** với format `field: value` chuẩn, nhận định `True Positive` / `False Positive`, và khuyến nghị điều tra mở rộng.

---

## 1. Tổng quan kiến trúc

```
┌──────────────────┐        HTTP/JSON       ┌──────────────────┐
│ Máy client (bạn) │ ─────────────────────▶ │ Server Phobert   │
│ (n8n / curl /    │                        │  - Backend:8000  │
│  Python / app)   │ ◀───────────────────── │  - Ollama:11434  │
└──────────────────┘      Response          └──────────────────┘
```

Có **2 cách gọi local model** từ máy khác:

| # | Endpoint | Mô tả | Khuyến nghị |
|---|----------|-------|-------------|
| **A** | `POST http://<SERVER_IP>:8000/api/chat` | Đi qua Backend — có RAG, log analysis prompt, verdict tự động | ✅ **Khuyên dùng** cho log analysis |
| **B** | `POST http://<SERVER_IP>:11434/v1/chat/completions` | Gọi Ollama trực tiếp — raw LLM, không có prompt phân tích | Khi bạn muốn tự chủ prompt |

`<SERVER_IP>` = địa chỉ IP hoặc domain của server Phobert (thay bằng IP thật, ví dụ `192.168.1.100` hoặc `cyberai.example.com`).

---

## 2. Các model local hiện có

Chạy lệnh sau để kiểm tra model đã pull:

```bash
curl http://<SERVER_IP>:11434/api/tags
```

Kết quả:

| Model ID (gọi API) | Kích thước | Use case | Throughput thực đo (2 CPU, 12 GB RAM) |
|---|---|---|---|
| `gemma4:latest`   | 9.6 GB | Không khuyên dùng trên server này — quá chậm | **~0.8 tok/s** → 1024 tokens ≈ **21 phút** |
| `gemma3n:e4b`     | 7.5 GB | Log phân tích tầm trung | **~2-3 tok/s** (ước tính) → 1024 tokens ≈ **6-8 phút** |
| `gemma3n:e2b`     | 5.6 GB | **KHUYÊN DÙNG** — Log phân tích nhanh trên CPU yếu | **~5-7 tok/s** (ước tính) → 1024 tokens ≈ **2-3 phút** |

> ⚠️ **Thực tế đo trên server này (2 CPU, 12 GB RAM) lúc 11:15 UTC 17/04/2026**:
> Gemma 4 chỉ đạt **0.80 tokens/giây** — không khả thi cho phân tích log real-time.
> Lần load đầu tiên (chưa có trong RAM) mất **~8 phút** cho Gemma 4 (9.4 GB model vs 12 GB RAM).
>
> **Khuyến nghị**:
> 1. Mặc định dùng `gemma3n:e2b` cho phân tích log local
> 2. Dùng cloud model (Gemini 3 Flash, GPT-5) cho log nhạy cảm cần tốc độ
> 3. Nếu bắt buộc Gemma 4 local → nâng server lên ≥ 8 CPU cores + 24 GB RAM

---

## 3. CÁCH A — Gọi qua Backend (khuyên dùng cho log analysis)

### 3.1. Endpoint

- **URL**: `http://<SERVER_IP>:8000/api/chat`
- **Method**: `POST`
- **Content-Type**: `application/json`

### 3.2. Request Body

```json
{
  "message": "<nội dung log cần phân tích>",
  "session_id": "n8n-log-analyzer-001",
  "model": "gemma4:latest",
  "prefer_cloud": false
}
```

#### Chi tiết từng field:

| Field | Kiểu | Bắt buộc | Giá trị | Mô tả |
|---|---|---|---|---|
| `message` | string | ✅ | 1-15000 ký tự | Nội dung log + câu hỏi (ví dụ: `"<log>\n\nPhân tích log này xem?"`) |
| `session_id` | string | ❌ | Bất kỳ | ID phiên để nhóm hội thoại. Đặt unique cho n8n (ví dụ: `n8n-<workflow_id>-<run_id>`). Mặc định: `"default"` |
| `model` | string | ❌ | `gemma4:latest` / `gemma3n:e4b` / `gemma3n:e2b` | Chọn model local cụ thể. Mặc định: `gemini-3-flash-preview` (cloud) |
| `prefer_cloud` | boolean | ✅ | **`false`** | **Phải đặt `false` để dùng local model.** Nếu `true` → chọn cloud dù đã chỉ định model local |

> ⚠️ **QUAN TRỌNG**: Khi muốn dùng local model, **BẮT BUỘC** gửi `"prefer_cloud": false`. Nếu không, backend sẽ route về cloud model và bỏ qua `model` field.

### 3.3. Response Body

```json
{
  "response": "### 1. Thông tin sự kiện\n- **Event ID**: `4688` — ...\n\n### 2. Nhận định\n- **Nhận định**: `False Positive`\n...",
  "model": "gemma4:latest",
  "session_id": "n8n-log-analyzer-001",
  "tokens": { "prompt_tokens": 1234, "completion_tokens": 567, "total_tokens": 1801 },
  "error": false,
  "route": "ollama",
  "provider": "ollama",
  "rag_used": false,
  "search_used": false
}
```

#### Chi tiết response:

| Field | Kiểu | Mô tả |
|---|---|---|
| `response` | string | **Kết quả phân tích** — dạng Markdown có cấu trúc 4 section (xem Mục 5) |
| `model` | string | Model thực sự đã dùng (có thể khác `model` trong request nếu backend fallback) |
| `session_id` | string | ID phiên (giống request) |
| `tokens` | object | Token usage: `prompt_tokens`, `completion_tokens`, `total_tokens` |
| `error` | boolean | `true` nếu có lỗi, `false` nếu thành công |
| `route` | string | Provider thực sự đã chạy: `ollama` / `localai` / `cloud` |
| `provider` | string | Giống `route` |
| `rag_used` | boolean | Có dùng knowledge base RAG không |
| `search_used` | boolean | Có dùng web search không |

### 3.4. Ví dụ curl

```bash
curl -X POST http://<SERVER_IP>:8000/api/chat \
  -H "Content-Type: application/json" \
  --max-time 600 \
  -d '{
    "message": "Event ID: 4688 — New Process Creation\nProcess Name: C:\\Windows\\System32\\cmd.exe\nParent Process: C:\\Windows\\explorer.exe\nAccount Name: hoalx_pm\n\nPhân tích log này xem?",
    "session_id": "ext-client-001",
    "model": "gemma4:latest",
    "prefer_cloud": false
  }'
```

> ⏱️ **Lưu ý timeout**: Lần gọi đầu tiên có thể mất **5-7 phút** do Ollama cần load Gemma 4 (9.4GB) vào RAM. Các lần sau nhanh hơn nhiều (~60-90s). Đặt `--max-time 600` (10 phút) để tránh client bị cắt.

### 3.5. Ví dụ Python

```python
import requests, json

def analyze_log(log_content: str, model: str = "gemma4:latest") -> dict:
    """Phân tích log qua Backend API.

    Returns dict với keys: verdict, severity, reason, fields (dict), raw_response.
    """
    resp = requests.post(
        "http://<SERVER_IP>:8000/api/chat",
        headers={"Content-Type": "application/json"},
        json={
            "message": f"{log_content}\n\nPhân tích log này xem?",
            "session_id": f"py-client-{int(__import__('time').time())}",
            "model": model,
            "prefer_cloud": False,
        },
        timeout=600,  # 10 phút
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Backend error: {data.get('response')}")

    # Parse structured response thành dict field:value
    import re
    text = data["response"]
    fields = {}
    for match in re.finditer(r"\*\*([^*]+?)\*\*:\s*`?([^`\n]+?)`?(?:\s+—\s+(.*))?$", text, re.M):
        key = match.group(1).strip()
        value = match.group(2).strip()
        fields[key] = value

    return {
        "verdict":       fields.get("Nhận định", "N/A"),
        "severity":      fields.get("Mức độ",    "N/A"),
        "event_id":      fields.get("Event ID",  "N/A"),
        "process_name":  fields.get("Process Name", "N/A"),
        "mitre":         fields.get("Technique ID", "N/A"),
        "fields":        fields,
        "raw_response":  text,
        "tokens":        data.get("tokens"),
    }

# Sử dụng
result = analyze_log("""Event ID: 4688
Process Name: C:\\Windows\\System32\\cmd.exe
Account Name: hoalx_pm""")
print(f"Nhận định: {result['verdict']}")
print(f"Mức độ: {result['severity']}")
print(f"MITRE: {result['mitre']}")
```

### 3.6. Ví dụ n8n HTTP Request Node

**Node Type**: `HTTP Request`

| Config | Giá trị |
|---|---|
| **Method** | `POST` |
| **URL** | `http://<SERVER_IP>:8000/api/chat` |
| **Authentication** | `None` |
| **Send Headers** | ✅ |
| **Header Parameters** | `Content-Type` = `application/json` |
| **Send Body** | ✅ |
| **Body Content Type** | `JSON` |
| **JSON/RAW Parameters** | ✅ |
| **Body (JSON)** | (xem bên dưới) |
| **Timeout (ms)** | `600000` (10 phút) |
| **Response Format** | `JSON` |

**Body JSON** (ví dụ dùng expression n8n):

```json
{
  "message": "={{ $json.log_content }}\n\nPhân tích log này xem?",
  "session_id": "n8n-{{ $workflow.id }}-{{ $execution.id }}",
  "model": "gemma4:latest",
  "prefer_cloud": false
}
```

**Extract field sau response** (node tiếp theo, ví dụ `Code` node):

```javascript
const text = $input.first().json.response;

// Regex trích xuất field:value từ markdown bold-backtick
const fields = {};
const regex = /\*\*([^*]+?)\*\*:\s*`?([^`\n]+?)`?(?:\s+—\s+.*)?$/gm;
let m;
while ((m = regex.exec(text)) !== null) {
  fields[m[1].trim()] = m[2].trim();
}

return [{
  json: {
    verdict:      fields["Nhận định"]    || "N/A",
    severity:     fields["Mức độ"]       || "N/A",
    event_id:     fields["Event ID"]     || "N/A",
    process_name: fields["Process Name"] || "N/A",
    command_line: fields["Command Line"] || "N/A",
    mitre:        fields["Technique ID"] || "N/A",
    all_fields:   fields,
    raw_response: text,
  }
}];
```

---

## 4. CÁCH B — Gọi Ollama trực tiếp (raw LLM)

Nếu bạn muốn **tự chủ hoàn toàn prompt** (không dùng prompt mặc định của backend), gọi thẳng Ollama API.

### 4.1. Endpoint

- **URL**: `http://<SERVER_IP>:11434/v1/chat/completions`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Format**: Tương thích OpenAI Chat Completions API

### 4.2. Request Body

```json
{
  "model": "gemma4:latest",
  "messages": [
    { "role": "system", "content": "<system prompt tự viết>" },
    { "role": "user",   "content": "<log + câu hỏi>" }
  ],
  "temperature": 0.3,
  "max_tokens": 2048,
  "stream": false
}
```

### 4.3. Response Body

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "gemma4:latest",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "",
      "reasoning": "..."
    },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600 }
}
```

> ⚠️ **Lưu ý quan trọng**: Với Gemma 4, nội dung trả lời có thể nằm ở trường **`reasoning`** (thinking mode) thay vì `content`. Code của bạn PHẢI check cả 2:
>
> ```python
> msg = data["choices"][0]["message"]
> text = msg.get("content") or msg.get("reasoning") or ""
> ```

### 4.4. Ví dụ curl — gọi Ollama trực tiếp

```bash
curl -X POST http://<SERVER_IP>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  --max-time 600 \
  -d '{
    "model": "gemma4:latest",
    "messages": [
      { "role": "system", "content": "Bạn là SOC Analyst. Phân tích log và trả lời dưới dạng field:value." },
      { "role": "user",   "content": "Event ID: 4688\nProcess Name: cmd.exe\n\nPhân tích log này xem?" }
    ],
    "temperature": 0.3,
    "max_tokens": 2048
  }'
```

---

## 5. Format output phân tích log (khi dùng CÁCH A)

Khi backend nhận diện user đang gửi log (qua keyword/pattern detection), nó tự động apply **Log Analysis Prompt** và trả về theo format chuẩn 4 section:

```markdown
### 1. Thông tin sự kiện
- **Event ID**: `4688` — New Process Creation
- **Source**: `Microsoft-Windows-Security-Auditing`
- **TimeCreated**: `2025-10-17T08:42:15Z`
- **Computer**: `WIN-CLIENT-01`
- **Account Name**: `hoalx_pm`
- **Account Domain**: `CORP`
- **Process ID**: `0x4b8c`
- **Process Name**: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` — PowerShell, công cụ scripting
- **Command Line**: `powershell.exe -Command "Setup Proxy.ps1"` — Chạy script cấu hình proxy
- **Parent Process**: `C:\Windows\explorer.exe` — User mở từ File Explorer
- **Token Elevation Type**: `TokenElevationTypeLimited (3)` — Limited token, UAC bật, không Run as Admin

### 2. Nhận định
- **Nhận định**: `False Positive`
- **Mức độ**: `Low`
- **Lý do**: User `hoalx_pm` chạy PowerShell qua File Explorer với limited token (UAC enforced, không elevation). Script `Setup Proxy.ps1` là tác vụ IT thông thường (cấu hình proxy). Không có dấu hiệu living-off-the-land hay persistence.

### 3. MITRE ATT&CK
- **Technique ID**: `T1059.001` — PowerShell
- **Tactic**: `Execution`

### 4. Khuyến nghị điều tra mở rộng
**Khuyến nghị**: `Không cần hành động — đây là hoạt động bình thường.`
```

### 5.1. Field được trích xuất (dùng regex trên response)

Regex pattern cho n8n/Python:
```regex
\*\*([^*]+?)\*\*:\s*`?([^`\n]+?)`?(?:\s+—\s+.*)?$
```

Field tiêu chuẩn luôn xuất hiện:
- `Nhận định` → `True Positive` / `False Positive` / `Cần điều tra thêm`
- `Mức độ` → `Critical` / `High` / `Medium` / `Low` / `Informational`
- `Lý do` (trong section Nhận định)
- `Technique ID`, `Tactic` (nếu detect được MITRE)

---

## 6. Phân biệt khi nào dùng local vs cloud

| Tình huống | Local (Gemma 4) | Cloud |
|---|---|---|
| Phân tích log nhạy cảm (không được gửi ra ngoài) | ✅ **Bắt buộc** | ❌ |
| Phân tích log đơn giản, cần tốc độ | Gemma 3n:e2b | ✅ |
| Phân tích log phức tạp, độ chính xác cao | Gemma 4 | ✅ |
| Không có kết nối internet | ✅ **Bắt buộc** | ❌ |
| Xử lý batch 1000+ log/ngày | ✅ (không tốn API cost) | Tốn phí |

---

## 7. Lỗi thường gặp & cách xử lý

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Timeout sau 600s lần đầu gọi | Gemma 4 đang load từ disk (9.4GB) | Tăng timeout client ≥ 900s. Lần 2 sẽ nhanh |
| Response empty (`content=""`) | Gemma 4 trả lời ở field `reasoning` | Code phải check: `msg.get("content") or msg.get("reasoning")` |
| `⚠️ LocalAI không khả dụng` | `prefer_cloud=true` khi chọn local model | Đảm bảo gửi `"prefer_cloud": false` |
| `model not found` | Ollama chưa pull model đó | `docker exec phobert-ollama ollama pull gemma4:latest` |
| Response chậm 60-90s/lần | Bình thường với CPU 2 core | Dùng model nhỏ hơn (gemma3n:e2b) hoặc tăng CPU |
| Ollama healthcheck "unhealthy" | Dummy: curl không có trong image Ollama | Không ảnh hưởng — Ollama vẫn hoạt động |

---

## 8. Monitoring & Debug

### Xem model đang load trong RAM:

```bash
docker exec phobert-ollama ollama ps
```

### Xem log Backend:

```bash
docker logs phobert-backend --tail 200 -f
```

### Xem log Ollama:

```bash
docker logs phobert-ollama --tail 100 -f
```

### Test latency Gemma 4:

```bash
time curl -s http://<SERVER_IP>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4:latest","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

---

## 9. Security hardening (khi mở API ra internet)

⚠️ Mặc định các port `8000` (backend) và `11434` (ollama) **không có authentication**. Nếu mở cho máy khác truy cập qua internet, BẮT BUỘC:

1. **Firewall** — chỉ whitelist IP client cho phép:
   ```bash
   ufw allow from <CLIENT_IP> to any port 8000
   ufw allow from <CLIENT_IP> to any port 11434
   ufw deny 8000
   ufw deny 11434
   ```

2. **Reverse proxy với HTTPS + API key** — dùng nginx (đã có [`nginx/nginx.conf`](nginx/nginx.conf:1)):
   ```nginx
   location /api/ {
       if ($http_x_api_key != "your-secret-key") { return 401; }
       proxy_pass http://backend:8000;
   }
   ```

3. **Rate limit** — giới hạn request/phút để tránh DoS (backend có sẵn slowapi, xem [`core/limiter.py`](backend/core/limiter.py:1)).

---

## 10. Tài liệu liên quan

- [`docs/vi/chatbot_rag.md`](docs/vi/chatbot_rag.md:1) — Tài liệu chatbot và RAG
- [`docs/vi/architecture.md`](docs/vi/architecture.md:1) — Kiến trúc tổng thể
- [`docs/vi/api.md`](docs/vi/api.md:1) — API reference đầy đủ
- [Ollama OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/openai.md) — Docs chính thức Ollama
