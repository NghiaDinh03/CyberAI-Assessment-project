"""Cloud LLM Service — Open Claude (primary) with LocalAI fallback.

Model routing:
  news_translate  → gemini-2.5-pro       (best translation quality)
  news_summary    → gemini-3-flash-preview (fast, cheap for summaries)
  chat            → gemini-3-pro-preview  (balanced chat)
  iso_local       → LocalAI only          (ISO assessment pre-processing)
  iso_analysis    → gemini-2.5-pro        (deep ISO analysis)
  complex         → gemini-2.5-pro        (any heavy task)
  default         → gemini-3-pro-preview
"""

import time
import logging
import requests
import httpx
from typing import Dict, Any, List
from core.config import settings

logger = logging.getLogger(__name__)

MIN_MAX_TOKENS = 10000

# Task-type → preferred model on Open Claude
TASK_MODEL_MAP: Dict[str, str] = {
    "news_translate": "gemini-2.5-pro",
    "news_summary":   "gemini-3-flash-preview",
    "iso_analysis":   "gemini-2.5-pro",
    "complex":        "gemini-2.5-pro",
    "chat":           "gemini-3-pro-preview",
    "default":        "gemini-3-pro-preview",
}

# Tasks that must go to LocalAI only (never Cloud)
LOCAL_ONLY_TASKS = {"iso_local"}


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
    def _resolve_model(cls, task_type: str = None, model_override: str = None) -> str:
        """Return the best model for a given task_type."""
        if model_override:
            return model_override
        if task_type and task_type in TASK_MODEL_MAP:
            return TASK_MODEL_MAP[task_type]
        return settings.CLOUD_MODEL_NAME or TASK_MODEL_MAP["default"]

    @classmethod
    def _call_open_claude(cls, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 8192, model: str = None,
                          task_type: str = None) -> Dict[str, Any]:
        model = model or cls._resolve_model(task_type)
        keys = settings.cloud_api_key_list
        if not keys:
            raise Exception("[OpenClaude] No API key configured")

        effective_max_tokens = max(max_tokens, MIN_MAX_TOKENS)
        logger.info(f"[OpenClaude] Requesting model={model}, task={task_type or 'auto'}, "
                    f"max_tokens={effective_max_tokens}, messages={len(messages)}")

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
                    logger.error(f"[OpenClaude] 401 Unauthorized for key {idx} — "
                                 f"check API key validity. Response: {response.text[:200]}")
                    last_error = "Auth failed (401) — invalid API key"
                    continue  # NO cooldown — 401 is a config issue, not rate limit

                if response.status_code == 404:
                    logger.error(f"[OpenClaude] 404 — model '{model}' not found. "
                                 f"Response: {response.text[:200]}")
                    last_error = f"Model not found (404): {model}"
                    # Try fallback to default model
                    if model != settings.CLOUD_MODEL_NAME:
                        model = settings.CLOUD_MODEL_NAME
                        logger.warning(f"[OpenClaude] Retrying with default model: {model}")
                    continue

                if response.status_code != 200:
                    logger.error(f"[OpenClaude] HTTP {response.status_code}: {response.text[:300]}")
                    last_error = f"HTTP {response.status_code}"
                    continue

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not content:
                    logger.error(f"[OpenClaude] 200 OK but empty content — model={model}, "
                                 f"response={str(data)[:300]}")
                    last_error = "Empty content in response"
                    continue

                usage = data.get("usage", {})
                logger.info(
                    f"[OpenClaude] OK — model={model}, "
                    f"prompt_tokens={usage.get('prompt_tokens','?')}, "
                    f"completion_tokens={usage.get('completion_tokens','?')}, "
                    f"total={usage.get('total_tokens','?')}"
                )
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
    def localai_health_check(cls, model: str = None, timeout: int = 10) -> bool:
        """Quick health check — verify LocalAI is up and model is loadable.
        Returns True if healthy, False otherwise.
        """
        check_model = model or settings.SECURITY_MODEL_NAME
        try:
            response = requests.post(
                f"{settings.LOCALAI_URL}/v1/chat/completions",
                json={
                    "model": check_model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                    "temperature": 0,
                    "stream": False,
                },
                timeout=timeout,
            )
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"[LocalAI] Health check OK — model={check_model}, response='{content[:20]}'")
                return True
            logger.warning(f"[LocalAI] Health check HTTP {response.status_code}: {response.text[:150]}")
            return False
        except Exception as e:
            logger.warning(f"[LocalAI] Health check failed: {e}")
            return False

    @classmethod
    def _call_localai(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                      priority: bool = False) -> Dict[str, Any]:
        """Call LocalAI. priority=True: bypass news-busy check, used for ISO assessments."""
        logger.info(f"[LocalAI] Requesting model={model}, messages={len(messages)}, priority={priority}")

        try:
            from services.news_service import get_ai_status, set_ai_status
            ai_status = get_ai_status()
            if "Đang rảnh" not in ai_status:
                if priority:
                    logger.warning(f"[LocalAI] News busy ({ai_status[:60]}) — ISO priority, pausing")
                    set_ai_status("⏸️ Tạm dừng (ISO assessment ưu tiên)")
                    import time as _time
                    _time.sleep(1.5)
                else:
                    raise Exception(f"[LocalAI] Busy: {ai_status}")
        except ImportError:
            pass

        # Cap max_tokens for small models to avoid OOM
        effective_max_tokens = settings.MAX_TOKENS if settings.MAX_TOKENS > 0 else 2048

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "stream": False,
        }

        response = None
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
        finally:
            if priority:
                try:
                    from services.news_service import get_ai_status, set_ai_status
                    if "Tạm dừng" in get_ai_status():
                        set_ai_status("Đang rảnh")
                except ImportError:
                    pass

        if response.status_code != 200:
            err_text = response.text[:300]
            # Detect model-load failures specifically
            if "could not load model" in err_text or "rpc error" in err_text or "Canceled" in err_text:
                raise Exception(f"[LocalAI] Model load failed (OOM/RPC): {err_text[:150]}")
            raise Exception(f"[LocalAI] HTTP {response.status_code}: {err_text}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            logger.warning(f"[LocalAI] Empty content: {str(data)[:200]}")

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
        """Route to the best model based on task_type, then fallback LocalAI → Open Claude."""
        local_model = local_model or settings.MODEL_NAME
        errors = []

        # ISO local: try LocalAI first; if model fails to load, auto-fallback to cloud
        if task_type in LOCAL_ONLY_TASKS:
            logger.info(f"[ChatCompletion] task_type={task_type} → LocalAI (priority), cloud fallback on load-fail")
            try:
                result = cls._call_localai(local_model, messages, temperature, priority=True)
                if result["content"]:
                    return result
                errors.append("LocalAI: empty content")
            except Exception as e:
                err_str = str(e)
                errors.append(f"LocalAI: {err_str}")
                logger.warning(f"[ChatCompletion] LocalAI failed: {err_str}")

                # If model couldn't load (OOM/RPC error) AND cloud keys exist → fallback gracefully
                is_load_error = any(kw in err_str for kw in [
                    "Model load failed", "could not load model", "rpc error", "Canceled",
                    "HTTP 500", "Connection error"
                ])
                if is_load_error and settings.cloud_api_key_list:
                    logger.warning("[ChatCompletion] LocalAI model load error → auto-fallback to cloud for this request")
                    try:
                        cloud_model = cls._resolve_model("iso_analysis")
                        result = cls._call_open_claude(messages, temperature, max_tokens,
                                                       model=cloud_model, task_type="iso_analysis")
                        if result["content"]:
                            result["provider"] = f"cloud-fallback(localai-failed)"
                            return result
                    except Exception as ce:
                        errors.append(f"Cloud fallback: {ce}")
                        logger.error(f"[ChatCompletion] Cloud fallback also failed: {ce}")

            raise Exception(f"LocalAI failed for local-only task: {' | '.join(errors)}")

        model = cls._resolve_model(task_type)
        logger.info(f"[ChatCompletion] task_type={task_type or 'auto'}, model={model}, "
                    f"max_tokens={max_tokens}, prefer_cloud={prefer_cloud}")

        if prefer_cloud and settings.cloud_api_key_list:
            try:
                result = cls._call_open_claude(messages, temperature, max_tokens,
                                               model=model, task_type=task_type)
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
                         temperature: float = 0.3, max_tokens: int = 500,
                         task_type: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            result = cls.chat_completion(messages=messages, temperature=temperature,
                                         max_tokens=max_tokens, task_type=task_type)
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
                "default_model": settings.CLOUD_MODEL_NAME,
                "task_routing": TASK_MODEL_MAP,
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
