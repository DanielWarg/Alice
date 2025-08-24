'use client';

export function buildWsUrl(path: string, base?: string) {
  // 1) Om env finns, använd den (t.ex. ws://localhost:8000)
  if (base) {
    try {
      const u = new URL(base);
      u.pathname = path.startsWith('/') ? path : `/${path}`;
      return u.toString();
    } catch {
      // fall through
    }
  }
  // 2) Auto—browser: använd samma host, rätt scheme och vettig port
  if (typeof window !== 'undefined') {
    const isHTTPS = window.location.protocol === 'https:';
    const proto = isHTTPS ? 'wss:' : 'ws:';
    const host = window.location.hostname;

    // Antag backend:8000 när devservern är 3000, annars behåll aktuell port
    const backendPort =
      process.env.NEXT_PUBLIC_BACKEND_PORT ||
      (window.location.port === '3000' ? '8000' : window.location.port);

    return `${proto}//${host}:${backendPort}${path.startsWith('/') ? path : `/${path}`}`;
  }
  // 3) SSR / fallback
  return `ws://127.0.0.1:8000${path.startsWith('/') ? path : `/${path}`}`;
}