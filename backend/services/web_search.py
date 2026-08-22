import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class WebSearch:
    @staticmethod
    def search(query: str, max_results: int = 5, retries: int = 1) -> List[Dict[str, str]]:
        if not query or not query.strip():
            return []

        # 1. Bảo vệ: Nếu query là log kỹ thuật, tuyệt đối không tìm kiếm web
        try:
            from services.model_router import is_log_analysis_query
            if is_log_analysis_query(query):
                logger.info("[WebSearch] Log payload detected -> skipping web search to protect data and avoid delay.")
                return []
        except Exception:
            pass

        # 2. Tiền xử lý query: loại bỏ ký tự lạ, rút gọn tối đa 150 ký tự
        cleaned_query = " ".join(query.strip().split())[:150]
        if len(cleaned_query) < 3:
            return []

        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.error("ddgs chưa được cài đặt: pip install ddgs")
                return []

        for attempt in range(retries + 1):
            try:
                with DDGS(headers={"User-Agent": USER_AGENT}, timeout=5) as ddgs:
                    raw = list(ddgs.text(cleaned_query, max_results=max_results, region="vn-vi"))

                if raw:
                    results = []
                    for item in raw:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", "")
                        })
                    return results

                if attempt < retries:
                    time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Web search attempt {attempt + 1} thất bại: {e}")
                if attempt < retries:
                    time.sleep(1)

        logger.info("[WebSearch] Không có kết quả tìm kiếm web hoặc search engine bận.")
        return []

    @staticmethod
    def format_context(results: List[Dict[str, str]]) -> str:
        if not results:
            return ""

        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"[{i}] {r['title']}\n"
                f"URL: {r['url']}\n"
                f"{r['snippet']}"
            )
        return "\n\n---\n\n".join(parts)
