/**
 * FAS 3 - Memory Fetch API
 * Retrieves artifacts from long-term memory
 */

import { NextRequest, NextResponse } from "next/server";
import memory from "@/src/memory";
import type { ArtifactKind } from "@/src/memory/types";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { user_id, k = 5, kinds } = body || {};
    
    // Input validation
    if (!user_id) {
      return NextResponse.json({ 
        error: "user_id is required" 
      }, { status: 400 });
    }

    if (typeof k !== 'number' || k < 1 || k > 100) {
      return NextResponse.json({ 
        error: "k must be a number between 1 and 100" 
      }, { status: 400 });
    }

    // Validate kinds if provided
    if (kinds && !Array.isArray(kinds)) {
      return NextResponse.json({ 
        error: "kinds must be an array" 
      }, { status: 400 });
    }

    const validKinds = ["insight", "kb_chunk", "plan", "policy", "vision_event"];
    if (kinds && kinds.some((kind: string) => !validKinds.includes(kind))) {
      return NextResponse.json({ 
        error: `Invalid kinds. Must be one of: ${validKinds.join(", ")}` 
      }, { status: 400 });
    }

    const arts = await memory.fetch(String(user_id), Number(k), kinds as ArtifactKind[] | undefined);

    // Log the fetch
    emit("tool_result", {
      tool: "memory.fetch",
      user_id: String(user_id),
      k: Number(k),
      kinds: kinds || null,
      results_count: arts.length
    });

    return NextResponse.json({ artifacts: arts }, { status: 200 });
    
  } catch (e: any) {
    console.error('Memory fetch error:', e);
    return NextResponse.json({ 
      error: e?.message || "fetch failed" 
    }, { status: 500 });
  }
}