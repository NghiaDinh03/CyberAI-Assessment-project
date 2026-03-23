"""Summary Service — Article processing with Cloud LLM translation & Edge-TTS."""

import os
import json
import hashlib
import logging
import asyncio
import edge_tts
import re
import time
import threading
import traceback
import random
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
_process_lock = threading.Semaphore(1)

CACHE_DIR = "/data/summaries"
AUDIO_DIR = os.path.join(CACHE_DIR, "audio")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Rotating User-Agents to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# Sites known to block bots aggressively — use special handling
BOT_BLOCKING_DOMAINS = {
    "darkreading.com": {"strategy": "requests_bs4", "needs_cookies": True},
    "marketwatch.com": {"strategy": "requests_bs4", "needs_cookies": True},
    "thehackernews.com": {"strategy": "requests_bs4", "needs_cookies": False},
    "securityweek.com": {"strategy": "newspaper", "needs_cookies": False},
    "cnbc.com": {"strategy": "requests_bs4", "needs_cookies": False},
    "yahoo.com": {"strategy": "requests_bs4", "needs_cookies": False},
}


def _get_random_headers() -> Dict[str, str]:
    """Generate realistic browser headers to bypass anti-bot detection."""
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def _get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except Exception:
        return ""


def _scrape_with_requests_bs4(url: str) -> Optional[str]:
    """Scrape article using requests + BeautifulSoup (bypasses many anti-bot measures)."""
    try:
        import requests
        from bs4 import BeautifulSoup

        session = requests.Session()
        headers = _get_random_headers()

        # First request to get cookies
        resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        if resp.status_code == 403:
            # Retry with different UA
            headers["User-Agent"] = random.choice(USER_AGENTS)
            time.sleep(2)
            resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        if resp.status_code == 401:
            # Some sites need a Referer
            headers["Referer"] = f"https://www.google.com/search?q={url}"
            time.sleep(1)
            resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        if resp.status_code not in (200, 206):
            logger.warning(f"requests_bs4 got status {resp.status_code} for {url}")
            return None

        soup = BeautifulSoup(resp.content, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                                   "aside", "form", "iframe", "noscript",
                                   "button", "input", "select"]):
            tag.decompose()

        # Try common article selectors
        article_selectors = [
            "article",
            '[role="article"]',
            ".article-body",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".story-body",
            "#article-body",
            ".article__body",
            ".article-text",
            ".caas-body",           # Yahoo
            ".articleBody",
            "#js-article-text",     # DarkReading
            ".ContentModule",       # DarkReading
            "#main-content",
            ".article__content",
            ".paywall",
        ]

        text = None
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                paragraphs = []
                for el in elements:
                    for p in el.find_all(["p", "li", "h2", "h3", "blockquote"]):
                        t = p.get_text(strip=True)
                        if t and len(t) > 20:
                            paragraphs.append(t)
                if paragraphs:
                    text = "\n\n".join(paragraphs)
                    if len(text) > 300:
                        break

        # Fallback: grab all paragraphs from the body
        if not text or len(text) < 300:
            paragraphs = []
            for p in soup.find_all("p"):
                t = p.get_text(strip=True)
                if t and len(t) > 30:
                    paragraphs.append(t)
            if paragraphs:
                text = "\n\n".join(paragraphs)

        if text and len(text) > 300:
            logger.info(f"requests_bs4 extracted {len(text)} chars from: {url}")
            return text

        return None
    except Exception as e:
        logger.warning(f"requests_bs4 failed for {url}: {e}")
        return None


def _scrape_with_trafilatura(url: str) -> Optional[str]:
    """Scrape article using trafilatura (excellent for news articles)."""
    try:
        import trafilatura
        headers = _get_random_headers()
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False,
                                        include_tables=False, favor_recall=True)
            if text and len(text) > 300:
                logger.info(f"trafilatura extracted {len(text)} chars from: {url}")
                return text
        return None
    except ImportError:
        logger.debug("trafilatura not installed, skipping")
        return None
    except Exception as e:
        logger.warning(f"trafilatura failed for {url}: {e}")
        return None


def _scrape_with_newspaper(url: str) -> Optional[str]:
    """Scrape article using newspaper3k with enhanced headers."""
    try:
        from newspaper import Article, Config

        config = Config()
        config.browser_user_agent = random.choice(USER_AGENTS)
        config.request_timeout = 20
        config.fetch_images = False

        article = Article(url, config=config)
        article.download()
        article.parse()
        text = article.text

        if text and len(text) > 300:
            logger.info(f"newspaper extracted {len(text)} chars from: {url}")
            return text
        return None
    except Exception as e:
        logger.warning(f"newspaper failed for {url}: {e}")
        return None


