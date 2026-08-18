"""System statistics routes — uses psutil instead of /proc mounts for security."""

import platform
import os
import json
import logging
from fastapi import APIRouter

import psutil

logger = logging.getLogger(__name__)

router = APIRouter()


def get_cpu_info():
    cpu_name = ""
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        cpu_name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
    if not cpu_name:
        cpu_name = platform.processor() or "AMD / Intel Processor"

    # Format cleanly
    cpu_name = cpu_name.replace("(R)", "").replace("(TM)", "").strip()

    logical_cores = psutil.cpu_count(logical=True) or 0
    physical_cores = psutil.cpu_count(logical=False) or 0
    cores = logical_cores if logical_cores > 0 else (physical_cores if physical_cores > 0 else 4)
    return {"name": cpu_name, "cores": cores, "logical_cores": logical_cores, "physical_cores": physical_cores}


def get_cpu_percent():
    return psutil.cpu_percent(interval=0.3)


def get_memory_info():
    vm = psutil.virtual_memory()
    return {
        "used": vm.used,
        "total": vm.total,
        "percent": vm.percent,
    }


def get_disk_info():
    try:
        du = psutil.disk_usage("/")
        return {
            "used": du.used,
            "total": du.total,
            "percent": du.percent,
        }
    except Exception:
        return {"used": 0, "total": 0, "percent": 0}


def get_uptime():
    try:
        import time
        return round(time.time() - psutil.boot_time(), 1)
    except Exception:
        return 0.0


from services.cloud_llm_service import CloudLLMService
from services.model_guard import ModelGuard
from core.config import settings


@router.get("/system/stats")
def system_stats():
    cpu_info = get_cpu_info()
    cpu_percent = get_cpu_percent()
    memory = get_memory_info()
    disk = get_disk_info()
    uptime = get_uptime()

    return {
        "cpu": {
            "name": cpu_info["name"],
            "cores": cpu_info["cores"],
            "percent": cpu_percent,
        },
        "memory": {
            "used": memory["used"],
            "total": memory["total"],
            "percent": memory["percent"],
        },
        "disk": {
            "used": disk["used"],
            "total": disk["total"],
            "percent": disk["percent"],
        },
        "uptime_seconds": uptime,
        "platform": platform.system(),
    }


def get_dir_size(path: str):
    total_size = 0
    total_files = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
                    total_files += 1
    return total_size, total_files


@router.get("/system/cache-stats")
def cache_stats():
    sessions_size, sessions_files = get_dir_size("/data/sessions")
    exports_size, exports_files = get_dir_size("/data/exports")

    return {
        "sessions": {
            "size_bytes": sessions_size,
            "files": sessions_files,
        },
        "exports": {
            "size_bytes": exports_size,
            "files": exports_files,
        },
        "total_size_bytes": sessions_size + exports_size,
        "total_files": sessions_files + exports_files,
    }


@router.get("/system/ai-status")
def ai_status():
    from services.cloud_llm_service import get_ollama_models
    health = CloudLLMService.health_check()
    models_ready = ModelGuard.is_ready()
    cloud_ready = bool(settings.cloud_api_key_list)

    if settings.LOCAL_ONLY_MODE:
        mode_label = "local-only"
    elif settings.PREFER_LOCAL:
        mode_label = "local-first"
    else:
        mode_label = "cloud-first"

    ollama_available_models = get_ollama_models()

    return {
        "local_only_mode": settings.LOCAL_ONLY_MODE,
        "prefer_local": settings.PREFER_LOCAL,
        "mode_label": mode_label,
        "models_ready": models_ready,
        "cloud_keys": cloud_ready,
        "model_guard": ModelGuard.status(),
        "localai": health.get("localai", {}),
        "open_claude": health.get("open_claude", {}),
        "ollama": health.get("ollama", {}),
        "ollama_models": ollama_available_models,
    }


_BUILTIN_MODELS = [
    {
        "id": "gemma4:latest",
        "name": "Gemma 4",
        "status": "available",
        "type": "chat",
        "provider": "local",
        "description": "Mô hình local Gemma 4 tối ưu cho phân tích bảo mật và đánh giá tuân thủ.",
    },
]


def _load_models_json() -> list:
    """Read models.json from the project root; return [] on any error."""
    candidates = [
        os.path.join(os.getenv("DATA_PATH", "./data"), "..", "models.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "models.json"),
        "/app/models.json",
        "./models.json",
    ]
    for path in candidates:
        try:
            normalized = os.path.normpath(path)
            if os.path.isfile(normalized):
                with open(normalized, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    logger.debug(f"models.json loaded from {normalized} ({len(data)} entries)")
                    return data
        except Exception as exc:
            logger.debug(f"models.json read attempt failed ({path}): {exc}")
    logger.debug("models.json not found — using built-in model list only")
    return []


def _build_model_list() -> list:
    """Merge built-in models with any extra entries from models.json.

    Built-in entries take precedence; models.json entries are appended only
    when they introduce a new ``id`` not already present.
    """
    merged: list = list(_BUILTIN_MODELS)
    existing_ids = {m["id"] for m in merged}

    for raw in _load_models_json():
        model_id = raw.get("id") or raw.get("modelId", "")
        if not model_id or model_id in existing_ids:
            continue
        merged.append({
            "id": model_id,
            "name": raw.get("name", model_id),
            "status": "available",
            "type": raw.get("pipeline_tag", "unknown"),
            "provider": "huggingface",
            "description": ", ".join(raw.get("tags", []))[:120],
        })
        existing_ids.add(model_id)

    return merged


@router.get("/models")
def list_models():
    """Return all available models with their status and metadata.

    Merges the built-in model catalogue with optional entries from
    ``models.json`` in the project root.  Gracefully returns an empty list
    when ``models.json`` is missing rather than raising an error.
    """
    guard_status = ModelGuard.status()
    models = _build_model_list()

    # Reflect real-time local-model availability from ModelGuard
    for model in models:
        mid = model["id"]
        if mid in guard_status:
            model["status"] = "available" if guard_status[mid] == "present" else "unavailable"

    default_model = getattr(settings, "MODEL_NAME", "gemma4:latest") or "gemma4:latest"

    return {
        "models": models,
        "default_model": default_model,
        "total": len(models),
    }
