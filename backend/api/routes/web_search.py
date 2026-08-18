"""Web Search API Route — DuckDuckGo-based search for Discover page fallback."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from services.web_search import WebSearch

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: Optional[int] = Field(default=5, ge=1, le=20)


@router.post("/web-search")
async def web_search(request: WebSearchRequest):
    """Search the web using DuckDuckGo. Used as fallback when SearXNG is unavailable."""
    try:
        results = WebSearch.search(
            query=request.query,
            max_results=request.max_results,
        )
        return {
            "status": "ok",
            "query": request.query,
            "results": results,
            "total": len(results),
        }
    except Exception as e:
        logger.exception("Web search error")
        raise HTTPException(status_code=500, detail="Web search failed")
