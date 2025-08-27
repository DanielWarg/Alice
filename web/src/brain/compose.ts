/**
 * FAS 1 - Brain Compose System
 * Central brain that composes responses for Strict TTS
 */

import { AnswerPackage, BrainComposeInput } from "../types/answer";
import { emit } from "../core/eventBus";
import { buildPromptWithContext } from "../core/promptBuilder";

export async function composeAnswer(input: BrainComposeInput): Promise<AnswerPackage> {
  const t0 = Date.now();
  
  try {
    // Emit brain compose start event
    emit("brain_compose", {
      user_id: input.user_id,
      session_id: input.session_id,
      text_len: input.text?.length || 0,
      locale: input.locale,
      stage: "start"
    });

    // Build enriched prompt with memory context and persona
    const { messages, stats } = await buildPromptWithContext(input.user_id, input.text);
    
    // Log the prompt building stats
    emit("brain_compose", {
      stage: "context_injected",
      user_id: input.user_id,
      session_id: input.session_id,
      injected_tokens_pct: stats.injected_tokens_pct,
      artifacts_used: stats.artifacts_used,
      budget_compliant: stats.injected_tokens_pct <= 25
    });
    
    // For now, still use voice-handler but this will be replaced with GPT-OSS
    const baseUrl = process.env.NODE_ENV === 'production' 
      ? 'http://localhost:3000' 
      : 'http://localhost:3000';
      
    const response = await fetch(`${baseUrl}/api/voice-handler`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: input.text,
        session_id: input.session_id
      })
    });

    if (!response.ok) {
      throw new Error(`Voice handler failed: ${response.status}`);
    }

    const result = await response.json();
    
    if (!result.success || !result.response) {
      throw new Error('Invalid response from voice handler');
    }

    // Create answer package in strict format
    const pkg: AnswerPackage = {
      spoken_text: result.response,
      screen_text: result.response.slice(0, 100) + (result.response.length > 100 ? "..." : ""),
      meta: { 
        confidence: 0.85, 
        tone: "friendly",
        tool_used: result.tool_used || null,
        injected_tokens_pct: stats.injected_tokens_pct,
        artifacts_used: stats.artifacts_used
      }
    };

    // Log completion
    emit("brain_compose", {
      t_ms: Date.now() - t0,
      user_id: input.user_id,
      session_id: input.session_id,
      text_len: input.text?.length || 0,
      response_len: pkg.spoken_text.length,
      stage: "complete",
      success: true
    });

    return pkg;

  } catch (error) {
    // Log error
    emit("brain_compose", {
      t_ms: Date.now() - t0,
      user_id: input.user_id,
      session_id: input.session_id,
      text_len: input.text?.length || 0,
      stage: "error",
      success: false,
      error: error instanceof Error ? error.message : String(error)
    });

    // Return error package
    return {
      spoken_text: "Jag hade problem att bearbeta din fråga. Kan du försöka igen?",
      screen_text: "Fel vid bearbetning",
      meta: { confidence: 0.1, tone: "apologetic" }
    };
  }
}