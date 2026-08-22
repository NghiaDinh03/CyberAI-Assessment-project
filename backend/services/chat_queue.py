"""Chat Queue & Concurrency Management — Serializes requests per session and limits local LLM inference concurrency."""

import time
import uuid
import logging
import threading
from typing import Dict, List, Optional, Generator, Any

logger = logging.getLogger(__name__)


class ChatQueueTicket:
    def __init__(self, ticket_id: str, session_id: str, is_local: bool):
        self.ticket_id = ticket_id
        self.session_id = session_id
        self.is_local = is_local
        self.created_at = time.time()
        self.event = threading.Event()
        self.cancelled = False


class ChatQueueManager:
    """Thread-safe queue manager for chat sessions and local inference hardware concurrency."""

    _instance: Optional["ChatQueueManager"] = None
    _lock = threading.Lock()

    def __init__(self, max_local_concurrency: int = 1):
        self._max_local_concurrency = max_local_concurrency
        self._current_local_active = 0
        self._state_lock = threading.Lock()

        # Per-session queue of tickets: session_id -> list[ChatQueueTicket]
        self._session_queues: Dict[str, List[ChatQueueTicket]] = {}
        # Global queue of tickets waiting for local inference: list[ChatQueueTicket]
        self._local_inference_queue: List[ChatQueueTicket] = []
        # Active ticket per session: session_id -> ChatQueueTicket
        self._active_session_tickets: Dict[str, ChatQueueTicket] = {}

    @classmethod
    def get_instance(cls, max_local_concurrency: int = 1) -> "ChatQueueManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_local_concurrency=max_local_concurrency)
            return cls._instance

    def enqueue_and_wait(
        self,
        session_id: str,
        is_local: bool = True,
        poll_interval: float = 1.0,
        max_wait_seconds: float = 300.0,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yields queue status events until the ticket is granted its execution turn.

        Yields:
            {"step": "queued", "position": N, "total_waiting": M, "message": str}

        Once this generator finishes, the caller holds the execution turn.
        MUST call `release_turn(ticket)` in a finally block!
        """
        ticket_id = str(uuid.uuid4())[:8]
        ticket = ChatQueueTicket(ticket_id=ticket_id, session_id=session_id, is_local=is_local)

        with self._state_lock:
            if session_id not in self._session_queues:
                self._session_queues[session_id] = []
            self._session_queues[session_id].append(ticket)
            if is_local:
                self._local_inference_queue.append(ticket)

        logger.info(
            "[ChatQueue] Enqueued ticket=%s session=%s is_local=%s (session_q_len=%d, local_q_len=%d)",
            ticket_id, session_id, is_local,
            len(self._session_queues.get(session_id, [])),
            len(self._local_inference_queue),
        )

        start_time = time.time()
        granted = False

        try:
            while not granted:
                with self._state_lock:
                    # 1. Check Session turn: must be first in its session queue, or active ticket is itself
                    session_q = self._session_queues.get(session_id, [])
                    session_pos = session_q.index(ticket) if ticket in session_q else -1

                    # 2. Check Local Inference turn (if applicable)
                    local_pos = self._local_inference_queue.index(ticket) if (is_local and ticket in self._local_inference_queue) else 0

                    can_run_session = (session_pos == 0) and (session_id not in self._active_session_tickets or self._active_session_tickets[session_id] == ticket)
                    can_run_local = (not is_local) or (local_pos == 0 and self._current_local_active < self._max_local_concurrency)

                    if can_run_session and can_run_local:
                        # Grant turn!
                        self._active_session_tickets[session_id] = ticket
                        if session_q and session_q[0] == ticket:
                            session_q.pop(0)
                        if is_local:
                            if self._local_inference_queue and self._local_inference_queue[0] == ticket:
                                self._local_inference_queue.pop(0)
                            self._current_local_active += 1
                        granted = True
                        logger.info("[ChatQueue] Granted turn for ticket=%s session=%s (active_local=%d)", ticket_id, session_id, self._current_local_active)
                        break

                    # Calculate display position
                    wait_pos = max(1, session_pos + 1) if session_pos > 0 else (max(1, local_pos + 1) if is_local else 1)
                    if session_pos > 0:
                        msg = f"Đang chờ câu hỏi trước trong phiên hoàn tất (Vị trí: {wait_pos})..."
                    else:
                        msg = f"Đang chờ máy chủ AI sẵn sàng (Vị trí hàng đợi: {wait_pos})..."

                if time.time() - start_time > max_wait_seconds:
                    logger.warning("[ChatQueue] Timeout waiting in queue ticket=%s session=%s", ticket_id, session_id)
                    raise TimeoutError(f"Hàng đợi quá tải: Yêu cầu chờ quá {max_wait_seconds}s.")

                yield {
                    "step": "queued",
                    "position": wait_pos,
                    "ticket_id": ticket_id,
                    "session_id": session_id,
                    "message": msg,
                }

                time.sleep(poll_interval)

        except Exception:
            self.release_turn(ticket)
            raise

        # Return ticket via special event marker or attribute
        yield {"step": "queue_granted", "ticket": ticket}

    def release_turn(self, ticket: ChatQueueTicket):
        """Release execution slot and notify waiting requests."""
        if not ticket:
            return
        with self._state_lock:
            session_id = ticket.session_id
            # Remove from session queues if still there
            if session_id in self._session_queues and ticket in self._session_queues[session_id]:
                self._session_queues[session_id].remove(ticket)
            if not self._session_queues.get(session_id):
                self._session_queues.pop(session_id, None)

            # Remove from active session ticket
            if self._active_session_tickets.get(session_id) == ticket:
                self._active_session_tickets.pop(session_id, None)

            # Remove from local queue if still there
            if ticket.is_local:
                if ticket in self._local_inference_queue:
                    self._local_inference_queue.remove(ticket)
                if self._current_local_active > 0:
                    self._current_local_active -= 1

        logger.info(
            "[ChatQueue] Released ticket=%s session=%s (active_local=%d)",
            ticket.ticket_id, ticket.session_id, self._current_local_active,
        )
