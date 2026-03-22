"""Cloud LLM Service — Multi-tier fallback: Open Claude → OpenRouter → LocalAI."""

import time
import logging
import requests
import httpx
from typing import Dict, Any, List, Optional
from core.config import settings

logger = logging.getLogger(__name__)


class CloudLLMService:
    _key_index: int = 0
    _cooldowns: Dict[int, float] = {}
    COOLDOWN_SECONDS: int = 60

    @classmethod
    def _get_next_key(cls) -> Optional[str]:
        keys = settings.cloud_api_key_list
        if not keys:
            return None
        now = time.time()
        for _ in range(len(keys)):
            idx = cls._key_index % len(keys)
            cls._key_index += 1
            if now - cls._cooldowns.get(idx, 0) < cls.COOLDOWN_SECONDS:
                continue
            return keys[idx]
        return None

    @classmethod
    def _mark_rate_limited(cls, key_idx: int):
        cls._cooldowns[key_idx] = time.time()
        logger.warning(f"Cloud API key {key_idx} rate limited, cooldown {cls.COOLDOWN_SECONDS}s")

    @classmethod
    def _call_open_claude(cls, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 8192, model: str = None) -> Dict[str, Any]:
        model = model or settings.CLOUD_MODEL_NAME
        keys = settings.cloud_api_key_list
        if not keys:
            raise Exception("Cloud API key not configured")

        last_error = None
        for _ in range(len(keys)):
            idx = cls._key_index % len(keys)
            current_key = keys[idx]
            cls._key_index += 1

            if time.time() - cls._cooldowns.get(idx, 0) < cls.COOLDOWN_SECONDS:
                continue

            try:
                response = httpx.post(
                    f"{settings.CLOUD_LLM_API_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": temperature,
                          "max_tokens": max_tokens, "stream": False},
                    timeout=settings.CLOUD_TIMEOUT,
                )

                if response.status_code == 429:
                    cls._mark_rate_limited(idx)
                    last_error = "Rate limited (429)"
                    continue

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    return {
                        "content": content.strip() if content else "",
                        "usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                  "completion_tokens": usage.get("completion_tokens", 0),
                                  "total_tokens": usage.get("total_tokens", 0)},
                        "model": model, "provider": "open-claude",
                    }

                logger.warning(f"Open Claude error ({response.status_code}): {response.text[:300]}")
                last_error = f"HTTP {response.status_code}"
            except httpx.TimeoutException:
                last_error = f"Timeout {settings.CLOUD_TIMEOUT}s"
            except Exception as e:
                last_error = str(e)

        raise Exception(f"Open Claude failed: {last_error}")

    @classmethod
    def _call_openrouter(cls, messages: List[Dict], temperature: float = 0.7,
                         max_tokens: int = 8192) -> Dict[str, Any]:
        keys = settings.openrouter_api_key_list
        if not keys:
            raise Exception("OpenRouter API key not configured")

        for key in keys:
            try:
                response = httpx.post(
                    f"{settings.OPENROUTER_API_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": settings.OPENROUTER_MODEL, "messages": messages,
                          "temperature": temperature, "max_tokens": max_tokens},
                    timeout=settings.CLOUD_TIMEOUT,
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    return {
                        "content": content.strip() if content else "",
                        "usage": {"prompt_tokens": usage.get("prompt_tokens", 0),
                                  "completion_tokens": usage.get("completion_tokens", 0),
                                  "total_tokens": usage.get("total_tokens", 0)},
                        "model": settings.OPENROUTER_MODEL, "provider": "openrouter",
                    }
                logger.warning(f"OpenRouter error ({response.status_code}): {response.text[:200]}")
            except Exception as e:
                logger.warning(f"OpenRouter exception: {e}")
        raise Exception("OpenRouter failed")

    @classmethod
    def _call_localai(cls, model: str, messages: List[Dict], temperature: float = 0.7) -> Dict[str, Any]:
        try:
            from services.news_service import get_ai_status
            ai_status = get_ai_status()
            if "Đang rảnh" not in ai_status:
                raise Exception(f"LocalAI busy: {ai_status}")
        except ImportError:
            pass

        payload = {"model": model, "messages": messages, "temperature": temperature, "stream": False}
        if settings.MAX_TOKENS > 0:
            payload["max_tokens"] = settings.MAX_TOKENS

        response = requests.post(
            f"{settings.LOCALAI_URL}/v1/chat/completions", json=payload, timeout=settings.INFERENCE_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"content": content.strip() if content else "", "usage": data.get("usage", {}),
                    "model": model, "provider": "localai"}
        raise Exception(f"LocalAI error ({response.status_code}): {response.text[:200]}")

    @classmethod
    def chat_completion(cls, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 8192,
                        prefer_cloud: bool = True, local_model: str = None) -> Dict[str, Any]:
        """Multi-tier fallback: Open Claude → OpenRouter → LocalAI."""
        local_model = local_model or settings.MODEL_NAME
        errors = []

        if prefer_cloud:
            if settings.cloud_api_key_list:
                try:
                    result = cls._call_open_claude(messages, temperature, max_tokens)
                    if result["content"]:
                        return result
                except Exception as e:
                    errors.append(f"Open Claude: {e}")
                    logger.warning(f"Open Claude failed: {e}")

            if settings.openrouter_api_key_list:
                try:
                    result = cls._call_openrouter(messages, temperature, max_tokens)
                    if result["content"]:
                        return result
                except Exception as e:
                    errors.append(f"OpenRouter: {e}")
                    logger.warning(f"OpenRouter failed: {e}")

        try:
            result = cls._call_localai(local_model, messages, temperature)
            if result["content"]:
                return result
        except Exception as e:
            errors.append(f"LocalAI: {e}")
            logger.warning(f"LocalAI failed: {e}")

        raise Exception(f"All AI providers failed: {' | '.join(errors)}")

    @classmethod
    def quick_completion(cls, prompt: str, system_prompt: str = None,
                         temperature: float = 0.3, max_tokens: int = 100) -> str:
        """Quick helper for lightweight tasks (tagging, classification). Returns string."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            result = cls.chat_completion(messages=messages, temperature=temperature, max_tokens=max_tokens)
            return result.get("content", "").strip()
        except Exception as e:
            logger.warning(f"Quick completion failed: {e}")
            return ""

    @classmethod
    def is_cloud_available(cls) -> bool:
        return bool(settings.cloud_api_key_list) or bool(settings.openrouter_api_key_list)

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        status = {
            "open_claude": {
                "configured": bool(settings.cloud_api_key_list),
                "url": settings.CLOUD_LLM_API_URL,
                "model": settings.CLOUD_MODEL_NAME,
                "keys": len(settings.cloud_api_key_list),
            },
            "openrouter": {
                "configured": bool(settings.openrouter_api_key_list),
                "url": settings.OPENROUTER_API_URL,
                "model": settings.OPENROUTER_MODEL,
                "keys": len(settings.openrouter_api_key_list),
            },
            "localai": {
                "configured": True, "url": settings.LOCALAI_URL, "model": settings.MODEL_NAME,
            },
        }

        if status["open_claude"]["configured"]:
            try:
                cls._call_open_claude([{"role": "user", "content": "ping"}], max_tokens=5)
                status["open_claude"]["status"] = "healthy"
            except Exception as e:
                status["open_claude"]["status"] = f"error: {str(e)[:100]}"

        try:
            resp = requests.get(f"{settings.LOCALAI_URL}/readyz", timeout=5)
            status["localai"]["status"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except Exception:
            status["localai"]["status"] = "unreachable"

        return status
