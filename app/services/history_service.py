import threading

from app.core.utils import utc_now_iso
from app.schemas.chat import ChatMessage


class HistoryService:
    def __init__(self, max_messages_per_session: int = 40) -> None:
        self._max_messages_per_session = max_messages_per_session
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._lock = threading.RLock()

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            role=role, content=content, created_at=utc_now_iso(), metadata=metadata or {}
        )
        with self._lock:
            messages = self._sessions.setdefault(session_id, [])
            messages.append(message)
            if len(messages) > self._max_messages_per_session:
                self._sessions[session_id] = messages[-self._max_messages_per_session :]
        return message

    def get(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> bool:
        with self._lock:
            existed = session_id in self._sessions
            self._sessions.pop(session_id, None)
            return existed

