import re
import os


SECURITY_MODEL = os.getenv("SECURITY_MODEL_NAME", "SecurityLLM-7B-Q4_K_M.gguf")
GENERAL_MODEL = os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")

ISO_KEYWORDS = [
    "iso", "27001", "27002", "14423", "tcvn", "annex", "compliance",
    "tuân thủ", "đánh giá", "kiểm soát", "chính sách", "attt",
    "an toàn thông tin", "bảo mật", "rủi ro", "sự cố",
    "firewall", "ids", "ips", "siem", "backup", "mã hóa",
    "truy cập", "xác thực", "audit", "pentest", "vulnerability",
    "isms", "gap analysis", "điều khoản", "biện pháp",
    "hạ tầng", "mạng", "server", "thiết bị", "network"
]

_pattern = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in ISO_KEYWORDS) + r')\b',
    re.IGNORECASE
)


def route_model(message: str) -> dict:
    matches = _pattern.findall(message.lower())
    is_iso = len(matches) >= 1

    return {
        "model": SECURITY_MODEL if is_iso else GENERAL_MODEL,
        "use_rag": is_iso,
        "matched_keywords": list(set(matches)),
        "route": "security" if is_iso else "general"
    }
