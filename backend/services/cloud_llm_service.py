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
    "gemma-3-4b-it":       "gemma3:4b",
    "gemma-3-12b-it":      "gemma3:12b",
    "gemma4:latest":       "gemma4:latest",
    "gemma3n:e4b":         "gemma3n:e4b",
    "gemma3n:e2b":         "gemma3n:e2b",
    "qwen2.5-coder:7b":    "qwen2.5-coder:7b",
    "qwen2.5-coder:latest": "qwen2.5-coder:7b",
    "qwen2.5-coder":       "qwen2.5-coder:7b",
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
        """Return True only if Google AI Studio API key or Cloud API key is configured."""
        if getattr(settings, "LOCAL_ONLY_MODE", False):
            return False
        key = getattr(settings, "GOOGLE_AI_STUDIO_API_KEY", "") or getattr(settings, "CLOUD_API_KEYS", "")
        return bool(key and key.strip())

    @classmethod
    def _call_google_ai_studio(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                               max_tokens: int = 4096) -> Dict[str, Any]:
        """Call Google AI Studio (Gemini free tier) via standard REST v1beta API."""
        api_key = getattr(settings, "GOOGLE_AI_STUDIO_API_KEY", "") or getattr(settings, "CLOUD_API_KEYS", "")
        if not api_key or not api_key.strip():
            raise ValueError("GOOGLE_AI_STUDIO_API_KEY is not configured")

        target_model = model or getattr(settings, "GOOGLE_AI_STUDIO_MODEL", "gemini-2.5-flash")
        if ":" in target_model:
            target_model = target_model.split(":")[0]
        if not target_model.startswith("gemini-"):
            target_model = getattr(settings, "GOOGLE_AI_STUDIO_MODEL", "gemini-2.5-flash")

        base_url = getattr(settings, "GOOGLE_AI_STUDIO_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        endpoint = f"{base_url}/models/{target_model}:generateContent?key={api_key.strip()}"

        system_instruction = None
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content_str = msg.get("content", "")
            if not content_str:
                continue
            if role == "system":
                system_instruction = {"parts": [{"text": content_str}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content_str}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content_str}]})

        if not contents and system_instruction:
            contents.append({"role": "user", "parts": [{"text": "Tiếp tục phân tích."}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": max(0.0, min(1.0, temperature)),
                "maxOutputTokens": max_tokens if max_tokens > 0 else 4096,
            }
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        timeout = getattr(settings, "CLOUD_TIMEOUT", 60)
        logger.info(f"[GoogleAIStudio] Calling model={target_model} with {len(contents)} turns")
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise Exception(f"Google AI Studio error {resp.status_code}: {resp.text[:250]}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise Exception("Google AI Studio returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_out = "".join(p.get("text", "") for p in parts if "text" in p)

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)

        return {
            "content": text_out.strip(),
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "model": target_model,
            "provider": "google_ai_studio",
        }

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
        trimmed = messages[:1] + messages[-9:] if len(messages) > 10 else messages
        
        MAX_PROMPT_CHARS = 16000
        for i, msg in enumerate(trimmed):
            if msg.get("role") == "user" and len(msg.get("content", "")) > MAX_PROMPT_CHARS:
                trimmed[i] = {**msg, "content": msg["content"][:MAX_PROMPT_CHARS] + "\n\n[... content truncated to fit context ...]"}

        max_cap = int(os.getenv("OLLAMA_MAX_TOKENS", "8192"))
        if max_tokens <= 0:
            effective_max_tokens = 4096
        else:
            effective_max_tokens = max(64, min(max_cap, max_tokens))
        return resolved, trimmed, effective_max_tokens

    _active_ollama_url: Optional[str] = None

    @classmethod
    def _get_candidate_ollama_urls(cls) -> List[str]:
        if cls._active_ollama_url:
            return [cls._active_ollama_url]
        env_url = (os.getenv("OLLAMA_URL") or getattr(settings, "OLLAMA_URL", "") or "").rstrip('/')
        candidates = []
        # In Docker desktop environment, host.docker.internal connects directly to host Ollama
        for url in ["http://host.docker.internal:11434", env_url, "http://127.0.0.1:11434", "http://ollama:11434"]:
            if url and url not in candidates:
                candidates.append(url)
        return candidates

    @classmethod
    def _call_ollama(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                     max_tokens: int = 4096) -> Dict[str, Any]:
        resolved, trimmed, effective_max_tokens = cls._prepare_ollama_payload(
            model, messages, temperature, max_tokens
        )
        total_chars = sum(len(m.get("content", "")) for m in trimmed)
        ollama_timeout = settings.INFERENCE_TIMEOUT
        
        logger.info(f"[Ollama] Requesting model={resolved}, messages={len(trimmed)}, total_chars={total_chars}")
        response = None
        last_error = None
        for ollama_url in cls._get_candidate_ollama_urls():
            try:
                response = requests.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": resolved,
                        "messages": trimmed,
                        "options": {
                            "temperature": temperature,
                            "num_predict": effective_max_tokens,
                            "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "10")),
                            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                        },
                        "stream": False,
                    },
                    timeout=(5, ollama_timeout),
                )
                if response.status_code == 200:
                    cls._active_ollama_url = ollama_url
                    break
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {ollama_timeout}s — model '{resolved}' needs more time."
                logger.warning(f"[Ollama] URL {ollama_url} timed out, trying next candidate...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Ollama] URL {ollama_url} failed ({e}), trying next candidate...")

        if response is None or response.status_code != 200:
            err_text = response.text[:300] if response is not None else (last_error or "All Ollama endpoints unreachable")
            raise Exception(f"[Ollama] Connection error: {err_text}")

        data = response.json()
        msg = data.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning", "") or msg.get("thinking", "")
        if not content and reasoning:
            content = reasoning
            
        actual_model = data.get("model") or resolved
        return {
            "content": content.strip() if content else "",
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                "total_duration_ns": data.get("total_duration", 0),
                "load_duration_ns": data.get("load_duration", 0),
                "prompt_eval_duration_ns": data.get("prompt_eval_duration", 0),
                "eval_duration_ns": data.get("eval_duration", 0),
            },
            "model": actual_model,
            "provider": "ollama",
        }

    @classmethod
    def call_ollama_stream(cls, model: str, messages: List[Dict], temperature: float = 0.7,
                           max_tokens: int = 4096):
        """Stream tokens from Ollama with candidate URL auto-failover."""
        resolved, trimmed, effective_max_tokens = cls._prepare_ollama_payload(
            model, messages, temperature, max_tokens
        )
        ollama_timeout = settings.INFERENCE_TIMEOUT
        logger.info(f"[Ollama-stream] model={resolved}, messages={len(trimmed)}")

        full_content = []
        usage = {}
        stream_success = False
        last_error = None

        for ollama_url in cls._get_candidate_ollama_urls():
            try:
                with requests.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": resolved,
                        "messages": trimmed,
                        "options": {
                            "temperature": temperature,
                            "num_predict": effective_max_tokens,
                            "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "10")),
                            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                        },
                        "stream": True,
                    },
                    stream=True,
                    timeout=ollama_timeout,
                ) as response:
                    if response.status_code != 200:
                        err_text = response.text[:300] if hasattr(response, "text") else "unknown"
                        last_error = f"HTTP {response.status_code}: {err_text}"
                        logger.warning(f"[Ollama-stream] URL {ollama_url} returned {response.status_code}, trying next...")
                        continue

                    thinking_buffer = []
                    for raw_line in response.iter_lines(decode_unicode=True):
                        if not raw_line:
                            continue
                        try:
                            chunk = json.loads(raw_line)
                        except Exception:
                            continue
                        msg = chunk.get("message", {}) or {}
                        content_tok = msg.get("content", "")
                        thinking_tok = msg.get("thinking", "") or msg.get("reasoning", "")
                        if content_tok:
                            full_content.append(content_tok)
                            yield {"type": "token", "content": content_tok}
                        elif thinking_tok:
                            thinking_buffer.append(thinking_tok)
                            yield {"type": "thinking_token", "content": thinking_tok}
                        if chunk.get("done"):
                            usage = {
                                "prompt_tokens": chunk.get("prompt_eval_count", 0),
                                "completion_tokens": chunk.get("eval_count", 0),
                                "total_tokens": chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0),
                            }
                            break
                    stream_success = True
                    break
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {ollama_timeout}s"
                logger.warning(f"[Ollama-stream] URL {ollama_url} timed out, trying next...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[Ollama-stream] URL {ollama_url} failed ({e}), trying next...")

        if not stream_success:
            raise Exception(f"[Ollama-stream] Connection error: {last_error or 'All endpoints failed'}")

        final_content = "".join(full_content).strip()
        if not final_content and 'thinking_buffer' in locals() and thinking_buffer:
            final_content = "".join(thinking_buffer).strip()

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
        """Định tuyến ưu tiên 100% Local AI Offline (gemma4:latest).
        Mô hình Cloud (Gemini / Claude) chỉ đóng vai trò kênh fallback dự phòng khi có API Key.
        """
        is_gemini_requested = bool(
            (local_model and str(local_model).startswith("gemini")) or
            (cloud_model and str(cloud_model).startswith("gemini")) or
            prefer_cloud
        )

        if is_gemini_requested and cls.is_cloud_available():
            try:
                target_cloud = cloud_model or local_model or settings.GOOGLE_AI_STUDIO_MODEL or "gemini-2.5-flash"
                logger.info(f"[ChatCompletion] Routing to Cloud Gemini fallback: {target_cloud}")
                return cls._call_google_ai_studio(target_cloud, messages, temperature, max_tokens)
            except Exception as cloud_err:
                logger.warning(f"[ChatCompletion] Cloud Gemini call failed, falling back to local Ollama: {cloud_err}")

        # Local inference via Ollama
        target_model = local_model or settings.MODEL_NAME or "gemma4:latest"
        if not target_model or not target_model.strip() or str(target_model).startswith("gemini"):
            target_model = settings.MODEL_NAME or "gemma4:latest"
        ollama_model = target_model if ":" in target_model else _LOCALAI_TO_OLLAMA.get(target_model, target_model)

        logger.info(f"[LocalChatCompletion] Requesting model={ollama_model}, task_type={task_type or 'auto'}")

        try:
            result = cls._call_ollama(ollama_model, messages, temperature, max_tokens)
            if result.get("content"):
                return result
        except Exception as e:
            logger.warning(f"[ChatCompletion] Ollama ({ollama_model}) failed: {e}")
            if cls.is_cloud_available():
                logger.info("[ChatCompletion] Ollama failed -> Fallback to Google AI Studio (gemini-2.5-flash)...")
                try:
                    fallback_cloud = cloud_model or settings.GOOGLE_AI_STUDIO_MODEL or "gemini-2.5-flash"
                    return cls._call_google_ai_studio(fallback_cloud, messages, temperature, max_tokens)
                except Exception as fb_err:
                    logger.warning(f"[ChatCompletion] Google AI Studio fallback also failed: {fb_err}")
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
