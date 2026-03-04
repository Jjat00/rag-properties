"""In-memory session manager for chat conversations."""

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class ChatSession:
    session_id: str
    model: str
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """Manages chat sessions in-memory. thread_id in LangGraph = session_id."""

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}

    def create(self, model: str, session_id: str | None = None) -> ChatSession:
        sid = session_id or uuid.uuid4().hex
        session = ChatSession(session_id=sid, model=model)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> list[ChatSession]:
        return list(self._sessions.values())
