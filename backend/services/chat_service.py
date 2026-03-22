"""Chat Service — Conversation routing with session memory and Cloud-first strategy."""

import re
import logging
import threading
from typing import Dict, Any, Generator, List

from core.config import settings
from services.cloud_llm_service import CloudLLMService
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

    @staticmethod
    def clean_response(text: str) -> str:
        return SPECIAL_TOKENS.sub('', text).strip()

    @staticmethod
    def _build_messages(message: str, routing: dict, context: str = "",
                        search_context: str = "", history: List[Dict[str, str]] = None) -> list:
        use_rag = routing["use_rag"]
        use_search = routing.get("use_search", False)

        if use_rag and context:
            system_prompt = (
                "Bạn là chuyên gia đánh giá ISO 27001:2022 và an toàn thông tin. "
                "Trả lời chính xác dựa trên tài liệu chuẩn được cung cấp. "
                "Không bịa thêm thông tin ngoài tài liệu. "
                "Nếu không tìm thấy thông tin, hãy nói rõ. "
                "Trả lời bằng tiếng Việt, rõ ràng và có cấu trúc."
            )
            user_content = f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"
        elif use_search and search_context:
            system_prompt = (
                "Bạn là trợ lý AI thông minh có khả năng phân tích thông tin từ internet. "
                "Dưới đây là kết quả tìm kiếm web. Hãy tổng hợp và trả lời chính xác dựa trên những nguồn này. "
                "Trích dẫn nguồn URL khi cần. Trả lời bằng tiếng Việt."
            )
            user_content = f"Kết quả tìm kiếm:\n{search_context}\n\nCâu hỏi: {message}"
        else:
            system_prompt = (
                "Bạn là trợ lý AI thông minh, chuyên gia về an ninh mạng và công nghệ thông tin. "
                "Trả lời bằng tiếng Việt, rõ ràng, chính xác và có cấu trúc."
            )
            user_content = message

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_content})
        return messages

    @staticmethod
    def generate_response(message: str, session_id: str = "default") -> Dict[str, Any]:
        try:
            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=5)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]

            ss = ChatService.get_session_store()
            history = ss.get_context_messages(session_id, max_messages=10)
            messages = ChatService._build_messages(message, routing, context, search_context, history)

            result = CloudLLMService.chat_completion(messages=messages, temperature=0.7, local_model=model_name)
            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""

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
                "response": f"Lỗi: {str(e)}", "model": settings.MODEL_NAME,
                "provider": "error", "session_id": session_id, "error": True,
            }

    @staticmethod
    def generate_response_stream(message: str, session_id: str = "default") -> Generator:
        try:
            # Check if AI is busy
            try:
                from services.news_service import get_ai_status
                ai_status = get_ai_status()
                if "Đang rảnh" not in ai_status:
                    yield {
                        "step": "done",
                        "data": {
                            "response": f"⚠️ Hệ thống AI hiện đang bận ({ai_status}). Vui lòng chờ rồi thử lại!",
                            "model": settings.MODEL_NAME, "provider": "blocked",
                            "route": "blocked_by_queue", "session_id": session_id,
                            "rag_used": False, "search_used": False,
                            "sources": [], "web_sources": [],
                            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        },
                    }
                    return
            except ImportError:
                pass

            yield {"step": "routing", "message": "Đang phân tích câu hỏi..."}

            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                yield {"step": "rag", "message": "📚 Đang tra cứu tài liệu nội bộ..."}
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=5)
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

            yield {"step": "thinking", "message": "🤖 Đang tạo câu trả lời (gemini-3-pro-preview)..."}

            ss = ChatService.get_session_store()
            history = ss.get_context_messages(session_id, max_messages=10)
            messages = ChatService._build_messages(message, routing, context, search_context, history)

            result = CloudLLMService.chat_completion(messages=messages, temperature=0.7, local_model=model_name)
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
                "data": {"response": f"Lỗi: {str(e)}", "model": settings.MODEL_NAME,
                         "session_id": session_id, "error": True},
            }

    @staticmethod
    def clear_conversation(session_id: str) -> Dict[str, Any]:
        ss = ChatService.get_session_store()
        ss.clear_history(session_id)
        return {"status": "ok", "message": "Đã xóa ngữ cảnh hội thoại", "session_id": session_id}

    @staticmethod
    def assess_system(system_data: Dict[str, Any]) -> Dict[str, Any]:
        vs = ChatService.get_vector_store()

        standard = system_data.get("assessment_standard", "iso27001")
        search_query = "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"
        if standard == "tcvn11930":
            search_query = "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        elif standard == "nd13":
            search_query = "Nghị định 13 bảo vệ dữ liệu cá nhân"

        context_results = vs.search(search_query, top_k=6)
        context = "\n---\n".join([r["text"] for r in context_results])

        implemented = system_data.get("compliance", {}).get("implemented_controls", [])
        score = len(implemented)
        max_score = 93
        std_name = "ISO 27001:2022"

        if standard == "tcvn11930":
            max_score = 34
            std_name = "TCVN 11930:2017 (Yêu cầu kỹ thuật theo 5 cấp độ)"

        percentage = round((score / max_score) * 100, 1)

        system_info_txt = f"Tiêu chuẩn đánh giá: {std_name}\n"
        system_info_txt += f"Mức độ tuân thủ: {score}/{max_score} Controls đạt yêu cầu ({percentage}%).\n"
        system_info_txt += f"Các Controls đã đạt: {', '.join(implemented)}\n\nCHI TIẾT HẠ TẦNG HỆ THỐNG:\n"

        for key, value in system_data.items():
            if key in ["compliance", "assessment_standard", "implemented_controls"]:
                continue
            if isinstance(value, dict):
                for k, v in value.items():
                    system_info_txt += f"- {k}: {v}\n"
            elif isinstance(value, list):
                system_info_txt += f"- {key}: {', '.join(str(v) for v in value)}\n"
            else:
                system_info_txt += f"- {key}: {value}\n"

        # Phase 1: Security analysis
        security_prompt = (
            f"Bạn là chuyên gia Auditor về {std_name}. Hệ thống đang chấm điểm sơ bộ đạt {percentage}% "
            f"tuân thủ ({score}/{max_score} Controls). Dựa vào các Controls ĐÃ ĐẠT và THÔNG TIN HỆ THỐNG, "
            f"hãy chỉ ra những RỦI RO, lỗ hổng (GAPs). Chỉ trả về danh sách phát hiện kỹ thuật thô."
        )
        messages_p1 = [
            {"role": "system", "content": security_prompt},
            {"role": "user", "content": f"Tài liệu {std_name}:\n{context}\n\nBiên bản khảo sát:\n{system_info_txt}"},
        ]

        try:
            result_p1 = CloudLLMService.chat_completion(
                messages=messages_p1, temperature=0.3, local_model=settings.SECURITY_MODEL_NAME)
            raw_analysis = result_p1.get("content", "")

            # Phase 2: Format report
            formatting_prompt = (
                f"Bạn là chuyên gia trình bày Báo cáo Đánh giá ATTT chuyên nghiệp. "
                f"Trình bày lại báo cáo bằng Markdown tiếng Việt gồm:\n"
                f"1. ĐÁNH GIÁ TỔNG QUAN (tóm tắt {percentage}%)\n"
                f"2. PHÂN TÍCH LỖ HỔNG (GAP ANALYSIS)\n"
                f"3. KHUYẾN NGHỊ ƯU TIÊN (ACTION PLAN)\n\n"
                f"Dữ liệu thô từ Security Auditor:\n{raw_analysis}"
            )
            result_p2 = CloudLLMService.chat_completion(
                messages=[{"role": "user", "content": formatting_prompt}],
                temperature=0.5, local_model=settings.MODEL_NAME)

            return {
                "report": result_p2.get("content", ""),
                "details": [],
                "model_used": {
                    "phase1": f"{result_p1.get('provider')}:{result_p1.get('model')}",
                    "phase2": f"{result_p2.get('provider')}:{result_p2.get('model')}",
                },
            }
        except Exception as e:
            logger.error(f"Assessment error: {e}")
            return {"report": f"Lỗi tạo báo cáo: {str(e)}", "details": [], "error": True}

    @staticmethod
    def health_check() -> Dict[str, Any]:
        return CloudLLMService.health_check()
