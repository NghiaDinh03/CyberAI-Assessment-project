"""Cloud LLM Service — tinh giản thành Local LLM Service (100% Local-First).

Chỉ hỗ trợ kết nối trực tiếp đến Ollama và LocalAI chạy cục bộ (ngoại tuyến).
Bỏ hoàn toàn toàn bộ code API đám mây (Claude, Gemini, GPT).
"""

import json
import os
import time
import logging
import requests
import threading
from typing import Dict, Any, List, Optional
from core.config import settings

logger = logging.getLogger(__name__)

MIN_MAX_TOKENS = 10000

_LOCALAI_TO_OLLAMA: Dict[str, str] = {
    "gemma-3-4b-it":  "gemma3:4b",
    "gemma-3-12b-it": "gemma3:12b",
    "gemma4:latest":  "gemma4:latest",
    "gemma3n:e4b":    "gemma3n:e4b",
    "gemma3n:e2b":    "gemma3n:e2b",
}

# Cached list of Ollama models with TTL
_ollama_models_cache: List[str] = []
_ollama_cache_lock = threading.Lock()
_ollama_cache_ts: float = 0
_OLLAMA_CACHE_TTL = 60  # seconds

# Health check result cache
_health_cache: Dict[str, Any] = {}
_health_cache_ts: float = 0
_health_cache_lock = threading.Lock()
_HEALTH_CACHE_TTL = 30  # seconds


def get_ollama_models(timeout: int = 5) -> List[str]:
    """Fetch available model names from Ollama /api/tags with caching."""
    global _ollama_models_cache, _ollama_cache_ts
    now = time.time()
    if _ollama_models_cache and (now - _ollama_cache_ts) < _OLLAMA_CACHE_TTL:
        return _ollama_models_cache

    with _ollama_cache_lock:
        if _ollama_models_cache and (time.time() - _ollama_cache_ts) < _OLLAMA_CACHE_TTL:
            return _ollama_models_cache
        try:
            resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                _ollama_models_cache = models
                _ollama_cache_ts = time.time()
                return models
        except Exception as e:
            logger.debug(f"[Ollama] Failed to fetch models: {e}")
    return _ollama_models_cache


def resolve_ollama_model(requested: str) -> Optional[str]:
    """Resolve an Ollama model name, falling back to any available model if
    the requested one is not installed."""
    available = get_ollama_models()
    if not available:
        return requested

    if requested in available:
        return requested

    mapped = _LOCALAI_TO_OLLAMA.get(requested, requested)
    if mapped in available:
        return mapped

    for avail in available:
        if avail.startswith(mapped.split(":")[0] + ":"):
            return avail

    fallback = available[0]
    logger.warning(
        f"[Ollama] Model '{requested}' not found. Falling back to '{fallback}'"
    )
    return fallback


