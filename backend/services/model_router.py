import re
import os


SECURITY_MODEL = os.getenv("SECURITY_MODEL_NAME", "SecurityLLM-7B-Q4_K_M.gguf")
GENERAL_MODEL = os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")

ISO_KEYWORDS = [
    "iso 27001", "iso 27002", "iso27001", "iso27002",
    "tcvn 14423", "tcvn14423",
    "annex a", "compliance", "tuân thủ",
    "isms", "gap analysis",
    "điều khoản iso", "biện pháp kiểm soát",
    "đánh giá iso", "kiểm toán",
    "audit", "pentest", "vulnerability assessment",
    "chứng chỉ iso", "chứng nhận iso",
    "an toàn thông tin", "attt",
]

SEARCH_KEYWORDS = [
    "tìm kiếm", "tra cứu", "search", "tìm giúp",
    "mới nhất", "latest", "gần đây", "recent",
    "hiện tại", "currently", "bây giờ",
    "năm 2024", "năm 2025", "năm 2026",
    "tin tức", "news", "cập nhật",
    "so sánh", "compare",
    "giá cổ phiếu", "thị trường chứng khoán",
    "xu hướng", "trend",
    "sự kiện", "event",
    "ai biết", "cho tôi biết",
    "tình hình", "diễn biến",
    "thông tin về", "nói cho tôi",
]

ISO_STRICT_KEYWORDS = [
    "iso", "27001", "27002", "14423", "tcvn",
    "isms", "annex", "compliance",
    "đánh giá rủi ro", "kiểm soát truy cập",
    "chính sách bảo mật", "firewall", "siem",
    "ids", "ips", "pentest", "audit",
    "gap analysis", "điều khoản"
]

_iso_pattern = re.compile(
    r'(' + '|'.join(re.escape(kw) for kw in ISO_KEYWORDS) + r')',
    re.IGNORECASE
)

_iso_strict_pattern = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in ISO_STRICT_KEYWORDS) + r')\b',
    re.IGNORECASE
)

_search_pattern = re.compile(
    r'(' + '|'.join(re.escape(kw) for kw in SEARCH_KEYWORDS) + r')',
    re.IGNORECASE
)


def route_model(message: str) -> dict:
    msg = message.lower()

    iso_matches = _iso_pattern.findall(msg)
    iso_strict_matches = _iso_strict_pattern.findall(msg)
    search_matches = _search_pattern.findall(msg)

    has_iso = len(iso_matches) >= 1
    has_iso_strict = len(iso_strict_matches) >= 2
    has_search = len(search_matches) >= 1

    if has_search and has_iso and not has_iso_strict:
        use_rag = False
        use_search = True
        route = "search"
        model = GENERAL_MODEL
    elif has_iso_strict or (has_iso and not has_search):
        use_rag = True
        use_search = False
        route = "security"
        model = SECURITY_MODEL
    elif has_search:
        use_rag = False
        use_search = True
        route = "search"
        model = GENERAL_MODEL
    else:
        use_rag = False
        use_search = False
        route = "general"
        model = GENERAL_MODEL

    return {
        "model": model,
        "use_rag": use_rag,
        "use_search": use_search,
        "matched_keywords": list(set(iso_matches + search_matches)),
        "route": route
    }
