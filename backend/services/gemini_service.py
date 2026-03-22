"""DEPRECATED: Use CloudLLMService instead. This wrapper exists for backward compatibility."""

import logging
logger = logging.getLogger(__name__)

try:
    from services.cloud_llm_service import CloudLLMService

    class GeminiService:
        @staticmethod
        def generate(prompt: str, **kwargs) -> str:
            logger.warning("GeminiService is deprecated. Use CloudLLMService instead.")
            result = CloudLLMService.chat_completion(
                messages=[{"role": "user", "content": prompt}], **kwargs)
            return result.get("content", "")
except ImportError:
    class GeminiService:
        @staticmethod
        def generate(prompt: str, **kwargs) -> str:
            raise NotImplementedError("CloudLLMService not available")
