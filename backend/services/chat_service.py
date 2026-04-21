"""Chat Service — Conversation routing with session memory and Cloud-first strategy."""

import asyncio
import json
import re
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Generator, List

from fastapi import HTTPException

from core.config import settings
from services.cloud_llm_service import CloudLLMService, MIN_MAX_TOKENS
from services.model_guard import ModelGuard
from services.model_router import route_model
from services.web_search import WebSearch
from repositories.vector_store import VectorStore
from repositories.session_store import SessionStore
from prompts import get_prompt

logger = logging.getLogger(__name__)

SPECIAL_TOKENS = re.compile(
    r'<\|eot_id\|>|<\|start_header_id\|>|<\|end_header_id\|>|'
    r'<\|begin_of_text\|>|<\|end_of_text\|>|<\|finetune_right_pad_id\|>|'
    r'<\|reserved_special_token_\d+\|>'
)

# Prompt-injection patterns — case-insensitive, matched anywhere in the message.
_INJECTION_PATTERNS = re.compile(
    r'ignore\s+previous\s+instructions'
    r'|disregard\s+all\s+prior'
    r'|you\s+are\s+now\b'
    r'|act\s+as\b'
    r'|forget\s+everything'
    r'|<\|im_start\|>'
    r'|<\|im_end\|>',
    re.IGNORECASE,
)
# "system:" is only an injection signal when it appears at the very start of the message.
_SYSTEM_PREFIX_RE = re.compile(r'^\s*system\s*:', re.IGNORECASE)


def sanitize_user_input(text: str) -> str:
    """Strip known prompt-injection patterns from *text*.

    Raises :class:`fastapi.HTTPException` 400 if a definitive injection attempt
    is detected so callers can surface a clear error to the client.  Benign text
    is returned unchanged.
    """
    if _INJECTION_PATTERNS.search(text) or _SYSTEM_PREFIX_RE.match(text):
        logger.warning("Prompt injection attempt blocked: %.120s", text)
        raise HTTPException(
            status_code=400,
            detail="Invalid input: message contains disallowed content.",
        )
    return text


