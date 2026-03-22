"""Chat API Routes — Streaming, history, and session management."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from services.chat_service import ChatService
from typing import Optional
import json

router = APIRouter()

try:
    from main import limiter, _has_rate_limit
except ImportError:
    limiter = None
    _has_rate_limit = False


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")


class ChatResponse(BaseModel):
    response: str
    model: str
    session_id: str
    tokens: Optional[dict] = None
    error: Optional[bool] = False
    route: Optional[str] = None
    provider: Optional[str] = None
    rag_used: Optional[bool] = None
    search_used: Optional[bool] = None
    sources: Optional[list] = None
    web_sources: Optional[list] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        return ChatService.generate_response(message=request.message.strip(), session_id=request.session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    def event_generator():
        for event in ChatService.generate_response_stream(
            message=request.message.strip(), session_id=request.session_id
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    return ChatService.clear_conversation(session_id)


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    ss = ChatService.get_session_store()
    history = ss.get_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.get("/chat/health")
async def chat_health():
    return ChatService.health_check()
