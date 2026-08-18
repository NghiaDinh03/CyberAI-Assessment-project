# Local Models API Guide (English)

> Full Vietnamese reference: [`docs/vi/local_models_api.md`](../vi/local_models_api.md). This English doc mirrors the most-used surface so non-VI integrators can wire `n8n` / `curl` / Python without reading the VI version.

---

## 1. Architecture overview

```text
┌──────────────────┐        HTTP / JSON        ┌───────────────────────┐
│  Client          │ ────────────────────────▶ │  Server               │
│  (n8n / curl /   │                           │   - Backend  :8000    │
│   Python / app)  │ ◀──────────────────────── │   - Ollama   :11434   │
└──────────────────┘         Response          └───────────────────────┘
```

Two ways to call a local model from a remote machine:

| # | Endpoint                                             | Description                                                                | Recommendation                       |
|---|------------------------------------------------------|----------------------------------------------------------------------------|--------------------------------------|
| A | `POST http://<SERVER_IP>:8000/api/chat`              | Through Backend — applies RAG, log-analysis prompt, automatic TP/FP verdict | ✅ **Recommended** for log analysis  |
| B | `POST http://<SERVER_IP>:11434/v1/chat/completions`  | Direct Ollama — raw LLM, no analysis prompt (OpenAI-compatible schema)      | When you need full prompt control    |

`<SERVER_IP>` = the server's IP or hostname (e.g. `192.168.1.100`, `cyberai.example.com`).

---

## 2. Available local models

Check pulled models:

```bash
curl http://<SERVER_IP>:11434/api/tags
```

| Model ID         | Size    | Use case                                            | Throughput (2 CPU / 12 GB RAM)        |
|------------------|---------|-----------------------------------------------------|---------------------------------------|
| `gemma4:latest`  | 9.6 GB  | Not recommended on this server — too slow           | ~0.8 tok/s → 1024 tok ≈ **~21 min**   |
| `gemma3n:e4b`    | 7.5 GB  | Mid-tier log analysis                               | ~2–3 tok/s → 1024 tok ≈ **~6–8 min**  |
| `gemma3n:e2b`    | 5.6 GB  | **Recommended** — fast log analysis on weak CPU     | ~5–7 tok/s → 1024 tok ≈ **~2–3 min**  |

> ⚠️ First call after server start can take **5–8 minutes** as Ollama loads the GGUF blob into RAM. Subsequent calls reuse the warm model (~60–90 s).

---

## 3. Method A — Backend `/api/chat` (recommended)

### 3.1. Endpoint

| Field          | Value                                  |
|----------------|----------------------------------------|
| URL            | `http://<SERVER_IP>:8000/api/chat`     |
| Method         | `POST`                                 |
| Content-Type   | `application/json`                     |

### 3.2. Request body

```json
{
  "message": "<log content + question>",
  "session_id": "n8n-log-analyzer-001",
  "model": "gemma3n:e2b",
  "prefer_cloud": false
}
```

| Field          | Type    | Required | Allowed values                                     | Notes                                                                                  |
|----------------|---------|----------|----------------------------------------------------|----------------------------------------------------------------------------------------|
| `message`      | string  | ✅       | 1–15000 chars                                      | Log content + question (e.g. `"<log>\n\nAnalyze this log."`)                            |
| `session_id`   | string  | ❌       | Any                                                | Conversation key. Use unique per workflow run. Default: `"default"`                     |
| `model`        | string  | ❌       | `gemma4:latest` / `gemma3n:e4b` / `gemma3n:e2b`    | Specific local model. Default: `gemini-3-flash-preview` (cloud)                         |
| `prefer_cloud` | boolean | ✅       | **`false`**                                        | **Must be `false`** to use a local model; otherwise backend routes to cloud and ignores `model` |

### 3.3. Response body

```json
{
  "response": "## 1. 📋 Thông tin sự kiện\n- **Event ID**: `4688` — ...\n\n## 2. 🎯 Nhận định\n- **Nhận định**: ⚠️ **True Positive**\n...",
  "model": "gemma3n:e2b",
  "session_id": "n8n-log-analyzer-001",
  "tokens": { "prompt_tokens": 1234, "completion_tokens": 567, "total_tokens": 1801 },
  "error": false,
  "route": "ollama",
  "provider": "ollama",
  "rag_used": false,
  "search_used": false
}
```