class ChatService:
    _vector_store = None
    _session_store = None
    _vs_lock = threading.Lock()
    _ss_lock = threading.Lock()

    @classmethod
    def get_vector_store(cls):
        if cls._vector_store is None:
            with cls._vs_lock:
                if cls._vector_store is None:
                    cls._vector_store = VectorStore()
        return cls._vector_store

    @classmethod
    def get_session_store(cls) -> SessionStore:
        if cls._session_store is None:
            with cls._ss_lock:
                if cls._session_store is None:
                    cls._session_store = SessionStore()
        return cls._session_store

    # LocalAI GGUF model IDs — CPU-bound, need short prompts and no RAG
    _LOCALAI_GGUF_IDS = {
        "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "SecurityLLM-7B-Q4_K_M.gguf",
    }

    _OLLAMA_PREFIXES = ("gemma3:", "gemma3n:", "gemma4:", "phi4:", "llama3:", "mistral:", "qwen3:")

    @classmethod
    def _is_local_model(cls, model_name: str) -> bool:
        """Check if a model is a local/Ollama model (CPU-bound, needs short prompts)."""
        if not model_name:
            return False
        if any(model_name.startswith(p) for p in cls._OLLAMA_PREFIXES):
            return True
        if model_name in cls._LOCALAI_GGUF_IDS:
            return True
        if model_name.endswith(".gguf"):
            return True
        return False

    @classmethod
    def _is_ollama_model(cls, model_name: str) -> bool:
        """True only for Ollama-served models (excludes LocalAI GGUF files)."""
        if not model_name:
            return False
        return any(model_name.startswith(p) for p in cls._OLLAMA_PREFIXES)

    @staticmethod
    def clean_response(text: str) -> str:
        return SPECIAL_TOKENS.sub('', text).strip()

    # Keys that strongly indicate a SIEM / EDR / firewall / access log payload.
    # Matched substring-wise so both flat ("agent.ip":) and nested JSON formats hit.
    _LOG_JSON_KEY_HINTS = (
        '"rule"', '"agent"', '"manager"', '"decoder"',        # Wazuh
        '"event_src"', '"behavior_type"', '"behavior_category"',  # NCS/EDR
        '"srcip"', '"dstip"', '"src_port"', '"dst_port"',     # firewall
        '"action":"allow"', '"action":"deny"', '"action":"block"',
        '"http_method"', '"status_code"', '"user_agent"', '"request_uri"',
        '"syscall"', '"auid"', '"ses"', '"exe"',              # auditd
        '"EventID"', '"EventCode"', '"Computer"', '"Channel"',  # Windows Event
        '"full_log"', '"@timestamp"', '"_source"',            # ELK/OpenSearch
    )

    @staticmethod
    def _is_log_analysis(message: str) -> bool:
        """Detect if the user is requesting log/event analysis.

        Returns True for:
        - Natural-language requests mentioning log/event analysis.
        - Text-format logs (Windows Event IDs, ISO timestamps, field:value blocks).
        - JSON payloads from SIEM/EDR/firewall/auditd/access-log systems.
        """
        if not message:
            return False
        msg_lower = message.lower()
        log_keywords = (
            "phân tích log", "analyze log", "event id", "eventid",
            "sự kiện", "windows event", "syslog", "security log",
            "audit log", "process creation", "logon", "logoff",
            "firewall log", "access log", "error log", "phân tích sự kiện",
            "raw log", "alert", "siem log", "edr log",
        )
        if any(kw in msg_lower for kw in log_keywords):
            return True

        # JSON-shaped payload with any known log key hint.
        stripped = message.lstrip()
        if stripped.startswith(('{', '[')):
            for hint in ChatService._LOG_JSON_KEY_HINTS:
                if hint in message:
                    return True

        # Regex fallbacks for plain-text logs.
        log_patterns = (
            r"Event\s*ID[:\s]*\d+",
            r"Source[:\s]*(Microsoft|Security|System|Application)",
            r"Token\s*Elevation\s*Type",
            r"Process\s*(Name|ID|Command\s*Line)[:\s]",
            r"Logon\s*Type[:\s]*\d+",
            r"Creator\s*Process",
            r"New\s*Process\s*Name",
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            r"Mandatory\s*Label",
            r"Account\s*Name[:\s]",
            # firewall / access / auditd
            r"\bsrc(?:ip|_ip)?\s*=\s*\d+\.\d+\.\d+\.\d+",
            r"\bdst(?:ip|_ip)?\s*=\s*\d+\.\d+\.\d+\.\d+",
            r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+/\S+\s+HTTP/\d",
            r"type=SYSCALL\s+msg=audit",
        )
        for pattern in log_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    # Field keys to drop when flattening (noise for SOC analysis).
    _FLATTEN_SKIP_KEYS = frozenset({
        "_index", "_id", "_version", "_score", "_type",
        "fields", "highlight", "sort", "location", "input",
    })
    _FLATTEN_MAX_FIELDS = 40
    _FLATTEN_MAX_VAL_LEN = 400

    @staticmethod
    def _flatten_log_to_fields(message: str) -> str:
        """Convert a JSON log payload to plain `field: value` lines.

        No-op (returns original message) when the input is not valid JSON or
        cannot be flattened. Small/local models struggle with deeply nested
        JSON; pre-flattening dramatically improves prompt adherence.
        """
        if not message:
            return message
        stripped = message.strip()
        if not stripped.startswith(('{', '[')):
            return message
        try:
            data = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return message

        # If list → flatten first element only (typical for alert arrays).
        if isinstance(data, list):
            if not data:
                return message
            data = data[0]
        if not isinstance(data, dict):
            return message

        # Prefer the `_source` sub-object when present (ELK/OpenSearch shape).
        if isinstance(data.get("_source"), dict):
            data = data["_source"]

        lines: List[str] = []
        seen: set = set()

        def _walk(obj: Any, prefix: str = "") -> None:
            if len(lines) >= ChatService._FLATTEN_MAX_FIELDS:
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ChatService._FLATTEN_SKIP_KEYS:
                        continue
                    key = f"{prefix}.{k}" if prefix else str(k)
                    _walk(v, key)
            elif isinstance(obj, list):
                if obj and all(not isinstance(x, (dict, list)) for x in obj):
                    _emit(prefix, ", ".join(str(x) for x in obj))
                else:
                    for i, item in enumerate(obj[:3]):
                        _walk(item, f"{prefix}[{i}]")
            else:
                _emit(prefix, obj)

        def _emit(key: str, value: Any) -> None:
            if value is None or value == "":
                return
            sval = str(value).strip()
            if not sval or sval in {"-", "N/A", "null"}:
                return
            # De-duplicate identical (key,value) pairs caused by raw_log + parsed fields.
            sig = (key, sval[:80])
            if sig in seen:
                return
            seen.add(sig)
            if len(sval) > ChatService._FLATTEN_MAX_VAL_LEN:
                sval = sval[: ChatService._FLATTEN_MAX_VAL_LEN] + "…"
            lines.append(f"{key}: {sval}")

        _walk(data)

        if len(lines) < 3:
            return message
        header = "Log đã chuẩn hoá (field: value) — phân tích theo format bắt buộc:\n"
        return header + "\n".join(lines[: ChatService._FLATTEN_MAX_FIELDS])

    # Markdown artefacts the model sometimes emits despite the strict prompt.
    _NORMALIZE_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
    # Horizontal rules — ASCII runs (---, ___, ***, ===, ~~~) and Unicode box/drawing
    # characters (━ ─ ═ ▬ ⎯ ⸻ ▀ ■ ◼ •) repeated 3+ times. Matches anywhere on the
    # line (full-line divider) including inline trailing dividers.
    _NORMALIZE_HRULE_RE = re.compile(
        r"^\s{0,3}[-_*=~\u2014\u2015\u2500\u2501\u2550\u25AC\u23AF\u2E3B\u2580\u25A0\u25FC\u2022]{3,}\s*$",
        re.MULTILINE,
    )
    # Inline dividers at end of line (e.g. a title followed by `━━━━━━` on same line)
    _NORMALIZE_INLINE_DIVIDER_RE = re.compile(
        r"[\u2014\u2015\u2500\u2501\u2550\u25AC\u23AF\u2E3B]{3,}"
    )
    _NORMALIZE_BULLET_RE = re.compile(r"^\s{0,3}[-*+•]\s+(?=[A-Za-zÀ-ỹ])", re.MULTILINE)
    _NORMALIZE_BOLD_LABEL_RE = re.compile(r"^\s*\*\*([^*\n:]{1,60})\*\*\s*:", re.MULTILINE)
    # Strip leading emoji/pictograph cluster at start of a line (e.g. "🚨 BÁO CÁO")
    _NORMALIZE_LEADING_EMOJI_RE = re.compile(
        r"^\s*[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2B00-\u2BFF]+\s*",
        re.MULTILINE,
    )

    @staticmethod
    def _normalize_log_output(text: str) -> str:
        """Strip markdown artefacts from a log-analysis response.

        Small local models (gemma, phi, llama3-8B) often ignore the
        "no markdown" rule and emit headings, tables, or bullets.  This is a
        defensive post-processor: cheap, idempotent, only runs when log mode
        was triggered.
        """
        if not text:
            return text
        out = ChatService._NORMALIZE_HEADING_RE.sub("", text)
        out = ChatService._NORMALIZE_HRULE_RE.sub("", out)
        out = ChatService._NORMALIZE_INLINE_DIVIDER_RE.sub("", out)
        out = ChatService._NORMALIZE_LEADING_EMOJI_RE.sub("", out)
        out = ChatService._NORMALIZE_BULLET_RE.sub("", out)
        out = ChatService._NORMALIZE_BOLD_LABEL_RE.sub(r"\1:", out)
        # Strip any remaining **bold** spans (keep inner text).
        out = re.sub(r"\*\*([^*\n]{1,120})\*\*", r"\1", out)
        # Strip trailing whitespace on each line.
        out = re.sub(r"[ \t]+\n", "\n", out)
        # Collapse runs of 3+ blank lines.
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()

    # Vietnamese diacritics — detection for language enforcement.
    _VN_DIACRITIC_RE = re.compile(
        r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
        re.IGNORECASE,
    )

    @staticmethod
    def _is_vietnamese(text: str) -> bool:
        """Heuristic: text contains Vietnamese diacritics → treat as VN."""
        if not text:
            return False
        return bool(ChatService._VN_DIACRITIC_RE.search(text))

    # Marker fields in a prior log-analysis response — used to detect sticky mode.
    _LOG_RESPONSE_MARKERS = (
        "Nhận định:", "Mức độ:", "Technique:", "Tactic:",
        "Log cần kiểm tra:", "Truy vấn gợi ý:", "IOCs:",
    )

    @staticmethod
    def _session_in_log_mode(history: List[Dict[str, str]]) -> bool:
        """True if the most recent assistant reply looks like log analysis.

        Lets follow-up questions ("dịch đoạn trên", "giải thích thêm") keep
        the strict field:value format instead of falling back to generic chat.
        """
        if not history:
            return False
        for msg in reversed(history):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "") or ""
            hits = sum(1 for m in ChatService._LOG_RESPONSE_MARKERS if m in content)
            return hits >= 2
        return False

    # ── Structured output template for log/event analysis ────────────────
    # Source of truth lives in :mod:`prompts.defaults` (key ``chat.log_analysis``).
    # The literal below is kept ONLY as a fallback when the prompt registry
    # cannot be loaded (e.g. test environments without DATA_PATH).
    # Kept in sync with prompts.defaults.CHAT_LOG_ANALYSIS (field:value plain format).
    # Source of truth is prompts/defaults.py; this mirror is used only when the
    # prompt registry is unavailable (e.g. tests without DATA_PATH).
    _LOG_ANALYSIS_PROMPT_FALLBACK = (
        "Bạn là SOC Analyst Level 3. Phân tích log và trả về dạng `Field: Value` thuần. "
        "KHÔNG heading markdown, KHÔNG emoji, KHÔNG bullet, KHÔNG horizontal rule, "
        "KHÔNG intro/outro.\n\n"
        "Format: mỗi dòng 1 field `<Field>: <value>`. Label KHÔNG in đậm.\n\n"
        "Bắt buộc có các dòng:\n"
        "- `Nhận định: True Positive | False Positive | Cần điều tra thêm`\n"
        "- `Mức độ: Critical | High | Medium | Low | Informational`\n"
        "- `Lý do: <2-3 câu>`\n"
        "- `Technique: Txxxx.xxx - <tên>` và `Tactic: <tên>` (hoặc `MITRE: N/A`)\n"
        "- Nếu False Positive → `Khuyến nghị: Không cần hành động - hoạt động bình thường.`\n"
        "- Nếu TP/Cần điều tra → `Log cần kiểm tra:`, `Truy vấn gợi ý:`, `IOCs:`\n\n"
        "QUY TẮC CỨNG: KHÔNG `#`/`##`/`###`, KHÔNG `**bold label**:`, KHÔNG emoji, KHÔNG `---`, "
        "KHÔNG `===`, KHÔNG bullet `-`/`*` đầu dòng field, KHÔNG bảng, KHÔNG subtitle "
        "(`Tóm tắt`, `Phân tích kỹ thuật`). Dùng label cũ `Kết luận` = SAI."
    )

    @staticmethod
    def _safe_prompt(key: str, fallback: str) -> str:
        """Read from prompt registry; fall back to literal if registry fails."""
        try:
            return get_prompt(key)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("prompt registry lookup failed for %s: %s", key, exc)
            return fallback

    @staticmethod
    def _build_messages(message: str, routing: dict, context: str = "",
                        search_context: str = "", history: List[Dict[str, str]] = None,
                        is_local: bool = False) -> list:
        use_rag = routing["use_rag"]
        use_search = routing.get("use_search", False)

        # Detect log analysis requests — use specialized structured prompt.
        # Sticky mode: if previous assistant reply in session was log-analysis,
        # keep strict format for follow-ups (translate/summarize/explain).
        is_log = (
            ChatService._is_log_analysis(message)
            or ChatService._session_in_log_mode(history or [])
        )
        log_prompt = ChatService._safe_prompt(
            "chat.log_analysis", ChatService._LOG_ANALYSIS_PROMPT_FALLBACK,
        )
        # Language lock — force Vietnamese output when user writes VN,
        # even if raw log content is English.
        if ChatService._is_vietnamese(message):
            log_prompt = log_prompt + (
                "\n\nNGÔN NGỮ BẮT BUỘC: Toàn bộ giải thích/nhận định/khuyến nghị "
                "PHẢI viết TIẾNG VIỆT, kể cả khi log gốc tiếng Anh. Chỉ giữ nguyên "
                "tên field, rule name, IOC, command, MITRE ID."
            )
        # Pre-flatten JSON logs → field:value. Small local models obey the
        # strict format much better when they receive a pre-parsed log.
        log_message = (
            ChatService._flatten_log_to_fields(message) if is_log else message
        )

        # Short system prompt for local CPU models — no RAG context, minimal tokens
        if is_local:
            if is_log:
                system_prompt = log_prompt
                user_content = log_message
            else:
                system_prompt = ChatService._safe_prompt(
                    "chat.local_default",
                    "Bạn là trợ lý AI chuyên gia về an ninh mạng và bảo mật thông tin.",
                )
                user_content = message
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-2:])
            messages.append({"role": "user", "content": user_content})
            return messages

        # Log analysis takes priority — use structured prompt regardless of RAG/search
        if is_log:
            system_prompt = log_prompt
            user_content = log_message
        # Cloud model with RAG context from knowledge base
        elif use_rag and context:
            system_prompt = ChatService._safe_prompt("chat.rag", "")
            user_content = f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"
        # Cloud model with web search results
        elif use_search and search_context:
            system_prompt = ChatService._safe_prompt("chat.web_search", "")
            user_content = f"Kết quả tìm kiếm:\n{search_context}\n\nCâu hỏi: {message}"
        # Cloud model — general knowledge, no RAG/search
        else:
            system_prompt = ChatService._safe_prompt("chat.general", "")
            user_content = message

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_content})
        return messages

    @staticmethod
    async def generate_response(message: str, session_id: str = "default",
                                model_override: str = None, prefer_cloud: bool = True,
                                background_tasks=None) -> Dict[str, Any]:
        message = sanitize_user_input(message)
        guard_error = ChatService._local_only_guard()
        if guard_error:
            return guard_error
        try:
            routing = route_model(message)
            model_name = model_override or routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            # Disable RAG for local CPU models — keeps context small, avoids timeouts
            # Web search is kept active as a useful chatbot feature
            is_local = ChatService._is_local_model(model_name)
            if is_local:
                use_rag = False

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                vs = ChatService.get_vector_store()
                results = await asyncio.to_thread(vs.search, message, 5)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                search_results = await asyncio.to_thread(WebSearch.search, message, 5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]

            ss = ChatService.get_session_store()
            max_hist = 2 if is_local else 10
            history = ss.get_context_messages(session_id, max_messages=max_hist)
            is_log = (
                ChatService._is_log_analysis(message)
                or ChatService._session_in_log_mode(history or [])
            )
            messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)

            # cloud_model must only be set when prefer_cloud=True
            result = await asyncio.to_thread(
                CloudLLMService.chat_completion,
                messages=messages,
                temperature=0.7,
                local_model=model_name,
                prefer_cloud=prefer_cloud,
                cloud_model=model_override if prefer_cloud else None,
            )
            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""
            if is_log and response_text:
                response_text = ChatService._normalize_log_output(response_text)

            if background_tasks is not None:
                background_tasks.add_task(ss.add_message, session_id, "user", message)
                if response_text:
                    background_tasks.add_task(ss.add_message, session_id, "assistant", response_text)
            else:
                ss.add_message(session_id, "user", message)
                if response_text:
                    ss.add_message(session_id, "assistant", response_text)

            return {
                "response": response_text or "Model không trả về response. Vui lòng thử lại.",
                "model": result.get("model", model_name),
                "provider": result.get("provider", "unknown"),
                "route": routing["route"],
                "session_id": session_id,
                "rag_used": use_rag,
                "search_used": use_search,
                "sources": list(set(sources)) if sources else [],
                "web_sources": web_sources,
                "tokens": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                },
            }
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": f"Lỗi: {str(e)}", "model": model_name if 'model_name' in locals() else settings.MODEL_NAME,
                "provider": "error", "session_id": session_id, "error": True,
            }

    @staticmethod
    def generate_response_stream(message: str, session_id: str = "default",
                                  model_override: str = None, prefer_cloud: bool = True) -> Generator:
        message = sanitize_user_input(message)
        _error_model = model_override or settings.MODEL_NAME
        guard_error = ChatService._local_only_guard(stream=True, session_id=session_id)
        if guard_error:
            yield guard_error
            return
        try:
            yield {"step": "routing", "i18n_key": "stream.routing",
                   "message": "Analyzing question..."}

            routing = route_model(message)
            model_name = model_override or routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            is_local = ChatService._is_local_model(model_name)
            if is_local:
                use_rag = False

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                yield {"step": "rag", "i18n_key": "stream.rag",
                       "message": "📚 Searching internal documents..."}
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=2)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                yield {"step": "searching", "i18n_key": "stream.searching",
                       "message": "🔍 Searching the web..."}
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]
                    yield {"step": "search_done", "i18n_key": "stream.searchDone",
                           "i18n_params": {"count": len(search_results)},
                           "message": f"✅ Found {len(search_results)} results, analyzing..."}

            display_model = model_name if model_name else settings.CLOUD_MODEL_NAME
            yield {"step": "thinking", "i18n_key": "stream.thinking",
                   "i18n_params": {"model": display_model},
                   "message": f"🤖 Generating response ({display_model})..."}

            ss = ChatService.get_session_store()
            max_hist = 2 if is_local else 10
            history = ss.get_context_messages(session_id, max_messages=max_hist)
            is_log = (
                ChatService._is_log_analysis(message)
                or ChatService._session_in_log_mode(history or [])
            )
            messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)

            # Decide streaming path: only Ollama models support live token streaming here.
            response_text = ""
            result_meta = {"model": model_name, "provider": "unknown", "usage": {}}
            ollama_streamed = False

            if not prefer_cloud and is_local and ChatService._is_ollama_model(model_name):
                try:
                    yield {"step": "stream_start", "i18n_key": "stream.streamStart",
                           "message": "💭 Model is thinking — streaming live..."}
                    chunks = []
                    for ev in CloudLLMService.call_ollama_stream(
                        model=model_name, messages=messages, temperature=0.7
                    ):
                        if ev.get("type") == "token":
                            chunks.append(ev["content"])
                            yield {"step": "token", "token": ev["content"]}
                        elif ev.get("type") == "done":
                            response_text = ChatService.clean_response(ev.get("content", "") or "".join(chunks))
                            result_meta = {
                                "model": ev.get("model", model_name),
                                "provider": ev.get("provider", "ollama"),
                                "usage": ev.get("usage", {}),
                            }
                    ollama_streamed = True
                except Exception as stream_err:
                    logger.warning(f"[Stream] Ollama stream failed → falling back to non-stream: {stream_err}")
                    yield {"step": "stream_fallback", "i18n_key": "stream.fallback",
                           "message": "⚠️ Stream failed, switching to standard mode..."}

            if not ollama_streamed:
                result = CloudLLMService.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    local_model=model_name,
                    prefer_cloud=prefer_cloud,
                    cloud_model=model_override if prefer_cloud else None,
                )
                response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""
                result_meta = {
                    "model": result.get("model", model_name),
                    "provider": result.get("provider", "unknown"),
                    "usage": result.get("usage", {}),
                }

            if is_log and response_text:
                response_text = ChatService._normalize_log_output(response_text)

            ss.add_message(session_id, "user", message)
            if response_text:
                ss.add_message(session_id, "assistant", response_text)

            yield {
                "step": "done",
                "data": {
                    "response": response_text or "",
                    "response_i18n_key": None if response_text else "stream.noResponse",
                    "model": result_meta["model"],
                    "provider": result_meta["provider"],
                    "route": routing["route"],
                    "session_id": session_id,
                    "rag_used": use_rag, "search_used": use_search,
                    "sources": list(set(sources)) if sources else [],
                    "web_sources": web_sources,
                    "tokens": {
                        "prompt_tokens": result_meta["usage"].get("prompt_tokens", 0),
                        "completion_tokens": result_meta["usage"].get("completion_tokens", 0),
                        "total_tokens": result_meta["usage"].get("total_tokens", 0),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "step": "error",
                "data": {
                    "response": f"Error: {str(e)}",
                    "response_i18n_key": "stream.errorPrefix",
                    "response_i18n_params": {"message": str(e)},
                    "model": _error_model,
                    "session_id": session_id, "error": True,
                },
            }

    @staticmethod
    def clear_conversation(session_id: str) -> Dict[str, Any]:
        ss = ChatService.get_session_store()
        ss.clear_history(session_id)
        return {"status": "ok", "message": "Đã xóa ngữ cảnh hội thoại", "session_id": session_id}

    @staticmethod
    def _local_only_guard(stream: bool = False, session_id: str = "default"):
        if not settings.LOCAL_ONLY_MODE:
            return None
        models_ready = ModelGuard.is_ready()
        localai_ready = CloudLLMService.localai_health_check(model=settings.MODEL_NAME, timeout=8)
        if models_ready and localai_ready:
            return None

        message = "⚠️ Local-only mode đang bật nhưng hệ thống chưa sẵn sàng. "
        if not models_ready:
            missing = [m for m, status in ModelGuard.status().items() if status != "present"]
            message += f"Thiếu model: {', '.join(missing)}. "
        if not localai_ready:
            message += "LocalAI không phản hồi — kiểm tra container phobert-localai."

        if stream:
            return {
                "step": "done",
                "data": {
                    "response": message,
                    "model": settings.MODEL_NAME,
                    "provider": "local-only-guard",
                    "route": "guard",
                    "session_id": session_id,
                    "rag_used": False,
                    "search_used": False,
                    "sources": [],
                    "web_sources": [],
                    "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "error": True,
                },
            }

        return {
            "response": message,
            "model": settings.MODEL_NAME,
            "provider": "local-only-guard",
            "session_id": session_id,
            "error": True,
        }

    @staticmethod
    def assess_system(system_data: Dict[str, Any], model_mode: str = None,
                      progress_callback=None) -> Dict[str, Any]:
        """progress_callback(message: str, percent: int) — optional, called per chunk."""
        from services.controls_catalog import get_categories, get_flat_controls, calc_compliance, build_weight_breakdown
        from services.assessment_helpers import (
            build_chunk_prompt, validate_chunk_output, gap_items_to_markdown,
            build_full_prompt, build_weight_breakdown_txt, compress_for_phase2,
            build_sys_summary, infer_gap_from_control, normalize_severity_distribution,
            summarize_evidence,
        )

        # Step 3 — resolve effective mode with priority:
        # explicit arg → system_data["model_mode"] (request override) → settings default.
        effective_mode = (
            model_mode
            or system_data.get("model_mode")
            or getattr(settings, "ASSESSMENT_MODE", "hybrid")
            or "hybrid"
        ).lower()
        if effective_mode not in ("cloud", "local", "hybrid"):
            logger.warning(f"[Assessment] unknown mode '{effective_mode}' — falling back to 'hybrid'")
            effective_mode = "hybrid"
        vs = ChatService.get_vector_store()
        standard = system_data.get("assessment_standard", "iso27001")

        # Map assessment standard to its dedicated ChromaDB collection
        STANDARD_DOMAIN_MAP = {
            "iso27001": "iso27001",
            "tcvn11930": "tcvn11930",
            "nd13": "nd13",
            "nist_csf": "nist_csf",
            "pci_dss": "pci_dss",
            "hipaa": "hipaa",
            "gdpr": "gdpr",
            "soc2": "soc2",
        }
        rag_domain = STANDARD_DOMAIN_MAP.get(standard, "iso_documents")

        if standard == "tcvn11930":
            search_query = "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        elif standard == "nd13":
            search_query = "Nghị định 13 bảo vệ dữ liệu cá nhân"
        else:
            search_query = "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"

        custom_std = None
        try:
            from services.standard_service import load_standard
            custom_std = load_standard(standard)
        except Exception:
            pass

        if custom_std:
            std_name = custom_std.get("name", standard)
            search_query = f"{std_name} compliance security controls"
            for cat in custom_std.get("controls", []):
                search_query += f", {cat.get('category', '')}"
        else:
            std_name = "ISO 27001:2022" if standard != "tcvn11930" else "TCVN 11930:2017 (Yêu cầu kỹ thuật theo 5 cấp độ)"

        context_results = vs.search(search_query, top_k=6, domain=rag_domain)
        context = "\n---\n".join([r["text"] for r in context_results])

        implemented = system_data.get("compliance", {}).get("implemented_controls", [])
        compliance = calc_compliance(implemented, standard, custom_std)
        score = compliance["score"]
        max_score = compliance["max_score"]
        percentage = compliance["percentage"]

        # Load control catalog from controls_catalog module (ISO 27001, TCVN 11930, or custom)
        builtin_std_categories = get_categories(standard, custom_std)
        all_controls_flat = get_flat_controls(standard, custom_std)
        weight_breakdown, missing_controls_by_weight = build_weight_breakdown(implemented, all_controls_flat)
        weight_breakdown_txt = build_weight_breakdown_txt(weight_breakdown, missing_controls_by_weight)
        sys_summary_short = build_sys_summary(system_data)

        system_info_txt = (
            f"Tiêu chuẩn đánh giá: {std_name}\n"
            f"Mức độ tuân thủ: {score}/{max_score} Controls đạt yêu cầu ({percentage}%).\n"
            f"Các Controls đã đạt: {', '.join(implemented)}\n"
            f"{weight_breakdown_txt}\n"
            f"\nCHI TIẾT HẠ TẦNG HỆ THỐNG:\n{sys_summary_short}"
        )


        local_available = False
        if effective_mode in ("local", "hybrid"):
            local_available = CloudLLMService.localai_health_check(
                model=settings.SECURITY_MODEL_NAME, timeout=15
            )
            if not local_available:
                logger.warning(
                    f"[Assessment] LocalAI health check FAILED (model={settings.SECURITY_MODEL_NAME}) — "
                    f"auto-upgrade mode: local→hybrid, hybrid→cloud"
                )
                if effective_mode == "local":
                    if settings.cloud_api_key_list:
                        effective_mode = "hybrid"
                        logger.warning("[Assessment] local→hybrid fallback")
                    else:
                        raise Exception(
                            "LocalAI không khởi động được và không có Cloud API key. "
                            "Kiểm tra RAM và model GGUF trong LocalAI container."
                        )
                elif effective_mode == "hybrid":
                    effective_mode = "cloud"
                    logger.warning("[Assessment] hybrid→cloud fallback (LocalAI unavailable)")

        def _try_phase(messages, temperature, local_model, task_type, priority=False):
            """Try LocalAI first, then fallback to cloud if local load fails."""
            errors = []
            # If in hybrid and local is intended
            if effective_mode in ("local", "hybrid"):
                try:
                    return CloudLLMService._call_localai(local_model, messages, temperature, priority=priority)
                except Exception as e:
                    err_str = str(e)
                    errors.append(f"LocalAI: {err_str}")
                    logger.warning(f"[Assessment] LocalAI failed (task={task_type}): {err_str}")
                    is_load_error = any(kw in err_str for kw in ["Model load failed", "could not load model", "rpc error", "Canceled", "HTTP 500", "Connection error"])
                    if effective_mode == "local":
                        raise
                    # In hybrid: attempt cloud fallback for the phase
                    if is_load_error and settings.cloud_api_key_list:
                        try:
                            cloud_model = CloudLLMService._resolve_model("iso_analysis")
                            cloud_res = CloudLLMService._call_open_claude(messages, temperature, max_tokens=MIN_MAX_TOKENS, model=cloud_model, task_type="iso_analysis")
                            cloud_res["provider"] = cloud_res.get("provider", "open-claude") + "-fallback"
                            return cloud_res
                        except Exception as ce:
                            errors.append(f"Cloud fallback: {ce}")
                            logger.error(f"[Assessment] Cloud fallback failed after LocalAI error: {ce}")
            else:
                # cloud mode only
                return CloudLLMService._call_open_claude(messages, temperature, max_tokens=MIN_MAX_TOKENS, task_type=task_type)

            raise Exception("; ".join(errors))

        if effective_mode == "local":
            p1_task_type = "iso_local"
            p1_model = settings.SECURITY_MODEL_NAME
            p2_task_type = "iso_local"
            p2_model = settings.MODEL_NAME  # Meta-Llama cho report formatting
            logger.info(f"[Assessment] local — P1={p1_model}, P2={p2_model}")
        elif effective_mode == "cloud":
            p1_task_type = "iso_analysis"
            p1_model = None  # resolved by CloudLLMService
            p2_task_type = "iso_analysis"
            p2_model = None
            logger.info("[Assessment] cloud — both phases OpenClaude")
        else:  # hybrid
            p1_task_type = "iso_local"
            p1_model = settings.SECURITY_MODEL_NAME
            p2_task_type = "iso_analysis"
            p2_model = None  # OpenClaude for report
            logger.info(f"[Assessment] hybrid — P1={p1_model} (LocalAI), P2=OpenClaude")

        # Step 3 — for hybrid/local, pre-compute a SecurityLM evidence summary
        # so chunk drafting can cite it instead of re-reading raw evidence.
        evidence_summary = ""
        if effective_mode in ("hybrid", "local"):
            evidence_text = (system_data.get("notes", "") or "").strip()
            if evidence_text:
                try:
                    evidence_summary = summarize_evidence(
                        evidence_text,
                        max_tokens=getattr(settings, "EVIDENCE_SUMMARY_TOKENS", 256),
                        logger=logger,
                    )
                    if evidence_summary:
                        logger.info(
                            f"[Assessment] evidence summary OK "
                            f"({len(evidence_summary)} chars, mode={effective_mode})"
                        )
                    else:
                        logger.info(f"[Assessment] evidence summary empty (mode={effective_mode})")
                except Exception as se:
                    logger.warning(f"[Assessment] summarize_evidence failed: {se}")
                    evidence_summary = ""

        try:
            raw_analysis = ""
            result_p1 = None

            if p1_task_type == "iso_local" and all_controls_flat:
                std_categories = builtin_std_categories or [{"category": "Tất cả Controls", "controls": all_controls_flat}]

                all_gap_items = []
                n_cats = len(std_categories)
                logger.info(f"[Assessment] Chunked mode: {n_cats} categories")

                if progress_callback:
                    progress_callback("Bắt đầu phân tích từng nhóm controls...", 10)

                for cat_idx, category in enumerate(std_categories):
                    cat_name = category.get("category", f"Category {cat_idx+1}")
                    cat_controls = category.get("controls", [])
                    missing_in_cat = [c for c in cat_controls if c["id"] not in implemented]

                    if progress_callback:
                        pct = 10 + int((cat_idx / n_cats) * 70)
                        progress_callback(f"Đang phân tích {cat_name}... ({cat_idx+1}/{n_cats})", pct)

                    if not missing_in_cat:
                        logger.info(f"[Assessment] '{cat_name}' — all implemented, skip")
                        continue

                    # RAG: get category-specific context from ChromaDB (domain-scoped)
                    cat_rag_query = f"{cat_name} {std_name} controls requirements"
                    try:
                        cat_rag = vs.search(cat_rag_query, top_k=2, domain=rag_domain)
                        cat_rag_ctx = "\n---\n".join(r["text"][:300] for r in cat_rag)
                    except Exception:
                        cat_rag_ctx = ""

                    chunk_prompt = build_chunk_prompt(
                        cat_name, cat_controls, implemented,
                        percentage, score, max_score,
                        sys_summary_short, std_name, cat_rag_ctx,
                        evidence_summary=evidence_summary or None,
                    )
                    chunk_messages = [{"role": "user", "content": chunk_prompt}]

                    chunk_gap_items = None
                    for attempt in range(3):
                        try:
                            chunk_result = _try_phase(
                                messages=chunk_messages,
                                temperature=0.1,
                                local_model=p1_model or settings.SECURITY_MODEL_NAME,
                                task_type=p1_task_type,
                                priority=True,
                            )
                            if result_p1 is None:
                                result_p1 = chunk_result
                            chunk_content = chunk_result.get("content", "").strip()
                            valid_ids = [c["id"] for c in cat_controls]
                            chunk_gap_items = validate_chunk_output(chunk_content, cat_name, valid_ids=valid_ids)
                            if chunk_gap_items is not None:
                                logger.info(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {len(chunk_gap_items)} gaps")
                                break
                            logger.warning(f"[Assessment] Chunk '{cat_name}' invalid JSON attempt {attempt+1}")
                        except Exception as chunk_err:
                            logger.warning(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {chunk_err}")

                    if chunk_gap_items:
                        all_gap_items.extend(chunk_gap_items)
                    elif chunk_gap_items is None:
                        # All LLM attempts failed — infer gaps from control metadata as fallback
                        logger.warning(f"[Assessment] Chunk '{cat_name}' all attempts failed — using inferred gaps")
                        for ctrl in missing_in_cat[:10]:
                            all_gap_items.append(infer_gap_from_control(ctrl, cat_name))

                # Normalize severity if model marks too many as critical
                all_gap_items = normalize_severity_distribution(all_gap_items)
                raw_analysis = gap_items_to_markdown(all_gap_items)
                logger.info(f"[Assessment] All chunks complete — {len(all_gap_items)} total gaps, raw: {len(raw_analysis)} chars")

            else:
                security_prompt, user_msg = build_full_prompt(std_name, percentage, score, max_score, system_info_txt, context)
                messages_p1 = [
                    {"role": "system", "content": security_prompt},
                    {"role": "user", "content": user_msg},
                ]
                result_p1 = _try_phase(
                    messages=messages_p1,
                    temperature=0.1,
                    local_model=p1_model or settings.SECURITY_MODEL_NAME,
                    task_type=p1_task_type,
                    priority=True,
                )
                raw_analysis = result_p1.get("content", "")

            raw_analysis_p2 = compress_for_phase2(raw_analysis)

            today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
            org_name = system_data.get("organization", {}).get("name", "Tổ chức")
            industry = system_data.get("organization", {}).get("industry", "")
            org_size = system_data.get("organization", {}).get("size", "")
            employees = system_data.get("organization", {}).get("employees", 0)
            mode_label = {
                "local": "LocalAI: SecurityLM (Phase 1) + Meta-Llama (Phase 2)",
                "cloud": "Cloud only (OpenClaude)",
                "hybrid": "Hybrid: SecurityLM local (Phase 1) + OpenClaude (Phase 2)"
            }

            weight_summary = f"\n\nDữ liệu trọng số:\n{weight_breakdown_txt}" if weight_breakdown_txt else ""

            formatting_prompt = (
                f"Bạn là chuyên gia trình bày Báo cáo Đánh giá An toàn Thông tin chuyên nghiệp.\n"
                f"Trình bày báo cáo bằng Markdown tiếng Việt, CẤU TRÚC BẮT BUỘC:\n\n"
                f"## 1. ĐÁNH GIÁ TỔNG QUAN\n"
                f"Tuân thủ: {percentage}% — {score}/{max_score} Controls đạt\n"
                f"Bảng phân bổ: Critical/High/Medium/Low đạt bao nhiêu %\n\n"
                f"## 2. RISK REGISTER\n"
                f"| # | Control | GAP | Severity | L | I | Risk | Khuyến nghị | Timeline |\n"
                f"|---|---------|-----|----------|---|---|------|-------------|----------|\n"
                f"Severity: 🔴 Critical 🟠 High 🟡 Medium ⚪ Low | Risk=L×I giảm dần\n\n"
                f"## 3. GAP ANALYSIS\n"
                f"Phân nhóm theo severity, Critical trước.\n\n"
                f"## 4. ACTION PLAN\n"
                f"Ngắn hạn (0-30 ngày) | Trung hạn (1-3 tháng) | Dài hạn (3-12 tháng)\n\n"
                f"## 5. EXECUTIVE SUMMARY\n"
                f"a) Metrics: compliance%, controls đạt/thiếu, risk breakdown\n"
                f"b) Top 3 rủi ro + ngân sách khắc phục ước tính (VND)\n"
                f"c) Next Steps: 3 hành động ưu tiên trong 30 ngày\n\n"
                f"Tổ chức: {org_name} | Ngành: {industry} | Tiêu chuẩn: {std_name} | {today}\n\n"
                f"--- DỮ LIỆU ĐẦU VÀO ---\n{raw_analysis_p2}{weight_summary}"
            )
            result_p2 = _try_phase(
                messages=[{"role": "user", "content": formatting_prompt}],
                temperature=0.5,
                local_model=p2_model or settings.MODEL_NAME,
                task_type=p2_task_type,
                priority=False,
            )
            markdown_report = result_p2.get("content", "")

            json_data = ChatService._build_structured_json(
                raw_analysis=raw_analysis,
                percentage=percentage,
                score=score,
                max_score=max_score,
                implemented=implemented,
                weight_breakdown=weight_breakdown,
                missing_controls_by_weight=missing_controls_by_weight,
                org_name=org_name,
                industry=industry,
                org_size=org_size,
                employees=employees,
                std_name=std_name,
                standard=standard,
                today=today,
                effective_mode=effective_mode,
            )

            return {
                "report": markdown_report,
                "json_data": json_data,
                "details": [],
                "model_mode": effective_mode,
                "model_used": {
                    "phase1": f"{result_p1.get('provider') if result_p1 else 'localai'}:{result_p1.get('model') if result_p1 else settings.SECURITY_MODEL_NAME}",
                    "phase2": f"{result_p2.get('provider')}:{result_p2.get('model')}",
                },
            }
        except Exception as e:
            logger.error(f"Assessment error: {e}")
            return {"report": f"Lỗi tạo báo cáo: {str(e)}", "details": [], "error": True}

    @staticmethod
    def _build_structured_json(
        raw_analysis: str,
        percentage: float,
        score: int,
        max_score: int,
        implemented: list,
        weight_breakdown: dict,
        missing_controls_by_weight: dict,
        org_name: str,
        industry: str,
        org_size: str,
        employees: int,
        std_name: str,
        standard: str,
        today: str,
        effective_mode: str,
    ) -> dict:
        """
        Build structured JSON output for dashboard consumption.
        Parses GAP severity counts from raw Phase 1 analysis and packages
        all scoring data into a clean, frontend-parseable dict.
        """
        import re

        critical_count = len(re.findall(r'🔴|Critical|critical', raw_analysis))
        high_count = len(re.findall(r'🟠|High(?!est)', raw_analysis))
        medium_count = len(re.findall(r'🟡|Medium|medium', raw_analysis))
        low_count = len(re.findall(r'⚪|Low(?!est)', raw_analysis))

        # Clamp to plausible range (avoid duplicate mentions inflating counts)
        total_gap_mentions = critical_count + high_count + medium_count + low_count
        if total_gap_mentions > 200:
            # Normalise: divide by ~3 to account for repeated mentions
            critical_count = max(0, critical_count // 3)
            high_count = max(0, high_count // 3)
            medium_count = max(0, medium_count // 3)
            low_count = max(0, low_count // 3)

        wb = weight_breakdown or {}
        missing = missing_controls_by_weight or {}

        def wb_pct(w):
            bd = wb.get(w, {})
            total = bd.get("total", 0)
            impl = bd.get("implemented", 0)
            return round((impl / total * 100), 1) if total > 0 else 0.0

        if percentage >= 80:
            tier = "high"
            tier_label = "Tuân thủ cao"
        elif percentage >= 50:
            tier = "medium"
            tier_label = "Tuân thủ một phần"
        elif percentage >= 25:
            tier = "low"
            tier_label = "Tuân thủ thấp"
        else:
            tier = "critical"
            tier_label = "Không tuân thủ"

        top_gaps = []
        for sev in ["critical", "high", "medium"]:
            for ctrl_str in (missing.get(sev, []))[:5]:
                parts = ctrl_str.split(" (", 1)
                ctrl_id = parts[0].strip()
                ctrl_label = parts[1].rstrip(")") if len(parts) > 1 else ""
                top_gaps.append({"id": ctrl_id, "label": ctrl_label, "severity": sev})
            if len(top_gaps) >= 10:
                break

        return {
            "assessment_date": today,
            "standard": standard,
            "standard_name": std_name,
            "ai_mode": effective_mode,
            "organization": {
                "name": org_name,
                "industry": industry,
                "size": org_size,
                "employees": employees,
            },
            "compliance": {
                "score": score,
                "max_score": max_score,
                "percentage": percentage,
                "tier": tier,
                "tier_label": tier_label,
                "implemented_count": len(implemented),
                "missing_count": max_score - score,
            },
            "weight_breakdown": {
                "critical": {
                    "total": wb.get("critical", {}).get("total", 0),
                    "implemented": wb.get("critical", {}).get("implemented", 0),
                    "percent": wb_pct("critical"),
                },
                "high": {
                    "total": wb.get("high", {}).get("total", 0),
                    "implemented": wb.get("high", {}).get("implemented", 0),
                    "percent": wb_pct("high"),
                },
                "medium": {
                    "total": wb.get("medium", {}).get("total", 0),
                    "implemented": wb.get("medium", {}).get("implemented", 0),
                    "percent": wb_pct("medium"),
                },
                "low": {
                    "total": wb.get("low", {}).get("total", 0),
                    "implemented": wb.get("low", {}).get("implemented", 0),
                    "percent": wb_pct("low"),
                },
            },
            "risk_summary": {
                "critical_gaps": critical_count,
                "high_gaps": high_count,
                "medium_gaps": medium_count,
                "low_gaps": low_count,
                "total_gaps": critical_count + high_count + medium_count + low_count,
            },
            "top_gaps": top_gaps,
            "implemented_controls": implemented,
        }

    @staticmethod
    def health_check() -> Dict[str, Any]:
        return CloudLLMService.health_check()
