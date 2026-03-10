import os
import json
import hashlib
import logging
import asyncio
import edge_tts
import time
import google.generativeai as genai
from newspaper import Article
import httpx
import threading
import traceback
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
_process_lock = threading.Semaphore(1)

CACHE_DIR = "/data/summaries"
AUDIO_DIR = os.path.join(CACHE_DIR, "audio")

# Ensure directories exist
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
                logger.warning(f"Failed to read cache {cache_path}: {e}")
        return None

    @staticmethod
    def _save_cache(url: str, data: Dict):
        url_hash = SummaryService._generate_hash(url)
        cache_path = os.path.join(CACHE_DIR, f"{url_hash}.json")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

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
        """
        Logic thực tế để xử lý bài báo, được bảo vệ bởi Semaphore.
        """
        cached = SummaryService._get_cache(url)
        if cached:
            return cached

        url_hash = SummaryService._generate_hash(url)
        audio_filename = f"{url_hash}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        # 1. Crawl text
        try:
            article_scraper = Article(url)
            article_scraper.download()
            article_scraper.parse()
            text = article_scraper.text
            if not text or len(text) < 500:
                logger.warning(f"Bỏ qua bài báo do nội dung quá ngắn ({len(text) if text else 0} ký tự): {url}")
                raise Exception("Not enough text extracted")
            
            logger.info(f"[AI] Đã cào được {len(text)} ký tự từ: {url}")
            # Truncate to save context window (3000 chars is enough for summary)
            text = text[:3000] 
        except Exception as e:
            logger.error(f"Failed to parse article {url}: {e}")
            err_msg = str(e)
            if "Not enough text" in err_msg:
                err_msg = "Nội dung bài báo quá ngắn hoặc bị chặn cào bot."
            else:
                err_msg = f"Lỗi truy cập trang: {err_msg[:50]}"
            res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash}
            SummaryService._save_cache(url, res)
            return res

        # 2. Summarize via AI
        try:
            
            prompt = ""
            if lang == "en":
                prompt = (
                    "Bạn là một biên tập viên tin tức CNTT. "
                    "Nhiệm vụ: Dịch TOÀN BỘ bài báo sau sang Tiếng Việt. "
                    "Yêu cầu bắt buộc:\n"
                    "- DÒNG ĐẦU TIÊN của file kết quả PHẢI là Tiêu đề bài báo đã được dịch sang tiếng Việt một cách hấp dẫn.\n"
                    "- KHÔNG ĐƯỢC tóm tắt ngắn gọn. Phải GIỮ NGUYÊN TOÀN BỘ thông tin, thông số kỹ thuật, số liệu, và tên tổ chức/chuyên gia.\n"
                    "- Chỉ lược bỏ các thành phần rác (menu, quảng cáo, nút bấm) hoặc sơ đồ/code không thể đọc bằng giọng nói.\n"
                    "- Văn phong chuẩn báo chí, dịch thuật trơn tru mạch lạc để công cụ Text-to-Speech đọc dễ nghe.\n"
                    "- Tuyệt đối không xưng hô, không dùng ký tự đặc biệt (*, #, ngoặc vuông).\n"
                    f"\n\nTiêu đề gốc: {title}\nNội dung báo: {text}"
                )
            else:
                prompt = (
                    "Bạn là một biên tập viên tin tức CNTT. "
                    "Nhiệm vụ: Lọc lại bài báo Tiếng Việt sau đây thành một bài thuần text chuẩn báo chí. "
                    "Yêu cầu bắt buộc:\n"
                    "- DÒNG ĐẦU TIÊN của file kết quả PHẢI là Tiêu đề bài báo.\n"
                    "- KHÔNG ĐƯỢC tóm tắt ngắn. Phải GIỮ NGUYÊN TOÀN BỘ thông tin, số liệu, chi tiết.\n"
                    "- Lược bỏ thẻ HTML, sơ đồ mô hình, code dư thừa, quảng cáo, menu.\n"
                    "- Văn phong tự nhiên, trôi chảy, phù hợp để đọc bằng giọng nói nhân tạo.\n"
                    "- Tuyệt đối không dùng ký tự đặc biệt (*, #, ngoặc).\n"
                    f"\n\nTiêu đề: {title}\nNội dung báo: {text}"
                )

            summary_vi = ""
            # Priority 1: Dùng Gemini với vòng lặp Round-Robin (Xoay vòng 4 Keys)
            gemini_keys_env = os.getenv("GEMINI_API_KEYS", "").strip()
            if gemini_keys_env:
                gemini_keys = [k.strip() for k in gemini_keys_env.split(",") if k.strip()]
                if gemini_keys:
                    if not hasattr(SummaryService, '_gemini_key_index'):
                        SummaryService._gemini_key_index = 0
                    if not hasattr(SummaryService, '_gemini_cooldowns'):
                        SummaryService._gemini_cooldowns = {} # {key_index: timestamp}
                    
                    if not hasattr(SummaryService, '_openrouter_key_index'):
                        SummaryService._openrouter_key_index = 0
                    if not hasattr(SummaryService, '_openrouter_cooldowns'):
                        SummaryService._openrouter_cooldowns = {} # {key_index: timestamp}
                    
                    success = False
                    for _ in range(len(gemini_keys)):
                        idx = SummaryService._gemini_key_index % len(gemini_keys)
                        SummaryService._gemini_key_index += 1
                        
                        # Kiểm tra Cooldown của Key này
                        last_429 = SummaryService._gemini_cooldowns.get(idx, 0)
                        if time.time() - last_429 < 60:
                            continue

                        current_key = gemini_keys[idx]
                        try:
                            genai.configure(api_key=current_key)
                            model = genai.GenerativeModel('gemini-2.0-flash')
                            response = model.generate_content(
                                prompt,
                                generation_config=genai.GenerationConfig(
                                    temperature=0.3,
                                    max_output_tokens=2000,
                                )
                            )
                            summary_vi = response.text.strip()
                            success = True
                            logger.info(f"Đã tóm tắt bằng Gemini Flash (Key index {idx})")
                            break
                        except Exception as e:
                            err_str = str(e)
                            if "429" in err_str or "ResourceExhausted" in err_str:
                                SummaryService._gemini_cooldowns[idx] = time.time()
                                logger.error(f"Gemini Key index {idx} bị kịch hạn mức (429). Kích hoạt Cooldown 60s.")
                            else:
                                logger.warning(f"Gemini Key index {idx} lỗi ({e}). Thử key tiếp theo...")
                            time.sleep(0.5) 
            
            # Priority 2: Nếu không gọi được Gemini (Hoặc lỗi cả 4 keys), dùng dự phòng OpenRouter (Xoay vòng 2+ keys)
            if not summary_vi:
                or_keys_env = os.getenv("OPENROUTER_API_KEYS", "").strip()
                if not or_keys_env:
                    # Fallback cho biến môi trường cũ đơn lẻ nếu có
                    or_keys_env = os.getenv("OPENROUTER_API_KEY", "").strip()
                
                if or_keys_env:
                    or_keys = [k.strip() for k in or_keys_env.split(",") if k.strip()]
                    if or_keys:
                        logger.info(f"Tất cả Gemini Keys thất bại. Đang thử xoay vòng {len(or_keys)} OpenRouter Keys...")
                        
                        for _ in range(len(or_keys)):
                            idx = SummaryService._openrouter_key_index % len(or_keys)
                            SummaryService._openrouter_key_index += 1
                            
                            # Kiểm tra Cooldown của Key này
                            last_429 = SummaryService._openrouter_cooldowns.get(idx, 0)
                            if time.time() - last_429 < 60:
                                continue

                            current_or_key = or_keys[idx]
                            try:
                                headers = {
                                    "Authorization": f"Bearer {current_or_key}",
                                    "HTTP-Referer": "http://localhost:3000",
                                    "X-Title": "PhoBert Chatbot"
                                }
                                payload = {
                                    "model": "openrouter/free",
                                    "messages": [{"role": "user", "content": prompt}],
                                    "temperature": 0.3,
                                    "max_tokens": 2000
                                }
                                res = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
                                
                                if res.status_code == 429:
                                    SummaryService._openrouter_cooldowns[idx] = time.time()
                                    logger.error(f"OpenRouter Key index {idx} báo lỗi 429. Kích hoạt Cooldown 60s.")
                                    continue
                                    
                                res.raise_for_status()
                                summary_vi = res.json()["choices"][0]["message"]["content"].strip()
                                logger.info(f"Đã tóm tắt bằng OpenRouter (Key index {idx})")
                                break
                            except Exception as e:
                                logger.warning(f"OpenRouter Key index {idx} lỗi ({e}). Thử key tiếp theo...")
                                time.sleep(0.5)
            
            if not summary_vi:
                raise Exception("Tất cả các API Tóm tắt đang lỗi mạng hoặc cạn Quota. Xin chờ 5 phút.")
            
            # Post process summary
            if summary_vi:
                summary_vi = summary_vi.replace("*", "").replace("#", "").replace('"', "")
                summary_vi = summary_vi.replace("<|eot_id|>", "").replace("<|end_header_id|>", "").replace("assistant", "").strip()
                if summary_vi.lower().startswith("assistant"):
                    summary_vi = summary_vi[len("assistant"):].strip()

                # Tách tiêu đề (dòng đầu tiên) và nội dung tóm tắt để đồng bộ Lịch sử
                lines = [l.strip() for l in summary_vi.split("\n") if l.strip()]
                final_title_vi = title
                if lines:
                    final_title_vi = lines[0]
                
                # Cập nhật lịch sử ngay lập tức
                try:
                    from services.news_service import NewsService
                    NewsService._update_history([{
                        "url": url,
                        "title_vi": final_title_vi,
                        "summary_text": summary_vi[:500],
                        "audio_cached": True
                    }])
                except Exception as e:
                    logger.warning(f"Cập nhật lịch sử đồng bộ từ SummaryService thất bại: {e}")
            else:
                summary_vi = "AI đang bận hoặc cạn tài nguyên. Vui lòng thử lại sau."
        except Exception as e:
            logger.error(f"Failed to summarize article {url}: {e}")
            err_msg = str(e)
            if "timeout" in err_msg.lower():
                err_msg = "AI đang quá tải (Timeout). Vui lòng thử lại sau."
            else:
                err_msg = f"AI từ chối xử lý: {err_msg[:50]}"
            res = {"error": f"❌ {err_msg}", "url": url, "hash": url_hash}
            SummaryService._save_cache(url, res)
            return res

        # 3. Text to Speech (edge-tts)
        try:
            import re
            
            def fix_pronunciation(text: str) -> str:
                # Dictionary phiên âm các từ viết tắt chuyên ngành
                replacements = {
                    r'\bRAT\b': 'Rát',
                    r'\bAI\b': 'Ây ai',
                    r'\bFBI\b': 'Ép bi ai',
                    r'\bCIA\b': 'Xi ai ây',
                    r'\bAPT\b': 'Ê pi ti',
                    r'\bAPI\b': 'Ê pi ai',
                    r'\bCEO\b': 'Xi y âu',
                    r'\bIT\b': 'Ai ti',
                    r'\bCISA\b': 'Xi sa',
                    r'\bUS\b': 'Mỹ',
                    r'\bUSA\b': 'Mỹ',
                    r'\biOS\b': 'Ai âu ét',
                    r'\bIP\b': 'Ai pi',
                    r'\bIoT\b': 'Ai âu ti',
                    r'\bAWS\b': 'Ây đắp liu ét',
                    r'\bURL\b': 'U rờ lờ',
                    r'(?i)\bcybersecurity\b': 'An ninh mạng',
                    r'(?i)\bhacker\b': 'Hắc cờ',
                    r'(?i)\bmalware\b': 'Mã độc',
                    r'(?i)\bphishing\b': 'Lừa đảo qua mạng',
                    r'(?i)\bvinaconex\b': 'Vi na cô nếch',
                    r'(?i)\bvietstock\b': 'Việt xtốc',
                    r'(?i)\bvneconomy\b': 'Vi en i cô nô mi',
                    r'(?i)\bpost\b': 'Pốt',
                    r'(?i)\btrading\b': 'Tra đing',
                    r'(?i)\betfs\b': 'Ê tê ép',
                    r'(?i)\btech\b': 'Tếch'
                }
                for pattern, replacement in replacements.items():
                    text = re.sub(pattern, replacement, text)
                
                # Các từ in hoa còn lại (ví dụ IBM, HTTP), nếu để nguyên edge-tts tiếng Việt sẽ đọc từng chữ (vd: H T T P) - điều này chấp nhận được với đa số từ.
                return text

            voice = "vi-VN-HoaiMyNeural" 
            text_to_read = fix_pronunciation(summary_vi)
            
            communicate = edge_tts.Communicate(text_to_read, voice)
            asyncio.run(communicate.save(audio_path))
        except Exception as e:
            logger.error(f"edge-tts error for {url}: {e}")
            res = {"error": "Lỗi AI tạo giọng nói.", "url": url, "hash": url_hash}
            SummaryService._save_cache(url, res)
            return res

        result = {
            "url": url, "original_lang": lang, "summary_vi": summary_vi,
            "audio_url": f"/api/news/audio/{audio_filename}", "hash": url_hash
        }
        SummaryService._save_cache(url, result)
        return result
