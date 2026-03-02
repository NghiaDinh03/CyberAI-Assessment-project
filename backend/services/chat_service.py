import requests
import os
import re
from typing import Dict, Any
from services.model_router import route_model
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

    @classmethod
    def get_vector_store(cls):
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
            timeout=300
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
    def generate_response(message: str, session_id: str = "default") -> Dict[str, Any]:
        try:
            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]

            context = ""
            sources = []

            if use_rag:
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=5)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_rag and context:
                messages = [
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
            else:
                messages = [
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý AI thông minh. Trả lời bằng tiếng Việt, rõ ràng và chính xác."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]

            result = ChatService._call_model(model_name, messages)

            return {
                "response": result["content"] or "Model không trả về response. Vui lòng thử lại.",
                "model": model_name,
                "route": routing["route"],
                "session_id": session_id,
                "rag_used": use_rag,
                "sources": list(set(sources)) if sources else [],
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
    def assess_system(system_data: Dict[str, Any]) -> Dict[str, Any]:
        vs = ChatService.get_vector_store()

        categories = {
            "organization": "A.5 Kiểm soát tổ chức chính sách ATTT",
            "people": "A.6 Kiểm soát con người đào tạo nhận thức",
            "physical": "A.7 Kiểm soát vật lý server room camera",
            "technology": "A.8 Kiểm soát công nghệ firewall backup mã hóa"
        }

        assessment_results = []
        total_score = 0

        for category, search_query in categories.items():
            context_results = vs.search(search_query, top_k=3)
            context = "\n".join([r["text"] for r in context_results])

            system_info = ""
            for key, value in system_data.items():
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
                        "Bạn là auditor ISO 27001:2022. Đánh giá hệ thống dựa trên tiêu chuẩn. "
                        "Trả lời theo format:\n"
                        "ĐIỂM: [số từ 0-100]\n"
                        "ĐÁNH GIÁ: [Tuân thủ/Một phần/Không tuân thủ]\n"
                        "PHÁT HIỆN: [danh sách findings]\n"
                        "KHUYẾN NGHỊ: [danh sách recommendations]"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Tiêu chuẩn ISO 27001:\n{context}\n\n"
                        f"Thông tin hệ thống:\n{system_info}\n\n"
                        f"Đánh giá nhóm: {category}"
                    )
                }
            ]

            security_model = os.getenv("SECURITY_MODEL_NAME", ChatService.MODEL_NAME)
            try:
                result = ChatService._call_model(security_model, messages, temperature=0.3)
                assessment_results.append({
                    "category": category,
                    "analysis": result["content"]
                })
            except Exception as e:
                assessment_results.append({
                    "category": category,
                    "analysis": f"Lỗi phân tích: {str(e)}"
                })

        combined_analysis = "\n\n".join([
            f"### {r['category'].upper()}\n{r['analysis']}"
            for r in assessment_results
        ])

        summary_messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia ISO 27001. Tổng hợp kết quả đánh giá và viết báo cáo bằng tiếng Việt. "
                    "Bao gồm: điểm tổng thể, xếp hạng (A/B/C/D/F), các phát hiện quan trọng, "
                    "khuyến nghị ưu tiên, và lộ trình cải thiện."
                )
            },
            {
                "role": "user",
                "content": f"Kết quả phân tích chi tiết:\n{combined_analysis}\n\nViết báo cáo tổng hợp."
            }
        ]

        try:
            summary = ChatService._call_model(ChatService.MODEL_NAME, summary_messages, temperature=0.5)
            return {
                "report": summary["content"],
                "details": assessment_results,
                "model_used": {
                    "analysis": security_model,
                    "summary": ChatService.MODEL_NAME
                }
            }
        except Exception as e:
            return {
                "report": f"Lỗi tạo báo cáo: {str(e)}",
                "details": assessment_results,
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
