/**
 * Ack Flow - Voice v2 acknowledgment and crossfade system
 */

type AckCatalog = Record<string, string[]>;

interface TTSResponse {
  url: string;
  cached: boolean;
  processing_time_ms?: number;
}

interface AckOptions {
  voice?: string;
  rate?: number;
  timeout?: number;
}

// Client-side cache for TTS URLs
const ACK_CACHE: Record<string, string> = {};

// Default configuration
const DEFAULT_CONFIG = {
  voice: "nova",
  rate: 1.0,
  timeout: 5000,
  fadeMs: 150
};

/**
 * Pick random item from array
 */
function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Fill parameter slots in ack phrase templates
 */
function fillSlots(template: string, params: Record<string, string | number> = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? `{${key}}`));
}

/**
 * Create cache key for TTS request
 */
function createCacheKey(text: string, voice: string, rate: number): string {
  const normalized = text.trim().replace(/\s+/g, " ");
  return `${voice}|${rate}|${normalized}`;
}

/**
 * Fetch TTS audio URL via HTTP API
 */
async function fetchTTS(text: string, voice = "nova", rate = 1.0): Promise<string> {
  const cacheKey = createCacheKey(text, voice, rate);
  
  // Return cached URL if available
  if (ACK_CACHE[cacheKey]) {
    return ACK_CACHE[cacheKey];
  }
  
  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, rate })
    });
    
    if (!response.ok) {
      throw new Error(`TTS request failed: ${response.status}`);
    }
    
    const result: TTSResponse = await response.json();
    
    // Cache the URL for future use
    ACK_CACHE[cacheKey] = result.url;
    
    return result.url;
  } catch (error) {
    console.error("TTS fetch failed:", error);
    throw error;
  }
}

/**
 * Load acknowledgment catalog from server
 */
async function loadAckCatalog(): Promise<AckCatalog> {
  try {
    const response = await fetch("/voice/ack_catalog.json");
    if (!response.ok) {
      throw new Error("Failed to load ack catalog");
    }
    return await response.json();
  } catch (error) {
    console.warn("Using fallback ack catalog:", error);
    return {
      default: ["Let me check that for you...", "One moment...", "Got it. Checking now..."]
    };
  }
}

/**
 * Start playing acknowledgment phrase immediately
 */
export async function startAck(
  intent: string,
  params: Record<string, string | number> = {},
  audioElement: HTMLAudioElement,
  options: AckOptions = {}
): Promise<HTMLAudioElement> {
  
  const config = { ...DEFAULT_CONFIG, ...options };
  
  try {
    // Load ack catalog
    const catalog = await loadAckCatalog();
    
    // Select phrase for intent
    const phrases = catalog[intent] || catalog["default"];
    const selectedPhrase = pickRandom(phrases);
    
    // Fill parameter slots
    const finalPhrase = fillSlots(selectedPhrase, params);
    
    // Get TTS audio URL
    const audioUrl = await fetchTTS(finalPhrase, config.voice, config.rate);
    
    // Set up and play audio
    audioElement.src = audioUrl;
    audioElement.volume = 1.0;
    
    // Play with timeout protection
    const playPromise = audioElement.play();
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error("Ack play timeout")), config.timeout)
    );
    
    await Promise.race([playPromise, timeoutPromise]);
    
    console.log(`🎙️ Ack started: "${finalPhrase}"`);
    return audioElement;
    
  } catch (error) {
    console.error("Ack start failed:", error);
    
    // Fallback: play simple beep or silent audio
    try {
      audioElement.src = "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+L0u2kkCjeA3NaOOQkeadnZsGcXCkmH0+DAhzQJGnU=";
      await audioElement.play();
    } catch (fallbackError) {
      console.warn("Fallback ack also failed:", fallbackError);
    }
    
    return audioElement;
  }
}

/**
 * Announce final result with smooth crossfade from ack
 */
export async function announceResult(
  resultText: string,
  ackElement: HTMLAudioElement,
  resultElement: HTMLAudioElement,
  options: AckOptions = {}
): Promise<void> {
  
  const config = { ...DEFAULT_CONFIG, ...options };
  
  try {
    // Get TTS for result
    const resultUrl = await fetchTTS(resultText, config.voice, config.rate);
    
    // Prepare result audio
    resultElement.src = resultUrl;
    resultElement.volume = 0.0; // Start silent
    
    // Start result audio
    await resultElement.play();
    
    // Perform smooth crossfade
    await performCrossfade(ackElement, resultElement, config.fadeMs);
    
    console.log(`🎙️ Result announced: "${resultText}"`);
    
  } catch (error) {
    console.error("Result announcement failed:", error);
    
    // Fallback: just stop ack and speak result text
    try {
      ackElement.pause();
      ackElement.volume = 1.0; // Reset for next time
      
      const fallbackUrl = await fetchTTS(resultText, config.voice, config.rate);
      resultElement.src = fallbackUrl;
      resultElement.volume = 1.0;
      await resultElement.play();
    } catch (fallbackError) {
      console.error("Fallback result also failed:", fallbackError);
    }
  }
}

/**
 * Perform smooth audio crossfade between two elements
 */
async function performCrossfade(
  fromElement: HTMLAudioElement,
  toElement: HTMLAudioElement,
  fadeMs: number
): Promise<void> {
  
  const steps = Math.max(10, Math.floor(fadeMs / 10)); // 10ms per step minimum
  const stepTime = fadeMs / steps;
  
  return new Promise((resolve) => {
    let currentStep = 0;
    
    const fadeInterval = setInterval(() => {
      const progress = currentStep / steps;
      
      // Fade out ack, fade in result
      fromElement.volume = Math.max(0, 1 - progress);
      toElement.volume = Math.min(1, progress);
      
      currentStep++;
      
      if (currentStep > steps) {
        clearInterval(fadeInterval);
        
        // Ensure final volumes are correct
        fromElement.volume = 0;
        toElement.volume = 1;
        
        // Reset ack element for next time
        fromElement.volume = 1.0;
        
        resolve();
      }
    }, stepTime);
  });
}

/**
 * Pre-warm high-priority acknowledgment phrases
 */
export async function warmHighPriorityAcks(voice = "nova", rate = 1.0): Promise<void> {
  const highPriorityPhrases = [
    "Let me check that for you...",
    "One moment...",
    "Got it. Checking now...",
    "Working on it...",
    "Let me check your inbox for a second...",
    "Checking your email now...",
    "Let me pull up your schedule for today...",
    "Checking your meetings...",
    "Done!",
    "All set!"
  ];
  
  console.log(`🔥 Pre-warming ${highPriorityPhrases.length} high-priority acks...`);
  
  try {
    // Warm phrases in parallel (but limit concurrency to avoid overwhelming server)
    const batchSize = 3;
    for (let i = 0; i < highPriorityPhrases.length; i += batchSize) {
      const batch = highPriorityPhrases.slice(i, i + batchSize);
      await Promise.all(batch.map(phrase => fetchTTS(phrase, voice, rate)));
    }
    
    console.log("✅ High-priority ack warming complete");
  } catch (error) {
    console.warn("Ack warming failed:", error);
  }
}

/**
 * Get current cache statistics
 */
export function getAckCacheStats(): { cached_phrases: number, cache_keys: string[] } {
  return {
    cached_phrases: Object.keys(ACK_CACHE).length,
    cache_keys: Object.keys(ACK_CACHE)
  };
}

/**
 * Clear client-side ack cache
 */
export function clearAckCache(): void {
  Object.keys(ACK_CACHE).forEach(key => delete ACK_CACHE[key]);
  console.log("🗑️ Ack cache cleared");
}