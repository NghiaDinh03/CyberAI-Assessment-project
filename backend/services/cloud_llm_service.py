"""Cloud LLM Service — Open Claude (primary) with LocalAI fallback."""

import time
import logging
import requests
import httpx
from typing import Dict, Any, List
from core.config import settings

logger = logging.getLogger(__name__)

MIN_MAX_TOKENS = 10000


class CloudLLMService:
    _key_index: int = 0
    _rate_limit_cooldowns: Dict[int, float] = {}
    RATE_LIMIT_COOLDOWN: int = 60

    @classmethod
    def _is_rate_limited(cls, key_idx: int) -> bool:
        elapsed = time.time() - cls._rate_limit_cooldowns.get(key_idx, 0)
        return elapsed < cls.RATE_LIMIT_COOLDOWN

    @classmethod
    def _mark_rate_limited(cls, key_idx: int):
        cls._rate_limit_cooldowns[key_idx] = time.time()
        logger.warning(f"[OpenClaude] Key {key_idx} rate limited (429) — cooldown {cls.RATE_LIMIT_COOLDOWN}s")

    @classmethod
    def _call_open_claude(cls, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 8192, model: str = None) -> Dict[str, Any]:
        model = model or settings.CLOUD_MODEL_NAME
        keys = settings.cloud_api_key_list
        if not keys:
            raise Exception("[OpenClaude] No API key configured")

        effective_max_tokens = max(max_tokens, MIN_MAX_TOKENS)
        logger.info(f"[OpenClaude] Requesting model={model}, max_tokens={effective_max_tokens}, messages={len(messages)}")

        last_error = None
        for attempt in range(len(keys)):
            idx = cls._key_index % len(keys)
            current_key = keys[idx]
            cls._key_index += 1

            if cls._is_rate_limited(idx):
                remaining = cls.RATE_LIMIT_COOLDOWN - (time.time() - cls._rate_limit_cooldowns.get(idx, 0))
                logger.warning(f"[OpenClaude] Key {idx} in cooldown ({remaining:.0f}s remaining), skipping")
                last_error = f"Key {idx} in cooldown"
                continue

            try:
                logger.debug(f"[OpenClaude] Attempt {attempt+1}/{len(keys)} with key index {idx}")
                response = httpx.post(
                    f"{settings.CLOUD_LLM_API_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {current_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": effective_max_tokens,
                        "stream": False,
                    },
                    timeout=settings.CLOUD_TIMEOUT,
                )

                logger.debug(f"[OpenClaude] Response status: {response.status_code}")

                if response.status_code == 429:
                    cls._mark_rate_limited(idx)
                    last_error = "Rate limited (429)"
                    continue

                if response.status_code == 401:
                    logger.error(f"[OpenClaude] 401 Unauthorized for key {idx} — check API key validity. Response: {response.text[:200]}")
                    last_error = "Auth failed (401) — invalid API key"
                    continue

                if response.status_code != 200:
                    logger.error(f"[OpenClaude] HTTP {response.status_code}: {response.text[:300]}")
                    last_error = f"HTTP {response.status_code}"
                    continue

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not content:
                    logger.error(f"[OpenClaude] 200 OK but empty content — model={model}, max_tokens={effective_max_tokens}, response={str(data)[:300]}")
                    last_error = "Empty content in response"
                    continue

                usage = data.get("usage", {})
                logger.info(f"[OpenClaude] OK — model={model}, prompt_tokens={usage.get('prompt_tokens','?')}, completion_tokens={usage.get('completion_tokens','?')}, total={usage.get('total_tokens','?')}")
                return {
                    "content": content.strip(),
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "model": model,
                    "provider": "open-claude",
                }

            except httpx.TimeoutException:
                last_error = f"Timeout after {settings.CLOUD_TIMEOUT}s"
                logger.error(f"[OpenClaude] Timeout after {settings.CLOUD_TIMEOUT}s for key {idx}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"[OpenClaude] Exception with key {idx}: {e}")

        raise Exception(f"[OpenClaude] All keys failed. Last error: {last_error}")

    @classmethod
    def _call_localai(cls, model: str, messages: List[Dict], temperature: float = 0.7) -> Dict[str, Any]:
        logger.info(f"[LocalAI] Requesting model={model}, messages={len(messages)}")

        try:
            from services.news_service import get_ai_status
            ai_status = get_ai_status()
            if "Đang rảnh" not in ai_status:
                raise Exception(f"[LocalAI] Busy: {ai_status}")
        except ImportError:
            pass

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if settings.MAX_TOKENS > 0:
            payload["max_tokens"] = settings.MAX_TOKENS

        try:
            response = requests.post(
                f"{settings.LOCALAI_URL}/v1/chat/completions",
                json=payload,
                timeout=settings.INFERENCE_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            raise Exception(f"[LocalAI] Timeout after {settings.INFERENCE_TIMEOUT}s")
        except Exception as e:
            raise Exception(f"[LocalAI] Connection error: {e}")

        if response.status_code != 200:
            raise Exception(f"[LocalAI] HTTP {response.status_code}: {response.text[:200]}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            logger.warning(f"[LocalAI] Empty content in response: {str(data)[:200]}")

        logger.info(f"[LocalAI] OK — model={model}, output_len={len(content)}")
        return {
            "content": content.strip() if content else "",
            "usage": data.get("usage", {}),
            "model": model,
            "provider": "localai",
        }

    @classmethod
    def chat_completion(cls, messages: List[Dict], temperature: float = 0.7,
                        max_tokens: int = 8192, prefer_cloud: bool = True,
                        local_model: str = None, task_type: str = None) -> Dict[str, Any]:
        """Fallback chain: Open Claude → LocalAI."""
        local_model = local_model or settings.MODEL_NAME
        errors = []

        logger.info(f"[ChatCompletion] task_type={task_type or 'auto'}, max_tokens={max_tokens}, prefer_cloud={prefer_cloud}")

        if prefer_cloud and settings.cloud_api_key_list:
            try:
                result = cls._call_open_claude(messages, temperature, max_tokens)
                if result["content"]:
                    return result
                logger.warning("[ChatCompletion] Open Claude returned empty content, falling back to LocalAI")
                errors.append("Open Claude: empty content")
            except Exception as e:
                errors.append(f"Open Claude: {e}")
                logger.warning(f"[ChatCompletion] Open Claude failed: {e}")

        try:
            result = cls._call_localai(local_model, messages, temperature)
            if result["content"]:
                return result
            logger.warning("[ChatCompletion] LocalAI returned empty content")
            errors.append("LocalAI: empty content")
        except Exception as e:
            errors.append(f"LocalAI: {e}")
            logger.warning(f"[ChatCompletion] LocalAI failed: {e}")

        raise Exception(f"All AI providers failed: {' | '.join(errors)}")

    @classmethod
    def quick_completion(cls, prompt: str, system_prompt: str = None,
                         temperature: float = 0.3, max_tokens: int = 500) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            result = cls.chat_completion(messages=messages, temperature=temperature, max_tokens=max_tokens)
            return result.get("content", "").strip()
        except Exception as e:
            logger.warning(f"[QuickCompletion] Failed: {e}")
            return ""

    @classmethod
    def is_cloud_available(cls) -> bool:
        return bool(settings.cloud_api_key_list)

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        status = {
            "open_claude": {
                "configured": bool(settings.cloud_api_key_list),
                "url": settings.CLOUD_LLM_API_URL,
                "model": settings.CLOUD_MODEL_NAME,
                "keys_count": len(settings.cloud_api_key_list),
            },
            "localai": {
                "configured": True,
                "url": settings.LOCALAI_URL,
                "model": settings.MODEL_NAME,
            },
        }

        if status["open_claude"]["configured"]:
            try:
                cls._call_open_claude(
                    [{"role": "user", "content": "Say OK in one word"}],
                    max_tokens=MIN_MAX_TOKENS,
                )
                status["open_claude"]["status"] = "healthy"
            except Exception as e:
                status["open_claude"]["status"] = f"error: {str(e)[:100]}"
                logger.error(f"[HealthCheck] Open Claude error: {e}")

        try:
            resp = requests.get(f"{settings.LOCALAI_URL}/readyz", timeout=5)
            status["localai"]["status"] = "healthy" if resp.status_code == 200 else f"unhealthy ({resp.status_code})"
        except Exception as e:
            status["localai"]["status"] = f"unreachable: {e}"

        return status
