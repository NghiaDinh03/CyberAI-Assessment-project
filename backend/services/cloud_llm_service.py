"""Cloud LLM Service — routes to Cloud (Open Claude), LocalAI, or Ollama."""

import time
import logging
import requests
import httpx
from typing import Dict, Any, List
from core.config import settings
from services.model_guard import ModelGuard

logger = logging.getLogger(__name__)

MIN_MAX_TOKENS = 10000

TASK_MODEL_MAP: Dict[str, str] = {
    "iso_analysis":   "gemini-3-flash-preview",
    "complex":        "gemini-3-pro-preview",
    "chat":           "gemini-3-flash-preview",
    "default":        "gemini-3-flash-preview",
}

FALLBACK_CHAIN: list = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gpt-5-mini",
    "claude-sonnet-4",
    "gpt-5",
]

LOCAL_ONLY_TASKS = {"iso_local"}

_LOCALAI_TO_OLLAMA: Dict[str, str] = {
    "gemma-3-4b-it":  "gemma3:4b",
    "gemma-3-12b-it": "gemma3:12b",
    "gemma-4-31b-it": "gemma4:31b",
}


class CloudLLMService:
    _key_index: int = 0
    _rate_limit_cooldowns: Dict[int, float] = {}
    RATE_LIMIT_COOLDOWN: int = 30

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
        if model_override:
            return model_override
        if task_type and task_type in TASK_MODEL_MAP:
            return TASK_MODEL_MAP[task_type]
        return settings.CLOUD_MODEL_NAME or TASK_MODEL_MAP["default"]

    @classmethod
    def _call_open_claude(cls, messages: List[Dict], temperature: float = 0.7,
                          max_tokens: int = 8192, model: str = None,
                          task_type: str = None) -> Dict[str, Any]:
        requested_model = model or cls._resolve_model(task_type)
        keys = settings.cloud_api_key_list
        if not keys:
            raise Exception("[OpenClaude] No API key configured")

        effective_max_tokens = max(max_tokens, MIN_MAX_TOKENS)

        fallback_models = [requested_model]
        for m in FALLBACK_CHAIN:
            if m != requested_model:
                fallback_models.append(m)

        last_error = None
        for model_attempt, current_model in enumerate(fallback_models):
            logger.info(f"[OpenClaude] Requesting model={current_model}, task={task_type or 'auto'}, "
                        f"max_tokens={effective_max_tokens}, messages={len(messages)}"
                        + (f" [fallback #{model_attempt}]" if model_attempt > 0 else ""))

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
                    logger.debug(f"[OpenClaude] Key {idx}, model={current_model}")
                    response = httpx.post(
                        f"{settings.CLOUD_LLM_API_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {current_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": current_model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": effective_max_tokens,
                            "stream": False,
                        },
                        timeout=settings.CLOUD_TIMEOUT,
                    )
                    logger.debug(f"[OpenClaude] Response status: {response.status_code}")
                except httpx.TimeoutException:
                    last_error = f"Timeout after {settings.CLOUD_TIMEOUT}s"
                    logger.warning(f"[OpenClaude] Timeout model={current_model}, key {idx}")
                    continue
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"[OpenClaude] Exception model={current_model}, key {idx}: {e}")
                    continue

                if response.status_code == 429:
                    cls._mark_rate_limited(idx)
                    last_error = "Rate limited (429)"
                    continue

                if response.status_code == 401:
                    logger.error(f"[OpenClaude] 401 Unauthorized for key {idx}")
                    last_error = "Auth failed (401) — invalid API key"
                    continue

                if response.status_code in (404, 400):
                    logger.warning(f"[OpenClaude] {response.status_code} for model='{current_model}' — trying next fallback")
                    last_error = f"Model unavailable ({response.status_code}): {current_model}"
                    break

                if response.status_code in (500, 502, 503):
                    logger.warning(f"[OpenClaude] Server error {response.status_code} for model='{current_model}' — trying next fallback")
                    last_error = f"Server error ({response.status_code})"
                    break

                if response.status_code != 200:
                    logger.error(f"[OpenClaude] HTTP {response.status_code}: {response.text[:300]}")
                    last_error = f"HTTP {response.status_code}"
                    continue

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not content:
                    logger.error(f"[OpenClaude] 200 OK but empty content — model={current_model}")
                    last_error = "Empty content in response"
                    continue

                usage = data.get("usage", {})
                logger.info(
                    f"[OpenClaude] OK — model={current_model}, "
                    f"prompt_tokens={usage.get('prompt_tokens','?')}, "
                    f"completion_tokens={usage.get('completion_tokens','?')}, "
                    f"total={usage.get('total_tokens','?')}"
                    + (f" [fallback from {requested_model}]" if current_model != requested_model else "")
                )
                return {
                    "content": content.strip(),
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "model": current_model,
                    "provider": "open-claude",
                }

        raise Exception(f"[OpenClaude] All models/keys failed. Last error: {last_error}")

    @classmethod
    def localai_health_check(cls, model: str = None, timeout: int = 10) -> bool:
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
        logger.info(f"[LocalAI] Requesting model={model}, messages={len(messages)}, priority={priority}")

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
        if response.status_code != 200:
            err_text = response.text[:300]
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
    def _call_ollama(cls, model: str, messages: List[Dict], temperature: float = 0.7) -> Dict[str, Any]:
        ollama_url = settings.OLLAMA_URL
        logger.info(f"[Ollama] Requesting model={model}, messages={len(messages)}")
        effective_max_tokens = settings.MAX_TOKENS if settings.MAX_TOKENS > 0 else 512
        try:
            response = requests.post(
                f"{ollama_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": effective_max_tokens,
                    "stream": False,
                },
                timeout=settings.INFERENCE_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            raise Exception(f"[Ollama] Timeout after {settings.INFERENCE_TIMEOUT}s")
        except Exception as e:
            raise Exception(f"[Ollama] Connection error: {e}")

        if response.status_code != 200:
            err_text = response.text[:300]
            raise Exception(f"[Ollama] HTTP {response.status_code}: {err_text}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            logger.warning(f"[Ollama] Empty content: {str(data)[:200]}")

        logger.info(f"[Ollama] OK — model={model}, output_len={len(content)}")
        return {
            "content": content.strip() if content else "",
            "usage": data.get("usage", {}),
            "model": model,
            "provider": "ollama",
        }

    @classmethod
    def ollama_health_check(cls, model: str = None, timeout: int = 5) -> bool:
        try:
            response = requests.get(
                f"{settings.OLLAMA_URL}/api/tags",
                timeout=timeout,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                logger.info(f"[Ollama] Health check OK — {len(models)} model(s) available: {models[:5]}")
                return True
            return False
        except Exception as e:
            logger.warning(f"[Ollama] Health check failed: {e}")
            return False

    @classmethod
    def chat_completion(cls, messages: List[Dict], temperature: float = 0.7,
                        max_tokens: int = 8192, prefer_cloud: bool = True,
                        local_model: str = None, task_type: str = None,
                        cloud_model: str = None) -> Dict[str, Any]:
        local_model = local_model or settings.MODEL_NAME
        errors = []

        OLLAMA_MODEL_PREFIXES = ("gemma3:", "gemma3n:", "gemma4:", "phi4:", "llama3:", "mistral:", "qwen3:")
        LOCALAI_GEMMA_IDS = {"gemma-3-4b-it", "gemma-3-12b-it", "gemma-4-31b-it"}
        is_ollama_model = (
            any(local_model.startswith(p) for p in OLLAMA_MODEL_PREFIXES) or
            local_model in LOCALAI_GEMMA_IDS
        )

        force_local = not prefer_cloud
        effective_prefer_cloud = prefer_cloud and not settings.PREFER_LOCAL and not force_local

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

        model = cloud_model or cls._resolve_model(task_type)
        logger.info(f"[ChatCompletion] task_type={task_type or 'auto'}, model={model}, "
                    f"max_tokens={max_tokens}, prefer_cloud={effective_prefer_cloud}, prefer_local={settings.PREFER_LOCAL}")

        if settings.LOCAL_ONLY_MODE and not ModelGuard.is_ready():
            raise Exception("Local-only mode enabled nhưng thiếu file model. Kiểm tra thư mục ./models")

        if settings.LOCAL_ONLY_MODE:
            try:
                result = cls._call_localai(local_model, messages, temperature)
                if result.get("content"):
                    return result
                errors.append("Local-only: empty content")
            except Exception as e:
                errors.append(f"Local-only: {e}")
            raise Exception(f"Local-only mode: LocalAI failed: {' | '.join(errors)}")

        if settings.PREFER_LOCAL or force_local:
            if is_ollama_model:
                try:
                    ollama_model = local_model if ":" in local_model else _LOCALAI_TO_OLLAMA.get(local_model, local_model)
                    result = cls._call_ollama(ollama_model, messages, temperature)
                    if result.get("content"):
                        return result
                    errors.append("Ollama: empty content")
                except Exception as e:
                    errors.append(f"Ollama: {e}")
                    logger.warning(f"[ChatCompletion] Ollama failed for {local_model}: {e}")
            else:
                try:
                    result = cls._call_localai(local_model, messages, temperature)
                    if result.get("content"):
                        return result
                    logger.warning("[ChatCompletion] LocalAI returned empty content, trying cloud")
                    errors.append("LocalAI: empty content")
                except Exception as e:
                    errors.append(f"LocalAI: {e}")
                    logger.warning(f"[ChatCompletion] LocalAI failed: {e}")

            if force_local:
                err_msg = " | ".join(errors)
                raise Exception(
                    f"⚠️ LocalAI không khả dụng: {err_msg}. "
                    "Vui lòng tải model GGUF vào thư mục ./models hoặc chọn model Cloud ở dropdown."
                )

            if settings.cloud_api_key_list:
                try:
                    result = cls._call_open_claude(messages, temperature, max_tokens,
                                                   model=model, task_type=task_type)
                    if result.get("content"):
                        result["provider"] = result.get("provider", "open-claude") + "-fallback"
                        return result
                    logger.warning("[ChatCompletion] Cloud returned empty content after LocalAI fail")
                    errors.append("Open Claude: empty content")
                except Exception as e:
                    errors.append(f"Open Claude: {e}")
                    logger.warning(f"[ChatCompletion] Open Claude failed after LocalAI: {e}")

        else:
            if settings.cloud_api_key_list:
                try:
                    result = cls._call_open_claude(messages, temperature, max_tokens,
                                                   model=model, task_type=task_type)
                    if result.get("content"):
                        return result
                    logger.warning("[ChatCompletion] Open Claude returned empty content, falling back to LocalAI")
                    errors.append("Open Claude: empty content")
                except Exception as e:
                    errors.append(f"Open Claude: {e}")
                    logger.warning(f"[ChatCompletion] Open Claude failed: {e}")

            try:
                result = cls._call_localai(local_model, messages, temperature)
                if result.get("content"):
                    result["provider"] = result.get("provider", "localai") + "-fallback"
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
                keys = settings.cloud_api_key_list
                if keys:
                    resp = httpx.get(
                        f"{settings.CLOUD_LLM_API_URL}/models",
                        headers={"Authorization": f"Bearer {keys[0]}"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        status["open_claude"]["status"] = "healthy"
                    else:
                        status["open_claude"]["status"] = f"http_{resp.status_code}"
                else:
                    status["open_claude"]["status"] = "no_keys"
            except Exception as e:
                status["open_claude"]["status"] = f"unreachable: {str(e)[:80]}"

        try:
            resp = requests.get(f"{settings.LOCALAI_URL}/readyz", timeout=5)
            status["localai"]["status"] = "healthy" if resp.status_code == 200 else f"unhealthy ({resp.status_code})"
        except Exception as e:
            status["localai"]["status"] = f"unreachable: {e}"

        status["ollama"] = {"configured": True, "url": settings.OLLAMA_URL}
        try:
            resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                gemma_model = next((m for m in models if "gemma3n" in m.get("name", "") or "gemma3n:e4b" in m.get("name", "")), None)
                status["ollama"]["status"] = "healthy"
                status["ollama"]["models"] = model_names
                status["ollama"]["gemma3n_e4b"] = {
                    "available": gemma_model is not None,
                    "name": gemma_model.get("name", "") if gemma_model else "gemma3n:e4b",
                    "size": gemma_model.get("size", 0) if gemma_model else 0,
                }
            else:
                status["ollama"]["status"] = f"unhealthy ({resp.status_code})"
        except Exception as e:
            status["ollama"]["status"] = f"unreachable: {e}"

        return status
