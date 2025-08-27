/**
 * FAS 1 - Strict TTS Integration Hook
 * Integrates brain/compose with voice pipeline
 */

import { speakAnswerPackage } from "./strictTts";

export async function handleAsrFinal({
  userId, 
  sessionId, 
  text, 
  tts
}: { 
  userId: string; 
  sessionId: string; 
  text: string; 
  tts: { speak: (p: {text?: string; ssml?: string}) => Promise<void> } 
}) {
  // Call brain to compose answer (Strict TTS)
  const resp = await fetch("/api/brain/compose", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ 
      user_id: userId, 
      session_id: sessionId, 
      text, 
      locale: "sv-SE" 
    })
  });

  if (!resp.ok) {
    throw new Error(`brain/compose failed: ${resp.status}`);
  }
  
  const pkg = await resp.json();
  
  // Speak exactly what brain composed (Strict TTS)
  await speakAnswerPackage(tts, pkg);
  
  return pkg;
}