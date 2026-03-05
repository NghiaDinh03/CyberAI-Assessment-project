import logging
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import requests
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "cybersecurity": [
        {
            "name": "The Hacker News",
            "url": "https://feeds.feedburner.com/TheHackersNews",
            "icon": "🔓",
            "lang": "en"
        },
        {
            "name": "BleepingComputer",
            "url": "https://www.bleepingcomputer.com/feed/",
            "icon": "💻",
            "lang": "en"
        },
        {
            "name": "SecurityWeek",
            "url": "https://www.securityweek.com/feed/",
            "icon": "🛡️",
            "lang": "en"
        },
    ],
    "stocks_international": [
        {
            "name": "CNBC Markets",
            "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
            "icon": "📊",
            "lang": "en"
        },
        {
            "name": "MarketWatch",
            "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
            "icon": "📈",
            "lang": "en"
        },
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/news/rssindex",
            "icon": "💰",
            "lang": "en"
        },
    ],
    "stocks_vietnam": [
        {
            "name": "CafeF",
            "url": "https://cafef.vn/rss/trang-chu.rss",
            "icon": "🇻🇳",
            "lang": "vi"
        },
        {
            "name": "VnExpress Kinh doanh",
            "url": "https://vnexpress.net/rss/kinh-doanh.rss",
            "icon": "📰",
            "lang": "vi"
        },
        {
            "name": "VnEconomy",
            "url": "https://vneconomy.vn/chung-khoan.rss",
            "icon": "💹",
            "lang": "vi"
        },
    ]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

_cache: Dict[str, Dict] = {}
CACHE_TTL = 300


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
                    import re
                    description = re.sub(r'<[^>]+>', '', description)[:200]

                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "description": description,
                        "date": pub_date,
                        "source": source_name,
                        "icon": icon,
                        "lang": lang
                    })

            return articles

        except Exception as e:
            logger.warning(f"RSS fetch thất bại [{source_name}]: {e}")
            return []

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
            articles = NewsService._parse_rss(
                url=src["url"],
                source_name=src["name"],
                icon=src["icon"],
                lang=src["lang"],
                limit=per_source
            )
            all_articles.extend(articles)

        all_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        all_articles = all_articles[:limit]

        if category in ("cybersecurity", "stocks_international"):
            try:
                from services.translation_service import TranslationService
                en_titles = [a["title"] for a in all_articles if a.get("lang") == "en"]
                if en_titles:
                    trans_cache = TranslationService.translate_batch(en_titles, category)
                    for article in all_articles:
                        if article.get("lang") == "en":
                            vi = TranslationService.get_translation(article["title"], trans_cache)
                            if vi:
                                article["title_vi"] = vi
            except Exception as e:
                logger.warning(f"Translation failed: {e}")

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
    def get_all_categories() -> List[Dict]:
        return [
            {
                "id": "cybersecurity",
                "name": "An Ninh Mạng",
                "icon": "🛡️",
                "sources": [s["name"] for s in RSS_SOURCES["cybersecurity"]]
            },
            {
                "id": "stocks_international",
                "name": "Cổ Phiếu Quốc Tế",
                "icon": "📈",
                "sources": [s["name"] for s in RSS_SOURCES["stocks_international"]]
            },
            {
                "id": "stocks_vietnam",
                "name": "Chứng Khoán VN",
                "icon": "🇻🇳",
                "sources": [s["name"] for s in RSS_SOURCES["stocks_vietnam"]]
            },
        ]
