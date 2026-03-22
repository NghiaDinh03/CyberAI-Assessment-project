"""
Translation Service v2.0 — CPU Optimized.
- VinAI translate with torch thread control
- Batch processing with chunking
- Persistent cache
"""

import os
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


class AITranslator:
    _tokenizer = None
    _model = None

    @classmethod
    def _load_model(cls):
        if cls._model is None:
            logger.info("Đang tải model vinai/vinai-translate-en2vi (VinAI)...")
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            # CPU optimization: limit threads to avoid contention
            torch.set_num_threads(settings.TORCH_THREADS)
            torch.set_num_interop_threads(max(1, settings.TORCH_THREADS // 2))
            logger.info(f"PyTorch threads: {settings.TORCH_THREADS} (interop: {max(1, settings.TORCH_THREADS // 2)})")

            cls._tokenizer = AutoTokenizer.from_pretrained("vinai/vinai-translate-en2vi", src_lang="en_XX")
            cls._model = AutoModelForSeq2SeqLM.from_pretrained("vinai/vinai-translate-en2vi")
            cls._model.eval()

            # Use CPU with optimizations
            if torch.cuda.is_available():
                cls._model.to("cuda")
            else:
                # CPU inference optimization
                try:
                    cls._model = torch.jit.optimize_for_inference(torch.jit.script(cls._model))
                    logger.info("Applied torch.jit optimization for CPU inference")
                except Exception:
                    logger.info("JIT optimization not available, using standard CPU inference")

    @classmethod
    def translate(cls, texts: List[str]) -> List[str]:
        if not texts:
            return []

        try:
            cls._load_model()
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

            input_ids = cls._tokenizer(texts, padding=True, return_tensors="pt").to(device)
            with torch.no_grad():
                output_ids = cls._model.generate(
                    **input_ids,
                    decoder_start_token_id=cls._tokenizer.lang_code_to_id["vi_VN"],
                    num_return_sequences=1,
                    num_beams=5,
                    early_stopping=True,
                    max_length=512
                )

            vi_texts = cls._tokenizer.batch_decode(output_ids, skip_special_tokens=True)
            logger.info(f"Hoàn tất dịch VinAI cho {len(texts)} bài viết.")

            actual_translations = []
            for orig, trans in zip(texts, vi_texts):
                if trans.lower().strip() == orig.lower().strip():
                    logger.warning(f"Bản dịch giống hệt gốc, bỏ qua: {orig[:50]}")
                    actual_translations.append(None)
                else:
                    actual_translations.append(trans.strip())
            return actual_translations

        except Exception as e:
            logger.error(f"VinAI translate failed: {e}")
            return [None] * len(texts)


CACHE_DIR = Path(settings.DATA_PATH) / "translations"
CACHE_TTL = 43200  # 12 hours


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
        cache = TranslationService._load_cache(category)

        missing = [t for t in titles if TranslationService._make_key(t) not in cache]
        if not missing:
            return cache

        CHUNK_SIZE = 8
        for chunk_start in range(0, len(missing), CHUNK_SIZE):
            chunk = missing[chunk_start:chunk_start + CHUNK_SIZE]
            translated = []

            try:
                translated = AITranslator.translate(chunk)
                logger.info(f"Dịch {len(chunk)} titles qua AI Translate")
            except Exception as e:
                logger.warning(f"Chunk translation thất bại: {e}")
                continue

            for i, t in enumerate(chunk):
                key = TranslationService._make_key(t)
                if i < len(translated) and translated[i]:
                    cache[key] = translated[i]
                    logger.info(f"Đã dịch: '{t[:40]}' -> '{translated[i][:40]}'")

            if translated:
                TranslationService._save_cache(category, cache)

        return cache

    @staticmethod
    def get_translation(title: str, cache: Dict) -> Optional[str]:
        key = TranslationService._make_key(title)
        return cache.get(key)
