/**
 * Orchestrator Types and Event Contracts
 * 
 * Core type definitions for Alice's orchestrator system.
 * Defines state machines, metrics, and tool interfaces.
 */

// Turn state machine states
export type TurnState = 
  | "IDLE"           // Initial state, waiting for input
  | "LYSSNAR"        // Listening for audio input
  | "TOLKAR"         // Processing input (ASR/LLM)
  | "PLANNER"        // Planning tool execution
  | "KÖR_VERKTYG"    // Executing tools
  | "PRIVACY"        // Privacy filtering and safe summary
  | "TAL"            // Text-to-speech output
  | "KLAR"           // Turn completed successfully
  | "AVBRUTEN";      // Turn interrupted (barge-in)

// Session management
export interface Session {
  id: string;
  userId?: string;
  createdAt: number;
  lastActivity: number;
  settings: SessionSettings;
}

export interface SessionSettings {
  language: string;
  voiceId: string;
  privacyLevel: "strict" | "normal" | "permissive";
  cloudEnabled: boolean;
  visionEnabled: boolean;
}

// Turn management
export interface Turn {
  id: string;
  sessionId: string;
  state: TurnState;
  startedAt: number;
  updatedAt: number;
  input?: TurnInput;
  output?: TurnOutput;
  metrics: TurnMetrics;
}

export interface TurnInput {
  type: "audio" | "text";
  content: string | Buffer;
  timestamp: number;
  confidence?: number;
}

export interface TurnOutput {
  type: "text" | "audio" | "action";
  content: string | Buffer;
  timestamp: number;
  safeSummary?: string;
}

// Performance metrics
export interface TurnMetrics {
  // Timing measurements
  first_partial_ms?: number;    // Time to first ASR partial
  ttft_ms?: number;             // Time to first token (LLM)
  tts_first_chunk_ms?: number;  // Time to first TTS audio
  total_latency_ms?: number;    // End-to-end latency
  
  // Barge-in metrics
  barge_in_cut_ms?: number;     // How fast barge-in was handled
  
  // Privacy metrics
  privacy_leak_attempts?: number; // Number of blocked PII attempts
  
  // Tool metrics
  tool_execution_ms?: number;   // Time spent in tool execution
  tool_count?: number;          // Number of tools used
  
  // Quality metrics
  asr_confidence?: number;      // ASR confidence score
  llm_tokens?: number;          // LLM token count
  tts_quality?: number;         // TTS quality score
}

// Tool system
export interface ToolCall {
  name: string;
  args: Record<string, any>;
  mutating?: boolean;           // Does this tool modify state?
  requiresConfirmation?: boolean; // User confirmation needed?
  timeout?: number;             // Execution timeout in ms
}

export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
  executionTime: number;
  metadata?: Record<string, any>;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: ToolParameters;
  returns: ToolReturns;
  mutating: boolean;
  rateLimit?: RateLimit;
}

export interface ToolParameters {
  type: "object";
  properties: Record<string, ToolParameter>;
  required: string[];
}

export interface ToolParameter {
  type: string;
  description: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  pattern?: string;
}

export interface ToolReturns {
  type: string;
  description: string;
}

export interface RateLimit {
  maxCalls: number;
  timeWindow: number; // in seconds
}

// Privacy and security
export interface PrivacyCheck {
  input: any;
  hasPII: boolean;
  piiTypes: string[];
  safeSummary: string;
  riskLevel: "low" | "medium" | "high";
}

export interface PIIPattern {
  type: string;
  pattern: RegExp;
  replacement: string;
  riskLevel: "low" | "medium" | "high";
}

// Configuration
export interface OrchestratorConfig {
  // Performance settings
  jitterMs: number;
  asrChunkMs: number;
  asrStabilizeMs: number;
  llmMaxNewTokens: number;
  llmTemperature: number;
  ttsChunkMs: number;
  bargeInFadeMs: number;
  
  // Privacy settings
  safeSummaryMaxLen: number;
  allowCloud: boolean;
  cloudTtfaDegradeMs: number;
  
  // Feature flags
  allowVision: boolean;
  allowPatternLLM: boolean;
  
  // Rate limiting
  maxTurnsPerMinute: number;
  maxToolCallsPerTurn: number;
}

// Error types
export class OrchestratorError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = "OrchestratorError";
  }
}

export class TurnNotFoundError extends OrchestratorError {
  constructor(turnId: string) {
    super(`Turn ${turnId} not found`, "TURN_NOT_FOUND", { turnId });
    this.name = "TurnNotFoundError";
  }
}

export class InvalidStateTransitionError extends OrchestratorError {
  constructor(from: TurnState, to: TurnState) {
    super(`Invalid state transition: ${from} → ${to}`, "INVALID_STATE_TRANSITION", { from, to });
    this.name = "InvalidStateTransitionError";
  }
}

export class PrivacyViolationError extends OrchestratorError {
  constructor(details: string) {
    super(`Privacy violation: ${details}`, "PRIVACY_VIOLATION", { details });
    this.name = "PrivacyViolationError";
  }
}

// Event types for type safety
export type OrchestratorEvent = 
  | { type: "turn_started"; data: Turn }
  | { type: "turn_completed"; data: Turn }
  | { type: "turn_interrupted"; data: Turn }
  | { type: "state_changed"; data: { turnId: string; from: TurnState; to: TurnState } }
  | { type: "tool_started"; data: ToolCall }
  | { type: "tool_completed"; data: ToolResult }
  | { type: "privacy_check"; data: PrivacyCheck };

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
