from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from app.engine.state_factory import maak_ui_state
from app.core.natuurkunde import Deeltje, update_deeltjes


@dataclass
class SessionState:
    session_id: str
    level: str = "beginner"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    step_count: int = 0
    status: str = "active"
    ui_state: dict = field(default_factory=maak_ui_state)
    deeltjes: list = field(default_factory=list)


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


def step_session(session_id: str) -> SessionState | None:
    session = sessions.get(session_id)

    if session is None:
        return None

    session.step_count += 1
    session.status = "running"

    if len(session.deeltjes) == 0:
        session.deeltjes.append(
            Deeltje(
                x_m=0.01,
                y_m=0.05,
                vx=10000.0,
                vy=0.0,
                straal_m=0.0005,
                kleur=(80, 200, 255),
                m_kg=1.67e-27,
                q_c=1.60e-19,
            )
        )

    hits = update_deeltjes(
        session.deeltjes,
        dt=1e-7,
        instellingen=session.ui_state["values"],
    )

    session.ui_state["histogram"]["y_hits_m"].extend([hit.y_m for hit in hits])

    return session
