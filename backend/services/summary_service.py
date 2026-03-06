import os
import json
import hashlib
import logging
import asyncio
import edge_tts
from newspaper import Article
from typing import Dict, Optional

logger = logging.getLogger(__name__)

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
        """
        Crawls article, summarizes via Llama, generates TTS audio, caches results.
        lang: original language of the article ('en' or 'vi')
        title: article title (passed to edge-tts to read first)
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
            return {"error": "Không thể trích xuất nội dung bài viết gốc."}

        # 2. Summarize via Local Llama 3.1
        try:
            from services.translation_service import TranslationService
            import httpx
            
            prompt = ""
            if lang == "en":
                prompt = (
                    "Bạn là một biên tập viên tin tức AI. "
                    "Hãy tổng hợp và dịch bài báo Tiếng Anh sau đây sang Tiếng Việt một cách mạch lạc và dễ hiểu. "
                    "Kết quả phải là một bài viết thuần text, văn phong tự nhiên, phù hợp để đọc bằng giọng nói nhân tạo (voice). "
                    "Tuyệt đối không sử dụng các ký tự đặc biệt (*, #, ngoặc vuông, v.v.), không để lại URL hoặc thông tin thừa. "
                    f"\n\nNội dung báo: {text}"
                )
            else:
                prompt = (
                    "Bạn là một biên tập viên tin tức AI. "
                    "Hãy tổng hợp lại bài báo Tiếng Việt sau đây một cách mạch lạc và dễ hiểu. "
                    "Kết quả phải là một bài viết thuần text, văn phong tự nhiên, trôi chảy, phù hợp để đọc bằng giọng nói nhân tạo (voice). "
                    "Tuyệt đối không sử dụng các ký tự đặc biệt (*, #, ngoặc vuông, v.v.), không để lại URL hoặc thông tin rác. "
                    f"\n\nNội dung báo: {text}"
                )

            # Define messages for Llama 3.1
            messages = [{"role": "user", "content": prompt}]
            
            # Using httpx directly as in _translate_via_localai pattern
            LLM_API_URL = os.getenv("LLM_API_URL", "http://phobert-localai:8080/v1")
            payload = {
                "model": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2400
            }
            res = httpx.post(f"{LLM_API_URL}/chat/completions", json=payload, timeout=900.0)
            res.raise_for_status()
            summary_vi = res.json()["choices"][0]["message"]["content"].strip()
            
            # Post process summary (remove asterisks, weird artifacts)
            summary_vi = summary_vi.replace("*", "").replace("#", "").replace('"', "")
            summary_vi = summary_vi.replace("<|eot_id|>", "").replace("assistant", "").strip()
            
            # Loại bỏ từ assistant ở đầu nếu có
            if summary_vi.lower().startswith("assistant"):
                summary_vi = summary_vi[len("assistant"):].strip()
            
        except Exception as e:
            logger.error(f"Failed to summarize article {url}: {e}")
            return {"error": "Lỗi khi tổng hợp và tóm tắt nội dung bằng AI."}

        # 3. Text to Speech (edge-tts)
        try:
            # Sử dụng giọng tiếng Việt chất lượng cao của Microsoft Edge
            voice = "vi-VN-HoaiMyNeural" 
            
            # Ghép title vào trước bài đọc nếu có
            text_to_read = summary_vi
            if title:
                text_to_read = f"{title}.\n{summary_vi}"
                
            communicate = edge_tts.Communicate(text_to_read, voice)
            asyncio.run(communicate.save(audio_path))
        except Exception as e:
            logger.error(f"edge-tts error for {url}: {e}")
            return {"error": "Lỗi khi chuyển đổi văn bản thành giọng nói."}

        result = {
            "url": url,
            "original_lang": lang,
            "summary_vi": summary_vi,
            "audio_url": f"/api/news/audio/{audio_filename}",
            "hash": url_hash
        }
        
        SummaryService._save_cache(url, result)
        
        return result
