export function buildApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE || "";
  // Tillåt tomt (samma origin)
  return base.replace(/\/$/, "");
}

export function buildWsUrl(): string {
  // 1) Miljövariabel vinner alltid
  const env = process.env.NEXT_PUBLIC_VOICE_WS_URL;
  if (env && /^wss?:\/\//.test(env)) return env;

  // 2) Bygg från current location (http->ws, https->wss)
  const loc = typeof window !== 'undefined' ? window.location : { protocol: 'http:', host: 'localhost:3000' } as Location;
  const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:';

  // Standard path kan ändras i .env.local via NEXT_PUBLIC_VOICE_WS_PATH
  const path = process.env.NEXT_PUBLIC_VOICE_WS_PATH || '/ws/voice-gateway';

  return `${wsProto}//${loc.host}${path}`;
}

export function buildWsCandidates(): string[] {
  // Primär: env-url eller built
  const primary = buildWsUrl();
  // Fallback: om primär pekar på /ws/voice-gateway, prova /ws/alice också
  try {
    const u = new URL(primary);
    if (u.pathname === '/ws/voice-gateway') {
      const alt = new URL(primary);
      alt.pathname = '/ws/alice';
      return [primary, alt.toString()];
    }
  } catch { /* ignore */ }
  return [primary];
}

export function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}