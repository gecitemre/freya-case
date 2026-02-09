import time
import logging
from typing import Optional

from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.frames.frames import (
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    LLMFullResponseStartFrame,
    ErrorFrame,
)

logger = logging.getLogger("agent-console")


class BotStateObserver(BaseObserver):
    def __init__(self, on_state_change, on_latency, on_error):
        super().__init__(name="BotStateObserver")
        self._on_state_change = on_state_change
        self._on_latency = on_latency
        self._on_error = on_error
        self._last_user_stop: Optional[float] = None
        self._user_speaking = False

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame

        if isinstance(frame, UserStartedSpeakingFrame):
            self._user_speaking = True
            logger.info("state=listening (user started speaking)")
            self._on_state_change("listening")
            return

        if isinstance(frame, UserStoppedSpeakingFrame):
            self._user_speaking = False
            self._last_user_stop = time.time()
            logger.info("state=thinking (user stopped speaking)")
            self._on_state_change("thinking")
            return

        if isinstance(frame, LLMFullResponseStartFrame):
            logger.info("llm_response_start")
            self._on_state_change("thinking")
            return

        if isinstance(frame, BotStartedSpeakingFrame):
            if self._last_user_stop is not None:
                latency_ms = int((time.time() - self._last_user_stop) * 1000)
                self._on_latency(latency_ms)
                logger.info("bot_started_speaking latency_ms=%s", latency_ms)
            else:
                logger.info("bot_started_speaking latency_ms=unknown")
            self._on_state_change("speaking")
            return

        if isinstance(frame, BotStoppedSpeakingFrame):
            logger.info("state=idle (bot stopped speaking)")
            self._on_state_change("listening" if self._user_speaking else "idle")
            return

        if isinstance(frame, ErrorFrame):
            logger.error("pipeline_error: %s", frame.error)
            self._on_error(str(frame.error))
            self._on_state_change("error")
