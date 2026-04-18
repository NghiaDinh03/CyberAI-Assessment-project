"""Chat Service — Conversation routing with session memory and Cloud-first strategy."""

import asyncio
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

    @staticmethod
    def clean_response(text: str) -> str:
        return SPECIAL_TOKENS.sub('', text).strip()

    @staticmethod
    def _is_log_analysis(message: str) -> bool:
        """Detect if the user is requesting log/event analysis."""
        msg_lower = message.lower()
        # Check for log analysis keywords
        log_keywords = [
            "phân tích log", "analyze log", "event id", "eventid",
            "sự kiện", "windows event", "syslog", "security log",
            "audit log", "process creation", "logon", "logoff",
            "firewall log", "access log", "error log", "phân tích sự kiện",
        ]
        # Check for log-like patterns (Event ID, timestamps, field:value)
        import re
        log_patterns = [
            r"Event\s*ID[:\s]*\d+",
            r"Source[:\s]*(Microsoft|Security|System|Application)",
            r"Token\s*Elevation\s*Type",
            r"Process\s*(Name|ID|Command\s*Line)[:\s]",
            r"Logon\s*Type[:\s]*\d+",
            r"Subject[:\s]",
            r"Creator\s*Process",
            r"New\s*Process\s*Name",
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            r"Mandatory\s*Label",
            r"Account\s*Name[:\s]",
        ]
        if any(kw in msg_lower for kw in log_keywords):
            return True
        for pattern in log_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    # Structured output template for log/event analysis
    _LOG_ANALYSIS_PROMPT = (
        "Bạn là SOC Analyst Level 3 chuyên phân tích log/event an ninh.\n"
        "NHIỆM VỤ DUY NHẤT: phân tích log, trích xuất TẤT CẢ field quan trọng theo "
        "định dạng `**Field**: Value`, đưa ra nhận định True Positive / False Positive.\n\n"
        "## FORMAT OUTPUT BẮT BUỘC (tuân thủ CHÍNH XÁC):\n\n"
        "### 1. Thông tin sự kiện\n"
        "Trích xuất TẤT CẢ field có trong log, mỗi field một dòng:\n"
        "- **Event ID**: `<giá trị>` — <giải thích ngắn ý nghĩa>\n"
        "- **Source**: `<giá trị>` — <giải thích>\n"
        "- **TimeCreated**: `<giá trị>`\n"
        "- **Computer**: `<giá trị>`\n"
        "- **Account Name**: `<giá trị>`\n"
        "- **Account Domain**: `<giá trị>`\n"
        "- **Process ID**: `<giá trị>`\n"
        "- **Process Name**: `<giá trị>` — <giải thích process này là gì>\n"
        "- **Command Line**: `<giá trị>` — <giải thích lệnh làm gì>\n"
        "- **Parent Process**: `<giá trị>` — <giải thích>\n"
        "- **Token Elevation Type**: `<giá trị>` — <Type 1/2/3 nghĩa là gì>\n"
        "- (liệt kê TẤT CẢ field khác có trong log gốc, KHÔNG bỏ sót)\n\n"
        "### 2. Nhận định\n"
        "- **Nhận định**: `True Positive` HOẶC `False Positive` HOẶC `Cần điều tra thêm`\n"
        "  - `False Positive` → Khi đây là tiến trình hệ thống/user bình thường, "
        "không có dấu hiệu bất thường.\n"
        "  - `True Positive` → Khi có dấu hiệu độc hại rõ ràng và CẦN điều tra mở rộng.\n"
        "  - `Cần điều tra thêm` → Khi chưa đủ context để kết luận.\n"
        "- **Mức độ**: `Critical` / `High` / `Medium` / `Low` / `Informational`\n"
        "- **Lý do**: <2-4 câu giải thích cụ thể DỰA TRÊN các field ở trên>\n\n"
        "### 3. MITRE ATT&CK\n"
        "- **Technique ID**: `<Txxxx.xxx>` — `<tên technique>`\n"
        "- **Tactic**: `<tên tactic>`\n"
        "- (nếu không match MITRE thì ghi: **MITRE ATT&CK**: `N/A`)\n\n"
        "### 4. Khuyến nghị điều tra mở rộng\n"
        "CHỈ đưa ra nếu Nhận định là `True Positive` hoặc `Cần điều tra thêm`.\n"
        "Nếu `False Positive` → ghi: **Khuyến nghị**: `Không cần hành động — đây là hoạt động bình thường.`\n\n"
        "Nếu cần điều tra, liệt kê cụ thể:\n"
        "- **Log cần kiểm tra thêm**: <Event ID cụ thể, ví dụ: 4624, 4672, 4697>\n"
        "- **Truy vấn đề xuất**: `<KQL/SPL/câu lệnh cụ thể>`\n"
        "- **IOCs cần tra**: <file hash, IP, domain, user, machine>\n\n"
        "## QUY TẮC CỨNG:\n"
        "1. **LUÔN tiếng Việt.** Tên field giữ nguyên tiếng Anh (Event ID, Process Name...).\n"
        "2. **KHÔNG thêm lời mở đầu/kết thúc** kiểu \"Chào bạn, tôi sẽ...\". Đi thẳng vào phân tích.\n"
        "3. **KHÔNG lặp lại nội dung log gốc**.\n"
        "4. Chỉ ghi field có trong log. Nếu field không có trong log → bỏ hẳn dòng đó (không ghi `N/A`).\n"
        "5. Giữ đúng 4 section: `### 1. Thông tin sự kiện` → `### 2. Nhận định` → `### 3. MITRE ATT&CK` → `### 4. Khuyến nghị điều tra mở rộng`.\n"
    )

    @staticmethod
    def _build_messages(message: str, routing: dict, context: str = "",
                        search_context: str = "", history: List[Dict[str, str]] = None,
                        is_local: bool = False) -> list:
        use_rag = routing["use_rag"]
        use_search = routing.get("use_search", False)

        # Detect log analysis requests — use specialized structured prompt
        is_log = ChatService._is_log_analysis(message)

        # Short system prompt for local CPU models — no RAG context, minimal tokens
        if is_local:
            if is_log:
                system_prompt = ChatService._LOG_ANALYSIS_PROMPT
            else:
                system_prompt = (
                    "Bạn là trợ lý AI chuyên gia về an ninh mạng và bảo mật thông tin.\n"
                    "Trả lời bằng tiếng Việt, rõ ràng, đầy đủ nội dung.\n"
                    "Dùng Markdown: heading, bullet list, bold cho thuật ngữ quan trọng."
                )
            user_content = message
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history[-2:])
            messages.append({"role": "user", "content": user_content})
            return messages

        # Log analysis takes priority — use structured prompt regardless of RAG/search
        if is_log:
            system_prompt = ChatService._LOG_ANALYSIS_PROMPT
            user_content = message
        # Cloud model with RAG context from knowledge base
        elif use_rag and context:
            system_prompt = (
                "Bạn là trợ lý AI chuyên gia về an ninh mạng, bảo mật thông tin, "
                "ISO 27001, TCVN và các tiêu chuẩn an toàn thông tin.\n\n"
                "## Quy tắc\n"
                "1. **LUÔN trả lời bằng tiếng Việt.**\n"
                "2. Ưu tiên thông tin từ tài liệu tham chiếu. "
                "Có thể bổ sung kiến thức chuyên môn nếu tài liệu chưa đủ.\n"
                "3. Trích dẫn nguồn khi dùng tài liệu (ví dụ: *Annex A.8.1*).\n"
                "4. Nếu tài liệu không liên quan, trả lời từ kiến thức chuyên môn "
                "và ghi chú \"(từ kiến thức chuyên môn)\".\n\n"
                "## Định dạng (Markdown)\n"
                "- `## tiêu đề` cho phần chính\n"
                "- **Bullet list** / **numbered list** cho danh sách\n"
                "- **Bold** cho thuật ngữ quan trọng\n"
                "- Bảng khi so sánh nhiều mục\n"
                "- `code block` cho lệnh/cấu hình kỹ thuật\n"
                "- Trả lời ĐẦY ĐỦ, không cắt xén nội dung."
            )
            user_content = f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"
        # Cloud model with web search results
        elif use_search and search_context:
            system_prompt = (
                "Bạn là trợ lý AI chuyên phân tích và tổng hợp thông tin.\n\n"
                "## Quy tắc\n"
                "1. **LUÔN trả lời bằng tiếng Việt.**\n"
                "2. Tổng hợp từ kết quả tìm kiếm, bổ sung kiến thức nếu cần.\n"
                "3. Trích dẫn nguồn: [tiêu đề](url) sau mỗi thông tin quan trọng.\n"
                "4. Nếu kết quả tìm kiếm không đủ, nói rõ.\n\n"
                "## Định dạng (Markdown)\n"
                "- `## tiêu đề` cho phần chính\n"
                "- **Bullet list** / **numbered list** cho danh sách\n"
                "- **Bold** cho thuật ngữ quan trọng\n"
                "- Bảng khi so sánh nhiều mục\n"
                "- Cuối: **## Nguồn tham khảo** liệt kê tất cả URL\n"
                "- Trả lời ĐẦY ĐỦ, không cắt xén nội dung."
            )
            user_content = f"Kết quả tìm kiếm:\n{search_context}\n\nCâu hỏi: {message}"
        # Cloud model — general knowledge, no RAG/search
        else:
            system_prompt = (
                "Bạn là trợ lý AI chuyên gia về an ninh mạng, bảo mật thông tin, "
                "ISO 27001, NIST, TCVN và công nghệ thông tin.\n\n"
                "## Quy tắc\n"
                "1. **LUÔN trả lời bằng tiếng Việt.**\n"
                "2. Trả lời chính xác, đầy đủ từ kiến thức chuyên môn.\n"
                "3. Không bịa đặt. Nếu không chắc, nói rõ.\n"
                "4. Ghi rõ tên/phiên bản tiêu chuẩn khi đề cập "
                "(ví dụ: *ISO 27001:2022*, *NIST CSF 2.0*).\n\n"
                "## Định dạng (Markdown)\n"
                "- `## tiêu đề` cho phần chính\n"
                "- **Bullet list** / **numbered list** cho danh sách\n"
                "- **Bold** cho thuật ngữ quan trọng\n"
                "- Bảng khi so sánh nhiều mục\n"
                "- `code block` cho lệnh/cấu hình kỹ thuật\n"
                "- Trả lời ĐẦY ĐỦ, chi tiết, không cắt xén nội dung."
            )
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
            yield {"step": "routing", "message": "Đang phân tích câu hỏi..."}

            routing = route_model(message)
            model_name = model_override or routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            # Disable RAG for ALL local CPU models (Ollama + LocalAI GGUF)
            # Web search is kept active as a useful chatbot feature
            is_local = ChatService._is_local_model(model_name)
            if is_local:
                use_rag = False

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                yield {"step": "rag", "message": "📚 Đang tra cứu tài liệu nội bộ..."}
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=2)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                yield {"step": "searching", "message": "🔍 Đang tìm kiếm trên internet..."}
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]
                    yield {"step": "search_done", "message": f"✅ Tìm thấy {len(search_results)} kết quả, đang phân tích..."}

            display_model = model_name if model_name else settings.CLOUD_MODEL_NAME
            yield {"step": "thinking", "message": f"🤖 Đang tạo câu trả lời ({display_model})..."}

            ss = ChatService.get_session_store()
            max_hist = 2 if is_local else 10
            history = ss.get_context_messages(session_id, max_messages=max_hist)
            messages = ChatService._build_messages(message, routing, context, search_context, history, is_local=is_local)

            # Pass cloud_model ONLY when prefer_cloud=True (cloud model selected).
            # When prefer_cloud=False the model_override is a LocalAI model ID — do NOT
            # pass it as cloud_model or force_local computation breaks.
            result = CloudLLMService.chat_completion(
                messages=messages,
                temperature=0.7,
                local_model=model_name,
                prefer_cloud=prefer_cloud,
                cloud_model=model_override if prefer_cloud else None,
            )
            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""

            ss.add_message(session_id, "user", message)
            if response_text:
                ss.add_message(session_id, "assistant", response_text)

            yield {
                "step": "done",
                "data": {
                    "response": response_text or "Model không trả về response.",
                    "model": result.get("model", model_name),
                    "provider": result.get("provider", "unknown"),
                    "route": routing["route"],
                    "session_id": session_id,
                    "rag_used": use_rag, "search_used": use_search,
                    "sources": list(set(sources)) if sources else [],
                    "web_sources": web_sources,
                    "tokens": {
                        "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "step": "error",
                "data": {"response": f"Lỗi: {str(e)}", "model": _error_model,
                         "session_id": session_id, "error": True},
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
    def assess_system(system_data: Dict[str, Any], model_mode: str = "hybrid",
                      progress_callback=None) -> Dict[str, Any]:
        """progress_callback(message: str, percent: int) — optional, called per chunk."""
        from services.controls_catalog import get_categories, get_flat_controls, calc_compliance, build_weight_breakdown
        from services.assessment_helpers import (
            build_chunk_prompt, validate_chunk_output, gap_items_to_markdown,
            build_full_prompt, build_weight_breakdown_txt, compress_for_phase2,
            build_sys_summary, infer_gap_from_control, normalize_severity_distribution
        )

        effective_mode = model_mode or system_data.get("model_mode", "hybrid")
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
                        sys_summary_short, std_name, cat_rag_ctx
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
