"""Smart Model Router — Hybrid intent classification (semantic + keyword fallback)."""

import re
import logging
from typing import Dict

from core.config import settings

logger = logging.getLogger(__name__)

SECURITY_MODEL = settings.SECURITY_MODEL_NAME
GENERAL_MODEL = settings.MODEL_NAME


def get_security_model() -> str:
    """Return the configured SecurityLM model id.

    Thin accessor so callers (e.g. ``summarize_evidence``, ``chat_service``)
    don't reach into module-level constants. The constant ``SECURITY_MODEL``
    is preserved for backward compatibility.
    """
    return SECURITY_MODEL


def resolve_local_model(preferred: str, fallback: str | None = None) -> str:
    """Return a local model id, honoring the RAM-guard heavy-local disable flag.

    If the caller asked for the heavy 27B path (e.g. ``gemma3:27b``) and the
    RAM guard tripped at startup, fall back to ``fallback`` (or ``GENERAL_MODEL``).

    TODO: wire this into any future route that explicitly selects gemma3:27b.
    Today the 27B model is pulled by the Ollama container entrypoint but is
    not hard-coded in a router branch; this helper exists so heavy-model
    callers can consult ``HEAVY_LOCAL_DISABLED`` without duplicating logic.
    """
    try:
        from services.ram_guard import HEAVY_LOCAL_DISABLED
    except Exception:
        HEAVY_LOCAL_DISABLED = False  # type: ignore[assignment]

    if HEAVY_LOCAL_DISABLED and "27b" in (preferred or "").lower():
        chosen = fallback or GENERAL_MODEL
        logger.warning(
            "resolve_local_model: heavy local disabled by RAM guard — "
            "falling back from %s to %s",
            preferred, chosen,
        )
        return chosen
    return preferred

INTENT_TEMPLATES = {
    "security": [
        # Vietnamese
        "đánh giá rủi ro bảo mật", "cấu hình firewall", "iso 27001",
        "kiểm toán an toàn thông tin", "chính sách bảo mật",
        "tcvn 11930", "pentest", "vulnerability assessment",
        "annex a controls", "gap analysis", "isms",
        "mã hóa dữ liệu", "kiểm soát truy cập", "siem ids ips",
        "chứng nhận iso", "nghị định 13 bảo vệ dữ liệu cá nhân",
        "luật an ninh mạng", "biện pháp kiểm soát kỹ thuật",
        "kiểm soát", "tuân thủ", "kiểm toán", "đánh giá rủi ro",
        "hệ thống quản lý", "an toàn thông tin", "chính sách bảo mật",
        "lỗ hổng bảo mật", "vá lỗi bảo mật", "tường lửa", "mạng bảo mật",
        # English
        "risk assessment", "access control", "security policy",
        "information security management", "control objective",
        "annex a", "iso 27002", "nist", "encryption", "vulnerability",
        "patch management", "network security", "firewall configuration",
        "security audit", "compliance audit", "isms implementation",
        "security controls", "data protection", "incident response",
    ],
    "search": [
        # Vietnamese
        "tin tức mới nhất", "tìm kiếm thông tin", "cập nhật gần đây",
        "giá cổ phiếu hôm nay", "xu hướng thị trường",
        "sự kiện an ninh mạng mới", "so sánh sản phẩm",
        "tình hình chứng khoán", "diễn biến thị trường",
        "cho tôi biết về", "thông tin mới về",
        # English
        "latest news", "recent updates", "current events",
        "stock price today", "market trend", "compare products",
        "what is happening", "tell me about recent",
    ],
    "general": [
        # Vietnamese
        "xin chào", "giúp tôi", "cảm ơn",
        "giải thích khái niệm", "hướng dẫn sử dụng",
        "bạn là ai", "chatbot có thể làm gì",
        "chào", "giúp tôi với", "bạn có thể làm gì",
        "tôi cần hỗ trợ", "hỗ trợ tôi",
        # English
        "hello", "hi there", "help me", "what can you do",
        "who are you", "how does this work", "getting started",
        "thank you", "thanks", "explain to me",
    ],
}

ISO_KEYWORDS = [
    # Standards identifiers — language-neutral
    "iso 27001", "iso 27002", "iso27001", "iso27002",
    "tcvn 14423", "tcvn14423", "tcvn 11930", "tcvn11930", "cấp độ",
    "annex a", "isms", "gap analysis", "nist", "pci dss", "soc 2", "gdpr",
    # Vietnamese compliance terms
    "compliance", "tuân thủ", "kiểm toán", "đánh giá iso",
    "điều khoản iso", "biện pháp kiểm soát", "kiểm soát",
    "chứng chỉ iso", "chứng nhận iso", "an toàn thông tin", "attt",
    "nghị định 13", "bảo vệ dữ liệu cá nhân", "luật an ninh mạng",
    "hệ thống quản lý", "đánh giá rủi ro", "kiểm soát truy cập",
    "chính sách bảo mật", "mã hóa dữ liệu", "an ninh mạng",
    # English ISO/compliance terms
    "audit", "pentest", "vulnerability assessment", "risk assessment",
    "access control", "security policy", "information security",
    "data protection", "encryption", "patch management",
    "incident response", "business continuity", "disaster recovery",
    "security controls", "control objective", "compliance framework",
]

