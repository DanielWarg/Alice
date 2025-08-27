/**
 * Event Bus - In-process pub/sub system
 * 
 * Central event routing for Alice's orchestrator components.
 * Handles communication between state machines, tools, and UI components.
 */

import { EventEmitter } from "events";

// Create singleton event bus instance
export const bus = new EventEmitter();

// Set maximum listeners to prevent memory leaks
bus.setMaxListeners(100);

// Type-safe event handling
export const on = <T = any>(type: string, handler: (event: T) => void) => {
  bus.on(type, handler);
  return () => bus.off(type, handler); // Return unsubscribe function
};

export const emit = <T = any>(type: string, payload: T) => {
  bus.emit(type, payload);
};

// Event types for type safety
export const EVENTS = {
  // Turn management
  TURN_STARTED: "turn_started",
  TURN_COMPLETED: "turn_completed", 
  TURN_INTERRUPTED: "turn_interrupted",
  
  // State transitions
  STATE_CHANGED: "state_changed",
  
  // Tool execution
  TOOL_STARTED: "tool_started",
  TOOL_COMPLETED: "tool_completed",
  TOOL_ERROR: "tool_error",
  
  // Voice processing
  ASR_PARTIAL: "asr_partial",
  ASR_FINAL: "asr_final",
  TTS_STARTED: "tts_started",
  TTS_CHUNK: "tts_chunk",
  TTS_COMPLETED: "tts_completed",
  
  // Privacy and security
  PRIVACY_CHECK: "privacy_check",
  PII_DETECTED: "pii_detected",
  CLOUD_BLOCKED: "cloud_blocked",
  
  // Metrics and monitoring
  METRIC_RECORDED: "metric_recorded",
  HEALTH_CHECK: "health_check",
  
  // External integrations
  HA_EVENT: "ha_event",
  VISION_EVENT: "vision_event"
} as const;

// Event payload types
export interface TurnEvent {
  sessionId: string;
  turnId: string;
  state?: string;
  timestamp?: number;
}

export interface ToolEvent {
  toolName: string;
  args: any;
  result?: any;
  error?: string;
  duration?: number;
}

export interface VoiceEvent {
  turnId: string;
  audio?: Buffer;
  text?: string;
  confidence?: number;
}

export interface PrivacyEvent {
  input: any;
  hasPII: boolean;
  safeSummary?: string;
  blocked?: boolean;
}

// Helper functions for common event patterns
export const once = <T = any>(type: string, handler: (event: T) => void) => {
  bus.once(type, handler);
};

export const off = (type: string, handler: Function) => {
  bus.off(type, handler);
};

export const removeAllListeners = (type?: string) => {
  if (type) {
    bus.removeAllListeners(type);
  } else {
    bus.removeAllListeners();
  }
};

// Debug logging in development
if (process.env.NODE_ENV === "development") {
  bus.on("newListener", (event, listener) => {
    console.log(`🔔 New listener for ${event}:`, listener.name || "anonymous");
  });
  
  bus.on("removeListener", (event, listener) => {
    console.log(`🔕 Removed listener for ${event}:`, listener.name || "anonymous");
  });
}

export default bus;