| Field         | Type    | Description                                                                  |
|---------------|---------|------------------------------------------------------------------------------|
| `response`    | string  | Markdown analysis — fixed 4-section template (see §5)                        |
| `model`       | string  | Model actually used (may differ from request if backend fell back)           |
| `session_id`  | string  | Echoed conversation key                                                       |
| `tokens`      | object  | `prompt_tokens`, `completion_tokens`, `total_tokens`                          |
| `error`       | boolean | `true` on failure, `false` on success                                         |
| `route`       | string  | Provider that ran the call: `ollama` / `localai` / `cloud`                    |
| `rag_used`    | boolean | Whether knowledge-base RAG was injected                                       |
| `search_used` | boolean | Whether web search was injected                                               |

### 3.4. curl example

```bash
curl -X POST http://<SERVER_IP>:8000/api/chat \
  -H "Content-Type: application/json" \
  --max-time 600 \
  -d '{
    "message": "Event ID: 4688 — New Process Creation\nProcess Name: C:\\Windows\\System32\\cmd.exe\nParent Process: C:\\Windows\\explorer.exe\nAccount Name: alice\n\nAnalyze this log.",
    "session_id": "ext-client-001",
    "model": "gemma3n:e2b",
    "prefer_cloud": false
  }'
```

---

## 4. Method B — Direct Ollama (OpenAI-compatible)

### 4.1. Endpoint

| Field          | Value                                                       |
|----------------|-------------------------------------------------------------|
| URL            | `http://<SERVER_IP>:11434/v1/chat/completions`              |
| Method         | `POST`                                                      |
| Content-Type   | `application/json`                                          |
| Schema         | OpenAI Chat Completions (drop-in for OpenAI SDK / LangChain)|

### 4.2. Request body

```bash
curl -X POST http://<SERVER_IP>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  --max-time 600 \
  -d '{
    "model": "gemma3n:e2b",
    "messages": [
      { "role": "system", "content": "You are a SOC L3 analyst. Reply in field:value format." },
      { "role": "user",   "content": "Event ID: 4688\nProcess: cmd.exe" }
    ],
    "temperature": 0.3,
    "max_tokens": 2048
  }'
```

> ⚠️ **Gemma 4 thinking mode** sometimes places the answer in `choices[0].message.reasoning` instead of `.content`. Always check both:
>
> ```python
> msg = data["choices"][0]["message"]
> text = msg.get("content") or msg.get("reasoning") or ""
> ```

### 4.3. OpenAI-compatible — pros & cons for this repo

| Aspect                 | ✅ Pros                                                                                                | ⚠️ Cons / risks                                                                                       |
|------------------------|--------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| **Ecosystem fit**       | Drop-in for OpenAI SDK, LangChain, LlamaIndex, n8n OpenAI node, Continue.dev, Cursor, etc.            | Encourages bypassing the backend, losing project-specific features.                                  |
| **Vendor portability**  | Swap Ollama ↔ vLLM ↔ LM Studio ↔ OpenAI ↔ Groq with one base-URL change. No lock-in.                   | Different providers honour the schema unevenly (`reasoning`, `tool_calls`, JSON mode quirks).        |
| **Maintenance load**    | One contract to learn; no custom backend client to maintain.                                          | Backend's RAG / `model_guard` / `chat_service` value-add is bypassed.                                |
| **Security**            | —                                                                                                      | Skips prompt-injection check, PII scrub, rate-limit (`slowapi`), and session store.                  |
| **Log-analysis quality**| —                                                                                                      | Loses the strict 4-section TP/FP prompt → output becomes free-form, harder to parse downstream.      |
| **Performance**         | Same latency as Method A (both hit Ollama); one less hop.                                              | No caching/dedup that the backend can add later (e.g. session-aware response cache).                 |
| **Extensibility**       | Easy to expose new model providers behind the same `/v1/chat/completions` route.                       | Repo loses a single chokepoint for telemetry, audit logs, and policy.                                |

