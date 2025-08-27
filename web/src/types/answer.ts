/**
 * FAS 1 - Strict TTS Answer Package Interface
 * Defines the exact structure for voice responses
 */

export interface AnswerPackage {
  spoken_text: string;              // exakt vad TTS ska läsa upp
  screen_text?: string;             // kort text till UI
  ssml?: string;                    // om satt – använd denna före spoken_text
  citations?: { title: string; url?: string }[];
  meta?: { confidence: number; tone?: string };
}

export interface BrainComposeInput {
  user_id: string;
  session_id: string;
  text: string;
  locale: "sv-SE" | string;
}