def scrape_article(url: str) -> Optional[str]:
    """Multi-strategy article scraper with anti-bot bypass.
    
    Strategy order depends on the domain:
    1. Check domain-specific strategy
    2. Try newspaper3k first (fastest)
    3. Fall back to requests+BS4 (most robust)
    4. Fall back to trafilatura (best extraction quality)
    """
    domain = _get_domain(url)
    domain_config = None
    for blocked_domain, config in BOT_BLOCKING_DOMAINS.items():
        if blocked_domain in domain:
            domain_config = config
            break

    strategies = []
    if domain_config:
        primary = domain_config.get("strategy", "requests_bs4")
        if primary == "requests_bs4":
            strategies = [_scrape_with_requests_bs4, _scrape_with_trafilatura, _scrape_with_newspaper]
        else:
            strategies = [_scrape_with_newspaper, _scrape_with_requests_bs4, _scrape_with_trafilatura]
    else:
        # Default order: newspaper → requests_bs4 → trafilatura
        strategies = [_scrape_with_newspaper, _scrape_with_requests_bs4, _scrape_with_trafilatura]

    for i, strategy in enumerate(strategies):
        try:
            text = strategy(url)
            if text and len(text) > 300:
                return text
            if i < len(strategies) - 1:
                time.sleep(1)  # Small delay between strategies
        except Exception as e:
            logger.warning(f"Strategy {strategy.__name__} failed for {url}: {e}")

    return None


