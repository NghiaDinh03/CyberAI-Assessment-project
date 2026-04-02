"""RAG Service — Retrieval-Augmented Generation with CloudLLM and source attribution."""

import logging
from typing import Dict, List
from repositories.vector_store import VectorStore
from services.cloud_llm_service import CloudLLMService

logger = logging.getLogger(__name__)

# Minimum cosine similarity score (0..1, higher = more similar) for a retrieved
# chunk to be considered confident enough to include in the RAG context.
# VectorStore.search() converts ChromaDB cosine *distance* to similarity via
#   score = 1 - distance
# so score >= 0.35 means distance <= 0.65 — keeping only the closest matches.
RAG_CONFIDENCE_THRESHOLD = 0.35


def _filter_by_confidence(results: list) -> list:
    """Return only chunks whose cosine-similarity score meets the threshold.

    Increments the ``cyberai_rag_queries_total`` Prometheus counter:
    - ``result="hit"``  — at least one chunk survived the confidence filter.
    - ``result="miss"`` — all chunks were below the threshold (or list was empty).

    Logs a debug message when low-confidence chunks are discarded.
    """
    confident = [doc for doc in results if doc.get("score", 0) >= RAG_CONFIDENCE_THRESHOLD]
    discarded = len(results) - len(confident)
    if discarded > 0:
        logger.debug(
            f"RAG: filtered {discarded} low-confidence chunk(s) "
            f"(score < {RAG_CONFIDENCE_THRESHOLD})"
        )

    # Lazy import avoids circular dependency at module load time
    try:
        from api.routes.metrics import RAG_QUERIES
        RAG_QUERIES.labels(result="hit" if confident else "miss").inc()
    except Exception:
        pass  # Metrics must never break core RAG functionality

    return confident


class RAGService:
    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve_context(self, query: str, top_k: int = 5, domain: str = "iso_documents") -> str:
        results = self.vector_store.multi_query_search(query, top_k=top_k, domain=domain)
        if not results:
            return ""
        confident = _filter_by_confidence(results)
        if not confident:
            return ""
        return "\n\n---\n\n".join([doc["text"] for doc in confident])

    def retrieve_with_sources(self, query: str, top_k: int = 5, domain: str = "iso_documents") -> Dict:
        results = self.vector_store.multi_query_search(query, top_k=top_k, domain=domain)
        if not results:
            return {"context": "", "sources": []}

        confident = _filter_by_confidence(results)
        if not confident:
            # Signal "no confident context" — caller should fall back to general LLM
            return {"context": "", "sources": []}

        context = "\n\n---\n\n".join([doc["text"] for doc in confident])
        seen = set()
        unique_sources = []
        for doc in confident:
            f = doc.get("file", "")
            if f not in seen:
                seen.add(f)
                unique_sources.append({
                    "file": f, "title": doc.get("doc_title", ""),
                    "score": doc.get("score", 0), "source": doc.get("source", ""),
                })
        return {"context": context, "sources": unique_sources}

    def generate_response(self, query: str, context: str = None, domain: str = "iso_documents") -> str:
        if context is None:
            context = self.retrieve_context(query, domain=domain)

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

    def is_relevant(self, query: str, threshold: float = RAG_CONFIDENCE_THRESHOLD, domain: str = "iso_documents") -> bool:
        results = self.vector_store.search(query, top_k=1, domain=domain)
        return bool(results and results[0].get("score", 0) >= threshold)
