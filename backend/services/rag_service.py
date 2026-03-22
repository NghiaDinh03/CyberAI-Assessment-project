"""RAG Service — Retrieval-Augmented Generation with CloudLLM and source attribution."""

import logging
from typing import Dict, List
from repositories.vector_store import VectorStore
from services.cloud_llm_service import CloudLLMService

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        results = self.vector_store.multi_query_search(query, top_k=top_k)
        if not results:
            return ""
        return "\n\n---\n\n".join([doc["text"] for doc in results])

    def retrieve_with_sources(self, query: str, top_k: int = 5) -> Dict:
        results = self.vector_store.multi_query_search(query, top_k=top_k)
        if not results:
            return {"context": "", "sources": []}

        context = "\n\n---\n\n".join([doc["text"] for doc in results])
        seen = set()
        unique_sources = []
        for doc in results:
            f = doc.get("file", "")
            if f not in seen:
                seen.add(f)
                unique_sources.append({
                    "file": f, "title": doc.get("doc_title", ""),
                    "score": doc.get("score", 0), "source": doc.get("source", ""),
                })
        return {"context": context, "sources": unique_sources}

    def generate_response(self, query: str, context: str = None) -> str:
        if context is None:
            context = self.retrieve_context(query)

        if not context:
            try:
                result = CloudLLMService.chat_completion(
                    messages=[{"role": "user", "content": query}], temperature=0.3, max_tokens=2048)
                return result.get("content", "Xin lỗi, tôi không thể trả lời lúc này.")
            except Exception as e:
                logger.error(f"RAG generate without context failed: {e}")
                return "Xin lỗi, tôi không thể trả lời lúc này."

        prompt = (
            "Dựa trên tài liệu tham khảo bên dưới, hãy trả lời câu hỏi của người dùng.\n"
            "Nếu tài liệu không đủ thông tin, hãy nói rõ phần nào dựa trên tài liệu và phần nào là kiến thức chung.\n\n"
            f"Tài liệu tham khảo:\n{context}\n\nCâu hỏi: {query}\n\n"
            "Trả lời bằng Tiếng Việt, chi tiết và chính xác:"
        )
        try:
            result = CloudLLMService.chat_completion(
                messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=2048)
            return result.get("content", "Xin lỗi, tôi không thể trả lời lúc này.")
        except Exception as e:
            logger.error(f"RAG generate failed: {e}")
            return "Xin lỗi, tôi không thể trả lời lúc này."

    def is_relevant(self, query: str, threshold: float = 0.3) -> bool:
        results = self.vector_store.search(query, top_k=1)
        return bool(results and results[0].get("score", 0) >= threshold)
