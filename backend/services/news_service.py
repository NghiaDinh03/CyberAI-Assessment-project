"""News Service — RSS aggregation with Vietnamese translation & article summarization."""

import logging
import re
import time
import threading
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime, timedelta
import requests
import queue
import json
import os
import hashlib
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "cybersecurity": [
        {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "icon": "🔓", "lang": "en"},
        {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "icon": "💻", "lang": "en"},
        {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/", "icon": "🛡️", "lang": "en"},
    ],
    "stocks_international": [
        {"name": "CNBC Markets", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147", "icon": "📊", "lang": "en"},
        {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "icon": "📈", "lang": "en"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex", "icon": "💰", "lang": "en"},
    ],
    "stocks_vietnam": [
        {"name": "Znews Kinh doanh", "url": "https://znews.vn/rss/kinh-doanh-tai-chinh.rss", "icon": "💹", "lang": "vi"},
        {"name": "VnExpress Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "icon": "📰", "lang": "vi"},
        {"name": "VnEconomy", "url": "https://vneconomy.vn/chung-khoan.rss", "icon": "📊", "lang": "vi"},
    ],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_cache: Dict[str, Dict] = {}
CACHE_TTL = 15
_bg_started = False
_translation_queue = queue.Queue()
_llama_queue = queue.Queue()
_translation_queue_cats = set()
_llama_queue_cats = set()
_current_status = "Đang rảnh"
_status_lock = threading.Lock()

HISTORY_FILE = "/data/articles_history.json"
_history_lock = threading.Lock()


def set_ai_status(status: str):
    global _current_status
    with _status_lock:
        _current_status = status
        if status != "Đang rảnh":
            logger.info(f"[AI Status] {status}")


def get_ai_status():
    with _status_lock:
        return _current_status


class NewsService:
    @staticmethod
    def _update_history(articles: List[Dict]):
        with _history_lock:
            history = NewsService.get_history_no_lock()
            history_dict = {a["url"]: a for a in history}
            now = datetime.now()

            for a in articles:
                url = a["url"]

                if a.get("lang") == "en" and not a.get("title_vi"):
                    try:
                        from services.translation_service import TranslationService
                        cache = TranslationService._load_cache(a.get("category", "cybersecurity"))
                        vi = TranslationService.get_translation(a["title"], cache)
                        if vi:
                            a["title_vi"] = vi
                    except Exception as e:
                        logger.warning(f"[History] Translation lookup failed for '{a.get('title','')[:40]}': {e}")

                if url not in history_dict:
                    a_copy = a.copy()
                    a_copy["added_at"] = now.isoformat()
                    history_dict[url] = a_copy
                else:
                    curr = history_dict[url]
                    for key in ["title_vi", "audio_cached", "summary_text", "category", "lang"]:
                        if key in a:
                            curr[key] = a[key]
                    if not curr.get("title_vi") and a.get("lang") == "en":
                        try:
                            from services.translation_service import TranslationService
                            cache = TranslationService._load_cache(a.get("category", "cybersecurity"))
                            vi = TranslationService.get_translation(a.get("title", ""), cache)
                            if vi:
                                curr["title_vi"] = vi
                        except Exception as e:
                            logger.warning(f"[History] Translation fallback failed: {e}")

            cutoff = now - timedelta(days=7)
            new_history = []
            for a in history_dict.values():
                added = a.get("added_at")
                if added:
                    try:
                        if datetime.fromisoformat(added) >= cutoff:
                            new_history.append(a)
                    except Exception:
                        new_history.append(a)
                else:
                    a["added_at"] = now.isoformat()
                    new_history.append(a)

            new_history.sort(key=lambda x: x.get("added_at", ""), reverse=True)
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"[History] Failed to save to {HISTORY_FILE}: {e}")

    @staticmethod
    def get_history_no_lock() -> List[Dict]:
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[History] Failed to read {HISTORY_FILE}: {e}")
            return []

    @staticmethod
    def get_history(category: str = None) -> List[Dict]:
        with _history_lock:
            hist = NewsService.get_history_no_lock()
        if category and category != "all":
            hist = [a for a in hist if a.get("category") == category]
        for item in hist:
            if "hash" not in item and "url" in item:
                item["hash"] = hashlib.md5(item["url"].encode()).hexdigest()
        return hist

    @staticmethod
    def reprocess_article(url: str) -> Dict:
        hist = NewsService.get_history()
        article = next((a for a in hist if a["url"] == url), None)
        if not article:
            return {"error": "Không tìm thấy bài báo trong lịch sử."}

        from services.summary_service import SummaryService, CACHE_DIR, AUDIO_DIR
        url_hash = SummaryService._generate_hash(url)

        for path in [os.path.join(CACHE_DIR, f"{url_hash}.json"),
                     os.path.join(AUDIO_DIR, f"{url_hash}.mp3")]:
            try:
                os.remove(path)
                logger.info(f"[Reprocess] Deleted cache: {path}")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"[Reprocess] Could not delete {path}: {e}")

        article.pop("title_vi", None)
        article.pop("summary_text", None)
        article.pop("audio_cached", None)
        NewsService._update_history([article])

        cat = article.get("category", "cybersecurity")
        keys_to_delete = [k for k in _cache.keys() if k.startswith(f"{cat}_")]
        for k in keys_to_delete:
            del _cache[k]

        _translation_queue.put({"category": cat, "articles": [article]})
        _translation_queue_cats.add(cat)
        _llama_queue.put({"category": cat, "articles": [article]})
        _llama_queue_cats.add(cat)

        logger.info(f"[Reprocess] Article queued for reprocessing: {url}")
        return {"success": True, "message": "Đã xóa bản dịch cũ và đưa vào hàng chờ xử lý lại."}

    @staticmethod
    def _parse_rss(url: str, source_name: str, icon: str, lang: str, limit: int = 10) -> List[Dict]:
        logger.debug(f"[RSS] Fetching {source_name}: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:limit]

            articles = []
            for item in items:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()
                pub_date_raw = item.findtext("pubDate", "")

                pub_date = ""
                if pub_date_raw:
                    try:
                        dt = parsedate_to_datetime(pub_date_raw)
                        pub_date = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        pub_date = pub_date_raw[:25]

                if description:
                    description = description.replace("<![CDATA[", "").replace("]]>", "")
                    description = re.sub(r"<[^>]+>", "", description)[:200]

                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "description": description,
                        "date": pub_date,
                        "source": source_name,
                        "icon": icon,
                        "lang": lang,
                    })

            logger.debug(f"[RSS] {source_name}: fetched {len(articles)} articles")
            return articles
        except Exception as e:
            logger.warning(f"[RSS] Fetch failed [{source_name}] {url}: {e}")
            return []

    @staticmethod
    def _apply_translations(articles: List[Dict], category: str):
        try:
            from services.translation_service import TranslationService
            cache = TranslationService._load_cache(category)
            if not cache:
                return
            applied = 0
            for article in articles:
                if article.get("lang") == "en" and not article.get("title_vi"):
                    vi = TranslationService.get_translation(article["title"], cache)
                    if vi:
                        article["title_vi"] = vi
                        applied += 1
            if applied:
                logger.debug(f"[Translation] Applied {applied} cached translations for category={category}")
        except Exception as e:
            logger.warning(f"[Translation] _apply_translations error: {e}")

    @staticmethod
    def _translation_worker():
        """Background worker: translates EN article titles via VinAI."""
        while True:
            try:
                task = _translation_queue.get()
                if task is None:
                    _translation_queue.task_done()
                    break

                category = task.get("category")
                articles = task.get("articles", [])

                logger.info(f"[TranslationWorker] Processing {len(articles)} articles for category={category}")

                from services.translation_service import TranslationService
                en_titles = [a["title"] for a in articles if a.get("lang") == "en" and "title_vi" not in a]

                if en_titles:
                    logger.info(f"[TranslationWorker] Translating {len(en_titles)} EN titles")
                    TranslationService.translate_batch(en_titles, category)
                    logger.info(f"[TranslationWorker] Translation complete for {len(en_titles)} titles")

                NewsService._apply_translations(articles, category)
                NewsService._update_history(articles)
                _translation_queue_cats.discard(category)
                _translation_queue.task_done()

            except Exception as e:
                logger.error(f"[TranslationWorker] Error: {e}")
                if "category" in locals():
                    _translation_queue_cats.discard(category)
                _translation_queue.task_done()
                time.sleep(2)

    @staticmethod
    def _llama_worker():
        """Background worker: scrapes articles, translates via Open Claude, generates TTS audio."""
        while True:
            try:
                task = _llama_queue.get()
                if task is None:
                    _llama_queue.task_done()
                    break

                category = task.get("category")
                articles = task.get("articles", [])

                NewsService._apply_translations(articles, category)

                from services.summary_service import SummaryService

                to_process = [
                    a for a in articles
                    if not a.get("audio_cached") and a.get("audio_cached") != "error"
                ]
                logger.info(f"[LlamaWorker] category={category}, articles_to_process={len(to_process)}")

                for idx, a in enumerate(to_process):
                    title = a.get("title_vi") or a.get("title")
                    url = a.get("url", "")
                    set_ai_status(f"AI tóm tắt & dịch bài ({idx+1}/{len(to_process)}): {title[:40]}...")

                    logger.info(f"[LlamaWorker] Step 1 — clearing retryable cache for: {url}")
                    SummaryService._get_cache(url, skip_retryable=True)

                    logger.info(f"[LlamaWorker] Step 2 — processing article [{idx+1}/{len(to_process)}]: {url}")
                    result = SummaryService.process_article(url, a.get("lang", "en"), title)

                    if result.get("error"):
                        logger.error(f"[LlamaWorker] Step 2 FAILED for {url}: {result['error']}")
                        a["audio_cached"] = "error"
                        a["summary_text"] = result.get("error", "")
                    else:
                        logger.info(f"[LlamaWorker] Step 2 OK — audio_url={result.get('audio_url','?')}, summary_len={len(result.get('summary_vi',''))}")
                        a["audio_cached"] = True
                        a["summary_text"] = result.get("summary_vi", "")

                    logger.info(f"[LlamaWorker] Step 3 — updating history for: {url}")
                    NewsService._update_history([a])

                    keys_to_delete = [k for k in _cache.keys() if k.startswith(f"{category}_")]
                    for k in keys_to_delete:
                        del _cache[k]

                    logger.info(f"[LlamaWorker] Article {idx+1}/{len(to_process)} done — cache invalidated for category={category}")
                    time.sleep(3)

                set_ai_status("Đang rảnh")
                _llama_queue_cats.discard(category)
                _llama_queue.task_done()

            except Exception as e:
                logger.error(f"[LlamaWorker] Unhandled error: {e}")
                if "category" in locals():
                    _llama_queue_cats.discard(category)
                set_ai_status("Đang rảnh")
                _llama_queue.task_done()
                time.sleep(5)

    @staticmethod
    def get_news(category: str, limit: int = 15) -> Dict:
        start_bg_worker()

        cache_key = f"{category}_{limit}"
        now = time.time()

        if cache_key in _cache:
            cached = _cache[cache_key]
            if now - cached["timestamp"] < CACHE_TTL:
                return cached["data"]

        sources = RSS_SOURCES.get(category, [])
        if not sources:
            logger.warning(f"[GetNews] Unknown category: {category}")
            return {"articles": [], "error": f"Danh mục '{category}' không tồn tại"}

        all_articles = []
        per_source = max(5, limit // len(sources))
        for src in sources:
            fetched = NewsService._parse_rss(src["url"], src["name"], src["icon"], src["lang"], per_source)
            all_articles.extend(fetched)

        all_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        all_articles = all_articles[:limit]
        logger.info(f"[GetNews] category={category}, total_articles={len(all_articles)}")

        from services.summary_service import SummaryService
        needs_processing = False

        for article in all_articles:
            article["category"] = category
            cached_sum = SummaryService._get_cache(article["url"])
            if cached_sum:
                if "error" in cached_sum:
                    article["audio_cached"] = "error"
                    article["summary_text"] = cached_sum.get("error", "")
                elif "audio_url" in cached_sum:
                    article["audio_cached"] = True
                    article["summary_text"] = cached_sum.get("summary_vi", "")
            else:
                article["audio_cached"] = False
                needs_processing = True

        NewsService._apply_translations(all_articles, category)
        NewsService._update_history(all_articles)

        has_untranslated = any(a.get("lang") == "en" and "title_vi" not in a for a in all_articles)

        if has_untranslated and category not in _translation_queue_cats:
            logger.info(f"[GetNews] Queuing translation for {category}")
            _translation_queue_cats.add(category)
            _translation_queue.put({"category": category, "articles": all_articles})

        if needs_processing and category not in _llama_queue_cats:
            logger.info(f"[GetNews] Queuing LLM processing for {category} ({sum(1 for a in all_articles if not a.get('audio_cached'))} articles pending)")
            _llama_queue_cats.add(category)
            _llama_queue.put({"category": category, "articles": all_articles})

        result = {
            "articles": all_articles,
            "category": category,
            "count": len(all_articles),
            "sources": [s["name"] for s in sources],
            "cached_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        }

        _cache[cache_key] = {"data": result, "timestamp": now}
        return result

    @staticmethod
    def search_news(query: str, limit: int = 20) -> Dict:
        results = []
        query_lower = query.lower()
        logger.info(f"[Search] query='{query}', limit={limit}")

        for category in RSS_SOURCES:
            news = NewsService.get_news(category, limit=30)
            for article in news.get("articles", []):
                title = article.get("title", "").lower()
                title_vi = article.get("title_vi", "").lower()
                desc = article.get("description", "").lower()
                source = article.get("source", "").lower()
                if query_lower in title or query_lower in title_vi or query_lower in desc or query_lower in source:
                    article_copy = dict(article)
                    article_copy["category"] = category
                    results.append(article_copy)

        remaining_limit = limit - len(results)
        if remaining_limit > 0:
            try:
                from duckduckgo_search import DDGS
                logger.info(f"[Search] DuckDuckGo fallback for '{query}', need {remaining_limit} more results")
                with DDGS() as ddgs:
                    ddgs_results = []
                    for item in ddgs.news(query, max_results=remaining_limit):
                        ddgs_results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("body", "")[:200],
                            "date": item.get("date", "")[:25],
                            "source": item.get("source", "Web"),
                            "icon": "🌐",
                            "lang": "en",
                            "category": "cybersecurity",
                        })

                if ddgs_results:
                    NewsService._apply_translations(ddgs_results, "cybersecurity")
                    en_articles = [a for a in ddgs_results if a.get("lang") == "en" and "title_vi" not in a]
                    if en_articles:
                        threading.Thread(
                            target=NewsService._bg_translate,
                            args=(ddgs_results, "cybersecurity"),
                            daemon=True,
                        ).start()
                    results.extend(ddgs_results)
                    logger.info(f"[Search] DuckDuckGo returned {len(ddgs_results)} results")
            except Exception as e:
                logger.warning(f"[Search] DuckDuckGo error: {e}")

        results = results[:limit]
        return {"articles": results, "query": query, "count": len(results)}

    @staticmethod
    def _bg_translate(articles, category):
        try:
            from services.translation_service import TranslationService
            en_titles = [a["title"] for a in articles if a.get("lang") == "en" and "title_vi" not in a]
            if en_titles:
                TranslationService.translate_batch(en_titles, category)
        except Exception as e:
            logger.warning(f"[BgTranslate] Error: {e}")

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
        for cat in ("cybersecurity", "stocks_vietnam", "stocks_international"):
            try:
                NewsService.get_news(cat, limit=20)
                logger.info(f"[AutoWorker] Refresh triggered for category={cat}")
            except Exception as e:
                logger.warning(f"[AutoWorker] Refresh failed for {cat}: {e}")
            time.sleep(10)

        try:
            from services.summary_service import CACHE_DIR, AUDIO_DIR, SummaryService
            active_hashes = set()
            for cat in ("cybersecurity", "stocks_international", "stocks_vietnam"):
                recent = NewsService.get_news(cat, limit=20)
                for a in recent.get("articles", []):
                    active_hashes.add(SummaryService._generate_hash(a["url"]))

            removed = 0
            for directory, ext in [(CACHE_DIR, ".json"), (AUDIO_DIR, ".mp3")]:
                if os.path.exists(directory):
                    for f in os.listdir(directory):
                        if f.endswith(ext):
                            fname = f.replace(ext, "")
                            if fname not in active_hashes:
                                try:
                                    os.remove(os.path.join(directory, f))
                                    removed += 1
                                except Exception as e:
                                    logger.warning(f"[AutoWorker] Failed to remove {f}: {e}")
            if removed:
                logger.info(f"[AutoWorker] Cleaned {removed} stale cache files")
        except Exception as e:
            logger.warning(f"[AutoWorker] Cache cleanup failed: {e}")

        time.sleep(18000)


def start_bg_worker():
    global _bg_started
    if not _bg_started:
        _bg_started = True

        t_trans = threading.Thread(target=NewsService._translation_worker, daemon=True)
        t_trans.start()

        t_llama = threading.Thread(target=NewsService._llama_worker, daemon=True)
        t_llama.start()

        t_cron = threading.Thread(target=_auto_translate_worker, daemon=True)
        t_cron.start()

        logger.info("[Workers] Translation, LLM & AutoRefresh workers started")
