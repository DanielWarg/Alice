"use client";

import { useState, useRef, useEffect } from "react";
import { startAck, announceResult, warmHighPriorityAcks, getAckCacheStats } from "../lib/voice/ack-flow";

interface VoiceV2InterfaceProps {
  onCommand?: (command: string) => Promise<string>;
  className?: string;
}

interface VoiceSession {
  active: boolean;
  intent: string;
  startTime: number;
  ackPhrase?: string;
  resultText?: string;
}

export default function VoiceV2Interface({ onCommand, className = "" }: VoiceV2InterfaceProps) {
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [cacheStats, setCacheStats] = useState({ cached_phrases: 0, cache_keys: [] });
  const [isWarming, setIsWarming] = useState(false);
  
  // Audio elements for ack and result
  const ackAudioRef = useRef<HTMLAudioElement>(null);
  const resultAudioRef = useRef<HTMLAudioElement>(null);
  
  // Voice settings
  const voice = "nova";
  const rate = 1.0;
  
  useEffect(() => {
    // Pre-warm high-priority phrases on component mount
    const warmCache = async () => {
      setIsWarming(true);
      try {
        await warmHighPriorityAcks(voice, rate);
        setCacheStats(getAckCacheStats());
      } catch (error) {
        console.error("Cache warming failed:", error);
      } finally {
        setIsWarming(false);
      }
    };
    
    warmCache();
  }, []);
  
  /**
   * Execute voice command with ack-flow pattern
   */
  const executeVoiceCommand = async (
    intent: string, 
    command: string, 
    params: Record<string, string | number> = {},
    customHandler?: () => Promise<string>
  ) => {
    if (!ackAudioRef.current || !resultAudioRef.current) {
      console.error("Audio elements not available");
      return;
    }
    
    const sessionStart = Date.now();
    
    setSession({
      active: true,
      intent,
      startTime: sessionStart
    });
    
    try {
      // 1. Start immediate acknowledgment
      console.log(`🎙️ Starting ack for intent: ${intent}`);
      await startAck(intent, params, ackAudioRef.current, { voice, rate });
      
      // 2. Execute command in parallel with ack playback
      console.log(`🧠 Processing command: ${command}`);
      const result = customHandler 
        ? await customHandler()
        : onCommand 
        ? await onCommand(command) 
        : `Mock result for: ${command}`;
      
      // 3. Announce result with crossfade
      console.log(`🎵 Announcing result with crossfade`);
      await announceResult(result, ackAudioRef.current, resultAudioRef.current, { voice, rate });
      
      // Update session with result
      setSession(prev => prev ? {
        ...prev,
        resultText: result,
        active: false
      } : null);
      
      // Update cache stats
      setCacheStats(getAckCacheStats());
      
      const totalTime = Date.now() - sessionStart;
      console.log(`✅ Voice session complete: ${totalTime}ms total`);
      
    } catch (error) {
      console.error("Voice command failed:", error);
      setSession(prev => prev ? { ...prev, active: false } : null);
    }
  };
  
  /**
   * Real command handlers that use backend APIs
   */
  const realCommandHandlers: Record<string, () => Promise<string>> = {
    email: async () => {
      const response = await fetch('/api/brain/mail-count');
      const { count } = await response.json();
      return count === 0 
        ? "You have no new emails."
        : count === 1
        ? "You have 1 new email. Would you like me to read it?"
        : `You have ${count} new emails. Would you like me to read them?`;
    },
    
    calendar: async () => {
      // TODO: Implement real calendar API call
      return "Your calendar is clear for today.";
    },
    
    weather: async () => {
      // TODO: Implement real weather API call
      return "It's 19 degrees and partly cloudy in Stockholm right now.";
    },
    
    timer: async () => {
      // TODO: Implement real timer API call
      return "Timer set for 10 minutes. I'll let you know when it's done.";
    },
    
    music: async () => {
      // TODO: Implement real Spotify API call
      return "Playing your liked songs. Now playing music for you.";
    },
    
    search: async () => {
      // TODO: Implement real search API call
      return "AI is a broad field covering machine learning, neural networks, and intelligent systems.";
    }
  };

  /**
   * Handle different voice scenarios
   */
  const handleScenario = (scenario: string) => {
    switch (scenario) {
      case "email":
        executeVoiceCommand("mail.check_unread", "Check my unread emails", {}, realCommandHandlers.email);
        break;
      case "calendar":
        executeVoiceCommand("calendar.today", "What's on my calendar today?", {}, realCommandHandlers.calendar);
        break;
      case "weather":
        executeVoiceCommand("weather.current", "What's the weather in Stockholm?", { city: "Stockholm" }, realCommandHandlers.weather);
        break;
      case "timer":
        executeVoiceCommand("timer.set", "Set a timer for 10 minutes", { duration: "10 minutes" }, realCommandHandlers.timer);
        break;
      case "music":
        executeVoiceCommand("spotify.play", "Play some music", {}, realCommandHandlers.music);
        break;
      case "search":
        executeVoiceCommand("general.search", "Search for information about AI", {}, realCommandHandlers.search);
        break;
      default:
        executeVoiceCommand("default", `Unknown command: ${scenario}`);
    }
  };
  
  return (
    <div className={`voice-v2-interface bg-white border border-gray-200 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          🎙️ Voice v2 - Ack Flow System
        </h2>
        
        <div className="flex items-center space-x-2">
          {isWarming && (
            <span className="text-sm text-yellow-600">🔥 Warming cache...</span>
          )}
          
          <span className="text-sm text-gray-500">
            Cache: {cacheStats.cached_phrases} phrases
          </span>
        </div>
      </div>
      
      {/* Current Session Status */}
      {session && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-blue-900">
                Current Session: {session.intent}
              </h3>
              {session.active && (
                <p className="text-sm text-blue-700">
                  🎵 Processing... ({Math.round((Date.now() - session.startTime) / 1000)}s)
                </p>
              )}
              {session.resultText && !session.active && (
                <p className="text-sm text-green-700">
                  ✅ Complete: "{session.resultText}"
                </p>
              )}
            </div>
            
            {session.active && (
              <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
            )}
          </div>
        </div>
      )}
      
      {/* Test Scenarios */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => handleScenario("email")}
          disabled={session?.active}
          className="p-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          📧 Check Email
        </button>
        
        <button
          onClick={() => handleScenario("calendar")}
          disabled={session?.active}
          className="p-3 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          📅 Today's Calendar
        </button>
        
        <button
          onClick={() => handleScenario("weather")}
          disabled={session?.active}
          className="p-3 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          🌤️ Weather in Stockholm
        </button>
        
        <button
          onClick={() => handleScenario("timer")}
          disabled={session?.active}
          className="p-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          ⏰ Set Timer (10min)
        </button>
        
        <button
          onClick={() => handleScenario("music")}
          disabled={session?.active}
          className="p-3 bg-pink-500 text-white rounded-lg hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          🎵 Play Music
        </button>
        
        <button
          onClick={() => handleScenario("search")}
          disabled={session?.active}
          className="p-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          🔍 Search AI Info
        </button>
      </div>
      
      {/* Audio Elements */}
      <div className="hidden">
        <audio 
          ref={ackAudioRef}
          preload="none"
          onError={(e) => console.error("Ack audio error:", e)}
        />
        <audio 
          ref={resultAudioRef}
          preload="none"
          onError={(e) => console.error("Result audio error:", e)}
        />
      </div>
      
      {/* Debug Info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-6 p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm">
          <h4 className="font-medium text-gray-700 mb-2">Debug Info:</h4>
          <div className="space-y-1 text-gray-600">
            <p>Voice: {voice} | Rate: {rate}</p>
            <p>Cache: {cacheStats.cached_phrases} phrases loaded</p>
            {session && (
              <p>Session: {session.intent} | Active: {session.active}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}