SEARCH_KEYWORDS = [
    # Vietnamese search intent
    "tìm kiếm", "tra cứu", "tìm giúp",
    "mới nhất", "gần đây", "hiện tại", "bây giờ",
    "năm 2024", "năm 2025", "năm 2026",
    "tin tức", "cập nhật", "so sánh",
    "giá cổ phiếu", "thị trường chứng khoán", "xu hướng",
    "sự kiện", "ai biết", "cho tôi biết",
    "tình hình", "diễn biến", "thông tin về", "nói cho tôi",
    # English search intent
    "search", "latest", "recent", "currently", "news",
    "compare", "trend", "event", "stock price", "market",
    "what happened", "today", "this week", "breaking",
]

ISO_STRICT_KEYWORDS = [
    # Standards / framework identifiers
    "iso", "27001", "27002", "14423", "tcvn", "isms", "annex", "nist",
    # Vietnamese strict compliance terms
    "compliance", "đánh giá rủi ro", "kiểm soát truy cập",
    "chính sách bảo mật", "kiểm toán", "kiểm soát",
    "tuân thủ", "an toàn thông tin", "hệ thống quản lý",
    "mã hóa", "lỗ hổng", "vá lỗi", "tường lửa", "mạng bảo mật",
    "nghị định 13", "luật an ninh mạng", "điều khoản", "gap analysis",
    # English strict security/compliance terms
    "firewall", "siem", "ids", "ips", "pentest", "audit",
    "encryption", "vulnerability", "patch", "risk assessment",
    "access control", "security policy", "incident response",
    "data protection", "security controls",
]

_iso_pattern = re.compile(r'(' + '|'.join(re.escape(kw) for kw in ISO_KEYWORDS) + r')', re.IGNORECASE)
_iso_strict_pattern = re.compile(r'\b(' + '|'.join(re.escape(kw) for kw in ISO_STRICT_KEYWORDS) + r')\b', re.IGNORECASE)
_search_pattern = re.compile(r'(' + '|'.join(re.escape(kw) for kw in SEARCH_KEYWORDS) + r')', re.IGNORECASE)

_intent_collection = None


def _get_intent_collection():
    global _intent_collection
    if _intent_collection is not None:
        return _intent_collection

    try:
        import chromadb
        client = chromadb.Client()
        collection = client.get_or_create_collection(name="intent_classifier", metadata={"hnsw:space": "cosine"})

        if collection.count() == 0:
            all_docs, all_ids, all_metas = [], [], []
            for intent, templates in INTENT_TEMPLATES.items():
                for i, t in enumerate(templates):
                    all_docs.append(t)
                    all_ids.append(f"{intent}_{i}")
                    all_metas.append({"intent": intent})
            collection.add(documents=all_docs, ids=all_ids, metadatas=all_metas)
            logger.info(f"Intent classifier initialized with {len(all_docs)} templates")

        _intent_collection = collection
        return collection
    except Exception as e:
        logger.warning(f"Semantic router init failed: {e}")
        return None


def _semantic_classify(message: str) -> Dict:
    collection = _get_intent_collection()
    if collection is None:
        return {"intent": None, "confidence": 0}

    try:
        results = collection.query(query_texts=[message], n_results=3)
        if not results or not results.get("metadatas"):
            return {"intent": None, "confidence": 0}

        votes = {}
        distances = results.get("distances", [[]])[0]
        metadatas = results["metadatas"][0]

        for i, meta in enumerate(metadatas):
            intent = meta.get("intent", "general")
            similarity = 1 - distances[i] if i < len(distances) else 0
            votes[intent] = votes.get(intent, 0) + similarity

        best_intent = max(votes, key=votes.get)
        best_score = votes[best_intent] / len(metadatas)
        return {"intent": best_intent, "confidence": round(best_score, 3)}
    except Exception as e:
        logger.warning(f"Semantic classification error: {e}")
        return {"intent": None, "confidence": 0}


def route_model(message: str) -> dict:
    """Hybrid routing: Semantic first → Keyword fallback."""
    msg = message.lower()

    semantic_result = _semantic_classify(message)
    semantic_intent = semantic_result["intent"]
    confidence = semantic_result["confidence"]

    iso_matches = _iso_pattern.findall(msg)
    iso_strict_matches = _iso_strict_pattern.findall(msg)
    search_matches = _search_pattern.findall(msg)

    has_iso = len(iso_matches) >= 1
    has_iso_strict = len(iso_strict_matches) >= 2
    has_search = len(search_matches) >= 1

    # High confidence semantic → use semantic result
    if confidence > 0.6 and semantic_intent:
        if semantic_intent == "security":
            route, use_rag, use_search, model = "security", True, False, SECURITY_MODEL
        elif semantic_intent == "search":
            route, use_rag, use_search, model = "search", False, True, GENERAL_MODEL
        else:
            route, use_rag, use_search, model = "general", False, False, GENERAL_MODEL
    else:
        # Keyword fallback
        if has_search and has_iso and not has_iso_strict:
            route, use_rag, use_search, model = "search", False, True, GENERAL_MODEL
        elif has_iso_strict or (has_iso and not has_search):
            route, use_rag, use_search, model = "security", True, False, SECURITY_MODEL
        elif has_search:
            route, use_rag, use_search, model = "search", False, True, GENERAL_MODEL
        else:
            route, use_rag, use_search, model = "general", False, False, GENERAL_MODEL

    return {
        "model": model, "use_rag": use_rag, "use_search": use_search,
        "matched_keywords": list(set(iso_matches + search_matches)),
        "route": route, "confidence": confidence,
        "classification_method": "semantic" if confidence > 0.6 else "keyword",
    }
