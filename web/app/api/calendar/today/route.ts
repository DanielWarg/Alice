// web/app/api/calendar/today/route.ts
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/calendar/today`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // ingen cache så vi slipper stale data
      cache: "no-store",
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: `Backend HTTP ${res.status}` },
        { status: res.status }
      );
    }
    
    const json = await res.json();
    return NextResponse.json(json);
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: `Proxy error: ${e?.message || String(e)}` },
      { status: 502 }
    );
  }
}