**Recommended direction for this repo:** keep Method A as the default for product features and expose **a thin OpenAI-compatible wrapper at the backend** (`POST /v1/chat/completions`) that internally still runs through `model_guard` + log-analysis prompt + RAG. Best of both worlds: external clients get the standard schema; internal value-add stays enforced.

---

## 5. Log-analysis output format (Method A)

When the backend detects a log-shaped input, it injects the **Log Analysis Prompt** (see [`backend/prompts/defaults.py`](../../backend/prompts/defaults.py:104)). Output is **always** the same 4-section template — strict enough to regex-parse downstream.

### 5.1. Section schema

| §   | Heading                          | Required lines                                                                 |
|-----|----------------------------------|--------------------------------------------------------------------------------|
| 1   | `## 1. 📋 Thông tin sự kiện`      | One bullet per non-empty field: `- **<Field>**: \`<value>\` — <≤12 word note>` |
| 2   | `## 2. 🎯 Nhận định`              | Exactly 3 bullets: `Nhận định`, `Mức độ`, `Lý do` (see §5.2)                    |
| 3   | `## 3. 🗺️ MITRE ATT&CK`           | One bullet: `- **Technique**: \`Txxxx.xxx\` — name \| **Tactic**: name`         |
| 4   | `## 4. 🛡️ Khuyến nghị`            | 1 line if FP; 3 bullets (Log / Query / IOCs) if TP or "needs investigation"     |

### 5.2. Verdict labels (always in section 2)

| Label                          | When to use                                                                                                          |
|--------------------------------|----------------------------------------------------------------------------------------------------------------------|
| ⚠️ **True Positive**           | Clear malicious indicator — investigate further. e.g. PowerShell `-ExecutionPolicy Bypass`, exe in `\Temp\` / `\Downloads\` / `\AppData\`, unknown hash, hidden process, abnormal logon, persistence registry key. |
| ✅ **False Positive**          | Legitimate system / signed vendor binary (Microsoft, Trend Micro, Symantec, …) running normally. **No action needed.** |
| ❓ **Cần điều tra thêm**        | Insufficient context to conclude.                                                                                     |

Severity scale: `Critical` / `High` / `Medium` / `Low` / `Informational`.

### 5.3. Example — ⚠️ True Positive

```markdown
## 1. 📋 Thông tin sự kiện
- **Event ID**: `4688` — New Process Creation
- **Account Name**: `alice` — standard user, not admin
- **Process Name**: `C:\Users\alice\Downloads\invoice.exe` — exe in Downloads, suspicious
- **Command Line**: `invoice.exe -enc SQBFAFgA...` — PowerShell-style encoded payload
- **Parent Process**: `C:\Program Files\Microsoft Office\winword.exe` — spawned by Word, classic macro chain
- **SHA256**: `a1b2c3d4...e9f0` — unknown hash, not in threat-intel cache

## 2. 🎯 Nhận định
- **Nhận định**: ⚠️ **True Positive**
- **Mức độ**: `High`
- **Lý do**: Word spawning an unsigned exe from `\Downloads\` with an encoded command line is a textbook macro-to-payload chain. Hash is unknown and the user is non-admin, so impact is contained but lateral risk remains.

## 3. 🗺️ MITRE ATT&CK
- **Technique**: `T1059.001` — PowerShell | **Tactic**: `Execution`

## 4. 🛡️ Khuyến nghị
- **Log cần kiểm tra**: `4688`, `4624`, `4697`, Sysmon `1`, `3`, `11`
- **Truy vấn gợi ý**: `process where parent_image == "winword.exe" and image endswith ".exe"`
- **IOCs cần tra**: SHA256 `a1b2c3d4...e9f0`, host `WIN-CLIENT-01`, user `alice`
```

### 5.4. Example — ✅ False Positive

