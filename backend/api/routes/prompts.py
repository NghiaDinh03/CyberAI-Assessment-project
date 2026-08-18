"""System prompt management routes — read/update/reset runtime overrides."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prompts import list_prompts, set_prompt, reset_prompt, get_prompt
from prompts import defaults as prompt_defaults

logger = logging.getLogger(__name__)

router = APIRouter()


class PromptUpdate(BaseModel):
    value: str = Field(..., description="New prompt text")


@router.get("/prompts")
async def get_prompts(group: Optional[str] = Query(default=None, description="chat | assessment")):
    """List all prompts with current value, default, override status.

    Filter by ``group`` to render separate pages in the UI.
    """
    items = list_prompts()
    if group:
        if group not in ("chat", "assessment"):
            raise HTTPException(status_code=400, detail="group must be 'chat' or 'assessment'")
        items = [i for i in items if i["group"] == group]
    return {"items": items, "count": len(items)}


@router.get("/prompts/{key}")
async def get_single_prompt(key: str):
    if key not in prompt_defaults.REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    meta = prompt_defaults.REGISTRY[key]
    return {
        "key": key,
        "title": meta["title"],
        "description": meta["description"],
        "group": meta["group"],
        "default": meta["default"],
        "current": get_prompt(key),
        "required_placeholders": meta.get("required_placeholders", []),
    }


@router.put("/prompts/{key}")
async def update_prompt(key: str, body: PromptUpdate):
    try:
        result = set_prompt(key, body.value)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("prompt updated: %s (len=%d)", key, result["length"])
    return result


@router.post("/prompts/{key}/reset")
async def reset_single_prompt(key: str):
    try:
        result = reset_prompt(key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    logger.info("prompt reset: %s", key)
    return result
