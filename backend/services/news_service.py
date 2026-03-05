import logging
import re
import time
import threading
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime
import requests
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "cybersecurity": [
        {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "icon": "🔓", "lang": "en"},
        {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "icon": "💻", "lang": "en"},
        {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/", "icon": "🛡️", "lang": "en"},
    ],
    "stocks_international": [
        {"name": "CNBC Markets", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147", "icon": "📊", "lang": "en"},
        {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "icon": "📈", "lang": "en"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex", "icon": "💰", "lang": "en"},
    ],
    "stocks_vietnam": [
        {"name": "CafeF", "url": "https://cafef.vn/rss/trang-chu.rss", "icon": "🇻🇳", "lang": "vi"},
        {"name": "VnExpress Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "icon": "📰", "lang": "vi"},
        {"name": "VnEconomy", "url": "https://vneconomy.vn/chung-khoan.rss", "icon": "💹", "lang": "vi"},
    ]
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_cache: Dict[str, Dict] = {}
CACHE_TTL = 300
_translate_lock = threading.Lock()
_bg_started = False


class NewsService:
    @staticmethod
    def _parse_rss(url: str, source_name: str, icon: str, lang: str, limit: int = 10) -> List[Dict]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')[:limit]

            articles = []
            for item in items:
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                description = item.findtext('description', '').strip()
                pub_date_raw = item.findtext('pubDate', '')

                pub_date = ""
                if pub_date_raw:
                    try:
                        dt = parsedate_to_datetime(pub_date_raw)
                        pub_date = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        pub_date = pub_date_raw[:25]

                if description:
                    description = description.replace('<![CDATA[', '').replace(']]>', '')
                    description = re.sub(r'<[^>]+>', '', description)[:200]

                if title and link:
                    articles.append({
                        "title": title, "url": link, "description": description,
                        "date": pub_date, "source": source_name, "icon": icon, "lang": lang
                    })

            return articles
        except Exception as e:
            logger.warning(f"RSS fetch thất bại [{source_name}]: {e}")
            return []

    @staticmethod
    def _apply_translations(articles: List[Dict], category: str):
        try:
            from services.translation_service import TranslationService
            cache = TranslationService._load_cache(category)
            if not cache:
                return
            for article in articles:
                if article.get("lang") == "en":
                    vi = TranslationService.get_translation(article["title"], cache)
                    if vi:
                        article["title_vi"] = vi
        except Exception:
            pass

    @staticmethod
    def _bg_translate(articles: List[Dict], category: str):
        with _translate_lock:
            try:
                from services.translation_service import TranslationService
                en_titles = [a["title"] for a in articles if a.get("lang") == "en"]
                if en_titles:
                    TranslationService.translate_batch(en_titles, category)
                    logger.info(f"Background translate [{category}] xong: {len(en_titles)} titles")
            except Exception as e:
                logger.warning(f"Background translate thất bại: {e}")

    @staticmethod
    def get_news(category: str, limit: int = 15) -> Dict:
        cache_key = f"{category}_{limit}"
        now = time.time()

        if cache_key in _cache:
            cached = _cache[cache_key]
            if now - cached["timestamp"] < CACHE_TTL:
                return cached["data"]

        sources = RSS_SOURCES.get(category, [])
        if not sources:
            return {"articles": [], "error": f"Danh mục '{category}' không tồn tại"}

        all_articles = []
        per_source = max(5, limit // len(sources))
        for src in sources:
            all_articles.extend(NewsService._parse_rss(
                src["url"], src["name"], src["icon"], src["lang"], per_source
            ))

        all_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        all_articles = all_articles[:limit]

        if category in ("cybersecurity", "stocks_international"):
            NewsService._apply_translations(all_articles, category)

            has_untranslated = any(
                a.get("lang") == "en" and "title_vi" not in a for a in all_articles
            )
            if has_untranslated:
                thread = threading.Thread(
                    target=NewsService._bg_translate,
                    args=(all_articles, category),
                    daemon=True
                )
                thread.start()

        result = {
            "articles": all_articles,
            "category": category,
            "count": len(all_articles),
            "sources": [s["name"] for s in sources],
            "cached_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y")
        }

        _cache[cache_key] = {"data": result, "timestamp": now}
        return result

    @staticmethod
    def search_news(query: str, limit: int = 20) -> Dict:
        query_lower = query.lower()
        results = []

        for category in RSS_SOURCES:
            news = NewsService.get_news(category, limit=30)
            for article in news.get("articles", []):
                title = article.get("title", "").lower()
                title_vi = article.get("title_vi", "").lower()
                desc = article.get("description", "").lower()
                source = article.get("source", "").lower()

                if (query_lower in title or query_lower in title_vi
                        or query_lower in desc or query_lower in source):
                    article_copy = dict(article)
                    article_copy["category"] = category
                    results.append(article_copy)

        results = results[:limit]
        return {
            "articles": results,
            "query": query,
            "count": len(results)
        }

    @staticmethod
    def get_all_categories() -> List[Dict]:
        return [
            {"id": "cybersecurity", "name": "An Ninh Mạng", "icon": "🛡️",
             "sources": [s["name"] for s in RSS_SOURCES["cybersecurity"]]},
            {"id": "stocks_international", "name": "Cổ Phiếu Quốc Tế", "icon": "📈",
             "sources": [s["name"] for s in RSS_SOURCES["stocks_international"]]},
            {"id": "stocks_vietnam", "name": "Chứng Khoán VN", "icon": "🇻🇳",
             "sources": [s["name"] for s in RSS_SOURCES["stocks_vietnam"]]},
        ]


def _auto_translate_worker():
    time.sleep(30)
    while True:
        for cat in ("cybersecurity", "stocks_international"):
            try:
                news = NewsService.get_news(cat, limit=20)
                en_titles = [a["title"] for a in news.get("articles", []) if a.get("lang") == "en"]
                if en_titles:
                    from services.translation_service import TranslationService
                    TranslationService.translate_batch(en_titles, cat)
                    logger.info(f"Auto-translate [{cat}] xong: {len(en_titles)} titles")
            except Exception as e:
                logger.warning(f"Auto-translate [{cat}] lỗi: {e}")
            time.sleep(10)
        time.sleep(43200)


def start_bg_worker():
    global _bg_started
    if not _bg_started:
        _bg_started = True
        t = threading.Thread(target=_auto_translate_worker, daemon=True)
        t.start()
        logger.info("Background translation worker started (12h interval)")
