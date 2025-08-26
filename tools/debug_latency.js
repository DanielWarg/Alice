// Verkligt latens-mätningsscript för Alice röstpipeline
// Kör detta i browserkonsolen för att se exakt var tiden går

async function measureVoiceLatency() {
  console.log("🔍 STARTING REAL VOICE LATENCY MEASUREMENT");
  console.log("=".repeat(60));
  
  const testPrompt = "Hej Alice, vad är klockan?";
  const startTime = performance.now();
  let lastTime = startTime;
  
  function logStep(stepName, description = "") {
    const now = performance.now();
    const stepTime = now - lastTime;
    const totalTime = now - startTime;
    console.log(`⏱️  ${stepName}: ${stepTime.toFixed(0)}ms (total: ${totalTime.toFixed(0)}ms) ${description}`);
    lastTime = now;
    return now;
  }
  
  try {
    // Step 1: Prepare request
    logStep("PREP", "Building request payload");
    
    const contextData = {
      weather: "22°C, Soligt",
      location: "Göteborg", 
      time: new Date().toLocaleString('sv-SE'),
      systemMetrics: { cpu: 45, mem: 60, net: 25 }
    };
    
    const chatPayload = {
      prompt: testPrompt + " (svara kort och naturligt på svenska, max 2 meningar)",
      model: 'gpt-4o-mini',
      stream: false,
      provider: 'openai',
      raw: true,
      context: contextData
    };
    
    // Step 2: Send to backend  
    logStep("REQ_START", "Sending request to /api/chat");
    
    const response = await fetch('http://127.0.0.1:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(chatPayload)
    });
    
    logStep("REQ_COMPLETE", `Response status: ${response.status}`);
    
    // Step 3: Parse response
    const data = await response.json();
    logStep("PARSE", "Parsed JSON response");
    
    console.log("📋 AI Response:", {
      ok: data.ok,
      provider: data.provider,
      engine: data.engine,
      textLength: data.text?.length || 0,
      textPreview: data.text?.substring(0, 50) + "..."
    });
    
    if (!data.ok || !data.text) {
      console.error("❌ AI request failed:", data);
      return;
    }
    
    // Step 4: Start TTS
    logStep("TTS_START", "Starting TTS synthesis");
    
    const ttsResponse = await fetch('http://127.0.0.1:8000/api/tts/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: data.text,
        personality: 'alice',
        emotion: 'friendly',
        voice: 'sv_SE-nst-medium',
        cache: true
      })
    });
    
    logStep("TTS_COMPLETE", `TTS status: ${ttsResponse.status}`);
    
    // Step 5: Parse TTS
    const ttsData = await ttsResponse.json();
    logStep("TTS_PARSE", "Parsed TTS response");
    
    console.log("🔊 TTS Response:", {
      success: ttsData.success,
      cached: ttsData.cached,
      audioLength: ttsData.audio_data?.length || 0,
      format: ttsData.format
    });
    
    if (!ttsData.success) {
      console.error("❌ TTS failed:", ttsData);
      return;
    }
    
    // Step 6: Decode audio
    logStep("AUDIO_DECODE", "Decoding base64 audio");
    
    const audioBuffer = Uint8Array.from(atob(ttsData.audio_data), c => c.charCodeAt(0));
    const blob = new Blob([audioBuffer], { type: 'audio/wav' });
    const audioUrl = URL.createObjectURL(blob);
    
    logStep("AUDIO_BLOB", `Created audio blob (${blob.size} bytes)`);
    
    // Step 7: Play audio
    const audio = new Audio(audioUrl);
    
    logStep("AUDIO_PREP", "Prepared Audio object");
    
    // Measure actual playback start
    await new Promise((resolve, reject) => {
      let playStarted = false;
      
      audio.addEventListener('loadeddata', () => {
        if (!playStarted) {
          logStep("AUDIO_LOADED", "Audio data loaded");
        }
      });
      
      audio.addEventListener('canplay', () => {
        if (!playStarted) {
          logStep("AUDIO_CANPLAY", "Audio ready to play");
        }
      });
      
      audio.addEventListener('playing', () => {
        if (!playStarted) {
          playStarted = true;
          logStep("AUDIO_PLAYING", "🎵 AUDIO ACTUALLY STARTED PLAYING");
        }
      });
      
      audio.addEventListener('ended', () => {
        logStep("AUDIO_ENDED", "🏁 Audio playback finished");
        resolve();
      });
      
      audio.addEventListener('error', (e) => {
        logStep("AUDIO_ERROR", "❌ Audio playback failed");
        reject(e);
      });
      
      // Try to play
      audio.play().then(() => {
        logStep("PLAY_PROMISE", "Play promise resolved");
      }).catch(reject);
    });
    
    const totalTime = performance.now() - startTime;
    
    console.log("=".repeat(60));
    console.log(`🏁 TOTAL VOICE PIPELINE TIME: ${totalTime.toFixed(0)}ms (${(totalTime/1000).toFixed(1)}s)`);
    console.log("=".repeat(60));
    
    // Cleanup
    URL.revokeObjectURL(audioUrl);
    
  } catch (error) {
    logStep("ERROR", "❌ Pipeline failed");
    console.error("Pipeline error:", error);
    console.error("Error stack:", error.stack);
  }
}

// Kör flera mätningar för att se variation
async function runLatencyBenchmark(iterations = 3) {
  console.log(`🚀 Running ${iterations} latency benchmarks...`);
  
  for (let i = 1; i <= iterations; i++) {
    console.log(`\n${"=".repeat(20)} RUN ${i}/${iterations} ${"=".repeat(20)}`);
    await measureVoiceLatency();
    
    if (i < iterations) {
      console.log("⏳ Waiting 2s before next run...");
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  console.log("\n🎯 Benchmark complete! Check the logs above for bottlenecks.");
}

// Starta benchmark
console.log("Starting voice latency benchmark...");
runLatencyBenchmark(2);