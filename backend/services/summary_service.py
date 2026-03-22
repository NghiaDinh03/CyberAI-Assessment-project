"""Summary Service — Full-content article processing with Cloud LLM translation & Edge-TTS."""

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
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
_process_lock = threading.Semaphore(1)

CACHE_DIR = "/data/summaries"
AUDIO_DIR = os.path.join(CACHE_DIR, "audio")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


class SummaryService:
    @staticmethod
    def _generate_hash(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    @staticmethod
    def _get_cache(url: str) -> Optional[Dict]:
        url_hash = SummaryService._generate_hash(url)
        cache_path = os.path.join(CACHE_DIR, f"{url_hash}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
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

        # Step 1: Crawl full article text
        try:
            from newspaper import Article
            article_scraper = Article(url)
            article_scraper.download()
            article_scraper.parse()
            text = article_scraper.text

            if not text or len(text) < 300:
                logger.warning(f"Article too short ({len(text) if text else 0} chars): {url}")
                raise Exception("Not enough text extracted")

            logger.info(f"Crawled {len(text)} chars from: {url}")
            # No hard truncation — send full text to Cloud API for maximum accuracy
            # Only soft limit at 12000 chars to stay within token limits
            if len(text) > 12000:
                text = text[:12000]

        except Exception as e:
            logger.error(f"Failed to parse article {url}: {e}")
            err_msg = "Nội dung bài báo quá ngắn hoặc bị chặn bot." if "Not enough text" in str(e) else f"Lỗi truy cập: {str(e)[:80]}"
            res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash}
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
            res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash}
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
