"use client";

import { PipecatClient } from "@pipecat-ai/client-js";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type AgentConfig = {
  llm: { system_prompt: string; temperature: number; max_tokens: number };
  stt: { temperature: number };
  tts: { voice: string; speed: number; temperature: number };
  interruptibility_pct: number;
};

const clampNumber = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const parseNumber = (value: string, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [roomUrl, setRoomUrl] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [transportState, setTransportState] = useState<string>("idle");
  const [sessionError, setSessionError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const clientRef = useRef<PipecatClient | null>(null);
  const [config, setConfig] = useState<AgentConfig>({
    llm: {
      system_prompt: "You are a QA bot working at Zepliner. Zepliner is an e-SIM company and sells e-SIMs through the Zepliner mobile app.",
      temperature: 0.7,
      max_tokens: 512,
    },
    stt: { temperature: 0.0 },
    tts: { voice: "e00d0e4c-a5c8-443f-a8a3-473eb9a62355", speed: 1.0, temperature: 0.3 },
    interruptibility_pct: 100,
  });

  const createSession = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`${backendUrl}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!resp.ok) throw new Error("failed to create session");
      return (await resp.json()) as { session_id: string; room_url: string; token: string };
    },
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setRoomUrl(data.room_url);
      setToken(data.token);
      setSessionError(null);
    },
  });

  const stateQuery = useQuery({
    queryKey: ["state", sessionId],
    queryFn: async () => {
      const resp = await fetch(`${backendUrl}/sessions/${sessionId}/state`);
      if (resp.status === 404) {
        setSessionError("Session expired — click Start Session again.");
        setSessionId(null);
        setRoomUrl(null);
        setToken(null);
        return { state: "idle", round_trip_latency_ms: null, error_message: null };
      }
      if (!resp.ok) throw new Error("failed to fetch state");
      return (await resp.json()) as {
        state: string;
        round_trip_latency_ms: number | null;
        error_message?: string | null;
      };
    },
    enabled: !!sessionId,
    refetchInterval: 500,
  });

  const botState = stateQuery.data?.state || "idle";
  const latency = stateQuery.data?.round_trip_latency_ms;
  const errorMessage = stateQuery.data?.error_message;

  const stateDotClass = useMemo(() => {
    if (botState === "listening") return "dot listening";
    if (botState === "thinking") return "dot thinking";
    if (botState === "speaking") return "dot speaking";
    return "dot";
  }, [botState]);

  const resetSession = () => {
    setSessionId(null);
    setRoomUrl(null);
    setToken(null);
    setSessionError(null);
  };

  useEffect(() => {
    if (!roomUrl || !token) return;
    if (clientRef.current) return;

    const pcClient = new PipecatClient({
      transport: new DailyTransport({ bufferLocalAudioUntilBotReady: true }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onTrackStarted: (track: MediaStreamTrack, participant: { local: boolean }) => {
          if (participant.local || track.kind !== "audio") return;
          if (!audioRef.current) return;
          audioRef.current.srcObject = new MediaStream([track]);
          audioRef.current.play();
        },
        onTransportStateChanged: (state: string) => {
          setTransportState(state);
        },
      },
    });

    clientRef.current = pcClient;
    pcClient.connect({ url: roomUrl, token });

    return () => {
      pcClient.disconnect();
      clientRef.current = null;
    };
  }, [roomUrl, token]);

  return (
    <main>
      <h1>Agent Console</h1>
      <p>Configure the agent before starting a session.</p>

      <div className="section">
        <h2>Configuration</h2>
        <label>System Prompt</label>
        <textarea
          rows={4}
          value={config.llm.system_prompt}
          onChange={(e) =>
            setConfig({
              ...config,
              llm: { ...config.llm, system_prompt: e.target.value },
            })
          }
        />

        <div className="row">
          <div>
            <label>LLM Temperature</label>
            <input
              type="number"
              min={0}
              max={2}
              step="0.1"
              value={config.llm.temperature}
              onChange={(e) =>
                setConfig({
                  ...config,
                  llm: {
                    ...config.llm,
                    temperature: clampNumber(parseNumber(e.target.value, config.llm.temperature), 0, 2),
                  },
                })
              }
            />
          </div>
          <div>
            <label>LLM Max Tokens</label>
            <input
              type="number"
              min={1}
              max={4096}
              value={config.llm.max_tokens}
              onChange={(e) =>
                setConfig({
                  ...config,
                  llm: {
                    ...config.llm,
                    max_tokens: clampNumber(
                      parseNumber(e.target.value, config.llm.max_tokens),
                      1,
                      4096
                    ),
                  },
                })
              }
            />
          </div>
        </div>

        <div className="row">
          <div>
            <label>STT Temperature</label>
            <input
              type="number"
              min={0}
              max={1}
              step="0.1"
              value={config.stt.temperature}
              onChange={(e) =>
                setConfig({
                  ...config,
                  stt: {
                    temperature: clampNumber(
                      parseNumber(e.target.value, config.stt.temperature),
                      0,
                      1
                    ),
                  },
                })
              }
            />
          </div>
          <div>
            <label>Interruptibility %</label>
            <input
              type="number"
              min={0}
              max={100}
              value={config.interruptibility_pct}
              onChange={(e) =>
                setConfig({
                  ...config,
                  interruptibility_pct: clampNumber(
                    parseNumber(e.target.value, config.interruptibility_pct),
                    0,
                    100
                  ),
                })
              }
            />
          </div>
        </div>

        <div className="row">
          <div>
            <label>Cartesia Voice ID</label>
            <input
              type="text"
              placeholder="e00d0e4c-a5c8-443f-a8a3-473eb9a62355"
              value={config.tts.voice}
              onChange={(e) =>
                setConfig({
                  ...config,
                  tts: { ...config.tts, voice: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label>TTS Speed</label>
            <input
              type="number"
              min={0.5}
              max={2}
              step="0.1"
              value={config.tts.speed}
              onChange={(e) =>
                setConfig({
                  ...config,
                  tts: {
                    ...config.tts,
                    speed: clampNumber(parseNumber(e.target.value, config.tts.speed), 0.5, 2),
                  },
                })
              }
            />
          </div>
        </div>

        <div className="row">
          <div>
            <label>TTS Temperature</label>
            <input
              type="number"
              min={0}
              max={1}
              step="0.1"
              value={config.tts.temperature}
              onChange={(e) =>
                setConfig({
                  ...config,
                  tts: {
                    ...config.tts,
                    temperature: clampNumber(
                      parseNumber(e.target.value, config.tts.temperature),
                      0,
                      1
                    ),
                  },
                })
              }
            />
          </div>
        </div>

        <div className="row">
          <button onClick={() => createSession.mutate()} disabled={createSession.isPending}>
            {createSession.isPending ? "Starting..." : "Start Session"}
          </button>
          <button onClick={resetSession} type="button">
            Reset Session
          </button>
        </div>
        {createSession.isError && (
          <div className="small">Failed to start session. Check backend logs.</div>
        )}
        {sessionError && <div className="small">{sessionError}</div>}
      </div>

      <div className="section">
        <h2>Bot State</h2>
        <div className="status">
          <div className={stateDotClass} />
          <div>{botState}</div>
        </div>
        <div className="small">Round Trip Latency: {latency ?? "-"} ms</div>
        {botState === "error" && (
          <div className="small">Error: {errorMessage || "Unknown error"}</div>
        )}
      </div>

      <div className="section">
        <h2>Voice</h2>
        <div className="small">Transport: {transportState}</div>
        <audio ref={audioRef} autoPlay />
      </div>
    </main>
  );
}
