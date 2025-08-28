// web/components/lib/http.ts
export function buildApiBase(): string {
  const base = (process.env.NEXT_PUBLIC_API_BASE || "").trim();
  return base ? base.replace(/\/$/, "") : "";
}

export async function getJson<T>(
  path: string,
  opts: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const timeoutMs = opts.timeoutMs ?? 6000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // 1) Först prova Next-proxyn (samma origin)
  const candidates = [path];

  // 2) Fallback till backend-bas om satt (för direktanrop i dev)
  const base = buildApiBase();
  if (base) candidates.push(`${base}${path}`);

  const errors: string[] = [];
  try {
    for (const url of candidates) {
      try {
        const res = await fetch(url, {
          ...opts,
          signal: controller.signal,
          cache: "no-store",
        });
        if (!res.ok) {
          errors.push(`${url} -> HTTP ${res.status}`);
          continue;
        }
        const data = (await res.json()) as T;
        clearTimeout(timer);
        return data;
      } catch (e: any) {
        errors.push(`${url} -> ${e?.message || String(e)}`);
      }
    }
    throw new Error(errors.join(" | "));
  } finally {
    clearTimeout(timer);
  }
}