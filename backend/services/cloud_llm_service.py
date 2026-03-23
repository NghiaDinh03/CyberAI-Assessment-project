"""Cloud LLM Service — Open Claude API (primary) with Gemini & LocalAI fallback."""

import time
import logging
import requests
import httpx
import re
from typing import Dict, Any, List
from core.config import settings

logger = logging.getLogger(__name__)

# Minimum tokens to send — open-claude.com rejects requests with very low max_tokens
MIN_MAX_TOKENS = 10000


def classify_task_complexity(messages: List[Dict], max_tokens: int = 8192) -> str:
    full_text = " ".join(m.get("content", "") for m in messages).lower()
    total_chars = len(full_text)

    simple_patterns = [
        r"gán.*tag", r"phân loại", r"classify", r"tag.*tin",
        r"chỉ.*1 từ", r"1-2 từ", r"đúng 1", r"only.*one word",
        r"yes or no", r"true or false", r"ping",
    ]
    for pattern in simple_patterns:
        if re.search(pattern, full_text):
            return "simple"

    complex_patterns = [
        r"dịch.*toàn bộ", r"dịch.*đầy đủ", r"translate.*entire",
        r"biên dịch", r"biên tập.*bài báo",
        r"phân tích.*chi tiết", r"analyze.*detail",
        r"viết.*bài", r"write.*article",
    ]
    for pattern in complex_patterns:
        if re.search(pattern, full_text):
            return "complex"

    if max_tokens <= 200:
        return "simple"
    if max_tokens >= 8000 or total_chars > 5000:
        return "complex"

    return "medium"