class SummaryService:
    @staticmethod
    def _generate_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    @staticmethod
    def _get_cache(url: str, skip_retryable: bool = False) -> Optional[Dict]:
        url_hash = SummaryService._generate_hash(url)
        cache_path = os.path.join(CACHE_DIR, f"{url_hash}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Auto-clean error caches that are retryable
                if skip_retryable and data.get("retryable"):
                    os.remove(cache_path)
                    logger.info(f"Removed retryable error cache for: {url}")
                    return None
                # Also auto-clean old error caches (older than 2 hours)
                if "error" in data and skip_retryable:
                    cache_time = os.path.getmtime(cache_path)
                    if time.time() - cache_time > 7200:  # 2 hours
                        os.remove(cache_path)
                        logger.info(f"Removed stale error cache (>2h) for: {url}")
                        return None
                return data
            except Exception as e:
                logger.warning(f"Cache read failed {cache_path}: {e}")
        return None

    @staticmethod
    def _save_cache(url: str, data: Dict):
        url_hash = SummaryService._generate_hash(url)
        cache_path = os.path.join(CACHE_DIR, f"{url_hash}.json")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Cache save failed {cache_path}: {e}")

    @staticmethod
    def process_article(url: str, lang: str = "en", title: str = "") -> Dict:
        with _process_lock:
            try:
                return SummaryService._process_article_internal(url, lang, title)
            except Exception as e:
                logger.error(f"Critical error in process_article: {e}\n{traceback.format_exc()}")
                return {"error": f"Lỗi hệ thống: {str(e)}"}

    @staticmethod
    def _process_article_internal(url: str, lang: str = "en", title: str = "") -> Dict:
        cached = SummaryService._get_cache(url)
        if cached:
            return cached

        url_hash = SummaryService._generate_hash(url)
        audio_filename = f"{url_hash}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        # Step 1: Crawl full article text with multi-strategy scraper
        text = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
                text = scrape_article(url)

                if not text or len(text) < 300:
                    logger.warning(f"All scrape strategies insufficient ({len(text) if text else 0} chars), "
                                   f"attempt {attempt+1}: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(3 * (attempt + 1))
                        continue

                    # Last resort: use the RSS description/title as minimal content
                    if title:
                        text = f"{title}\n\n{text or ''}"
                        if len(text) > 100:
                            logger.info(f"Using title+partial text ({len(text)} chars) for: {url}")
                            break

                    raise Exception("Not enough text extracted from any strategy")

                logger.info(f"Successfully scraped {len(text)} chars from: {url}")
                if len(text) > 12000:
                    text = text[:12000]
                break

            except Exception as e:
                logger.warning(f"Scrape attempt {attempt+1}/{max_retries} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                else:
                    err_str = str(e)
                    is_blocked = any(k in err_str for k in ["401", "403", "429", "blocked", "Not enough text"])
                    domain = _get_domain(url)
                    if is_blocked:
                        err_msg = f"Trang {domain} chặn truy cập bot. Sẽ tự động thử lại sau."
                    else:
                        err_msg = f"Lỗi truy cập: {err_str[:80]}"
                    res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash, "retryable": True}
                    SummaryService._save_cache(url, res)
                    return res

        # Step 2: Cloud LLM — Translate (if EN) + Rewrite to broadcast-quality Vietnamese
        try:
            from services.cloud_llm_service import CloudLLMService

            if lang == "en":
                prompt = (
                    "Bạn là biên dịch viên báo chí chuyên nghiệp. "
                    "Hãy dịch TOÀN BỘ bài báo tiếng Anh sau sang Tiếng Việt hoàn chỉnh.\n\n"
                    "QUY TẮC BẮT BUỘC:\n"
                    "1. Dòng đầu tiên là tiêu đề tiếng Việt hấp dẫn, sát nghĩa gốc.\n"
                    "2. GIỮ NGUYÊN 100% mọi thông tin: tên người, tên tổ chức, số liệu thống kê, "
                    "thông số kỹ thuật, ngày tháng, mã CVE, địa chỉ IP, tên phần mềm, tên quốc gia. "
                    "KHÔNG được bỏ sót hay thay đổi bất kỳ dữ kiện nào.\n"
                    "3. KHÔNG rút gọn, KHÔNG tóm tắt, KHÔNG lược bỏ đoạn nào. Dịch ĐẦY ĐỦ từ đầu đến cuối.\n"
                    "4. Lược bỏ: menu điều hướng, quảng cáo, nút bấm, link đăng ký, footer website.\n"
                    "5. Văn phong báo chí chuyên nghiệp, mạch lạc, phù hợp đọc bằng giọng nói trên radio.\n"
                    "6. KHÔNG dùng ký tự đặc biệt: *, #, [], (), **. Chỉ dùng văn bản thuần.\n"
                    "7. TUYỆT ĐỐI KHÔNG thêm bất kỳ bình luận, ghi chú, lời giải thích nào của bạn. "
                    "Chỉ xuất ra nội dung bài báo đã dịch.\n\n"
                    f"TIÊU ĐỀ GỐC: {title}\n\n"
                    f"NỘI DUNG BÀI BÁO:\n{text}"
                )
            else:
                prompt = (
                    "Bạn là biên tập viên báo chí chuyên nghiệp. "
                    "Hãy biên tập lại bài báo Tiếng Việt sau thành bài viết hoàn chỉnh, chuẩn phát thanh.\n\n"
                    "QUY TẮC BẮT BUỘC:\n"
                    "1. Dòng đầu tiên là tiêu đề bài báo.\n"
                    "2. GIỮ NGUYÊN 100% mọi thông tin: tên người, tổ chức, số liệu, ngày tháng, "
                    "thông số kỹ thuật, dẫn chứng. KHÔNG được bỏ sót hay thay đổi bất kỳ dữ kiện nào.\n"
                    "3. KHÔNG rút gọn, KHÔNG tóm tắt. Giữ ĐẦY ĐỦ nội dung từ đầu đến cuối.\n"
                    "4. Lược bỏ: HTML, sơ đồ code, quảng cáo, menu, footer, link rác.\n"
                    "5. Văn phong tự nhiên, trôi chảy, phù hợp đọc bằng giọng nói trên radio.\n"
                    "6. KHÔNG dùng ký tự đặc biệt: *, #, [], (), **. Chỉ văn bản thuần.\n"
                    "7. TUYỆT ĐỐI KHÔNG thêm bất kỳ bình luận, ghi chú, lời giải thích nào của bạn.\n\n"
                    f"TIÊU ĐỀ: {title}\n\n"
                    f"NỘI DUNG BÀI BÁO:\n{text}"
                )

            result = CloudLLMService.chat_completion(
                messages=[
                    {"role": "system", "content": "Bạn là biên dịch viên/biên tập viên báo chí chuyên nghiệp. "
                     "Nhiệm vụ duy nhất: dịch/biên tập bài báo. Không giải thích, không bình luận."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.15,
                max_tokens=16000,
                task_type="complex",  # Intelligent routing: translation is a complex task
            )
            summary_vi = result.get("content", "").strip()
            provider = result.get("provider", "unknown")
            logger.info(f"Processed by {provider} (model: {result.get('model', '')}), output: {len(summary_vi)} chars")

            if not summary_vi:
                raise Exception("AI returned empty result")

            # Post-process: strip special chars and AI meta-commentary
            summary_vi = summary_vi.replace("*", "").replace("#", "").replace('"', "")
            summary_vi = summary_vi.replace("<|eot_id|>", "").replace("<|end_header_id|>", "")
            if summary_vi.lower().startswith("assistant"):
                summary_vi = summary_vi[len("assistant"):].strip()

            # Remove AI self-commentary patterns
            for pattern in [r'\(Đoạn văn tiếp theo.*$', r'\(Lưu ý:.*$', r'\(Ghi chú:.*$',
                            r'\(Chú thích:.*$', r'\(Dịch giả:.*$', r'\(Biên tập:.*$', r'---.*$']:
                summary_vi = re.sub(pattern, '', summary_vi, flags=re.DOTALL).strip()

            # Extract Vietnamese title for history sync
            lines = [l.strip() for l in summary_vi.split("\n") if l.strip()]
            final_title_vi = lines[0] if lines else title

            try:
                from services.news_service import NewsService
                NewsService._update_history([{
                    "url": url, "title_vi": final_title_vi,
                    "summary_text": summary_vi[:500], "audio_cached": True
                }])
            except Exception as e:
                logger.warning(f"History sync failed: {e}")

        except Exception as e:
            logger.error(f"Failed to process article {url}: {e}")
            err_msg = "AI timeout. Vui lòng thử lại sau." if "timeout" in str(e).lower() else f"AI error: {str(e)[:100]}"
            res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash, "retryable": True}
            SummaryService._save_cache(url, res)
            return res

        # Step 3: Text-to-Speech (Edge-TTS)
        try:
            text_to_read = SummaryService._fix_pronunciation(summary_vi)
            communicate = edge_tts.Communicate(text_to_read, "vi-VN-HoaiMyNeural")
            asyncio.run(communicate.save(audio_path))
        except Exception as e:
            logger.error(f"Edge-TTS error for {url}: {e}")
            res = {"error": "Lỗi tạo giọng nói.", "url": url, "hash": url_hash}
            SummaryService._save_cache(url, res)
            return res

        result = {
            "url": url, "original_lang": lang, "summary_vi": summary_vi,
            "audio_url": f"/api/news/audio/{audio_filename}", "hash": url_hash
        }
        SummaryService._save_cache(url, result)
        return result

    @staticmethod
    def _fix_pronunciation(text: str) -> str:
        replacements = {
            r'\bRAT\b': 'Rát', r'\bAI\b': 'Ây ai', r'\bFBI\b': 'Ép bi ai',
            r'\bCIA\b': 'Xi ai ây', r'\bAPT\b': 'Ê pi ti', r'\bAPI\b': 'Ê pi ai',
            r'\bCEO\b': 'Xi y âu', r'\bIT\b': 'Ai ti', r'\bCISA\b': 'Xi sa',
            r'\bUS\b': 'Mỹ', r'\bUSA\b': 'Mỹ', r'\biOS\b': 'Ai âu ét',
            r'\bIP\b': 'Ai pi', r'\bIoT\b': 'Ai âu ti', r'\bAWS\b': 'Ây đắp liu ét',
            r'\bURL\b': 'U rờ lờ', r'\bHTTPS?\b': 'Ếch ti ti pi',
            r'\bDDoS\b': 'Đi đốt', r'\bVPN\b': 'Vi pi en',
            r'\bSSL\b': 'Ét ét eo', r'\bTLS\b': 'Ti eo ét',
            r'(?i)\bcybersecurity\b': 'An ninh mạng', r'(?i)\bhacker\b': 'Hắc cờ',
            r'(?i)\bmalware\b': 'Mã độc', r'(?i)\bphishing\b': 'Lừa đảo qua mạng',
            r'(?i)\bransomware\b': 'Mã độc tống tiền',
            r'(?i)\bvinaconex\b': 'Vi na cô nếch', r'(?i)\bvietstock\b': 'Việt xtốc',
            r'(?i)\bvneconomy\b': 'Vi en i cô nô mi',
            r'(?i)\bpost\b': 'Pốt', r'(?i)\btrading\b': 'Tra đing',
            r'(?i)\betfs?\b': 'Ê tê ép', r'(?i)\btech\b': 'Tếch',
            r'(?i)\bblockchain\b': 'Bờ lốc chên', r'(?i)\bcrypto\b': 'Cờ ríp tô',
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        return text
