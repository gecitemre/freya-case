from dataclasses import dataclass
from typing import Dict, Optional
import time

from .models import AgentConfig


@dataclass
class SessionState:
    config: AgentConfig
    bot_state: str = "idle"
    round_trip_latency_ms: int | None = None
    created_at: float = time.time()
    room_url: Optional[str] = None
    client_token: Optional[str] = None
    bot_token: Optional[str] = None
    task: Optional[object] = None
    last_error: Optional[str] = None


_sessions: Dict[str, SessionState] = {}


def create_session(session_id: str, config: AgentConfig) -> SessionState:
    state = SessionState(config=config)
    _sessions[session_id] = state
    return state


def get_session(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)
