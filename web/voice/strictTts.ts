/**
 * FAS 1 - Strict TTS Helpers
 * Ensures TTS reads exactly what brain composed
 */

import type { AnswerPackage } from "@/src/types/answer";

export interface TTSLike {
  speak(input: { text?: string; ssml?: string }): Promise<void>;
  cancel?(): void;
}

export async function speakAnswerPackage(tts: TTSLike, pkg: AnswerPackage) {
  const ssml = pkg.ssml?.trim();
  
  if (ssml && ssml.startsWith("<speak")) {
    // Use SSML if provided and valid
    await tts.speak({ ssml });
  } else {
    // Use spoken_text (Strict TTS requirement)
    await tts.speak({ text: pkg.spoken_text });
  }
}