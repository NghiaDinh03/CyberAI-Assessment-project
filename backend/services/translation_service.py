import os
import json
import time
import hashlib
import logging
import requests
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

LOCALAI_URL = os.getenv("LOCALAI_URL", "http://localai:8080")
MODEL_NAME = os.getenv("MODEL_NAME", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CACHE_DIR = Path("/data/translations")
CACHE_TTL = 43200


class TranslationService:
    @staticmethod
    def _cache_path(category: str) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR / f"{category}.json"

    @staticmethod
    def _load_cache(category: str) -> Dict:
        path = TranslationService._cache_path(category)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if time.time() - data.get("timestamp", 0) < CACHE_TTL:
                    return data.get("translations", {})
            except Exception:
                pass
        return {}

    @staticmethod
    def _save_cache(category: str, translations: Dict):
        path = TranslationService._cache_path(category)
        path.write_text(json.dumps({
            "timestamp": time.time(),
            "translations": translations
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _make_key(title: str) -> str:
        return hashlib.md5(title.strip().lower().encode()).hexdigest()[:12]

    @staticmethod
    def _build_prompt(titles: List[str]) -> str:
        prompt = (
            "Dịch các tiêu đề tin tức sau sang tiếng Việt. "
            "Giữ nguyên tên riêng, thuật ngữ kỹ thuật. "
            "Dịch tự nhiên, ngắn gọn. "
            "Trả về duy nhất JSON array.\n\n"
        )
        for i, t in enumerate(titles):
            prompt += f"{i+1}. {t}\n"
        prompt += '\nJSON: ["bản dịch 1", "bản dịch 2", ...]'
        return prompt

    @staticmethod
    def _parse_response(text: str) -> List[str]:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]

        return json.loads(text)

    @staticmethod
    def _translate_via_localai(titles: List[str]) -> List[str]:
        prompt = TranslationService._build_prompt(titles)
        resp = requests.post(
            f"{LOCALAI_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "Bạn là dịch giả chuyên nghiệp. Chỉ trả về JSON array."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1024
            },
            timeout=300
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return TranslationService._parse_response(text)

    @staticmethod
    def _translate_via_gemini(titles: List[str]) -> List[str]:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        prompt = TranslationService._build_prompt(titles)
        resp = None
        for attempt in range(3):
            resp = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1}
                },
                timeout=30
            )
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            break
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return TranslationService._parse_response(text)

    @staticmethod
    def translate_batch(titles: List[str], category: str) -> Dict[str, str]:
        cache = TranslationService._load_cache(category)

        missing = [t for t in titles if TranslationService._make_key(t) not in cache]
        if not missing:
            return cache

        translated = []
        try:
            translated = TranslationService._translate_via_gemini(missing)
            logger.info(f"Dịch {len(missing)} titles qua Gemini")
        except Exception as e:
            logger.info(f"Gemini không khả dụng ({e}), chuyển sang LocalAI")
            try:
                translated = TranslationService._translate_via_localai(missing)
                logger.info(f"Dịch {len(missing)} titles qua LocalAI")
            except Exception as e2:
                logger.warning(f"Translation thất bại: {e2}")

        for i, t in enumerate(missing):
            key = TranslationService._make_key(t)
            if i < len(translated):
                cache[key] = translated[i]

        if translated:
            TranslationService._save_cache(category, cache)

        return cache

    @staticmethod
    def get_translation(title: str, cache: Dict) -> Optional[str]:
        key = TranslationService._make_key(title)
        return cache.get(key)
