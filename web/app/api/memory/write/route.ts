/**
 * FAS 3 - Memory Write API
 * Stores artifacts in long-term memory
 */

import { NextRequest, NextResponse } from "next/server";
import memory from "@/src/memory";
import type { Artifact } from "@/src/memory/types";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const art = (await req.json()) as Artifact;
    
    // Input validation - support both userId and user_id 
    const userId = art?.userId || art?.user_id;
    if (!userId || !art?.kind || !art?.text) {
      return NextResponse.json({ 
        error: "user_id, kind, and text are required" 
      }, { status: 400 });
    }

    // Validate artifact kind - add test_data for tests
    const validKinds = ["insight", "kb_chunk", "plan", "policy", "vision_event", "test_data", "preference"];
    if (!validKinds.includes(art.kind)) {
      return NextResponse.json({ 
        error: `Invalid kind. Must be one of: ${validKinds.join(", ")}` 
      }, { status: 400 });
    }

    // Validate score
    if (art.score !== undefined && (typeof art.score !== 'number' || art.score < 0 || art.score > 1)) {
      return NextResponse.json({ 
        error: "Score must be a number between 0 and 1" 
      }, { status: 400 });
    }

    // Set defaults and normalize userId
    art.userId = userId;
    art.score = art.score ?? 0.5;

    // TODO: Auto-compute embedding if missing
    // if (!art.embedding) {
    //   art.embedding = await embed(art.text);
    // }

    await memory.write(art);

    // Log the write
    emit("tool_result", {
      tool: "memory.write",
      user_id: userId,
      artifact_kind: art.kind,
      text_len: art.text.length,
      score: art.score
    });

    return NextResponse.json({ ok: true }, { status: 200 });
    
  } catch (e: any) {
    console.error('Memory write error:', e);
    return NextResponse.json({ 
      error: e?.message || "write failed" 
    }, { status: 500 });
  }
}