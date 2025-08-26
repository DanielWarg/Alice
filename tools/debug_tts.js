// Enkelt TTS debug-skript
// Kopiera och klistra in detta i browserkonsolen (F12 → Console)

async function debugTTS() {
  console.log("🔍 TTS Debug Start");
  
  const response = await fetch('http://127.0.0.1:8000/api/tts/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: "Hej test", voice: 'sv_SE-nst-medium' })
  });
  
  const data = await response.json();
  console.log("📋 TTS Response:", {
    success: data.success,
    format: data.format, 
    audioLength: data.audio_data?.length,
    audioStart: data.audio_data?.substring(0, 20)
  });
  
  if (!data.success) {
    console.error("❌ TTS failed");
    return;
  }
  
  const audioBuffer = Uint8Array.from(atob(data.audio_data), c => c.charCodeAt(0));
  console.log("🔓 Buffer:", audioBuffer.length, "bytes");
  console.log("📁 WAV Header:", Array.from(audioBuffer.slice(0, 12)).map(b => String.fromCharCode(b)).join(''));
  
  const blob = new Blob([audioBuffer], { type: 'audio/wav' });
  const audio = new Audio(URL.createObjectURL(blob));
  
  audio.onerror = (e) => console.error("❌ Audio Error:", audio.error?.code, audio.error?.message);
  audio.oncanplay = () => console.log("✅ Audio ready");
  
  try {
    await audio.play();
    console.log("🔊 Playing audio");
  } catch (err) {
    console.error("❌ Play failed:", err.message);
  }
}

debugTTS();