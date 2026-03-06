import logging
import re
import time
import threading
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime
import requests
import queue
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
        {"name": "CafeF", "url": "https://cafef.vn/rss/trang-chu.rss", "icon": "☕", "lang": "vi"},
        {"name": "VnExpress Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "icon": "📰", "lang": "vi"},
        {"name": "VnEconomy", "url": "https://vneconomy.vn/chung-khoan.rss", "icon": "💹", "lang": "vi"},
    ]
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_cache: Dict[str, Dict] = {}
CACHE_TTL = 300
_bg_started = False
_translation_queue = queue.Queue()
_llama_queue = queue.Queue()
_current_status = "Đang rảnh"
_status_lock = threading.Lock()

def set_ai_status(status: str):
    global _current_status
    with _status_lock:
        _current_status = status
        if status != "Đang rảnh":
            logger.info(f"[AI MONITOR] {status}")

def get_ai_status():
    with _status_lock:
        return _current_status


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
    def _translation_worker():
        """Worker xử lý ưu tiên việc dịch Title bằng VinAI (nhẹ và nhanh)"""
        while True:
            try:
                task = _translation_queue.get()
                if task is None:
                    _translation_queue.task_done()
                    break
                category = task.get("category")
                articles = task.get("articles")
                from services.translation_service import TranslationService
                
                en_titles = [a["title"] for a in articles if a.get("lang") == "en" and "title_vi" not in a]
                if en_titles:
                    TranslationService.translate_batch(en_titles, category)
                
                # Cập nhật title_vi vào list articles ngay sau khi dịch
                NewsService._apply_translations(articles, category)
                _translation_queue.task_done()
            except Exception as e:
                logger.error(f"Translation Worker error: {e}")
                _translation_queue.task_done()
                time.sleep(2)

    @staticmethod
    def _llama_worker():
        """Worker xử lý tuần tự Tagging & Summarization bằng LocalAI (tránh quá tải)"""
        while True:
            try:
                task = _llama_queue.get()
                if task is None:
                    _llama_queue.task_done()
                    break
                
                category = task.get("category")
                articles = task.get("articles")
                
                # 1. Cập nhật lại bản dịch mới nhất trước khi xử lý (đề phòng translation worker vừa chạy xong)
                NewsService._apply_translations(articles, category)
                

                import httpx
                import os
                LLM_API_URL = os.getenv("LLM_API_URL", "http://phobert-localai:8080/v1")
                
                untagged_articles = [a for a in articles if "tag" not in a]
                for idx, a in enumerate(untagged_articles):
                    check_title = a.get("title_vi") or a.get("title")
                    set_ai_status(f"AI đang phân loại tin ({idx+1}/{len(untagged_articles)}): {check_title[:40]}...")
                    try:
                        prompt = (
                            "Hãy gán đúng 1 từ khóa (tag) ngắn gọn nhất (1-2 từ) miêu tả thể loại tin tức. "
                            "Ví dụ: 'Thị trường', 'Chiến sự', 'Lỗ hổng', 'Doanh nghiệp', 'Công nghệ', 'Chứng khoán'. "
                            "Chỉ được in ra đúng 1 từ khóa đó, không giải thích gì thêm."
                            f"\n\nTiêu đề: {check_title}"
                        )
                        payload = {
                            "model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                            "max_tokens": 10
                        }
                        res = httpx.post(f"{LLM_API_URL}/chat/completions", json=payload, timeout=30.0)
                        res.raise_for_status()
                        tag_ai = res.json()["choices"][0]["message"]["content"].strip()
                        a["tag"] = tag_ai.replace(".", "").replace('"', "").replace("'", "")
                    except Exception:
                        a["tag"] = "Tin tức"

                # 3. Tóm tắt & Voice (Edge-TTS) - Chuyên mục nặng nhất
                from services.summary_service import SummaryService
                # Chỉ xử lý 3 bản tin mới nhất chưa có audio để tối ưu tài nguyên
                to_process = [a for a in articles if not a.get("audio_cached")][:3]
                for idx, a in enumerate(to_process):
                    title = a.get("title_vi") or a.get("title")
                    set_ai_status(f"AI tóm tắt & đọc bài ({idx+1}/{len(to_process)}): {title[:40]}...")
                    SummaryService.process_article(a["url"], a.get("lang", "en"), title)
                
                set_ai_status("Đang rảnh")
                _llama_queue.task_done()
            except Exception as e:
                logger.error(f"Llama Worker error: {e}")
                set_ai_status("Đang rảnh")
                _llama_queue.task_done()
                time.sleep(5)

    @staticmethod
    def get_news(category: str, limit: int = 15) -> Dict:
        # Khởi động worker chung nếu chưa chạy (gọi function module level)
        start_bg_worker()
        
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

        if category in ("cybersecurity", "stocks_international", "stocks_vietnam"):
            NewsService._apply_translations(all_articles, category)
            
            # Check audio status & cached data
            from services.summary_service import SummaryService
            needs_processing = False
            for article in all_articles:
                cached_sum = SummaryService._get_cache(article["url"])
                if cached_sum and "audio_url" in cached_sum:
                    article["audio_cached"] = True
                    article["summary_text"] = cached_sum.get("summary_vi", "")
                else:
                    article["audio_cached"] = False
                    needs_processing = True

            has_untranslated = any(a.get("lang") == "en" and "title_vi" not in a for a in all_articles)
            has_untagged = any("tag" not in a for a in all_articles)
            
            # Gửi task dịch title sang luồng Translation riêng biệt (nhanh)
            if has_untranslated:
                _translation_queue.put({"category": category, "articles": all_articles})
            
            # Gửi task xử lý Llama sang luồng Llama (chậm)
            if has_untagged or needs_processing:
                _llama_queue.put({"category": category, "articles": all_articles})

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
        results = []
        query_lower = query.lower()

        # Bước 1: Tìm trong RSS cục bộ trước
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

        # Bước 2: Bổ sung từ DuckDuckGo nếu kết quả còn mỏng
        remaining_limit = limit - len(results)
        if remaining_limit > 0:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    ddgs_results = []
                    for item in ddgs.news(query, max_results=remaining_limit):
                        title = item.get("title", "")
                        url = item.get("url", "")
                        body = item.get("body", "")[:200]
                        date_raw = item.get("date", "")[:25]
                        source = item.get("source", "Web")
                        
                        ddgs_results.append({
                            "title": title, "url": url, "description": body,
                            "date": date_raw, "source": source, "icon": "🌐",
                            "lang": "en", "category": "cybersecurity"
                        })
                
                if ddgs_results:
                    NewsService._apply_translations(ddgs_results, "cybersecurity")
                    en_articles = [a for a in ddgs_results if a.get("lang") == "en" and "title_vi" not in a]
                    if en_articles:
                        threading.Thread(
                            target=NewsService._bg_translate,
                            args=(ddgs_results, "cybersecurity"),
                            daemon=True
                        ).start()
                    results.extend(ddgs_results)
            except Exception as e:
                logger.warning(f"DuckDuckGo search error: {e}")

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
            {"id": "stocks_vietnam", "name": "Chứng Khoán VN", "icon": "💹",
             "sources": [s["name"] for s in RSS_SOURCES["stocks_vietnam"]]},
        ]


