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
    def _call_model(model: str, messages: list, temperature: float = 0.7) -> Dict[str, Any]:
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
            result = ChatService._call_model(model_name, messages)

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
            result = ChatService._call_model(model_name, messages)

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

        search_query = "A.5 Tổ chức nội bộ chính sách, A.6 Nhân sự đào tạo, A.7 Vật lý hệ thống camera quản lý, A.8 Công nghệ mạng firewall mã hóa backup"
        context_results = vs.search(search_query, top_k=6)
        context = "\n---\n".join([r["text"] for r in context_results])

        system_info = ""
        for key, value in system_data.items():
            system_info += f"### {key.upper()}\n"
            if isinstance(value, dict):
                for k, v in value.items():
                    system_info += f"- {k}: {v}\n"
            elif isinstance(value, list):
                system_info += f"- {key}: {', '.join(str(v) for v in value)}\n"
            else:
                system_info += f"- {key}: {value}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia Auditor ISO 27001:2022. Đánh giá TỔNG THỂ hệ thống.\n"
                    "Trả lời bằng tiếng Việt chuyên nghiệp, theo format sau:\n\n"
                    "1. ĐIỂM TỔNG THỂ: [số từ 0-100] (Xếp hạng A/B/C/D/F)\n"
                    "2. ĐÁNH GIÁ CHUNG: [Tuân thủ xuất sắc / Đạt yêu cầu cơ bản / Còn nhiều lỗ hổng]\n"
                    "3. PHÂN TÍCH THEO NHÓM:\n"
                    "   - Tổ chức (A.5): [Phát hiện & Nhận xét]\n"
                    "   - Nhân sự (A.6): [Phát hiện & Nhận xét]\n"
                    "   - Vật lý (A.7): [Phát hiện & Nhận xét]\n"
                    "   - Công nghệ (A.8): [Phát hiện & Nhận xét]\n"
                    "4. KHUYẾN NGHỊ ƯU TIÊN: [Danh sách ít nhất 3 hành động khắc phục cấp thiết nhất theo chuẩn ISO]"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Tiêu chuẩn ISO tham chiếu:\n{context}\n\n"
                    f"Thông tin hệ thống cần đánh giá:\n{system_info}"
                )
            }
        ]

        security_model = os.getenv("SECURITY_MODEL_NAME", ChatService.MODEL_NAME)
        
        try:
            result = ChatService._call_model(security_model, messages, temperature=0.3)
            report_text = result["content"]
            
            return {
                "report": report_text,
                "details": [],
                "model_used": {
                    "analysis_and_summary": security_model
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
                    "models": {
                        "general": ChatService.MODEL_NAME,
                        "security": ChatService.SECURITY_MODEL
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
