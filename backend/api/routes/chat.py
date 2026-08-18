"""Chat API Routes — Streaming, history, and user-scoped session management."""

import json
import logging
import threading
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.config import settings
from services.chat_service import ChatService
from api.routes.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

try:
    from core.limiter import limiter, _has_rate_limit
except ImportError:
    limiter = None
    _has_rate_limit = False


def _extract_user_id(request: Request, explicit_user_id: Optional[str] = None) -> Optional[str]:
    """Extract user_id from explicit field or Authorization JWT token header."""
    if explicit_user_id:
        return explicit_user_id
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = verify_token(token)
        if payload and "sub" in payload:
            return payload["sub"]
    return None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=15000)
    session_id: str = Field(default="default")
    model: Optional[str] = Field(default="gemma4:latest")
    prefer_cloud: bool = Field(default=False)
    organisation: Optional[str] = Field(default="")
    user_id: Optional[str] = Field(default=None)


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


class SaveSessionRequest(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    user_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(http_request: Request, request: ChatRequest, background_tasks: BackgroundTasks):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        return await ChatService.generate_response(
            message=request.message.strip(),
            session_id=request.session_id,
            model_override=request.model,
            prefer_cloud=request.prefer_cloud,
            background_tasks=background_tasks,
            organisation=request.organisation,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_id = _extract_user_id(http_request, request.user_id)

    logger.info(
        "[chat/stream] received — model=%s msg_len=%d session=%s user=%s prefer_cloud=%s",
        request.model, len(request.message), request.session_id, user_id, request.prefer_cloud,
    )

    def event_generator():
        """Generator that streams SSE events with heartbeat to keep connection alive."""
        import queue as q_module

        event_queue: q_module.Queue = q_module.Queue()
        done_event = threading.Event()

        def producer():
            try:
                for event in ChatService.generate_response_stream(
                    message=request.message.strip(),
                    session_id=request.session_id,
                    model_override=request.model,
                    prefer_cloud=request.prefer_cloud,
                    organisation=request.organisation,
                    user_id=user_id,
                ):
                    event_queue.put(event)
            except Exception as exc:
                event_queue.put({
                    "step": "error",
                    "data": {
                        "error": True,
                        "response": f"Lỗi: {str(exc)}",
                        "model": settings.MODEL_NAME,
                        "session_id": request.session_id,
                    },
                })
            finally:
                done_event.set()

        thread = threading.Thread(target=producer, daemon=True)
        thread.start()

        # Drain the queue, yielding heartbeats when no data arrives within 15s
        while not (done_event.is_set() and event_queue.empty()):
            try:
                event = event_queue.get(timeout=15)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("step") in ("done", "error"):
                    break
            except q_module.Empty:
                yield ": heartbeat\n\n"

        thread.join(timeout=5)

    return StreamingResponse(
        event_generator(), media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions")
async def list_chat_sessions(http_request: Request, user_id: Optional[str] = None):
    """Retrieve chat sessions stored in SQLite, optionally filtered by user."""
    eff_user_id = _extract_user_id(http_request, user_id)
    ss = ChatService.get_session_store()
    sessions = ss.list_sessions(user_id=eff_user_id)
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/chat/sessions")
async def create_or_save_session(req: SaveSessionRequest, http_request: Request):
    """Save full chat session history to SQLite database."""
    session_id = req.session_id or f"s_{int(req.messages[0].get('timestamp', 0)) if req.messages else 'default'}"
    eff_user_id = _extract_user_id(http_request, req.user_id)
    ss = ChatService.get_session_store()
    ss.save(
        session_id=session_id,
        data={
            "title": req.title,
            "messages": req.messages
        },
        user_id=eff_user_id
    )
    return {"status": "success", "session_id": session_id}


@router.get("/chat/sessions/{session_id}")
async def get_chat_session_detail(session_id: str, http_request: Request, user_id: Optional[str] = None):
    """Retrieve full session detail including message history from SQLite."""
    eff_user_id = _extract_user_id(http_request, user_id)
    ss = ChatService.get_session_store()
    session_data = ss.load(session_id, user_id=eff_user_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_data


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str, http_request: Request, user_id: Optional[str] = None):
    """Delete a chat session and its messages from SQLite."""
    eff_user_id = _extract_user_id(http_request, user_id)
    ss = ChatService.get_session_store()
    ss.delete(session_id, user_id=eff_user_id)
    return {"status": "success", "message": f"Session {session_id} deleted"}


@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str, http_request: Request, user_id: Optional[str] = None):
    eff_user_id = _extract_user_id(http_request, user_id)
    ss = ChatService.get_session_store()
    ss.clear_history(session_id, user_id=eff_user_id)
    return {"status": "success", "message": f"History for {session_id} cleared"}


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, http_request: Request, user_id: Optional[str] = None):
    eff_user_id = _extract_user_id(http_request, user_id)
    ss = ChatService.get_session_store()
    history = ss.get_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.get("/chat/health")
async def chat_health():
    base = ChatService.health_check()
    from services.model_guard import ModelGuard
    base["model_guard"] = ModelGuard.status()
    base["local_only_mode"] = settings.LOCAL_ONLY_MODE
    return base
