from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class SessionState:
    session_id: str
    level: str = "beginner"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    step_count: int = 0
    status: str = "active"


sessions: dict[str, SessionState] = {}


def create_session(level: str = "beginner") -> SessionState:
    session = SessionState(
        session_id=str(uuid4()),
        level=level,
    )
    sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> SessionState | None:
    return sessions.get(session_id)


def reset_session(session_id: str) -> SessionState | None:
    session = sessions.get(session_id)
    if session is None:
        return None

    session.step_count = 0
    session.status = "reset"
    return session
