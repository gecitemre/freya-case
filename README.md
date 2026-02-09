# Freya Take-Home: Agent Console (Minimal Scaffold)

This is a minimal starting point that matches the take-home requirements:
- Next.js + TypeScript frontend
- Python (FastAPI) backend that boots a Pipecat pipeline per session
- Docker Compose wiring
- .env placeholders

## Quick start
1. Fill in `.env` with real keys.
2. `docker compose up --build`

## Services
- `frontend` (Next.js) on `http://localhost:3000`
- `backend` (FastAPI) on `http://localhost:8000`

## Flow
1. UI POSTs `/sessions` with config.
2. Backend creates a Daily room, starts the bot, and returns `room_url` + token.
3. UI connects via Daily transport and streams audio.

## Config notes
- `tts.voice` expects a Cartesia `voice_id`.
