import requests
import os
import re
import json
import threading
from typing import Dict, Any, Generator
from services.model_router import route_model
from services.web_search import WebSearch
from repositories.vector_store import VectorStore


class ChatService:
    LOCALAI_URL = os.getenv("LOCALAI_URL", "http://localai:8080")
    MODEL_NAME = os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")
    SECURITY_MODEL = os.getenv("SECURITY_MODEL_NAME", "SecurityLLM-7B-Q4_K_M.gguf")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "-1"))

    CLOUD_LLM_URL = os.getenv("CLOUD_LLM_API_URL", "")
    CLOUD_MODEL = os.getenv("CLOUD_MODEL_NAME", "meta-llama/llama-3.1-8b-instruct:free")
    OPENROUTER_KEYS = os.getenv("OPENROUTER_API_KEYS", "")

    SPECIAL_TOKENS = re.compile(
        r'<\|eot_id\|>|<\|start_header_id\|>|<\|end_header_id\|>|'
        r'<\|begin_of_text\|>|<\|end_of_text\|>|<\|finetune_right_pad_id\|>|'
        r'<\|reserved_special_token_\d+\|>'
    )

    _vector_store = None
    _vs_lock = threading.Lock()

    @classmethod
    def get_vector_store(cls):
        if cls._vector_store is None:
            with cls._vs_lock:
                if cls._vector_store is None:
                    cls._vector_store = VectorStore()
        return cls._vector_store

    @staticmethod
    def clean_response(text: str) -> str:
        cleaned = ChatService.SPECIAL_TOKENS.sub('', text)
        return cleaned.strip()

    @staticmethod
    def _get_cloud_api_key():
        keys = ChatService.OPENROUTER_KEYS
        if not keys:
            return None
        key_list = [k.strip() for k in keys.split(",") if k.strip()]
        return key_list[0] if key_list else None

    @staticmethod
    def _call_cloud_model(model: str, messages: list, temperature: float = 0.7) -> Dict[str, Any]:
        api_key = ChatService._get_cloud_api_key()
        if not api_key or not ChatService.CLOUD_LLM_URL:
            raise Exception("Cloud LLM not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{ChatService.CLOUD_LLM_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "content": ChatService.clean_response(content) if content else "",
                "usage": data.get("usage", {})
            }
        else:
            raise Exception(f"Cloud LLM error ({response.status_code}): {response.text[:200]}")

    @staticmethod
    def _call_model(model: str, messages: list, temperature: float = 0.7) -> Dict[str, Any]:
        # Block if news background worker is using LocalAI
        try:
            from services.news_service import get_ai_status
            ai_status = get_ai_status()
            if "Đang rảnh" not in ai_status:
                return {
                    "content": f"⚠️ Hệ thống AI hiện đang bận tác vụ nền ({ai_status}).\nĐể tránh quá tải hệ thống, vui lòng chờ quá trình này hoàn tất rồi thử lại nhé!",
                    "usage": {}
                }
        except ImportError:
            pass

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        if ChatService.MAX_TOKENS > 0:
            payload["max_tokens"] = ChatService.MAX_TOKENS

        response = requests.post(
            f"{ChatService.LOCALAI_URL}/v1/chat/completions",
            json=payload,
            timeout=900
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "content": ChatService.clean_response(content) if content else "",
                "usage": data.get("usage", {})
            }
        else:
            raise Exception(f"LocalAI error ({response.status_code}): {response.text[:200]}")

    @staticmethod
    def _call_best_model(model: str, messages: list, temperature: float = 0.7) -> Dict[str, Any]:
        """Try cloud first, fallback to local."""
        if ChatService.CLOUD_LLM_URL and ChatService._get_cloud_api_key():
            try:
                return ChatService._call_cloud_model(
                    ChatService.CLOUD_MODEL, messages, temperature
                )
            except Exception:
                pass
        return ChatService._call_model(model, messages, temperature)

    @staticmethod
    def _build_messages(message: str, routing: dict, context: str = "", search_context: str = ""):
        use_rag = routing["use_rag"]
        use_search = routing.get("use_search", False)

        if use_rag and context:
            return [
                {
                    "role": "system",
                    "content": (
                        "Bạn là chuyên gia đánh giá ISO 27001:2022. "
                        "Trả lời chính xác dựa trên tài liệu chuẩn được cung cấp. "
                        "Không bịa thêm thông tin ngoài tài liệu. "
                        "Nếu không tìm thấy thông tin, hãy nói rõ."
                    )
                },
                {
                    "role": "user",
                    "content": f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"
                }
            ]
        elif use_search and search_context:
            return [
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý AI thông minh có khả năng phân tích thông tin từ internet. "
                        "Dưới đây là kết quả tìm kiếm web. Hãy tổng hợp và trả lời chính xác dựa trên những nguồn này. "
                        "Trích dẫn nguồn URL khi cần. Trả lời bằng tiếng Việt."
                    )
                },
                {
                    "role": "user",
                    "content": f"Kết quả tìm kiếm:\n{search_context}\n\nCâu hỏi: {message}"
                }
            ]
        else:
            return [
                {
                    "role": "system",
                    "content": "Bạn là trợ lý AI thông minh. Trả lời bằng tiếng Việt, rõ ràng và chính xác."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]

    @staticmethod
    def generate_response(message: str, session_id: str = "default") -> Dict[str, Any]:
        try:
            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context = ""
            search_context = ""
            sources = []
            web_sources = []

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

            messages = ChatService._build_messages(message, routing, context, search_context)
            result = ChatService._call_best_model(model_name, messages)

            return {
                "response": result["content"] or "Model không trả về response. Vui lòng thử lại.",
                "model": model_name,
                "route": routing["route"],
                "session_id": session_id,
                "rag_used": use_rag,
                "search_used": use_search,
                "sources": list(set(sources)) if sources else [],
                "web_sources": web_sources,
                "tokens": {
                    "prompt_tokens": result["usage"].get("prompt_tokens", 0),
                    "completion_tokens": result["usage"].get("completion_tokens", 0),
                    "total_tokens": result["usage"].get("total_tokens", 0)
                }
            }

        except requests.exceptions.Timeout:
            return {
                "response": "Request timeout. Model đang xử lý quá lâu.",
                "model": ChatService.MODEL_NAME,
                "session_id": session_id,
                "error": True
            }

        except requests.exceptions.ConnectionError:
            return {
                "response": "Không thể kết nối LocalAI. Kiểm tra container đang chạy.",
                "model": ChatService.MODEL_NAME,
                "session_id": session_id,
                "error": True
            }

        except Exception as e:
            return {
                "response": f"Lỗi: {str(e)}",
                "model": ChatService.MODEL_NAME,
                "session_id": session_id,
                "error": True
            }

    @staticmethod
    def generate_response_stream(message: str, session_id: str = "default") -> Generator:
        try:
            # Block if AI is busy with background tasks
            try:
                from services.news_service import get_ai_status
                ai_status = get_ai_status()
                if "Đang rảnh" not in ai_status:
                    yield {
                        "step": "done",
                        "data": {
                            "response": f"⚠️ Hệ thống AI hiện đang bận tác vụ nền ({ai_status}).\nĐể tránh quá tải hệ thống, vui lòng chờ trong giây lát rồi đặt lại câu hỏi nhé!",
                            "model": ChatService.MODEL_NAME,
                            "route": "blocked_by_queue",
                            "session_id": session_id,
                            "rag_used": False,
                            "search_used": False,
                            "sources": [],
                            "web_sources": [],
                            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                        }
                    }
                    return
            except ImportError:
                pass

            yield {"step": "routing", "message": "Đang phân tích câu hỏi..."}

            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context = ""
            search_context = ""
            sources = []
            web_sources = []

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

            yield {"step": "thinking", "message": "🤖 Đang tạo câu trả lời..."}

            messages = ChatService._build_messages(message, routing, context, search_context)
            result = ChatService._call_best_model(model_name, messages)

            yield {
                "step": "done",
                "data": {
                    "response": result["content"] or "Model không trả về response.",
                    "model": model_name,
                    "route": routing["route"],
                    "session_id": session_id,
                    "rag_used": use_rag,
                    "search_used": use_search,
                    "sources": list(set(sources)) if sources else [],
                    "web_sources": web_sources,
                    "tokens": {
                        "prompt_tokens": result["usage"].get("prompt_tokens", 0),
                        "completion_tokens": result["usage"].get("completion_tokens", 0),
                        "total_tokens": result["usage"].get("total_tokens", 0)
                    }
                }
            }

        except Exception as e:
            yield {
                "step": "error",
                "data": {
                    "response": f"Lỗi: {str(e)}",
                    "model": ChatService.MODEL_NAME,
                    "session_id": session_id,
                    "error": True
                }
            }

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

        # Calculate compliance score
        implemented = system_data.get("compliance", {}).get("implemented_controls", [])
        score = len(implemented)
        max_score = 93
        std_name = "ISO 27001:2022"

        if standard == "tcvn11930":
            max_score = 34
            std_name = "TCVN 11930:2017 (Yêu cầu kỹ thuật theo 5 cấp độ)"

        percentage = round((score / max_score) * 100, 1)

        # Build system info text for LLM
        system_info_txt = f"Tiêu chuẩn đánh giá: {std_name}\n"
        system_info_txt += f"Mức độ tuân thủ: {score}/{max_score} Controls đạt yêu cầu ({percentage}%).\n"
        system_info_txt += f"Các Controls đã đạt: {', '.join(implemented)}\n\n"
        system_info_txt += "CHI TIẾT HẠ TẦNG HỆ THỐNG:\n"

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
        security_prompt = f"""
Bạn là chuyên gia Auditor về {std_name}. Hệ thống đang chấm điểm sơ bộ đạt {percentage}% tuân thủ ({score}/{max_score} Controls).
Dựa vào các Controls ĐÃ ĐẠT và THÔNG TIN HỆ THỐNG được cung cấp, hãy chỉ ra những RỦI RO, lỗ hổng (GAPs) họ ĐANG GẶP PHẢI.
Nếu là TCVN 11930, hãy đánh giá họ đang đạt cấp độ mấy trong 5 cấp độ kỹ thuật và chỉ ra những điểm còn thiếu để lên cấp độ cao hơn.
Chỉ trả về danh sách phát hiện kỹ thuật thô.
"""
        messages_phase_1 = [
            {"role": "system", "content": security_prompt},
            {"role": "user", "content": f"Dữ liệu tài liệu {std_name}:\n{context}\n\nBiên bản khảo sát hệ thống:\n{system_info_txt}"}
        ]

        security_model = os.getenv("SECURITY_MODEL_NAME", ChatService.MODEL_NAME)

        try:
            # Phase 1: Run security analysis
            result_phase_1 = ChatService._call_best_model(security_model, messages_phase_1, temperature=0.3)
            raw_analysis = result_phase_1.get("content", "")

            # Phase 2: Format report
            formatting_prompt = f"""
Bạn là chuyên gia trình bày Báo cáo Đánh giá ATTT chuyên nghiệp. Dưới đây là phân tích kỹ thuật thô từ Security Auditor.
Nhiệm vụ của bạn là trình bày lại Báo cáo này thật chuyên nghiệp bằng định dạng Markdown tiếng Việt, bao gồm các mục:
1. ĐÁNH GIÁ TỔNG QUAN: (Tóm tắt mức tuân thủ {percentage}% và tình trạng hiện tại)
2. PHÂN TÍCH LỖ HỔNG (GAP ANALYSIS): (Dàn ý rõ ràng rủi ro do thiết kế kiến trúc và thiếu controls)
3. KHUYẾN NGHỊ ƯU TIÊN (ACTION PLAN): (Đề xuất thực tế để vá lỗ hổng)

Dữ liệu thô từ Security Auditor:
{raw_analysis}
            """

            general_model = os.getenv("MODEL_NAME", ChatService.MODEL_NAME)
            messages_phase_2 = [{"role": "user", "content": formatting_prompt}]

            result_phase_2 = ChatService._call_best_model(general_model, messages_phase_2, temperature=0.5)
            report_text = result_phase_2.get("content", "")

            return {
                "report": report_text,
                "details": [],
                "model_used": {
                    "analysis_and_summary": f"Phase 1: {security_model} -> Phase 2: {general_model}"
                }
            }
        except Exception as e:
            return {
                "report": f"Lỗi tạo báo cáo: {str(e)}",
                "details": [],
                "error": True
            }

    @staticmethod
    def health_check() -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{ChatService.LOCALAI_URL}/readyz",
                timeout=5
            )

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "localai_url": ChatService.LOCALAI_URL,
                    "cloud_url": ChatService.CLOUD_LLM_URL or "not configured",
                    "models": {
                        "general": ChatService.MODEL_NAME,
                        "security": ChatService.SECURITY_MODEL,
                        "cloud": ChatService.CLOUD_MODEL
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"LocalAI returned {response.status_code}"
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
