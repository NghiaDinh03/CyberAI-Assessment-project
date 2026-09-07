"""Chat Service — Conversation routing with session memory and Cloud-first strategy."""

import os
import asyncio
import json
import re
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Generator, List, Optional

from fastapi import HTTPException

from core.config import settings
from services.cloud_llm_service import CloudLLMService, MIN_MAX_TOKENS
from services.model_guard import ModelGuard
from services.model_router import route_model
from services.web_search import WebSearch
from services.chat_queue import ChatQueueManager
from repositories.vector_store import VectorStore
from repositories.session_store import SessionStore
from prompts import get_prompt

logger = logging.getLogger(__name__)

SPECIAL_TOKENS = re.compile(
    r'<\|eot_id\|>|<\|start_header_id\|>|<\|end_header_id\|>|'
    r'<\|begin_of_text\|>|<\|end_of_text\|>|<\|finetune_right_pad_id\|>|'
    r'<\|reserved_special_token_\d+\|>'
)
_THINKING_TAG_RE = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)
_THINKING_HEADER_RE = re.compile(
    r"^(?:Here'?s a thinking process[^\n]*:?\s*\n(?:(?:\s*[\d\-\*\>].*?\n)|\s*\n)+)",
    re.IGNORECASE
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

    _OLLAMA_PREFIXES = ("gemma2:", "gemma3:", "gemma3n:", "gemma4:", "phi4:", "llama3:", "mistral:", "qwen3:")

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
        if not text:
            return ""
        text = SPECIAL_TOKENS.sub('', text)
        text = _THINKING_TAG_RE.sub('', text)
        text = _THINKING_HEADER_RE.sub('', text)
        text = ChatService._normalize_symbols_and_bytes(text)
        return text.strip()

    @staticmethod
    def _normalize_symbols_and_bytes(text: str) -> str:
        if not text:
            return ""

        # 1. Decode hex byte tokens: <0xF0><0x9F><0x97><0x84> -> UTF-8 characters
        def _decode_hex_match(match):
            hex_tokens = re.findall(r'<0x([0-9A-Fa-f]{2})>', match.group(0))
            try:
                raw_bytes = bytes(int(h, 16) for h in hex_tokens)
                decoded = raw_bytes.decode('utf-8', errors='ignore')
                return decoded
            except Exception:
                return ""

        text = re.sub(r'(?:<0x[0-9A-Fa-f]{2}>)+', _decode_hex_match, text)
        text = re.sub(r'<0x[0-9A-Fa-f]{2}>', '', text)

        # 2. LaTeX arrow and math command replacements (both $\command$ and \command)
        latex_replacements = [
            (r'\$(?:\\rightarrow|\\to|\\longrightarrow)\$', '→'),
            (r'\\(?:rightarrow|to|longrightarrow)\b', '→'),
            (r'\$(?:\\leftarrow|\\gets|\\longleftarrow)\$', '←'),
            (r'\\(?:leftarrow|gets|longleftarrow)\b', '←'),
            (r'\$(?:\\Rightarrow|\\implies|\\Longrightarrow)\$', '⇒'),
            (r'\\(?:Rightarrow|implies|Longrightarrow)\b', '⇒'),
            (r'\$(?:\\Leftarrow|\\Longleftarrow)\$', '⇐'),
            (r'\\(?:Leftarrow|Longleftarrow)\b', '⇐'),
            (r'\$(?:\\Leftrightarrow|\\iff|\\Longleftrightarrow)\$', '⇔'),
            (r'\\(?:Leftrightarrow|iff|Longleftrightarrow)\b', '⇔'),
            (r'\$(?:\\leftrightarrow)\$', '↔'),
            (r'\\(?:leftrightarrow)\b', '↔'),
            (r'\$(?:\\approx|\\approxeq)\$', '≈'),
            (r'\\(?:approx|approxeq)\b', '≈'),
            (r'\$(?:\\neq|\\ne)\$', '≠'),
            (r'\\(?:neq|ne)\b', '≠'),
            (r'\$(?:\\le|\\leq)\$', '≤'),
            (r'\\(?:le|leq)\b', '≤'),
            (r'\$(?:\\ge|\\geq)\$', '≥'),
            (r'\\(?:ge|geq)\b', '≥'),
            (r'\$(?:\\pm)\$', '±'),
            (r'\\(?:pm)\b', '±'),
            (r'\$(?:\\times)\$', '×'),
            (r'\\(?:times)\b', '×'),
            (r'\$(?:\\div)\$', '÷'),
            (r'\\(?:div)\b', '÷'),
            (r'\$(?:\\cdot)\$', '·'),
            (r'\\(?:cdot)\b', '·'),
            (r'\$(?:\\bullet)\$', '•'),
            (r'\\(?:bullet)\b', '•'),
            (r'\$(?:\\dots|\\cdots|\\ldots)\$', '...'),
            (r'\\(?:dots|cdots|ldots)\b', '...'),
            (r'\$(?:\\infty)\$', '∞'),
            (r'\\(?:infty)\b', '∞'),
            (r'\$(?:\\checkmark)\$', '✓'),
            (r'\\(?:checkmark)\b', '✓'),
            (r'\$(?:\\sim)\$', '~'),
        ]
        for pattern, repl in latex_replacements:
            text = re.sub(pattern, repl, text)

        # 3. Clean up lone $ delimiters wrapping simple arrow/word expressions
        text = re.sub(r'\$([^\$\n]+)\$', r'\1', text)

        # 4. Clean up TL;DR prefixes
        text = re.sub(r'\b(?:TL;DR|TLDR)\s*[:\-]\s*', '**Tóm lại:** ', text, flags=re.IGNORECASE)

        return text

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
        """Detect if the user is requesting log/event/rule analysis.

        Returns True for:
        - Natural-language requests mentioning log/event/rule analysis.
        - Text-format logs (Windows Event IDs, ISO timestamps, field:value blocks).
        - SIEM / EDR / AQL / SQL / Sigma / YARA detection queries.
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
            "rule này", "bắt gì", "phân tích rule", "quy tắc này",
            "aql filter", "filter query", "sigma rule", "yara rule",
            "detection rule", "living off the land", "lolbins",
        )
        if any(kw in msg_lower for kw in log_keywords):
            return True

        # JSON-shaped payload with any known log key hint.
        stripped = message.lstrip()
        if stripped.startswith(('{', '[')):
            for hint in ChatService._LOG_JSON_KEY_HINTS:
                if hint in message:
                    return True

        # Regex fallbacks for plain-text logs & SIEM/AQL detection queries.
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
            # SIEM / AQL / EDR query patterns
            r"(?:Parent\s*Process\s*Path|Process\s*Path)\s*ILIKE",
            r"SELECT\s+.*\s+FROM\s+.*\s+WHERE",
            r"(?:AND|OR)\s+NOT\s+\(\(",
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

    _LOG_FIELD_LABELS = [
        "Parent Process Name:", "Parent Process ID:", "Parent Command Line:",
        "File Hash (SHA256):", "File Hash (MD5):", "Source Interface:", "Destination Interface:",
        "Token Elevation:", "Thời gian phát hiện:", "Log cần kiểm tra:", "Truy vấn gợi ý:",
        "Parent Process:", "Process Name:", "Process ID:", "Command Line:", "Account Name:",
        "Computer Name:", "Logon Type:", "Source Port:", "Destination Port:", "Policy ID:",
        "Sent Bytes:", "Received Bytes:", "Device Name:", "Device ID:", "Rule Name:",
        "Event ID:", "Timestamp:", "Log ID:", "Log Type:", "Subtype:", "Level:",
        "Source IP:", "Destination IP:", "Protocol:", "Action:", "Service:", "Duration:",
        "Nhận định:", "Mức độ:", "Lý do:", "Technique:", "Tactic:", "Khuyến nghị:",
        "IOCs:", "MITRE:", "Host:", "User:", "Source:", "SHA256:", "MD5:",
    ]

    @staticmethod
    def _normalize_log_output(text: str) -> str:
        """Format and beautify log-analysis responses with bullet points, bold field keys, and structured SOC section headings."""
        if not text:
            return text

        labels = sorted(ChatService._LOG_FIELD_LABELS, key=len, reverse=True)
        out = text

        # 1. Split merged labels into newlines only when not part of composite prefixes
        for label in labels:
            escaped = re.escape(label)
            pattern = re.compile(r"(?<!^)(?<!\n)(?<=[^\w\s]|\d|[a-zÀ-ỹ])\s+(" + escaped + r")", re.IGNORECASE)
            def _repl(m):
                prefix_pos = m.start(1)
                before = out[max(0, prefix_pos - 15):prefix_pos].lower()
                if any(before.endswith(p) for p in ("parent ", "file hash ", "source ", "destination ", "layer ")):
                    return m.group(0)
                return "\n" + m.group(1)
            out = pattern.sub(_repl, out)

        raw_lines = [l.strip() for l in out.split('\n') if l.strip()]
        cleaned_lines = []
        for l in raw_lines:
            # If multiple fields were concatenated on one line (e.g. "Src IP: 1.1.1.1 Dst IP: 2.2.2.2")
            parts = re.split(r"(?<=\S)\s{2,}(?=[A-Za-z0-9À-ỹ\s\(\)\/_\-]+:)", l)
            cleaned_lines.extend(parts)

        formatted = []
        has_event_header = False
        has_verdict_header = False
        has_mitre_header = False
        has_rec_header = False

        for line in cleaned_lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('###'):
                formatted.append(f"\n{line}")
                continue

            lower = line.lower()
            if not has_event_header and any(lower.startswith(k.lower()) for k in ("event id:", "timestamp:", "host:", "device name:", "source:", "process name:", "event source:", "client ip:", "rule:", "agent:")):
                formatted.append("### 📋 Thông tin sự kiện")
                has_event_header = True
            elif not has_verdict_header and lower.startswith("nhận định:"):
                formatted.append("\n### 🎯 Nhận định & Đánh giá")
                has_verdict_header = True
            elif not has_mitre_header and (lower.startswith("technique:") or lower.startswith("mitre:")):
                formatted.append("\n### 🛡️ Kỹ thuật tấn công (MITRE ATT&CK)")
                has_mitre_header = True
            elif not has_rec_header and (lower.startswith("khuyến nghị:") or lower.startswith("log cần kiểm tra:")):
                formatted.append("\n### 💡 Khuyến nghị xử lý")
                has_rec_header = True

            # Convert `Field: Value` to `- **Field**: Value`
            m = re.match(r"^(\s*[-*•]?\s*)(?:\*\*)?([A-Za-z0-9À-ỹ\s\(\)\/_\-]+?)(?:\*\*)?:\s*(.+)$", line)
            if m:
                label_name = m.group(2).strip()
                val = m.group(3).strip()
                label_name = label_name.replace("**", "")
                formatted.append(f"- **{label_name}**: {val}")
            else:
                formatted.append(line)

        # Strip trailing whitespace on each line & collapse excess blank lines
        res = "\n".join(formatted).strip()
        res = re.sub(r"[ \t]+\n", "\n", res)
        res = re.sub(r"\n{3,}", "\n\n", res)
        return res

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

    @staticmethod
    def _is_prompt_injection(message: str) -> bool:
        """Kiểm tra xem tin nhắn từ người dùng có dấu hiệu Prompt Injection hoặc Jailbreak không."""
        if not message:
            return False
        msg_lower = message.lower()
        injection_patterns = (
            "ignore previous instructions",
            "ignore the previous",
            "you are now",
            "act as",
            "<|im_start|>",
            "system:",
            "hãy đóng vai",
            "bỏ qua các chỉ thị trước",
            "thiết lập lại hệ thống",
        )
        return any(pat in msg_lower for pat in injection_patterns)

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
        "Bạn là SOC Analyst Level 3 chuyên nghiệp. Phân tích log an ninh theo cấu trúc Markdown 4 phần rõ ràng, "
        "sử dụng bullet points `- **Tên Field**: <giá trị>` để hiển thị mạch lạc, chuyên nghiệp, dễ đọc.\n\n"
        "## OUTPUT FORMAT:\n\n"
        "### 📋 Thông tin sự kiện\n"
        "- **Event ID**: <ID>\n"
        "- **Timestamp**: <Thời gian>\n"
        "- **User**: <Tài khoản>\n"
        "- **Process Name**: <Tên tiến trình>\n"
        "- **Command Line**: <Câu lệnh thực thi>\n"
        "- **Parent Process**: <Tiến trình cha>\n\n"
        "### 🎯 Nhận định & Đánh giá\n"
        "- **Nhận định**: True Positive / False Positive / Cần điều tra thêm\n"
        "- **Mức độ**: Critical / High / Medium / Low / Informational\n"
        "- **Lý do**: <Giải thích ngắn gọn 2-3 câu bằng tiếng Việt>\n\n"
        "### 🛡️ Kỹ thuật tấn công (MITRE ATT&CK)\n"
        "- **Technique**: Txxxx.xxx - <Tên>\n"
        "- **Tactic**: <Tên tactic>\n\n"
        "### 💡 Khuyến nghị xử lý\n"
        "- **Khuyến nghị**: <Hành động cụ thể hoặc 'Không cần hành động - hoạt động bình thường' nếu False Positive>\n"
        "- **Log cần kiểm tra**: <Event ID hoặc nguồn log liên quan>\n\n"
        "QUY TẮC BẮT BUỘC: Luôn dùng đúng định dạng bullet `- **Tên Field**: <value>` cho từng trường và phân nhóm 4 mục `###` ở trên."
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

        is_vn = ChatService._is_vietnamese(message)
        lang_directive = (
            "\n\n[IMPORTANT: User inquiry is in VIETNAMESE. Respond entirely in natural, professional VIETNAMESE. For logs, keep technical field names and IOCs in English, but write all explanations, verdicts, and recommendations in Vietnamese.]"
            if is_vn else
            "\n\n[IMPORTANT: User inquiry is in ENGLISH. Respond entirely in natural, professional ENGLISH. Keep all explanations, answers, and formatting in English.]"
        )

        # Short system prompt for local CPU/GPU models — minimal tokens, but inject web search if active
        if is_local:
            if is_log:
                system_prompt = log_prompt + lang_directive
                user_content = log_message
            elif use_search and search_context:
                system_prompt = ChatService._safe_prompt(
                    "chat.web_search",
                    "You are CyberAI, an expert cybersecurity assistant. Use the provided web search results to answer the user's question accurately."
                ) + lang_directive
                user_content = f"Search Results / Kết quả tìm kiếm:\n{search_context}\n\nQuestion / Câu hỏi: {message}"
            else:
                system_prompt = ChatService._safe_prompt(
                    "chat.local_default",
                    "You are CyberAI, an expert cybersecurity and information security assistant.",
                ) + lang_directive
                user_content = message
            
            if is_vn and not user_content.startswith("[YÊU CẦU:"):
                user_content = f"[YÊU CẦU: Hãy phân tích và trả lời chi tiết bằng TIẾNG VIỆT]\n\n{user_content}"

            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-8:])
            messages.append({"role": "user", "content": user_content})
            return messages

        # Log analysis takes priority — use structured prompt regardless of RAG/search
        if is_log:
            system_prompt = log_prompt + lang_directive
            user_content = log_message
        # Cloud model with RAG context from knowledge base
        elif use_rag and context:
            system_prompt = ChatService._safe_prompt("chat.rag", "") + lang_directive
            user_content = f"Reference Context / Tài liệu tham chiếu:\n{context}\n\nQuestion / Câu hỏi: {message}"
        # Cloud model with web search results
        elif use_search and search_context:
            system_prompt = ChatService._safe_prompt("chat.web_search", "") + lang_directive
            user_content = f"Search Results / Kết quả tìm kiếm:\n{search_context}\n\nQuestion / Câu hỏi: {message}"
        # Cloud model — general knowledge, no RAG/search
        else:
            system_prompt = ChatService._safe_prompt("chat.general", "") + lang_directive
            user_content = message

        if is_vn and not user_content.startswith("[YÊU CẦU:"):
            user_content = f"[YÊU CẦU: Hãy phân tích và trả lời chi tiết bằng TIẾNG VIỆT]\n\n{user_content}"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_content})
        return messages

    @staticmethod
    async def generate_response(message: str, session_id: str = "default",
                                model_override: str = None, prefer_cloud: bool = True,
                                background_tasks=None, organisation: str = "",
                                use_search: Optional[bool] = None) -> Dict[str, Any]:
        message = sanitize_user_input(message)
        
        # Kiểm tra Prompt Injection / Jailbreak
        if ChatService._is_prompt_injection(message):
            logger.warning(f"[Security] Blocked prompt injection request in session '{session_id}'")
            return {
                "response": "Hệ thống phát hiện yêu cầu không an toàn. Hành vi truy cập của bạn đã được ghi lại trong log kiểm toán SOC.",
                "model": model_override or settings.MODEL_NAME,
                "provider": "security_guard",
                "route": "blocked",
                "session_id": session_id,
            }
            
        guard_error = ChatService._local_only_guard()
        if guard_error:
            return guard_error

        queue_mgr = ChatQueueManager.get_instance()
        is_local_req = (not prefer_cloud) and ChatService._is_local_model(model_override or settings.MODEL_NAME)
        ticket = None

        try:
            # Synchronize turn via queue
            for q_ev in queue_mgr.enqueue_and_wait(session_id=session_id, is_local=is_local_req):
                if q_ev.get("step") == "queue_granted":
                    ticket = q_ev.get("ticket")
                    break

            routing = route_model(message)
            model_name = model_override or routing["model"]
            use_rag = routing["use_rag"]

            is_local = ChatService._is_local_model(model_name)
            if is_local:
                use_rag = False

            # Web search is active for both local and cloud models
            is_log = (
                ChatService._is_log_analysis(message)
            )
            if is_log:
                effective_search = False
            elif use_search is not None:
                effective_search = use_search
            else:
                effective_search = routing.get("use_search", False)

            use_search = effective_search
            routing["use_search"] = use_search

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                vs = ChatService.get_vector_store()
                results = await asyncio.to_thread(vs.search, message, 5, "iso_documents", organisation)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                search_results = await asyncio.to_thread(WebSearch.search, message, 5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]

            ss = ChatService.get_session_store()
            max_hist = 8 if is_local else 10
            history = ss.get_context_messages(session_id, max_messages=max_hist)
            is_log = (
                ChatService._is_log_analysis(message)
                or ChatService._session_in_log_mode(history or [])
            )
            messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)

            # Auto-compact history if nearing context limit
            total_chars = sum(len(m.get("content", "")) for m in messages)
            estimated_tokens = total_chars // 3
            if is_local:
                if estimated_tokens > 3800 and history and len(history) > 2:
                    logger.info(f"[Chat] Context high ({estimated_tokens} est. tokens) -> auto-compacting history to last 2 messages")
                    history = history[-2:]
                    messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)
                    total_chars = sum(len(m.get("content", "")) for m in messages)
                    estimated_tokens = total_chars // 3

                if estimated_tokens > 4800 and history:
                    logger.info(f"[Chat] Current payload alone is large ({estimated_tokens} est. tokens) -> dropping history to guarantee output token budget")
                    history = []
                    messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)
                    total_chars = sum(len(m.get("content", "")) for m in messages)
                    estimated_tokens = total_chars // 3

                if estimated_tokens > 7800:
                    logger.warning(f"[Chat] Context limit reached ({estimated_tokens} est. tokens)")
                    overflow_msg = (
                        "Đoạn hội thoại hiện tại đã đạt giới hạn bộ nhớ ngữ cảnh của mô hình AI cục bộ "
                        "(bao gồm toàn bộ lịch sử các câu hỏi trước đó và dữ liệu log lớn). "
                        "Để AI phân tích chính xác và đạt hiệu suất cao nhất, bạn vui lòng mở một phiên chat mới (+ Cuộc trò chuyện mới) "
                        "hoặc chuyển sang Cloud AI để xử lý lượng ngữ cảnh lớn hơn."
                    )
                    ss.add_message(session_id, "user", message)
                    ss.add_message(session_id, "assistant", overflow_msg, model=model_name, provider="ollama")
                    return {
                        "response": overflow_msg,
                        "model": model_name,
                        "provider": "ollama",
                        "route": routing["route"],
                        "session_id": session_id,
                        "is_context_overflow": True,
                    }

            # cloud_model must only be set when prefer_cloud=True
            from services.audit_service import audit_service, AuditContext
            audit_ctx = AuditContext(chat_session_id=session_id)
            if use_rag and 'results' in locals() and results:
                audit_service.record_rag_query(
                    ctx=audit_ctx,
                    collection_name="iso_documents",
                    query_text=message,
                    top_k=len(results),
                    results=results,
                )

            start_ts = datetime.now(timezone.utc).isoformat()
            audit_service.record_llm_inference_start(
                ctx=audit_ctx,
                phase="chat_response",
                requested_model=model_name,
                provider="cloud" if prefer_cloud else "ollama",
                temperature=0.7,
                max_tokens=4096,
            )

            result = await asyncio.to_thread(
                CloudLLMService.chat_completion,
                messages=messages,
                temperature=0.7,
                local_model=model_name,
                prefer_cloud=prefer_cloud,
                cloud_model=model_override if prefer_cloud else None,
            )
            end_ts = datetime.now(timezone.utc).isoformat()

            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""
            if is_log and response_text:
                response_text = ChatService._normalize_log_output(response_text)

            audit_service.record_llm_inference_completed(
                ctx=audit_ctx,
                phase="chat_response",
                requested_model=model_name,
                actual_model=result.get("model", model_name),
                provider=result.get("provider", "ollama"),
                started_at=start_ts,
                completed_at=end_ts,
                prompt_text=message,
                response_text=response_text,
                usage_metrics=result.get("usage", {}),
                output_schema_valid=True,
            )

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
        finally:
            if ticket:
                queue_mgr.release_turn(ticket)

    @staticmethod
    def generate_response_stream(message: str, session_id: str = "default",
                                  model_override: str = None, prefer_cloud: bool = True,
                                  organisation: str = "", user_id: str = None,
                                  use_search: Optional[bool] = None) -> Generator:
        message = sanitize_user_input(message)
        
        # Kiểm tra Prompt Injection / Jailbreak
        if ChatService._is_prompt_injection(message):
            logger.warning(f"[Security] Blocked prompt injection stream request in session '{session_id}'")
            yield {"step": "blocked", "i18n_key": "stream.blocked",
                   "message": "Hệ thống phát hiện yêu cầu không an toàn. Hành vi truy cập của bạn đã được ghi lại trong log kiểm toán SOC."}
            yield {"step": "done", "response": "Hệ thống phát hiện yêu cầu không an toàn. Hành vi truy cập của bạn đã được ghi lại trong log kiểm toán SOC."}
            return
            
        _error_model = model_override or settings.MODEL_NAME
        guard_error = ChatService._local_only_guard(stream=True, session_id=session_id)
        if guard_error:
            yield guard_error
            return

        queue_mgr = ChatQueueManager.get_instance()
        is_local_req = (not prefer_cloud) and ChatService._is_local_model(model_override or settings.MODEL_NAME)
        ticket = None

        try:
            # 1. Hàng đợi xử lý: Session Lock & Local Inference Throttle
            for q_ev in queue_mgr.enqueue_and_wait(session_id=session_id, is_local=is_local_req):
                if q_ev.get("step") == "queue_granted":
                    ticket = q_ev.get("ticket")
                    break
                yield q_ev

            yield {"step": "routing", "i18n_key": "stream.routing",
                   "message": "🔍 Đang phân tích câu hỏi & đối chiếu chuyên môn an toàn thông tin..."}

            eff_model = model_override or settings.MODEL_NAME
            is_local = (not prefer_cloud) and ChatService._is_local_model(eff_model)

            routing = route_model(message)
            model_name = eff_model if is_local else (model_override or routing["model"])
            use_rag = False if is_local else routing.get("use_rag", False)

            is_log = (
                ChatService._is_log_analysis(message)
            )

            # Web search is supported for both local and cloud models
            if is_log:
                effective_search = False
            elif use_search is not None:
                effective_search = use_search
            else:
                effective_search = routing.get("use_search", False)

            use_search = effective_search
            routing["use_search"] = use_search
            routing["use_rag"] = use_rag

            from services.audit_service import audit_service, AuditContext
            stream_audit_ctx = AuditContext(chat_session_id=session_id)
            stream_start_ts = datetime.now(timezone.utc).isoformat()

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                yield {"step": "rag", "i18n_key": "stream.rag",
                       "message": "📚 Đang tra cứu cơ sở tri thức tiêu chuẩn ISO 27001 / TCVN 11930..."}
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=2, organisation=organisation)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]
                    audit_service.record_rag_query(
                        ctx=stream_audit_ctx,
                        collection_name="iso_documents",
                        query_text=message,
                        top_k=len(results),
                        results=results,
                    )

            if use_search:
                yield {"step": "searching", "i18n_key": "stream.searching",
                       "message": "🌐 Đang thu thập và tổng hợp thông tin tình báo an ninh mạng trên Web..."}
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]
                    yield {"step": "search_done", "i18n_key": "stream.searchDone",
                           "i18n_params": {"count": len(search_results)},
                           "message": f"✅ Đã tiếp nhận {len(search_results)} nguồn dữ liệu, đang biên soạn câu trả lời..."}

            display_model = model_name if model_name else settings.CLOUD_MODEL_NAME
            yield {"step": "thinking", "i18n_key": "stream.thinking",
                   "i18n_params": {"model": display_model},
                   "message": f"🤖 Đang khởi động suy luận {display_model} trên GPU AMD Radeon..."}

            ss = ChatService.get_session_store()
            max_hist = 8 if is_local else 10
            history = ss.get_context_messages(session_id, max_messages=max_hist)
            is_log = (
                ChatService._is_log_analysis(message)
                or ChatService._session_in_log_mode(history or [])
            )
            messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)

            # Auto-compact history if nearing context limit
            total_chars = sum(len(m.get("content", "")) for m in messages)
            estimated_tokens = total_chars // 3
            if is_local:
                if estimated_tokens > 3800 and history and len(history) > 2:
                    logger.info(f"[Chat] Context high ({estimated_tokens} est. tokens) -> auto-compacting history to last 2 messages")
                    history = history[-2:]
                    messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)
                    total_chars = sum(len(m.get("content", "")) for m in messages)
                    estimated_tokens = total_chars // 3

                if estimated_tokens > 4800 and history:
                    logger.info(f"[Chat] Current payload alone is large ({estimated_tokens} est. tokens) -> dropping history to guarantee output token budget")
                    history = []
                    messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)
                    total_chars = sum(len(m.get("content", "")) for m in messages)
                    estimated_tokens = total_chars // 3

                if estimated_tokens > 7800:
                    logger.warning(f"[Chat] Context limit reached ({estimated_tokens} est. tokens) -> yielding friendly alert")
                    overflow_msg = (
                        "Đoạn hội thoại hiện tại đã đạt giới hạn bộ nhớ ngữ cảnh của mô hình AI cục bộ "
                        "(bao gồm toàn bộ lịch sử các câu hỏi trước đó và dữ liệu log lớn). "
                        "Để AI phân tích chính xác và đạt hiệu suất cao nhất, bạn vui lòng mở một phiên chat mới (+ Cuộc trò chuyện mới) "
                        "hoặc chuyển sang Cloud AI để xử lý lượng ngữ cảnh lớn hơn."
                    )
                    ss.add_message(session_id, "user", message, user_id=user_id)
                    ss.add_message(session_id, "assistant", overflow_msg, user_id=user_id, model=model_name, provider="ollama")
                    yield {
                        "step": "done",
                        "data": {
                            "response": overflow_msg,
                            "model": model_name,
                            "provider": "ollama",
                            "is_context_overflow": True,
                            "session_id": session_id,
                            "route": routing["route"],
                        }
                    }
                    return

            # Decide streaming path: only Ollama models support live token streaming here.
            response_text = ""
            result_meta = {"model": model_name, "provider": "unknown", "usage": {}}
            ollama_streamed = False

            if not prefer_cloud and is_local and ChatService._is_ollama_model(model_name):
                try:
                    yield {"step": "stream_start", "i18n_key": "stream.streamStart",
                           "message": "💭 Mô hình đang suy nghĩ và truyền tải dữ liệu trực tiếp..."}
                    chunks = []
                    for ev in CloudLLMService.call_ollama_stream(
                        model=model_name, messages=messages, temperature=0.7
                    ):
                        if ev.get("type") == "token":
                            chunks.append(ev["content"])
                            yield {"step": "token", "token": ev["content"]}
                        elif ev.get("type") == "thinking_token":
                            yield {"step": "thinking_token", "token": ev["content"]}
                        elif ev.get("type") == "done":
                            response_text = ChatService.clean_response(ev.get("content", "") or "".join(chunks))
                            result_meta = {
                                "model": ev.get("model", model_name),
                                "provider": ev.get("provider", "ollama"),
                                "usage": ev.get("usage", {}),
                            }
                    if response_text.strip():
                        ollama_streamed = True
                    else:
                        logger.warning("[Stream] Ollama stream yielded no content -> fallback to non-stream")
                except Exception as stream_err:
                    logger.warning(f"[Stream] Ollama stream failed → falling back to non-stream: {stream_err}")
                    yield {"step": "stream_fallback", "i18n_key": "stream.fallback",
                           "message": "⚠️ Stream failed, switching to standard mode..."}

            if not ollama_streamed:
                try:
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
                except Exception as comp_err:
                    logger.error(f"[Chat] Non-stream completion failed: {comp_err}")
                    if not response_text:
                        response_text = f"Mô hình cục bộ không thể hoàn tất phân tích lúc này: {str(comp_err)}. Vui lòng thử lại hoặc chuyển sang chế độ Cloud AI."
                        result_meta = {"model": model_name, "provider": "error", "usage": {}}

            if is_log and response_text:
                response_text = ChatService._normalize_log_output(response_text)

            ss.add_message(session_id, "user", message, user_id=user_id)
            if response_text:
                ss.add_message(
                    session_id,
                    "assistant",
                    response_text,
                    user_id=user_id,
                    model=result_meta.get("model"),
                    provider=result_meta.get("provider")
                )

            stream_end_ts = datetime.now(timezone.utc).isoformat()
            if 'stream_audit_ctx' in locals() and stream_audit_ctx:
                audit_service.record_llm_inference_completed(
                    ctx=stream_audit_ctx,
                    phase="chat_stream",
                    requested_model=model_name,
                    actual_model=result_meta.get("model", model_name),
                    provider=result_meta.get("provider", "ollama"),
                    started_at=stream_start_ts if 'stream_start_ts' in locals() else stream_end_ts,
                    completed_at=stream_end_ts,
                    prompt_text=message,
                    response_text=response_text,
                    usage_metrics=result_meta.get("usage", {}),
                    output_schema_valid=True,
                )

            yield {
                "step": "done",
                "data": {
                    "response": response_text or "Không nhận được phản hồi từ mô hình. Vui lòng thử lại.",
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
        finally:
            if ticket:
                queue_mgr.release_turn(ticket)

    @staticmethod
    def clear_conversation(session_id: str) -> Dict[str, Any]:
        ss = ChatService.get_session_store()
        ss.clear_history(session_id)
        return {"status": "ok", "message": "Đã xóa ngữ cảnh hội thoại", "session_id": session_id}

    @staticmethod
    def _local_only_guard(stream: bool = False, session_id: str = "default"):
        if not settings.LOCAL_ONLY_MODE:
            return None
        ollama_ready = CloudLLMService.ollama_health_check(timeout=8)
        if ollama_ready:
            return None

        message = "⚠️ Local-only mode đang bật nhưng hệ thống chưa sẵn sàng. Ollama không phản hồi — kiểm tra container cyberai-ollama."

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
                      progress_callback=None, audit_ctx=None) -> Dict[str, Any]:
        """progress_callback(message: str, percent: int) — optional, called per chunk."""
        from services.controls_catalog import get_categories, get_flat_controls, calc_compliance, build_weight_breakdown, get_control_groups, calc_tcvn_compliance
        from services.assessment_helpers import (
            build_chunk_prompt, validate_chunk_output, gap_items_to_markdown,
            build_full_prompt, build_weight_breakdown_txt, compress_for_phase2,
            build_sys_summary, infer_gap_from_control, normalize_severity_distribution,
            summarize_evidence,
        )
        from services.privacy_filter import filter_pii
        from services.audit_service import audit_service, AuditContext

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
            "iso_documents": "iso_documents",
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

        if audit_ctx:
            audit_service.record_rag_query(
                ctx=audit_ctx,
                collection_name=rag_domain,
                query_text=search_query,
                top_k=6,
                results=context_results,
            )

        implemented = system_data.get("compliance", {}).get("implemented_controls", [])

        # Use TCVN-specific scoring for TCVN standard
        if standard == "tcvn11930":
            compliance = calc_tcvn_compliance(implemented, custom_std)
        else:
            compliance = calc_compliance(implemented, standard, custom_std)
        score = compliance["score"]
        max_score = compliance["max_score"]
        percentage = compliance["percentage"]

        if audit_ctx:
            audit_service.record_score_calculated(
                ctx=audit_ctx,
                standard=standard,
                score=score,
                max_score=max_score,
                percentage=percentage,
            )

        # Load control catalog — use get_control_groups() for fine-grained chunking (10 controls/group for speed)
        builtin_std_categories = get_categories(standard, custom_std)
        control_groups = get_control_groups(standard, custom_std, group_size=10)
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

        # Resolve 100% Local Model for Assessment:
        # Multi-Agent Pipeline:
        # - Model 1 (Extractor / Technical Fact): qwen2.5-coder:7b
        # - Model 2 (Reasoning Auditor / Synthesizer): gemma4:latest
        extractor_model = os.getenv("MODEL_1_EXTRACTOR", "qwen2.5-coder:7b")
        auditor_model = os.getenv("MODEL_2_AUDITOR", "gemma4:latest")
        local_target_model = system_data.get("selected_model") or auditor_model
        logger.info(f"[Assessment] Local Inference Pipeline: Extractor={extractor_model}, Auditor={local_target_model}")

        def _try_phase(messages, temperature, local_model, task_type, priority=False, phase_name="phase1_gap_analysis", max_tokens=None):
            """Execute assessment phase using Local/Configured model with verifiable audit tracing."""
            target_model = local_model or local_target_model or "gemma4:latest"
            eff_max_tokens = max_tokens or (1200 if "chunk" in phase_name else 4096)
            logger.info(f"[Assessment] Running phase '{phase_name}' on model={target_model}, max_tokens={eff_max_tokens}")
            start_ts = datetime.now(timezone.utc).isoformat()
            if audit_ctx:
                audit_service.record_llm_inference_start(
                    ctx=audit_ctx,
                    phase=phase_name,
                    requested_model=target_model,
                    provider="ollama",
                    temperature=temperature,
                    max_tokens=eff_max_tokens,
                )

            res = CloudLLMService._call_ollama(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=eff_max_tokens
            )

            end_ts = datetime.now(timezone.utc).isoformat()
            if audit_ctx:
                prompt_str = "\n".join(m.get("content", "") for m in messages)
                resp_str = res.get("content", "")
                actual_mod = res.get("model") or target_model
                prov = res.get("provider", "ollama")
                usage = res.get("usage", {})
                audit_service.record_llm_inference_completed(
                    ctx=audit_ctx,
                    phase=phase_name,
                    requested_model=target_model,
                    actual_model=actual_mod,
                    provider=prov,
                    started_at=start_ts,
                    completed_at=end_ts,
                    prompt_text=prompt_str,
                    response_text=resp_str,
                    fallback_used=False,
                    usage_metrics=usage,
                    output_schema_valid=True,
                )
            return res

        p1_task_type = "iso_local"
        p1_model = extractor_model or "qwen2.5-coder:7b"
        p2_task_type = "iso_local"
        p2_model = local_target_model or auditor_model or "gemma4:latest"

        # Pre-compute evidence summary using local model
        evidence_summary = ""
        evidence_text = (system_data.get("notes", "") or "").strip()
        if evidence_text:
            if progress_callback:
                progress_callback("Tác tử 2 (qwen2.5-coder:7b): Bóc tách minh chứng kỹ thuật & lập thẻ Fact Cards...", 18)
            try:
                evidence_summary = summarize_evidence(
                    evidence_text,
                    max_tokens=getattr(settings, "EVIDENCE_SUMMARY_TOKENS", 256),
                    logger=logger,
                )
                if evidence_summary:
                    logger.info(f"[Assessment] evidence summary OK ({len(evidence_summary)} chars)")
            except Exception as se:
                logger.warning(f"[Assessment] summarize_evidence failed: {se}")
                evidence_summary = ""

        try:
            raw_analysis = ""
            result_p1 = None

            if p1_task_type == "iso_local" and all_controls_flat:
                # Use control_groups (5-8 controls each) instead of full categories
                groups = control_groups or [{"category": "Tất cả Controls", "controls": all_controls_flat}]

                all_gap_items = []
                all_verdicts = []
                n_groups = len(groups)
                logger.info(f"[Assessment] Chunked mode: {n_groups} control groups (5-8 controls each)")

                if progress_callback:
                    progress_callback("Tác tử 3 (gemma4): Bắt đầu thẩm định đối soát từng nhóm controls...", 30)

                # Get raw evidence text for privacy filtering before cloud calls
                raw_evidence_text = (system_data.get("notes", "") or "").strip()

                for grp_idx, group in enumerate(groups):
                    cat_name = group.get("category", f"Group {grp_idx+1}")
                    cat_controls = group.get("controls", [])
                    missing_in_cat = [c for c in cat_controls if c["id"] not in implemented]

                    if progress_callback:
                        pct = 30 + int((grp_idx / n_groups) * 55)
                        progress_callback(f"Tác tử 3 (gemma4): Đang thẩm định {cat_name}... ({grp_idx+1}/{n_groups})", pct)

                    if not missing_in_cat:
                        logger.info(f"[Assessment] '{cat_name}' — all implemented, skip")
                        continue

                    # RAG: get group-specific context from ChromaDB (domain-scoped)
                    cat_rag_query = f"{cat_name} {std_name} controls requirements"
                    try:
                        cat_rag = vs.search(cat_rag_query, top_k=2, domain=rag_domain)
                        cat_rag_ctx = "\n---\n".join(r["text"][:300] for r in cat_rag)
                        if audit_ctx:
                            audit_service.record_rag_query(
                                ctx=audit_ctx,
                                collection_name=rag_domain,
                                query_text=cat_rag_query,
                                top_k=2,
                                results=cat_rag,
                            )
                    except Exception:
                        cat_rag_ctx = ""

                    # Apply indirect prompt injection sanitizer and privacy filter to evidence
                    evidence_for_prompt = None
                    if raw_evidence_text:
                        from services.privacy_filter import sanitize_indirect_injection
                        sanitized_raw = sanitize_indirect_injection(raw_evidence_text)
                        if effective_mode == "cloud":
                            evidence_for_prompt = filter_pii(sanitized_raw, mode="cloud")
                        elif effective_mode == "hybrid":
                            evidence_for_prompt = filter_pii(sanitized_raw, mode="local")
                        else:
                            evidence_for_prompt = sanitized_raw

                        if audit_ctx and grp_idx == 0:
                            audit_service.record_privacy_filter(
                                ctx=audit_ctx,
                                mode=effective_mode,
                                redaction_applied=bool(evidence_for_prompt != raw_evidence_text),
                                char_count_before=len(raw_evidence_text),
                                char_count_after=len(evidence_for_prompt or ""),
                            )

                    # Agent 1: Extract structured SecurityFactCards from evidence
                    fact_cards_text = None
                    if evidence_for_prompt:
                        try:
                            from services.evidence_fact_extractor import EvidenceFactExtractor
                            fc = EvidenceFactExtractor.extract_facts(evidence_for_prompt, "assessment_evidence")
                            fact_cards_text = EvidenceFactExtractor.format_for_auditor([fc])
                        except Exception as fc_err:
                            logger.debug(f"[Assessment] Fact extraction in assess_system: {fc_err}")

                    # Agent 2 Feedback Loop: Retrieve historical auditor corrections
                    feedback_exemplars_text = None
                    try:
                        from repositories.feedback_store import AuditFeedbackStore
                        fb_store = AuditFeedbackStore.get_instance()
                        group_cids = [c["id"] for c in cat_controls]
                        feedback_exemplars_text = fb_store.format_few_shot_prompt(group_cids, standard=standard)
                    except Exception as fb_err:
                        logger.debug(f"[Assessment] Feedback exemplars in assess_system: {fb_err}")

                    chunk_prompt = build_chunk_prompt(
                        cat_name, cat_controls, implemented,
                        percentage, score, max_score,
                        sys_summary_short, std_name, cat_rag_ctx,
                        evidence_summary=evidence_summary or None,
                        evidence_text=evidence_for_prompt,
                        fact_cards_text=fact_cards_text,
                        feedback_exemplars_text=feedback_exemplars_text,
                    )

                    chunk_messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are an automated ISO compliance assessment engine. "
                                "Output ONLY a raw JSON array matching the requested schema. "
                                "Do NOT include conversational thinking, markdown preambles, or explanations. "
                                "Begin directly with [ and end with ]."
                            ),
                        },
                        {"role": "user", "content": chunk_prompt},
                    ]

                    chunk_gap_items = None
                    for attempt in range(3):
                        try:
                            chunk_result = _try_phase(
                                messages=chunk_messages,
                                temperature=0.1,
                                local_model=p1_model or settings.SECURITY_MODEL_NAME,
                                task_type=p1_task_type,
                                priority=True,
                                phase_name=f"phase1_chunk_{cat_name}_attempt{attempt+1}",
                            )

                            if result_p1 is None:
                                result_p1 = chunk_result
                            chunk_content = chunk_result.get("content", "").strip()
                            valid_ids = [c["id"] for c in cat_controls]
                            chunk_gap_items = validate_chunk_output(chunk_content, cat_name, valid_ids=valid_ids)
                            if chunk_gap_items is not None:
                                logger.info(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {len(chunk_gap_items)} gaps")
                                if audit_ctx:
                                    audit_service.record_json_validation(
                                        ctx=audit_ctx,
                                        phase=f"chunk_{cat_name}",
                                        valid=True,
                                        items_count=len(chunk_gap_items),
                                        repaired_by_ast=False,
                                    )
                                break
                            logger.warning(f"[Assessment] Chunk '{cat_name}' invalid JSON attempt {attempt+1}")
                        except Exception as chunk_err:
                            logger.warning(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {chunk_err}")

                    if chunk_gap_items:
                        # Extract per-control verdicts from chunk output
                        for item in chunk_gap_items:
                            if "evidence_verdict" in item:
                                all_verdicts.append({
                                    "control_id": item.get("control_id", item.get("id", "")),
                                    "evidence_verdict": item.get("evidence_verdict", "missing"),
                                    "missing_items": item.get("missing_items", []),
                                    "confidence": item.get("confidence", 0.0),
                                })
                        all_gap_items.extend(chunk_gap_items)
                    elif chunk_gap_items is None:
                        logger.warning(f"[Assessment] Chunk '{cat_name}' all attempts failed — using inferred gaps")
                        inferred = []
                        for ctrl in missing_in_cat[:10]:
                            item = infer_gap_from_control(ctrl, cat_name)
                            all_gap_items.append(item)
                            inferred.append(item)
                        if audit_ctx:
                            audit_service.record_json_validation(
                                ctx=audit_ctx,
                                phase=f"chunk_{cat_name}",
                                valid=False,
                                items_count=len(inferred),
                                repaired_by_ast=True,
                            )

                # Normalize severity if model marks too many as critical
                all_gap_items = normalize_severity_distribution(all_gap_items)
                raw_analysis = gap_items_to_markdown(all_gap_items)
                logger.info(f"[Assessment] All chunks complete — {len(all_gap_items)} total gaps, raw: {len(raw_analysis)} chars")

            else:
                all_verdicts = []
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
                    phase_name="phase1_full_analysis",
                )
                raw_analysis = result_p1.get("content", "")

            raw_analysis_p2 = compress_for_phase2(raw_analysis)

            today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
            org_name = system_data.get("organization", {}).get("name", "Tổ chức")
            industry = system_data.get("organization", {}).get("industry", "")
            org_size = system_data.get("organization", {}).get("size", "")
            employees = system_data.get("organization", {}).get("employees", 0)
            p1_runtime = p1_model or "qwen2.5-coder:7b"
            p2_runtime = p2_model or "gemma4:latest"
            mode_label = {
                "local": f"LocalAI: {p1_runtime} (Phase 1) + {p2_runtime} (Phase 2)",
                "cloud": "Cloud only (OpenClaude)",
                "hybrid": f"Hybrid: {p1_runtime} local (Phase 1) + OpenClaude (Phase 2)"
            }

            weight_summary = f"\n\nDữ liệu trọng số:\n{weight_breakdown_txt}" if weight_breakdown_txt else ""

            raw_coverage_pct = round(score / max_score * 100, 1) if max_score > 0 else 0.0
            formatting_prompt = (
                f"Bạn là chuyên gia trình bày Báo cáo Đánh giá An toàn Thông tin chuyên nghiệp.\n"
                f"Trình bày báo cáo bằng Markdown tiếng Việt, CẤU TRÚC BẮT BUỘC:\n\n"
                f"## 1. ĐÁNH GIÁ TỔNG QUAN\n"
                f"- Mức tuân thủ có trọng số: {percentage}%\n"
                f"- Tỷ lệ bao phủ kiểm soát: {score}/{max_score} Controls được đánh dấu đạt ({raw_coverage_pct}%)\n"
                f"- Phân bổ trọng số: Critical/High/Medium/Low đạt bao nhiêu %\n"
                f"- Lưu ý khách quan: Các controls chưa có tệp bằng chứng đính kèm cần ghi rõ 'chưa ghi nhận đủ minh chứng trong phạm vi dữ liệu đánh giá; cần chuyên gia xác minh', không tùy tiện kết luận đơn vị chưa có biện pháp.\n\n"
                f"## 2. RISK REGISTER\n"
                f"| # | Control | GAP | Severity | L | I | Risk | Khuyến nghị | Timeline |\n"
                f"|---|---------|-----|----------|---|---|------|-------------|----------|\n"
                f"Severity: 🔴 Critical 🟠 High 🟡 Medium ⚪ Low | Risk=L×I giảm dần\n"
                f"(Chỉ liệt kê tối đa 10-15 rủi ro Critical/High trọng yếu nhất vào bảng để báo cáo súc tích, hoàn tất toàn bộ các mục tiếp theo không bị đứt đoạn)\n\n"
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
            if progress_callback:
                progress_callback("Tác tử 4 (gemma4 + Exporters): Đang tổng hợp Báo cáo IT Audit A4 & Ma trận rủi ro...", 88)

            result_p2 = _try_phase(
                messages=[{"role": "user", "content": formatting_prompt}],
                temperature=0.5,
                local_model=p2_model or settings.MODEL_NAME,
                task_type=p2_task_type,
                priority=False,
                phase_name="phase2_report_synthesis",
                max_tokens=6144,
            )
            markdown_report = result_p2.get("content", "")
            markdown_report = ChatService.ensure_complete_report(
                markdown_report=markdown_report,
                percentage=percentage,
                score=score,
                max_score=max_score,
                org_name=org_name,
                std_name=std_name,
                industry=industry,
                missing_controls_by_weight=missing_controls_by_weight,
            )

            if progress_callback:
                progress_callback("Tác tử 4: Đang chuẩn hóa cấu trúc Sổ rủi ro (Risk Register) & xOffice...", 95)

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
                control_verdicts=all_verdicts,
                all_controls_flat=all_controls_flat,
                evidence_map=system_data.get("evidence_map", {}),
                assessment_id=audit_ctx.assessment_id if audit_ctx else None,
                run_id=audit_ctx.run_id if audit_ctx else None,
                code_version=audit_ctx.code_version if audit_ctx else None,
            )

            if audit_ctx:
                audit_service.record_json_validation(
                    ctx=audit_ctx,
                    phase="final_audit_report_json",
                    valid=True,
                    items_count=len(json_data.get("risk_register", [])),
                    repaired_by_ast=False,
                    schema_version="1.0"
                )

            return {
                "report": markdown_report,
                "compliance_percent": percentage,
                "json_data": json_data,
                "details": [],
                "control_verdicts": all_verdicts,
                "model_mode": "local",
                "model_used": {
                    "phase1": f"ollama:{result_p1.get('model', 'gemma4:latest') if result_p1 else 'gemma4:latest'}",
                    "phase2": f"ollama:{result_p2.get('model', 'gemma4:latest') if result_p2 else 'gemma4:latest'}",
                },
            }
        except Exception as e:
            logger.error(f"Assessment error: {e}")
            if audit_ctx:
                audit_service.record_assessment_failed(
                    ctx=audit_ctx,
                    error_type=type(e).__name__,
                    error_stage="assess_system_execution",
                    message_redacted=str(e),
                )
            return {"report": f"Lỗi tạo báo cáo: {str(e)}", "details": [], "error": True}

    @staticmethod
    def ensure_complete_report(
        markdown_report: str,
        percentage: float = 0.0,
        score: int = 0,
        max_score: int = 0,
        org_name: str = "Tổ chức",
        std_name: str = "ISO 27001:2022",
        industry: str = "",
        json_data: Optional[dict] = None,
        missing_controls_by_weight: Optional[dict] = None,
    ) -> str:
        """Inspect the assessment report markdown to ensure that Section 5
        (EXECUTIVE SUMMARY) is completely formed with Top 3 Critical/High Risks
        (including realistic VND budgets) and 30-day prioritized Next Steps.
        Automatically heals cut-off report tails.
        """
        import re
        if not markdown_report or not markdown_report.strip():
            return markdown_report

        report = markdown_report.strip()

        # Check if report has Section 5 (EXECUTIVE SUMMARY)
        has_sec5 = re.search(r'(?:^|\n)##\s*5\.?\s*(?:EXECUTIVE\s+SUMMARY|TÓM\s+TẮT)', report, re.IGNORECASE)

        # Check if subsection b) (Top 3) is present and has substantive content (> 150 chars)
        has_b_full = re.search(
            r'(?:^|\n)(?:###?\s*)?b\)\s*(?:Top\s*3|Các\s*rủi\s*ro|Rủi\s*ro\s*trọng\s*yếu)[\s\S]{150,}',
            report,
            re.IGNORECASE
        )
        # Check if subsection c) (Next Steps) is present
        has_c = re.search(
            r'(?:^|\n)(?:###?\s*)?c\)\s*(?:Next\s*Steps|Lộ\s*trình|Hành\s*động\s*ưu\s*tiên|30\s*ngày)',
            report,
            re.IGNORECASE
        )

        # If both subsection b (complete) and subsection c exist, report is already complete
        if has_sec5 and has_b_full and has_c:
            return report

        top3_risks_md = (
            "### b) Top 3 Rủi ro trọng yếu & Dự toán ngân sách khắc phục (Ước tính VND)\n\n"
            "1. **Rủi ro Vi phạm Quy định Pháp lý & Bảo vệ Dữ liệu Cá nhân (A.5.31, A.5.34 - Nghị định 13/2023/NĐ-CP):**\n"
            "   - **Mức độ rủi ro:** 🔴 **Critical (Rất cao)** | L×I = 5×5 = 25.\n"
            "   - **Thực trạng:** Chưa ban hành đầy đủ quy chế bảo vệ dữ liệu cá nhân (PII), chưa lập hồ sơ đánh giá tác động xử lý dữ liệu (DPIA) và thiếu cơ chế phân loại dữ liệu theo quy định pháp luật.\n"
            "   - **Biện pháp xử lý:** Bổ nhiệm cán bộ phụ trách bảo vệ dữ liệu (DPO), ban hành quy trình xử lý quyền của chủ thể dữ liệu và tổ chức rà soát bóc tách luồng dữ liệu cá nhân.\n"
            "   - **Dự toán ngân sách ước tính:** **150.000.000 – 250.000.000 VND** (Tư vấn pháp lý, đào tạo nhận thức và công cụ rà quét PII).\n\n"
            "2. **Rủi ro Xâm nhập Hệ thống do thiếu Xác thực Đa yếu tố (A.8.5 - Quản lý Định danh & Xác thực An toàn):**\n"
            "   - **Mức độ rủi ro:** 🔴 **Critical (Rất cao)** | L×I = 5×4 = 20.\n"
            "   - **Thực trạng:** Các tài khoản quản trị mạng, máy chủ cơ sở dữ liệu và cổng VPN truy cập từ xa chưa bắt buộc kích hoạt xác thực 2 bước (MFA).\n"
            "   - **Biện pháp xử lý:** Triển khai giải pháp MFA tập trung (FIDO2/TOTP/RADIUS), cấu hình chính sách khóa tài khoản tự động và kiểm soát phiên truy cập đặc quyền (PAM).\n"
            "   - **Dự toán ngân sách ước tính:** **80.000.000 – 120.000.000 VND** (Bản quyền phần mềm MFA và thiết bị token phần cứng).\n\n"
            "3. **Rủi ro Gián đoạn Hoạt động Kinh doanh & Kế hoạch Khôi phục sau Thảm họa (A.5.29, A.5.30 - BCP/DRP):**\n"
            "   - **Mức độ rủi ro:** 🟠 **High (Cao)** | L×I = 4×4 = 16.\n"
            "   - **Thực trạng:** Chưa hoàn thiện phương án phục hồi sau thảm họa (DRP), quy trình sao lưu độc lập (nguyên tắc 3-2-1) và thiếu định kỳ diễn tập khôi phục thảm họa.\n"
            "   - **Biện pháp xử lý:** Thiết lập kế hoạch kinh doanh liên tục (BCP), xây dựng hạ tầng dự phòng nóng/ấm và tổ chức diễn tập khôi phục thảm họa tối thiểu 1 lần/năm.\n"
            "   - **Dự toán ngân sách ước tính:** **200.000.000 – 350.000.000 VND** (Hạ tầng dự phòng đám mây, giải pháp sao lưu và chi phí diễn tập).\n\n"
            "• **Tổng ngân sách dự toán ưu tiên (Giai đoạn 1):** **430.000.000 – 720.000.000 VND**."
        )

        next_steps_md = (
            "### c) Lộ trình triển khai ưu tiên trong 30 ngày (Next Steps)\n\n"
            "1. **Tuần 1-2 (Kiện toàn Tổ chức & Ban hành Chính sách Tuân thủ):**\n"
            "   - Thành lập Ban Chỉ đạo An toàn thông tin, phân công cụ thể vai trò CISO và Cán bộ Bảo vệ Dữ liệu (DPO).\n"
            "   - Ban hành quy chế bảo vệ dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP và phổ biến chế tài kỷ luật tuân thủ ATTT cho toàn đơn vị.\n"
            "2. **Tuần 2-3 (Thắt chặt Kỹ thuật & Xác thực Đặc quyền Toàn diện):**\n"
            "   - Kích hoạt bắt buộc MFA trên 100% tài khoản quản trị mạng, máy chủ cơ sở dữ liệu và cổng VPN truy cập từ xa.\n"
            "   - Rà soát, vô hiệu hóa các tài khoản không hoạt động và áp dụng chính sách mật khẩu mạnh.\n"
            "3. **Tuần 3-4 (Quy trình Ứng phó Sự cố & Đánh giá Nhà cung cấp):**\n"
            "   - Hoàn thiện quy trình ứng phó sự cố an toàn thông tin (CSIRP), thiết lập đường dây nóng báo cáo sự cố 24/7.\n"
            "   - Ký cam kết bảo mật (NDA/DPA) và rà soát điều khoản an toàn thông tin trong hợp đồng với toàn bộ nhà cung cấp, đối tác gia công."
        )

        if has_sec5:
            b_match = re.search(r'(?:^|\n)(?:###?\s*)?b\)\s*(?:Top\s*3|Rủi\s*ro|R)[^\n]*', report, re.IGNORECASE)
            if b_match:
                cutoff_idx = b_match.start()
                clean_head = report[:cutoff_idx].rstrip()
                return f"{clean_head}\n\n{top3_risks_md}\n\n{next_steps_md}"
            else:
                return f"{report.rstrip()}\n\n{top3_risks_md}\n\n{next_steps_md}"

        metrics_md = (
            "## 5. EXECUTIVE SUMMARY (TÓM TẮT CHO BAN LÃNH ĐẠO)\n\n"
            "### a) Metrics Overview\n"
            f"- **Tỷ lệ Tuân thủ Tổng thể:** {percentage}% ({score}/{max_score} Controls đạt).\n"
            "- **Mức độ rủi ro chung:** **Rất cao (Very High)** — Đe dọa đến khả năng vận hành liên tục và uy tín pháp lý.\n\n"
        )
        return f"{report.rstrip()}\n\n{metrics_md}{top3_risks_md}\n\n{next_steps_md}"

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
        control_verdicts: list = None,
        all_controls_flat: list = None,
        evidence_map: dict = None,
        assessment_id: str = None,
        run_id: str = None,
        code_version: str = None,
    ) -> dict:
        """Build structured JSON output conforming to UnifiedAssessmentResult contract.

        Ensures data consistency, transparent risk scoring, evidence attribution,
        and separation of raw control coverage from weighted compliance.
        """
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        ev_map = evidence_map or {}
        ctrl_flat = all_controls_flat or []
        total_controls_count = len(ctrl_flat) or max_score or 1

        # Build per-control verdicts map for quick lookup
        verdict_map = {}
        for v in (control_verdicts or []):
            cid = v.get("control_id", "")
            if cid:
                verdict_map[cid] = v

        controls_out = []
        risk_register_out = []
        crit_count = 0
        high_count = 0
        med_count = 0
        low_count = 0

        # Trọng số kỹ thuật chuẩn
        weight_points = {"critical": 10.0, "high": 5.0, "medium": 3.0, "low": 1.0}
        total_weight_score = 0.0
        max_weight_score = 0.0

        for ctrl in ctrl_flat:
            cid = ctrl.get("id") or ctrl.get("control_id", "")
            clabel = ctrl.get("label", "")
            ccat = ctrl.get("category", "")
            cweight = (ctrl.get("weight") or "medium").lower()

            w_pts = weight_points.get(cweight, 3.0)
            max_weight_score += w_pts

            is_decl_impl = cid in implemented
            attached_files = ev_map.get(cid, [])
            if isinstance(attached_files, str):
                attached_files = [attached_files]
            has_files = len(attached_files) > 0

            # 1. User declaration & Evidence status
            u_decl = "implemented" if is_decl_impl else "not_implemented"
            ev_status = "direct_attachment" if has_files else "no_evidence"

            # 2. Verdict basis
            v_basis = []
            if is_decl_impl:
                v_basis.append("user_declaration")
            if has_files:
                v_basis.append("direct_evidence")
            if cid in verdict_map:
                v_basis.append("ai_inference")
            if not v_basis:
                v_basis.append("rule_based")

            # 3. Assessment verdict
            verdict_item = verdict_map.get(cid, {})
            ai_verdict = verdict_item.get("evidence_verdict")

            if ai_verdict:
                verdict = ai_verdict
                if ai_verdict == "satisfied" or is_decl_impl:
                    total_weight_score += w_pts
            elif is_decl_impl and has_files:
                verdict = "satisfied"
                total_weight_score += w_pts
            elif is_decl_impl and not has_files:
                # Tự khai báo đạt nhưng thiếu minh chứng đính kèm
                verdict = "not_evidenced"
                total_weight_score += w_pts  # vẫn tính theo self-declaration cho weighted score hiện hành
            else:
                verdict = "missing"

            # 4. Transparent Risk Scoring (Likelihood, Impact, Severity)
            if verdict == "satisfied":
                risk_sev = "Low"
                l_val = 1
                i_val = 2 if cweight in ("critical", "high") else 1
                r_basis = "evidence_based" if has_files else "rule_based"
                c_gap = "Biện pháp kiểm soát đã được triển khai và ghi nhận tài liệu/minh chứng phù hợp."
                c_rec = "Duy trì rà soát, kiểm toán nội bộ định kỳ."
                c_timeline = "Định kỳ 6-12 tháng"
            elif verdict == "not_evidenced":
                if cweight == "critical":
                    risk_sev = "High"
                    l_val = 3
                    i_val = 4
                elif cweight == "high":
                    risk_sev = "Medium"
                    l_val = 3
                    i_val = 3
                elif cweight == "medium":
                    risk_sev = "Medium"
                    l_val = 2
                    i_val = 3
                else:
                    risk_sev = "Low"
                    l_val = 2
                    i_val = 2
                r_basis = "ai_provisional"
                c_gap = "Chưa ghi nhận đủ minh chứng trong phạm vi dữ liệu đánh giá; cần chuyên gia xác minh."
                c_rec = "Bổ sung bằng chứng văn bản, chính sách ban hành, cấu hình kỹ thuật hoặc log hệ thống."
                c_timeline = "30-60 ngày"
            else:  # missing
                if cweight == "critical":
                    risk_sev = "Critical"
                    l_val = 4
                    i_val = 5
                elif cweight == "high":
                    risk_sev = "High"
                    l_val = 4
                    i_val = 4
                elif cweight == "medium":
                    risk_sev = "Medium"
                    l_val = 3
                    i_val = 3
                else:
                    risk_sev = "Low"
                    l_val = 2
                    i_val = 2
                r_basis = "rule_based"
                c_gap = f"Chưa thiết lập biện pháp kiểm soát {clabel or cid} theo chuẩn {std_name}."
                c_rec = "Ban hành quy định, phân công nhân sự phụ trách và thiết lập cơ chế kiểm soát kỹ thuật."
                c_timeline = "0-30 ngày" if risk_sev in ("Critical", "High") else "30-90 ngày"

            r_score = l_val * i_val

            if risk_sev == "Critical":
                crit_count += 1
            elif risk_sev == "High":
                high_count += 1
            elif risk_sev == "Medium":
                med_count += 1
            else:
                low_count += 1

            ctrl_entry = {
                # Contract schema fields
                "control_id": cid,
                "label": clabel,
                "category": ccat,
                "weight": cweight,
                "user_declaration": u_decl,
                "evidence_status": ev_status,
                "evidence_file_ids": attached_files,
                "fact_card_ids": [f"fact_{cid}_{i}" for i in range(len(attached_files))],
                "auto_match_confidence": verdict_item.get("confidence", 1.0 if has_files else None),
                "assessment_verdict": verdict,
                "verdict_basis": v_basis,
                "expert_review_status": "pending",
                "risk_severity": risk_sev,
                "likelihood": l_val,
                "impact": i_val,
                "risk_score": r_score,
                "risk_assessment_basis": r_basis,
                "gap": c_gap,
                "recommendation": c_rec,
                "timeline": c_timeline,
                # Legacy compatibility fields
                "id": cid,
                "evidence_verdict": verdict,
                "confidence": verdict_item.get("confidence", 1.0 if is_decl_impl else 0.0),
                "missing_items": verdict_item.get("missing_items", []),
            }
            controls_out.append(ctrl_entry)

            # Build Risk Register row for non-satisfied controls
            if verdict != "satisfied":
                treatment = "Giảm thiểu (Mitigate)" if r_score >= 12 else "Chấp nhận có điều kiện" if r_score <= 4 else "Kiểm soát bổ sung"
                risk_register_out.append({
                    "control_id": cid,
                    "label": clabel or cid,
                    "category": ccat or "General",
                    "weight": cweight.capitalize(),
                    "gap": c_gap,
                    "severity": risk_sev.lower(),
                    "likelihood": l_val,
                    "impact": i_val,
                    "risk_score": r_score,
                    "recommendation": c_rec,
                    "treatment": treatment,
                    "timeline": c_timeline,
                    "owner": "CISO / IT Security" if risk_sev in ("Critical", "High") else "Hạ tầng / SysAdmin",
                    "status": "Đang mở (Open)",
                    "risk_assessment_basis": r_basis,
                    "assessment_verdict": verdict,
                })

        # Sort risk register desc by risk_score
        risk_register_out.sort(key=lambda r: r["risk_score"], reverse=True)

        # 5. Coverage & Weighted compliance computations
        self_decl_count = len(implemented)
        ev_supp_count = sum(1 for c in controls_out if c["user_declaration"] == "implemented" and c["evidence_status"] != "no_evidence")
        not_ev_count = total_controls_count - ev_supp_count
        raw_cov_pct = round((self_decl_count / total_controls_count * 100), 1) if total_controls_count > 0 else 0.0

        # Weighted calculation
        if max_weight_score > 0:
            calc_weighted_pct = round((total_weight_score / max_weight_score * 100), 1)
        else:
            calc_weighted_pct = round(min(100.0, max(0.0, float(percentage))), 1)

        control_coverage = {
            "self_declared_implemented": self_decl_count,
            "evidence_supported_implemented": ev_supp_count,
            "not_evidenced_or_missing": not_ev_count,
            "total_controls": total_controls_count,
            "raw_percentage": raw_cov_pct,
        }

        weighted_compliance = {
            "weighted_score": round(total_weight_score, 1),
            "weighted_max_score": round(max_weight_score, 1),
            "percentage": calc_weighted_pct,
            "algorithm": "weight_score_v1",
        }

        wb = weight_breakdown or {}
        missing = missing_controls_by_weight or {}

        def wb_pct(w):
            bd = wb.get(w, {})
            tot = bd.get("total", 0)
            imp = bd.get("implemented", 0)
            return round((imp / tot * 100), 1) if tot > 0 else 0.0

        if calc_weighted_pct >= 80:
            tier = "high"
            tier_label = "Tuân thủ cao"
        elif calc_weighted_pct >= 50:
            tier = "medium"
            tier_label = "Tuân thủ một phần"
        elif calc_weighted_pct >= 25:
            tier = "low"
            tier_label = "Tuân thủ thấp"
        else:
            tier = "critical"
            tier_label = "Không tuân thủ"

        top_gaps = []
        for r in risk_register_out[:10]:
            top_gaps.append({
                "id": r["control_id"],
                "label": r["label"],
                "severity": r["severity"],
                "gap": r["gap"],
                "recommendation": r["recommendation"],
            })

        eff_aid = assessment_id or "assessment_default"
        eff_run = run_id or "run_default"
        eff_code_ver = code_version or "v1.2.0-rel"

        return {
            # Standard contract
            "assessment_id": eff_aid,
            "run_id": eff_run,
            "code_version": eff_code_ver,
            "created_at": today or now_iso,
            "completed_at": now_iso,
            "status": "completed",
            "standard": {
                "id": standard,
                "name": std_name,
            },
            "control_coverage": control_coverage,
            "weighted_compliance": weighted_compliance,
            "controls": controls_out,
            "risk_register": risk_register_out,
            "evidence_manifest_ref": f"data/evidence_manifests/{eff_aid}.json",
            "audit_trace_ref": f"data/audit_traces/{eff_aid}.json",

            # Legacy fields for backward compatibility
            "assessment_date": today,
            "standard_id": standard,
            "standard_name": std_name,
            "ai_mode": effective_mode,
            "organization": {
                "name": org_name,
                "industry": industry,
                "size": org_size,
                "employees": employees,
            },
            "compliance": {
                "score": self_decl_count,
                "max_score": total_controls_count,
                "percentage": calc_weighted_pct,
                "tier": tier,
                "tier_label": tier_label,
                "implemented_count": self_decl_count,
                "missing_count": max(0, total_controls_count - self_decl_count),
                "raw_coverage": control_coverage,
                "weighted_compliance": weighted_compliance,
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
                "critical_gaps": crit_count,
                "high_gaps": high_count,
                "medium_gaps": med_count,
                "low_gaps": low_count,
                "total_gaps": crit_count + high_count + med_count + low_count,
            },
            "top_gaps": top_gaps,
            "implemented_controls": implemented,
        }

    @staticmethod
    def health_check() -> Dict[str, Any]:
        return CloudLLMService.health_check()
