from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    system_prompt: str = Field(
        default="You are a QA bot working at Zepliner. Zepliner is an e-SIM company and sells e-SIMs through the Zepliner mobile app."
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class STTConfig(BaseModel):
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)


class TTSConfig(BaseModel):
    voice: str = Field(default="e00d0e4c-a5c8-443f-a8a3-473eb9a62355")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)


class AgentConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    interruptibility_pct: int = Field(default=100, ge=0, le=100)


class CreateSessionResponse(BaseModel):
    session_id: str
    room_url: str
    token: str


class BotState(BaseModel):
    state: str
    round_trip_latency_ms: int | None = None
    error_message: str | None = None
