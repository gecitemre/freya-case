import os
import asyncio

import aiohttp

from pipecat.audio.interruptions.min_words_interruption_strategy import (
    MinWordsInterruptionStrategy,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from .models import AgentConfig
from .observability import BotStateObserver


async def run_bot(
    room_url: str,
    token: str,
    config: AgentConfig,
    on_state_change,
    on_latency,
    on_error,
) -> None:
    # Map STT temperature loosely to VAD confidence (higher temp -> lower confidence)
    vad_confidence = max(0.3, min(0.9, 0.9 - (config.stt.temperature * 0.5)))
    vad_params = VADParams(
        confidence=vad_confidence,
        start_secs=0.2,
        stop_secs=0.8,
        min_volume=0.6,
    )

    allow_interruptions, min_words = _map_interruptibility(config.interruptibility_pct)

    async with aiohttp.ClientSession() as http_session:
        transport = DailyTransport(
            room_url,
            token,
            "Agent",
            DailyParams(
                api_url=os.environ.get("DAILY_API_URL", "https://api.daily.co/v1"),
                api_key=os.environ.get("DAILY_API_KEY"),
                audio_in_enabled=True,
                audio_out_enabled=True,
                transcription_enabled=True,
            ),
        )

        stt = DeepgramSTTService(
            api_key=os.environ.get("DEEPGRAM_API_KEY"),
            http_session=http_session,
        )

        llm = OpenAILLMService(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        voice_id = config.tts.voice
        if not voice_id:
            voice_id = os.environ.get("CARTESIA_DEFAULT_VOICE_ID")
        if not voice_id:
            raise RuntimeError("CARTESIA_DEFAULT_VOICE_ID is not set")

        tts = CartesiaTTSService(
            api_key=os.environ.get("CARTESIA_API_KEY"),
            voice_id=voice_id,
            speed=config.tts.speed,
            temperature=config.tts.temperature,
            http_session=http_session,
        )

        context = LLMContext(
            messages=[
                {
                    "role": "system",
                    "content": config.llm.system_prompt,
                }
            ]
        )

        user_params = LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=vad_params),
        )

        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=user_params,
        )

        observer = BotStateObserver(
            on_state_change=on_state_change, on_latency=on_latency, on_error=on_error
        )

        pipeline = Pipeline(
            [
                transport.input(),
                user_aggregator,
                stt,
                llm,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        )

        params = PipelineParams(
            allow_interruptions=allow_interruptions,
            interruption_strategies=(
                [MinWordsInterruptionStrategy(min_words=min_words)]
                if allow_interruptions
                else []
            ),
            observers=[observer],
        )

        task = PipelineTask(pipeline, params=params)

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])

        runner = PipelineRunner()
        await runner.run(task)


def _map_interruptibility(pct: int) -> tuple[bool, int]:
    if pct <= 0:
        return False, 0
    if pct <= 33:
        return True, 5
    if pct <= 66:
        return True, 3
    return True, 1