class CloudLLMService:
    _key_index: int = 0
    # Cooldown only for rate-limit (429), NOT for auth errors
    _rate_limit_cooldowns: Dict[int, float] = {}
    RATE_LIMIT_COOLDOWN: int = 60

    @classmethod
    def _is_rate_limited(cls, key_idx: int) -> bool:
        return time.time() - cls._rate_limit_cooldowns.get(key_idx, 0) < cls.RATE_LIMIT_COOLDOWN

    @classmethod
    def _mark_rate_limited(cls, key_idx: int):
        cls._rate_limit_cooldowns[key_idx] = time.time()
        logger.warning(f"Open Claude key {key_idx} rate limited (429), cooldown {cls.RATE_LIMIT_COOLDOWN}s")

    @classmethod
    def _call_open_claude(cls, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 8192, model: str = None) -> Dict[str, Any]:
        model = model or settings.CLOUD_MODEL_NAME
        keys = settings.cloud_api_key_list
        if not keys:
            raise Exception("Cloud API key not configured")

        # Enforce minimum max_tokens — API rejects very small values
        effective_max_tokens = max(max_tokens, MIN_MAX_TOKENS)

        last_error = None
        for _ in range(len(keys)):
            idx = cls._key_index % len(keys)
            current_key = keys[idx]
            cls._key_index += 1

            # Skip only if rate limited (429), NOT for auth errors
            if cls._is_rate_limited(idx):
                last_error = f"Key {idx} in cooldown"
                continue

            try:
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

                if response.status_code == 429:
                    cls._mark_rate_limited(idx)
                    last_error = "Rate limited (429)"
                    continue

                if response.status_code == 401:
                    logger.warning(f"Open Claude 401 Unauthorized for key {idx} — key may be invalid")
                    last_error = "Auth failed (401)"
                    # Do NOT put in cooldown for 401 — it's a permanent key error, not temporary
                    continue

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if not content:
                        logger.warning(f"Open Claude 200 but empty content. model={model}, max_tokens={effective_max_tokens}, response={str(data)[:300]}")
                        last_error = "Empty content"
                        continue
                    usage = data.get("usage", {})
                    logger.info(f"Open Claude OK — model={model}, tokens={usage.get('total_tokens', '?')}")
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

                logger.warning(f"Open Claude HTTP {response.status_code}: {response.text[:300]}")
                last_error = f"HTTP {response.status_code}"

            except httpx.TimeoutException:
                last_error = f"Timeout after {settings.CLOUD_TIMEOUT}s"
                logger.warning(f"Open Claude timeout after {settings.CLOUD_TIMEOUT}s")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Open Claude exception: {e}")

        raise Exception(f"Open Claude failed: {last_error}")

    @classmethod
    def _call_gemini_direct(cls, messages: List[Dict], temperature: float = 0.7,
                            max_tokens: int = 8192) -> Dict[str, Any]:
        gemini_keys = [k.strip() for k in settings.GEMINI_API_KEYS.split(",")
                       if k.strip() and k.strip() not in ("your_gemini_api_key_here", "")]
        if not gemini_keys:
            raise Exception("Gemini API key not configured")

        gemini_contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            elif role == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                gemini_contents.append({"role": "user", "parts": [{"text": content}]})

        for key in gemini_keys:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
                payload = {
                    "contents": gemini_contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max(max_tokens, MIN_MAX_TOKENS),
                    },
                }
                if system_instruction:
                    payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

                response = httpx.post(url, json=payload, timeout=settings.CLOUD_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if content:
                            usage = data.get("usageMetadata", {})
                            logger.info(f"Gemini Direct OK — tokens={usage.get('totalTokenCount', '?')}")
                            return {
                                "content": content.strip(),
                                "usage": {
                                    "prompt_tokens": usage.get("promptTokenCount", 0),
                                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                                    "total_tokens": usage.get("totalTokenCount", 0),
                                },
                                "model": "gemini-2.0-flash",
                                "provider": "gemini-direct",
                            }

                if response.status_code == 429:
                    logger.warning("Gemini rate limited (429)")
                    continue

                logger.warning(f"Gemini HTTP {response.status_code}: {response.text[:200]}")
            except httpx.TimeoutException:
                logger.warning("Gemini Direct timeout")
            except Exception as e:
                logger.warning(f"Gemini Direct exception: {e}")

        raise Exception("Gemini Direct failed")

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
            return {
                "content": content.strip() if content else "",
                "usage": data.get("usage", {}),
                "model": model,
                "provider": "localai",
            }
        raise Exception(f"LocalAI error ({response.status_code}): {response.text[:200]}")

    @classmethod
    def chat_completion(cls, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 8192,
                        prefer_cloud: bool = True, local_model: str = None,
                        task_type: str = None) -> Dict[str, Any]:
        """Fallback chain: Open Claude → Gemini Direct → LocalAI."""
        local_model = local_model or settings.MODEL_NAME
        errors = []

        if task_type is None:
            task_type = classify_task_complexity(messages, max_tokens)
        logger.info(f"[Routing] Task: {task_type}, max_tokens={max_tokens}")

        if prefer_cloud:
            if settings.cloud_api_key_list:
                try:
                    result = cls._call_open_claude(messages, temperature, max_tokens)
                    if result["content"]:
                        return result
                except Exception as e:
                    errors.append(f"Open Claude: {e}")
                    logger.warning(f"Open Claude failed: {e}")

            if settings.GEMINI_API_KEYS and settings.GEMINI_API_KEYS.strip():
                try:
                    result = cls._call_gemini_direct(messages, temperature, max_tokens)
                    if result["content"]:
                        return result
                except Exception as e:
                    errors.append(f"Gemini Direct: {e}")
                    logger.warning(f"Gemini Direct failed: {e}")

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
        return bool(settings.cloud_api_key_list) or bool(
            settings.GEMINI_API_KEYS and settings.GEMINI_API_KEYS.strip())

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        status = {
            "open_claude": {
                "configured": bool(settings.cloud_api_key_list),
                "url": settings.CLOUD_LLM_API_URL,
                "model": settings.CLOUD_MODEL_NAME,
                "keys": len(settings.cloud_api_key_list),
            },
            "gemini_direct": {
                "configured": bool(settings.GEMINI_API_KEYS and settings.GEMINI_API_KEYS.strip()),
                "model": "gemini-2.0-flash",
            },
            "localai": {
                "configured": True,
                "url": settings.LOCALAI_URL,
                "model": settings.MODEL_NAME,
            },
        }

        if status["open_claude"]["configured"]:
            try:
                cls._call_open_claude([{"role": "user", "content": "Say OK"}], max_tokens=MIN_MAX_TOKENS)
                status["open_claude"]["status"] = "healthy"
            except Exception as e:
                status["open_claude"]["status"] = f"error: {str(e)[:100]}"

        try:
            resp = requests.get(f"{settings.LOCALAI_URL}/readyz", timeout=5)
            status["localai"]["status"] = "healthy" if resp.status_code == 200 else "unhealthy"
        except Exception:
            status["localai"]["status"] = "unreachable"

        return status
