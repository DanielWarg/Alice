// components/VoiceGatewayClient.tsx
import React, { useImperativeHandle, forwardRef, useRef, useState } from "react";
import { buildWsCandidates } from "./lib/ws-utils";
import { trace } from "./lib/voice-trace"; // 👈 ADD

export type VoiceGatewayStatus = "idle" | "connecting" | "connected" | "streaming" | "error" | "closed";

export type VoiceGatewayHandle = {
  connect: () => Promise<void>;
  disconnect: () => void;
  startMic: () => Promise<void>;
  stopMic: () => void;
  isConnected: () => boolean;
  isStreaming: () => boolean;
};

type Props = {
  onStatus?: (s: VoiceGatewayStatus) => void;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
  sampleRate?: number; // default 16000
  bufferSize?: number; // default 4096
};

export const VoiceGatewayClient = forwardRef<VoiceGatewayHandle, Props>(
  ({ onStatus, onTranscript, onResponse, sampleRate = 16000, bufferSize = 4096 }, ref) => {
    const wsRef = useRef<WebSocket | null>(null);
    const ctxRef = useRef<AudioContext | null>(null);
    const procRef = useRef<ScriptProcessorNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const [connected, setConnected] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const sidRef = useRef<string>(trace.start("voicegw")); // 👈 session

    function setStatus(s: VoiceGatewayStatus) {
      onStatus?.(s);
      trace.ev(sidRef.current, "status", { s }, s === "error" ? "error" : "info");
    }

    async function connectOnce(url: string): Promise<boolean> {
      trace.timeStart(sidRef.current, "ws.connect", { url });
      return new Promise<boolean>((resolve) => {
        let resolved = false;
        try {
          const ws = new WebSocket(url);
          ws.binaryType = "arraybuffer";

          ws.onopen = () => {
            wsRef.current = ws;
            setConnected(true);
            setStatus("connected");
            trace.timeEnd(sidRef.current, "ws.connect", { ok: true, url });
            resolved = true;
            resolve(true);
          };
          ws.onerror = (e) => {
            trace.error(sidRef.current, "ws.error", e);
          };
          ws.onclose = (e) => {
            if (wsRef.current === ws) wsRef.current = null;
            setConnected(false);
            setStreaming(false);
            setStatus("closed");
            if (!resolved) {
              trace.timeEnd(sidRef.current, "ws.connect", { ok: false, url, code: e.code, reason: e.reason });
              resolve(false);
            }
          };
          ws.onmessage = (ev) => {
            try {
              const message = JSON.parse(ev.data);
              trace.ev(sidRef.current, "ws.message", { type: message.type });
              
              if (message.type === "transcript" && onTranscript) {
                onTranscript(message.text);
              } else if (message.type === "response" && onResponse) {
                onResponse(message.text);
              }
            } catch (e) {
              trace.ev(sidRef.current, "ws.message.parse_error", { data: ev.data });
            }
          };
        } catch (e) {
          trace.error(sidRef.current, "ws.construct", e);
          trace.timeEnd(sidRef.current, "ws.connect", { ok: false, url, thrown: true });
          resolve(false);
        }
      });
    }

    async function connect(): Promise<void> {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
      setStatus("connecting");
      const candidates = buildWsCandidates();
      trace.ev(sidRef.current, "ws.candidates", { candidates });
      for (const url of candidates) {
        const ok = await connectOnce(url);
        if (ok) return;
      }
      throw new Error("No WS endpoint reachable");
    }

    function disconnect() {
      trace.ev(sidRef.current, "disconnect");
      try { wsRef.current?.close(); } catch (e) { trace.error(sidRef.current, "ws.close", e); }
      wsRef.current = null;
      setConnected(false);
      stopMic();
      setStatus("closed");
    }

    async function startMic(): Promise<void> {
      trace.ev(sidRef.current, "mic.start.click");
      await connect();

      // getUserMedia
      try {
        trace.timeStart(sidRef.current, "gum.request");
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        streamRef.current = stream;
        trace.timeEnd(sidRef.current, "gum.request", { ok: true });
      } catch (e) {
        trace.timeEnd(sidRef.current, "gum.request", { ok: false });
        trace.error(sidRef.current, "gum.error", e);
        setStatus("error");
        throw e;
      }

      // AudioContext + ScriptProcessor
      try {
        trace.timeStart(sidRef.current, "audio.init", { sampleRate, bufferSize });
        const Ctx: any = (window as any).AudioContext || (window as any).webkitAudioContext;
        const ctx = new Ctx({ sampleRate });
        ctxRef.current = ctx;

        const src = ctx.createMediaStreamSource(streamRef.current!);
        const proc = ctx.createScriptProcessor(bufferSize, 1, 1);
        src.connect(proc);
        proc.connect(ctx.destination);

        proc.onaudioprocess = (e) => {
          if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            trace.ev(sidRef.current, "audio.process.skip", { wsReady: !!wsRef.current, readyState: wsRef.current?.readyState });
            return;
          }
          const input = e.inputBuffer.getChannelData(0);
          
          // Calculate RMS for debug
          const rms = Math.sqrt(input.reduce((sum, val) => sum + val * val, 0) / input.length);
          
          const buf = new ArrayBuffer(input.length * 2);
          const view = new DataView(buf);
          for (let i = 0; i < input.length; i++) {
            let s = Math.max(-1, Math.min(1, input[i]));
            view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
          }
          try {
            wsRef.current.send(buf);
            trace.ev(sidRef.current, "audio.sent", { samples: input.length, rms: rms.toFixed(4), bytes: buf.byteLength });
          } catch (sendErr) {
            trace.error(sidRef.current, "ws.send.error", sendErr);
          }
        };

        procRef.current = proc;
        trace.timeEnd(sidRef.current, "audio.init", { ok: true });
      } catch (e) {
        trace.timeEnd(sidRef.current, "audio.init", { ok: false });
        trace.error(sidRef.current, "audio.init.error", e);
        setStatus("error");
        throw e;
      }

      setStreaming(true);
      setStatus("streaming");
    }

    function stopMic() {
      trace.ev(sidRef.current, "mic.stop.click");
      try { procRef.current?.disconnect(); } catch (e) { trace.error(sidRef.current, "audio.proc.disconnect", e); }
      try { ctxRef.current?.close(); } catch (e) { trace.error(sidRef.current, "audio.ctx.close", e); }
      try { streamRef.current?.getTracks().forEach((t) => t.stop()); } catch (e) { trace.error(sidRef.current, "gum.tracks.stop", e); }
      procRef.current = null;
      ctxRef.current = null;
      streamRef.current = null;
      setStreaming(false);
      setStatus(connected ? "connected" : "idle");
    }

    useImperativeHandle(ref, () => ({
      connect,
      disconnect,
      startMic,
      stopMic,
      isConnected: () => !!connected,
      isStreaming: () => !!streaming,
    }));

    return null;
  }
);

VoiceGatewayClient.displayName = "VoiceGatewayClient";