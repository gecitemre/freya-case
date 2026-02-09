import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .models import AgentConfig, CreateSessionResponse, BotState
from .state import create_session, get_session
from .daily import create_room_and_tokens
from .bot import run_bot

logger = logging.getLogger("agent-console")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agent Console Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] ,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session_endpoint(config: AgentConfig, request: Request):
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)
    _require_env()
    session_id = str(uuid.uuid4())
    session = create_session(session_id, config)

    try:
        room_url, client_token, bot_token = await create_room_and_tokens(
            f"agent-{session_id}"
        )
    except Exception as exc:
        logger.exception("daily room creation failed")
        raise HTTPException(status_code=500, detail="failed to create room") from exc

    session.room_url = room_url
    session.client_token = client_token
    session.bot_token = bot_token

    def on_state_change(state: str):
        session.bot_state = state

    def on_latency(latency_ms: int):
        session.round_trip_latency_ms = latency_ms
        session.last_error = None

    def on_error(message: str):
        session.last_error = message
        session.bot_state = "error"

    async def _run_wrapper():
        try:
            await run_bot(
                room_url=room_url,
                token=bot_token,
                config=config,
                on_state_change=on_state_change,
                on_latency=on_latency,
                on_error=on_error,
            )
        except Exception:
            logger.exception("bot session failed")
            session.bot_state = "error"
            session.last_error = "bot session failed"

    session.task = asyncio.create_task(_run_wrapper())

    return CreateSessionResponse(session_id=session_id, room_url=room_url, token=client_token)


@app.get("/sessions/{session_id}/state", response_model=BotState)
def get_state(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return BotState(
        state=session.bot_state,
        round_trip_latency_ms=session.round_trip_latency_ms,
        error_message=session.last_error,
    )


_WINDOW_SECONDS = 60
_MAX_SESSIONS_PER_WINDOW = 5
_hits = defaultdict(lambda: deque())


def _rate_limit(ip: str) -> None:
    now = time.time()
    bucket = _hits[ip]
    while bucket and (now - bucket[0]) > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _MAX_SESSIONS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    bucket.append(now)


def _require_env() -> None:
    missing = []
    for key in ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY", "DAILY_API_KEY"]:
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        raise HTTPException(status_code=500, detail=f"missing env: {', '.join(missing)}")
