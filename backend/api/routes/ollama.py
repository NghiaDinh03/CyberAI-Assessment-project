"""Ollama model management — list, pull, and delete models."""

import threading
import time
from typing import Dict, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import settings
from utils.logger import logger
from services.cloud_llm_service import get_ollama_models
router = APIRouter()

# ── In-memory pull tracking ─────────────────────────────────────────
_pull_jobs: Dict[str, dict] = {}
_pull_lock = threading.Lock()

# Models available in the Ollama registry (curated list with metadata)
OLLAMA_CATALOG = [
    {"id": "gemma4:latest",   "name": "Gemma 4",        "params": "8B",  "size": "9.6 GB", "family": "gemma"},
    {"id": "gemma3n:e4b",     "name": "Gemma 3n E4B",   "params": "4B",  "size": "7.5 GB", "family": "gemma"},
    {"id": "gemma3n:e2b",     "name": "Gemma 3n E2B",   "params": "2B",  "size": "5.6 GB", "family": "gemma"},
    {"id": "qwen3:8b",        "name": "Qwen 3",         "params": "8B",  "size": "5.2 GB", "family": "qwen"},
    {"id": "qwen3:4b",        "name": "Qwen 3",         "params": "4B",  "size": "2.7 GB", "family": "qwen"},
    {"id": "qwen3:1.7b",      "name": "Qwen 3",         "params": "1.7B","size": "1.1 GB", "family": "qwen"},
    {"id": "phi4:latest",     "name": "Phi 4",           "params": "14B", "size": "9.1 GB", "family": "phi"},
    {"id": "phi4-mini:latest","name": "Phi 4 Mini",      "params": "3.8B","size": "2.5 GB", "family": "phi"},
    {"id": "deepseek-r1:8b",  "name": "DeepSeek R1",    "params": "8B",  "size": "4.9 GB", "family": "deepseek"},
    {"id": "deepseek-r1:1.5b","name": "DeepSeek R1",    "params": "1.5B","size": "1.1 GB", "family": "deepseek"},
    {"id": "llama3.2:3b",     "name": "Llama 3.2",      "params": "3B",  "size": "2.0 GB", "family": "llama"},
    {"id": "llama3.2:1b",     "name": "Llama 3.2",      "params": "1B",  "size": "1.3 GB", "family": "llama"},
    {"id": "mistral:7b",      "name": "Mistral",        "params": "7B",  "size": "4.1 GB", "family": "mistral"},
    {"id": "codellama:7b",    "name": "Code Llama",     "params": "7B",  "size": "3.8 GB", "family": "llama"},
]


class PullRequest(BaseModel):
    model: str


@router.get("/ollama/models")
async def list_ollama_models():
    """List installed models + catalog with install status."""
    installed = get_ollama_models(timeout=5)
    catalog = []
    for entry in OLLAMA_CATALOG:
        mid = entry["id"]
        is_installed = mid in installed or any(
            i.startswith(mid.split(":")[0] + ":") and i == mid for i in installed
        )
        pull_status = None
        with _pull_lock:
            if mid in _pull_jobs:
                pull_status = _pull_jobs[mid].copy()
        catalog.append({**entry, "installed": is_installed, "pull_status": pull_status})

    # Include any installed models not in catalog
    catalog_ids = {e["id"] for e in OLLAMA_CATALOG}
    for m in installed:
        if m not in catalog_ids:
            catalog.append({
                "id": m, "name": m.split(":")[0].title(),
                "params": "?", "size": "?", "family": m.split(":")[0],
                "installed": True, "pull_status": None,
            })
    return {"models": catalog, "installed": installed}


@router.post("/ollama/pull")
async def pull_ollama_model(req: PullRequest):
    """Start async pull of an Ollama model."""
    model = req.model
    with _pull_lock:
        if model in _pull_jobs and _pull_jobs[model].get("status") == "pulling":
            return {"message": f"Already pulling {model}", "status": "pulling"}

    with _pull_lock:
        _pull_jobs[model] = {"status": "pulling", "progress": 0, "started": time.time()}

    thread = threading.Thread(target=_do_pull, args=(model,), daemon=True)
    thread.start()
    logger.info(f"[Ollama] Started pull for {model}")
    return {"message": f"Pull started for {model}", "status": "pulling"}


@router.get("/ollama/pull/status")
async def pull_status(model: Optional[str] = None):
    """Get pull status for one or all models."""
    with _pull_lock:
        if model:
            job = _pull_jobs.get(model)
            return {"model": model, "status": job or {"status": "unknown"}}
        return {"jobs": dict(_pull_jobs)}


@router.delete("/ollama/models/{model_id:path}")
async def delete_ollama_model(model_id: str):
    """Delete a model from Ollama."""
    try:
        resp = requests.delete(
            f"{settings.OLLAMA_URL}/api/delete",
            json={"name": model_id}, timeout=30,
        )
        if resp.status_code == 200:
            # Invalidate cache
            from services.cloud_llm_service import _ollama_models_cache
            _ollama_models_cache.clear()
            return {"message": f"Deleted {model_id}"}
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))


def _do_pull(model: str):
    """Background pull with progress tracking via Ollama streaming API."""
    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/pull",
            json={"name": model, "stream": True},
            stream=True, timeout=7200,
        )
        if resp.status_code != 200:
            with _pull_lock:
                _pull_jobs[model] = {"status": "error", "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            return

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                import json
                data = json.loads(line)
                status = data.get("status", "")
                total = data.get("total", 0)
                completed = data.get("completed", 0)
                pct = int(completed / total * 100) if total > 0 else 0
                with _pull_lock:
                    _pull_jobs[model] = {
                        "status": "pulling", "progress": pct,
                        "detail": status, "started": _pull_jobs.get(model, {}).get("started", time.time()),
                    }
                if status == "success":
                    with _pull_lock:
                        _pull_jobs[model] = {"status": "done", "progress": 100}
                    # Invalidate model cache
                    from services.cloud_llm_service import _ollama_models_cache
                    _ollama_models_cache.clear()
                    logger.info(f"[Ollama] Pull complete: {model}")
                    return
            except Exception:
                pass

        # If we exit loop without "success", check final state
        with _pull_lock:
            if _pull_jobs.get(model, {}).get("status") == "pulling":
                _pull_jobs[model] = {"status": "done", "progress": 100}
        from services.cloud_llm_service import _ollama_models_cache
        _ollama_models_cache.clear()

    except Exception as e:
        logger.error(f"[Ollama] Pull failed for {model}: {e}")
        with _pull_lock:
            _pull_jobs[model] = {"status": "error", "error": str(e)[:200]}
