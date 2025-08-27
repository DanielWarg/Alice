/**
 * FAS 1 - Brain Compose API Endpoint
 * Strict TTS entry point for voice responses
 */

import { NextRequest, NextResponse } from "next/server";
import { composeAnswer } from "@/src/brain/compose";
import { emit } from "@/src/core/eventBus";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { user_id, session_id, text, message, locale = "sv-SE" } = body || {};
    
    // Support both 'text' and 'message' field names
    const userInput = text || message;
    
    // Input validation
    if (!user_id || !session_id || !userInput) {
      return NextResponse.json({ 
        error: "Missing required fields: user_id, session_id, message/text" 
      }, { status: 400 });
    }

    // Validate text length
    if (typeof userInput !== 'string' || userInput.trim().length === 0) {
      return NextResponse.json({ 
        error: "Message must be a non-empty string" 
      }, { status: 400 });
    }

    if (userInput.length > 5000) {
      return NextResponse.json({ 
        error: "Message too long (max 5000 characters)" 
      }, { status: 400 });
    }

    // Compose the answer using our brain
    const pkg = await composeAnswer({ 
      user_id: String(user_id), 
      session_id: String(session_id), 
      text: String(userInput).trim(), 
      locale: String(locale)
    });

    // Log successful response
    emit("agent_response", { 
      user_id, 
      session_id, 
      kind: "brain_pkg", 
      len: pkg.spoken_text.length,
      confidence: pkg.meta?.confidence || 0,
      tool_used: pkg.meta?.tool_used || null
    });

    return NextResponse.json(pkg, { status: 200 });

  } catch (err: any) {
    const errorMessage = err?.message || "Brain compose failed";
    
    // Log error
    emit("agent_response", {
      kind: "brain_error",
      error: errorMessage,
      success: false
    });

    return NextResponse.json({ 
      error: errorMessage 
    }, { status: 500 });
  }
}