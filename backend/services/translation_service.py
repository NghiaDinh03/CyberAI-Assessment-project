import os
import json
import time
import hashlib
import logging
import requests
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

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
    def translate_batch(titles: List[str], category: str) -> Dict[str, str]:
        if not GEMINI_API_KEY:
            return {}

        cache = TranslationService._load_cache(category)

        missing = []
        for t in titles:
            key = TranslationService._make_key(t)
            if key not in cache:
                missing.append(t)

        if not missing:
            return cache

        try:
            prompt = (
                "Dịch các tiêu đề tin tức sau sang tiếng Việt. "
                "Giữ nguyên tên riêng, thuật ngữ kỹ thuật. "
                "Dịch tự nhiên, ngắn gọn, dễ hiểu. "
                "Trả về JSON array theo thứ tự tương ứng.\n\n"
            )
            for i, t in enumerate(missing):
                prompt += f"{i+1}. {t}\n"

            prompt += '\nTrả về duy nhất JSON array: ["bản dịch 1", "bản dịch 2", ...]'

            resp = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1}
                },
                timeout=30
            )
            resp.raise_for_status()

            result = resp.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            translated = json.loads(text)

            for i, t in enumerate(missing):
                key = TranslationService._make_key(t)
                if i < len(translated):
                    cache[key] = translated[i]

            TranslationService._save_cache(category, cache)

        except Exception as e:
            logger.warning(f"Gemini translation thất bại: {e}")

        return cache

    @staticmethod
    def get_translation(title: str, cache: Dict) -> Optional[str]:
        key = TranslationService._make_key(title)
        return cache.get(key)