class CloudLLMService:
    """Wrapper class tương thích ngược. 
    Mặc dù tên là CloudLLMService nhưng đã được tinh giản 100% để chỉ chạy OFFLINE LOCAL model.
    """

    @classmethod
    def is_cloud_available(cls) -> bool:
        """Luôn trả về False để tắt toàn bộ Cloud API."""
        return False

    @classmethod
    def _call_localai(cls, model: str, messages: List[Dict], temperature: float = 0.7) -> Dict[str, Any]:
        logger.info(f"[LocalAI] Requesting model={model}, messages={len(messages)}")
        effective_max_tokens = settings.MAX_TOKENS if settings.MAX_TOKENS > 0 else 512

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            "stream": False,
        }

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
            raise Exception(f"[LocalAI] HTTP {response.status_code}: {err_text}")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "content": content.strip() if content else "",
            "usage": data.get("usage", {}),
            "model": model,
            "provider": "localai",
        }

    @staticmethod
    def _prepare_ollama_payload(model: str, messages: List[Dict], temperature: float, max_tokens: int):
        resolved = resolve_ollama_model(model)
        trimmed = messages[:1] + messages[-3:] if len(messages) > 4 else messages
        
        MAX_PROMPT_CHARS = 16000
        for i, msg in enumerate(trimmed):
            if msg.get("role") == "user" and len(msg.get("content", "")) > MAX_PROMPT_CHARS:
                trimmed[i] = {**msg, "content": msg["content"][:MAX_PROMPT_CHARS] + "\n\n[... content truncated to fit context ...]"}

        if max_tokens <= 0:
            effective_max_tokens = 4096
        else:
            effective_max_tokens = max(64, min(4096, max_tokens))
        return resolved, trimmed, effective_max_tokens

    @classmethod
    def _call_ollama(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                     max_tokens: int = 4096) -> Dict[str, Any]:
        ollama_url = settings.OLLAMA_URL
        resolved, trimmed, effective_max_tokens = cls._prepare_ollama_payload(
            model, messages, temperature, max_tokens
        )
        total_chars = sum(len(m.get("content", "")) for m in trimmed)
        ollama_timeout = settings.INFERENCE_TIMEOUT
        
        logger.info(f"[Ollama] Requesting model={resolved}, messages={len(trimmed)}, total_chars={total_chars}")
        try:
            response = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": resolved,
                    "messages": trimmed,
                    "options": {
                        "temperature": temperature,
                        "num_predict": effective_max_tokens,
                        "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "12")),
                        "num_ctx": 4096,
                    },
                    "stream": False,
                },
                timeout=ollama_timeout,
            )
        except requests.exceptions.Timeout:
            raise Exception(f"[Ollama] Timeout after {ollama_timeout}s — model '{resolved}' needs more time.")
        except Exception as e:
            raise Exception(f"[Ollama] Connection error: {e}")

        if response.status_code != 200:
            err_text = response.text[:300]
            raise Exception(f"[Ollama] HTTP {response.status_code}: {err_text}")

        data = response.json()
        msg = data.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning", "")
        if not content and reasoning:
            content = reasoning
            
        return {
            "content": content.strip() if content else "",
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            "model": resolved,
            "provider": "ollama",
        }

    @classmethod
    def call_ollama_stream(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                           max_tokens: int = 4096):
        """Stream tokens from Ollama."""
        ollama_url = settings.OLLAMA_URL
        resolved, trimmed, effective_max_tokens = cls._prepare_ollama_payload(
            model, messages, temperature, max_tokens
        )
        ollama_timeout = settings.INFERENCE_TIMEOUT
        logger.info(f"[Ollama-stream] model={resolved}, messages={len(trimmed)}")

        full_content = []
        usage = {}
        try:
            with requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": resolved,
                    "messages": trimmed,
                    "options": {
                        "temperature": temperature,
                        "num_predict": effective_max_tokens,
                        "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "12")),
                        "num_ctx": 4096,
                    },
                    "stream": True,
                },
                stream=True,
                timeout=ollama_timeout,
            ) as response:
                if response.status_code != 200:
                    err_text = response.text[:300] if hasattr(response, "text") else "unknown"
                    raise Exception(f"[Ollama-stream] HTTP {response.status_code}: {err_text}")

                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except Exception:
                        continue
                    msg = chunk.get("message", {}) or {}
                    token = msg.get("content", "") or msg.get("reasoning", "")
                    if token:
                        full_content.append(token)
                        yield {"type": "token", "content": token}
                    if chunk.get("done"):
                        usage = {
                            "prompt_tokens": chunk.get("prompt_eval_count", 0),
                            "completion_tokens": chunk.get("eval_count", 0),
                            "total_tokens": chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0),
                        }
                        break
        except requests.exceptions.Timeout:
            raise Exception(f"[Ollama-stream] Timeout after {ollama_timeout}s")

        final_content = "".join(full_content).strip()
        yield {
            "type": "done",
            "content": final_content,
            "usage": usage,
            "model": resolved,
            "provider": "ollama",
        }

    @classmethod
    def chat_completion(cls, messages: List[Dict], temperature: float = 0.7,
                        max_tokens: int = 8192, prefer_cloud: bool = False,
                        local_model: str = None, task_type: str = None,
                        cloud_model: str = None) -> Dict[str, Any]:
        """Tự động định tuyến cuộc gọi 100% sang Ollama (gemma4:latest)."""
        target_model = local_model or settings.MODEL_NAME or "gemma4:latest"
        if not target_model or not target_model.strip():
            target_model = "gemma4:latest"
        ollama_model = target_model if ":" in target_model else _LOCALAI_TO_OLLAMA.get(target_model, target_model)

        logger.info(f"[LocalChatCompletion] Requesting model={ollama_model}, task_type={task_type or 'auto'}")

        try:
            result = cls._call_ollama(ollama_model, messages, temperature)
            if result.get("content"):
                return result
        except Exception as e:
            logger.warning(f"[ChatCompletion] Ollama ({ollama_model}) failed: {e}")
            raise Exception(f"Ollama local inference failed: {e}")

        raise Exception(f"Ollama ({ollama_model}) returned empty content")

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
            return response.status_code == 200
        except Exception:
            return False

    @classmethod
    def ollama_health_check(cls, model: str = None, timeout: int = 5) -> bool:
        try:
            response = requests.get(
                f"{settings.OLLAMA_URL}/api/tags",
                timeout=timeout,
            )
            return response.status_code == 200
        except Exception:
            return False

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        global _health_cache, _health_cache_ts
        now = time.time()
        if _health_cache and (now - _health_cache_ts) < _HEALTH_CACHE_TTL:
            return _health_cache

        with _health_cache_lock:
            if _health_cache and (time.time() - _health_cache_ts) < _HEALTH_CACHE_TTL:
                return _health_cache
            result = cls._build_health_status()
            _health_cache = result
            _health_cache_ts = time.time()
            return result

    @classmethod
    def _build_health_status(cls) -> Dict[str, Any]:
        localai_url = getattr(settings, "LOCALAI_URL", None)
        status = {
            "open_claude": {
                "configured": False,
                "status": "disabled_local_only"
            },
            "localai": {
                "configured": bool(localai_url),
                "url": localai_url,
                "model": getattr(settings, "MODEL_NAME", "gemma4:latest"),
            },
        }

        if localai_url:
            try:
                resp = requests.get(f"{localai_url}/readyz", timeout=3)
                status["localai"]["status"] = "healthy" if resp.status_code == 200 else f"unhealthy ({resp.status_code})"
            except Exception as e:
                status["localai"]["status"] = f"unreachable: {e}"
        else:
            status["localai"]["status"] = "disabled_using_ollama"

        status["ollama"] = {"configured": True, "url": settings.OLLAMA_URL}
        try:
            resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                status["ollama"]["status"] = "healthy"
                status["ollama"]["models"] = model_names
            else:
                status["ollama"]["status"] = f"unhealthy ({resp.status_code})"
        except Exception as e:
            status["ollama"]["status"] = f"unreachable: {e}"

        return status
