import pytest
import httpx

from app.main import app
from app.state import create_session
from app.models import AgentConfig


@pytest.mark.anyio
async def test_create_session_invalid_config_returns_422():
    payload = {
        "llm": {"system_prompt": "x", "temperature": -1, "max_tokens": 10},
        "stt": {"temperature": 0.0},
        "tts": {"voice": "alloy", "speed": 1.0, "temperature": 0.3},
        "interruptibility_pct": 50,
    }
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/sessions", json=payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_state_includes_error_message():
    session_id = "test-session"
    session = create_session(session_id, AgentConfig())
    session.bot_state = "error"
    session.last_error = "boom"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/sessions/{session_id}/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "error"
    assert data["error_message"] == "boom"