```markdown
## 1. 📋 Thông tin sự kiện
- **Event ID**: `4688` — New Process Creation
- **Account Name**: `SYSTEM` — built-in system account
- **Process Name**: `C:\Program Files\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe` — signed Microsoft updater
- **Parent Process**: `C:\Windows\System32\svchost.exe` — Windows service host
- **Signature**: `Microsoft Corporation` — valid Authenticode signature

## 2. 🎯 Nhận định
- **Nhận định**: ✅ **False Positive**
- **Mức độ**: `Informational`
- **Lý do**: Edge auto-updater run by SYSTEM via svchost is the standard Microsoft update path. Binary is signed by Microsoft and parent chain is legitimate.

## 3. 🗺️ MITRE ATT&CK
- **MITRE**: N/A

## 4. 🛡️ Khuyến nghị
Không cần hành động — hoạt động bình thường của hệ thống.
```

### 5.5. Regex to extract fields

```regex
\*\*([^*]+?)\*\*:\s*`?([^`\n]+?)`?(?:\s+—\s+.*)?$
```

Stable keys you can rely on: `Nhận định`, `Mức độ`, `Lý do`, `Technique`, `Tactic`, plus any field present in section 1.

---

## 6. When to use local vs cloud

| Scenario                                  | Local (Gemma)        | Cloud           |
|-------------------------------------------|----------------------|-----------------|
| Sensitive logs (cannot leave network)     | ✅ Required          | ❌              |
| Simple log, throughput-bound              | `gemma3n:e2b`        | ✅              |
| Complex log, accuracy-bound               | `gemma4:latest`      | ✅              |
| Air-gapped / no internet                  | ✅ Required          | ❌              |
| Batch ≥ 1000 logs/day                     | ✅ (no API cost)     | $$$             |

---

## 7. Common errors

| Symptom                           | Cause                                              | Fix                                                                        |
|-----------------------------------|----------------------------------------------------|----------------------------------------------------------------------------|
| Timeout on first call             | Gemma 4 loading 9.4 GB into RAM                    | Set client timeout ≥ 900 s; warm-up with a tiny request                    |
| Empty `content`                   | Gemma 4 returned `reasoning` instead               | `text = msg.get("content") or msg.get("reasoning")`                        |
| `LocalAI unavailable`             | `prefer_cloud=true` while requesting a local model | Send `"prefer_cloud": false`                                               |
| `model not found`                 | Ollama hasn't pulled it                            | `docker exec phobert-ollama ollama pull <model>`                           |
| Response 60–90 s/call             | Normal on 2-core CPU                               | Use `gemma3n:e2b` or scale CPU cores                                       |
| Ollama healthcheck "unhealthy"    | `curl` not present in the Ollama image             | Cosmetic only — Ollama still serves traffic                                |

---

## 8. Monitoring & debug

```bash
# Models currently loaded in RAM
docker exec phobert-ollama ollama ps

# Backend logs
docker logs phobert-backend --tail 200 -f

# Ollama logs
docker logs phobert-ollama --tail 100 -f

# End-to-end latency probe (Method B)
time curl -s http://<SERVER_IP>:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma3n:e2b","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

---

## 9. Security hardening (when exposing to the internet)

Ports `8000` (backend) and `11434` (ollama) ship **without auth**. Before exposing publicly:

1. **Firewall** — whitelist only known clients:
   ```bash
   ufw allow from <CLIENT_IP> to any port 8000
   ufw allow from <CLIENT_IP> to any port 11434
   ufw deny 8000
   ufw deny 11434
   ```
2. **Reverse proxy + API key** — see [`nginx/`](../../nginx) for the bundled config:
   ```nginx
   location /api/ {
       if ($http_x_api_key != "your-secret-key") { return 401; }
       proxy_pass http://backend:8000;
   }
   ```
3. **Rate-limit** — `slowapi` is wired in [`backend/core/limiter.py`](../../backend/core/limiter.py:1).

---

## 10. Related docs

- [`docs/en/chatbot_rag.md`](chatbot_rag.md) — Chatbot & RAG pipeline
- [`docs/en/architecture.md`](architecture.md) — System architecture
- [`docs/en/api.md`](api.md) — Full API reference
- [`docs/vi/local_models_api.md`](../vi/local_models_api.md) — Vietnamese version (n8n examples, Python helpers, full monitoring section)
- [Ollama OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/openai.md)
