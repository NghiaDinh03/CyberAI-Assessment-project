import logging
import re
import time
from typing import List, Dict
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Common conversational filler phrases in Vietnamese queries that degrade search results
_FILLERS_REGEX = re.compile(
    r"\b(hôm nay có gì mới và hot hit|có gì mới và hot hit|có gì hot|hot hit|cho tôi biết|"
    r"tìm kiếm giúp|tìm kiếm|tra cứu|hãy cho biết|cho mình hỏi|bạn ơi|mới nhất hôm nay|hôm nay có gì mới)\b",
    re.IGNORECASE
)


class WebSearch:
    @staticmethod
    def _sanitize_query(raw_query: str) -> str:
        """Strip conversational filler words while preserving key security terms."""
        cleaned = _FILLERS_REGEX.sub("", raw_query)
        cleaned = re.sub(r"[?!.,:;]+$", "", cleaned)
        cleaned = " ".join(cleaned.split())
        # If sanitization stripped too much, fallback to original stripped query
        if len(cleaned) < 4:
            cleaned = " ".join(raw_query.strip().split())
        return cleaned[:150]

    @staticmethod
    def _search_searxng(query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Query the on-premise SearXNG meta-search engine via JSON API with fail-fast timeout."""
        searxng_base = getattr(settings, "SEARXNG_URL", "http://searxng:8080").rstrip("/")
        endpoints_to_try = [f"{searxng_base}/search"]
        if "searxng:8080" in searxng_base:
            endpoints_to_try.append("http://localhost:8888/search")

        for endpoint in endpoints_to_try:
            try:
                params = {
                    "q": query,
                    "format": "json",
                    "categories": "general",
                    "language": "vi",
                }
                with httpx.Client(timeout=3.5) as client:
                    resp = client.get(endpoint, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        results: List[Dict[str, str]] = []

                        # Include infobox summary if available (e.g. Wikipedia infobox)
                        infoboxes = data.get("infoboxes", [])
                        for info in infoboxes:
                            urls = info.get("urls", [])
                            first_url = urls[0].get("url", "") if urls else info.get("id", "")
                            title = info.get("infobox", "") or "Tổng quan"
                            content = info.get("content", "")
                            if content and first_url:
                                results.append({
                                    "title": f"Wikipedia: {title}",
                                    "url": first_url,
                                    "snippet": content[:350]
                                })

                        raw_results = data.get("results", [])
                        for item in raw_results:
                            if len(results) >= max_results:
                                break
                            title = item.get("title", "").strip()
                            url = item.get("url", "").strip()
                            snippet = (item.get("content", "") or item.get("snippet", "")).strip()
                            if title and url and not any(r["url"] == url for r in results):
                                results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet
                                })

                        if results:
                            logger.info(f"[WebSearch] SearXNG returned {len(results)} results from {endpoint}.")
                            return results[:max_results]
            except Exception as e:
                logger.debug(f"[WebSearch] SearXNG endpoint {endpoint} failed: {e}")
        return []

    @classmethod
    def _search_wikipedia_fallback(cls, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Fallback to direct Vietnamese Wikipedia API if meta-search and ddgs fail."""
        # Wikipedia is an encyclopedia, NOT a live news service. Skip Wikipedia fallback for news/current event queries.
        if re.search(r'\b(tin tức|hôm nay|mới nhất|thời sự|vừa qua|tuần này|sự kiện|năm nay|tháng này)\b', query, re.IGNORECASE):
            logger.info("[WebSearch] News/event query detected -> skipping Wikipedia fallback to avoid irrelevant matches.")
            return []

        try:
            url = "https://vi.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results * 2,
            }
            headers = {"User-Agent": USER_AGENT}
            with httpx.Client(timeout=3.0) as client:
                res = client.get(url, params=params, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    search_items = data.get("query", {}).get("search", [])
                    results = []
                    security_keywords = (
                        "an ninh", "bảo mật", "an toàn", "mạng", "luật", "tấn công", "mã độc",
                        "iso", "tcvn", "it", "cntt", "cyber", "security", "hacker", "lỗ hổng",
                        "dữ liệu", "quy định", "chính sách", "phần mềm", "hệ thống", "thông tin"
                    )
                    is_security_query = any(k in query.lower() for k in security_keywords)

                    for item in search_items:
                        title = item.get("title", "")
                        page_id = item.get("pageid", "")
                        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                        if not (title and page_id):
                            continue

                        if is_security_query:
                            t_lower = title.lower()
                            s_lower = snippet.lower()
                            # Exclude known false-positive biographical / geographical matches that just share "ninh" or "an ninh"
                            if any(t_lower.startswith(p) for p in ("nguyễn an ninh", "quảng ninh", "tây ninh", "bắc ninh", "ninh bình", "ninh thuận")):
                                continue
                            if not any(k in t_lower or k in s_lower for k in security_keywords):
                                continue

                        results.append({
                            "title": f"Wikipedia: {title}",
                            "url": f"https://vi.wikipedia.org/?curid={page_id}",
                            "snippet": snippet
                        })
                        if len(results) >= max_results:
                            break

                    if results:
                        logger.info(f"[WebSearch] Wikipedia fallback returned {len(results)} results.")
                        return results
        except Exception as e:
            logger.debug(f"[WebSearch] Wikipedia fallback failed: {e}")
        return []

    @classmethod
    def search(cls, query: str, max_results: int = 5, retries: int = 1) -> List[Dict[str, str]]:
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

        # 2. Tiền xử lý query: làm sạch từ ngữ cảm thán
        cleaned_query = cls._sanitize_query(query)
        if len(cleaned_query) < 3:
            return []

        # 3. Ưu tiên 1: Gọi SearXNG (On-Premise Private Meta-Search)
        try:
            searx_results = cls._search_searxng(cleaned_query, max_results=max_results)
            if searx_results:
                return searx_results
        except Exception as e:
            logger.warning(f"[WebSearch] SearXNG search error: {e}")

        logger.info("[WebSearch] SearXNG không khả dụng hoặc chưa có kết quả -> Fallback sang thư viện ddgs...")

        # 4. Fallback 2: Thư viện ddgs
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.warning("ddgs chưa được cài đặt: pip install ddgs")
                DDGS = None

        if DDGS is not None:
            for attempt in range(retries + 1):
                try:
                    with DDGS(headers={"User-Agent": USER_AGENT}, timeout=4) as ddgs:
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

        # 5. Fallback 3: Wikipedia direct query
        try:
            wiki_results = cls._search_wikipedia_fallback(cleaned_query, max_results=3)
            if wiki_results:
                return wiki_results
        except Exception as e:
            logger.warning(f"[WebSearch] Wikipedia fallback error: {e}")

        logger.info("[WebSearch] Không có kết quả tìm kiếm web từ cả SearXNG và fallbacks.")
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
                f"Nội dung tóm tắt: {r['snippet']}"
            )
        return "\n\n---\n\n".join(parts)