def _auto_translate_worker():
    time.sleep(30)
    while True:
        # Ưu tiên An ninh mạng và Chứng khoán VN trước
        for cat in ("cybersecurity", "stocks_vietnam", "stocks_international"):
            try:
                news = NewsService.get_news(cat, limit=20)
                # Note: get_news automatically triggers background process if anything is missing
                logger.info(f"Auto-translate [{cat}] triggered")
            except Exception as e:
                logger.warning(f"Auto-translate [{cat}] lỗi: {e}")
            time.sleep(10)
            
        # Dọn dẹp cache thừa sau 1 vòng lặp (2h)
        try:
            from services.summary_service import CACHE_DIR, AUDIO_DIR, SummaryService
            import os
            # Gom tất cả url đang hiển thị ở 3 categories (top 20)
            active_hashes = set()
            for cat in ("cybersecurity", "stocks_international", "stocks_vietnam"):
                recent = NewsService.get_news(cat, limit=20)
                for a in recent.get("articles", []):
                    active_hashes.add(SummaryService._generate_hash(a["url"]))
            
            # Quét và xoá file json, mp3 không nằm trong active_hashes
            if os.path.exists(CACHE_DIR):
                for f in os.listdir(CACHE_DIR):
                    if f.endswith(".json"):
                        fname = f.replace(".json", "")
                        if fname not in active_hashes:
                            os.remove(os.path.join(CACHE_DIR, f))
            
            if os.path.exists(AUDIO_DIR):
                for f in os.listdir(AUDIO_DIR):
                    if f.endswith(".mp3"):
                        fname = f.replace(".mp3", "")
                        if fname not in active_hashes:
                            os.remove(os.path.join(AUDIO_DIR, f))
            logger.info("Cleared old audio cache")
        except Exception as e:
            logger.warning(f"Failed to clear old cache: {e}")
            
        time.sleep(7200)


def start_bg_worker():
    global _bg_started
    if not _bg_started:
        _bg_started = True
        
        # Worker Dịch thuật (VinAI) - Mượt, chạy độc lập
        t_trans = threading.Thread(target=NewsService._translation_worker, daemon=True)
        t_trans.start()
        
        # Worker Llama - Tuần tự để tránh nghẽn CPU
        t_llama = threading.Thread(target=NewsService._llama_worker, daemon=True)
        t_llama.start()
        
        # Worker tự động quét RSS định kỳ
        t_cron = threading.Thread(target=_auto_translate_worker, daemon=True)
        t_cron.start()
        logger.info("Parallel Workers (Translation & Llama) & Cron started")
