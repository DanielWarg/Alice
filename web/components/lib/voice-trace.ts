// components/lib/voice-trace.ts
/* Tiny structured tracer for Voice flows. Drop-in, no deps. */
type Level = "debug" | "info" | "warn" | "error";
type Entry = {
  t: number;                // epoch ms
  lvl: Level;
  sid?: string;             // session id
  ev: string;               // event name
  data?: any;               // payload
  durMs?: number;           // duration for *:end events
};

const BUF_MAX = 2000;
const timers = new Map<string, number>();
const buf: Entry[] = [];
let enabled = true; // Force enable for debugging

let minLevel: Level = "debug"; // debug|info|warn|error

function push(e: Entry) {
  buf.push(e);
  if (buf.length > BUF_MAX) buf.shift();
  // console echo respecting minLevel
  const order: Record<Level, number> = { debug: 0, info: 1, warn: 2, error: 3 };
  if (!enabled || order[e.lvl] < order[minLevel]) return;
  const tag = `%c[Voice]%c ${e.sid ? `[${e.sid}] ` : ""}${e.ev}`;
  const s1 = "color:#06b6d4;font-weight:600";
  const s2 = "color:#A7F3D0";
  if (e.lvl === "error") console.error(tag, s1, s2, e.data ?? "");
  else if (e.lvl === "warn") console.warn(tag, s1, s2, e.data ?? "");
  else if (e.lvl === "info") console.info(tag, s1, s2, e.data ?? "");
  else console.debug(tag, s1, s2, e.data ?? "");
}

function id(prefix = "sid"): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}-${Date.now().toString(36)}`;
}

export const trace = {
  /** Enable/disable at runtime */
  enable(v: boolean) { enabled = v; },
  /** Raise minimum console level (still stored in buffer) */
  level(l: Level) { minLevel = l; },
  /** Start a new session; returns sid */
  start(label = "voice"): string {
    const sid = id(label);
    push({ t: Date.now(), lvl: "info", sid, ev: "session.start" });
    return sid;
  },
  /** Generic event */
  ev(sid: string | undefined, ev: string, data?: any, lvl: Level = "debug") {
    push({ t: Date.now(), lvl, sid, ev, data });
  },
  /** Time start/end helpers */
  timeStart(sid: string | undefined, key: string, data?: any) {
    const k = `${sid ?? "global"}::${key}`;
    timers.set(k, Date.now());
    push({ t: Date.now(), lvl: "info", sid, ev: `${key}.start`, data });
  },
  timeEnd(sid: string | undefined, key: string, data?: any) {
    const k = `${sid ?? "global"}::${key}`;
    const start = timers.get(k);
    const dur = start ? Date.now() - start : undefined;
    timers.delete(k);
    push({ t: Date.now(), lvl: dur != null ? "info" : "warn", sid, ev: `${key}.end`, data, durMs: dur });
  },
  /** Error helper */
  error(sid: string | undefined, ev: string, err: unknown) {
    const data = err instanceof Error ? { name: err.name, message: err.message, stack: err.stack } : err;
    push({ t: Date.now(), lvl: "error", sid, ev, data });
  },
  /** Inspect from console or UI */
  dump() { return [...buf]; },
  clear() { buf.length = 0; },
};

// Global handlers for unhandled errors (only in browser)
if (typeof window !== "undefined") {
  window.addEventListener("error", (e) => trace.error(undefined, "window.error", e.error ?? e.message));
  window.addEventListener("unhandledrejection", (e) => trace.error(undefined, "window.unhandledrejection", e.reason));
  // Expose convenience in DevTools:
  (window as any).voiceTrace = trace;
}