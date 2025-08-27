/**
 * Turn State Machine - Session and Turn Management
 * 
 * Manages the lifecycle of conversation turns with state validation
 * and transition logging for Alice's orchestrator.
 */

import { TurnState, Turn, TurnMetrics, InvalidStateTransitionError } from "./types";
import { emit } from "./eventBus";
import { logNDJSON } from "./metrics";

// Valid state transitions
const VALID_TRANSITIONS: Record<TurnState, TurnState[]> = {
  IDLE: ["LYSSNAR"],
  LYSSNAR: ["TOLKAR", "AVBRUTEN"],
  TOLKAR: ["PLANNER", "TAL", "AVBRUTEN"],
  PLANNER: ["KÖR_VERKTYG", "TAL", "AVBRUTEN"],
  KÖR_VERKTYG: ["PRIVACY", "AVBRUTEN"],
  PRIVACY: ["TAL", "AVBRUTEN"],
  TAL: ["KLAR", "AVBRUTEN"],
  KLAR: [], // Terminal state
  AVBRUTEN: ["LYSSNAR"] // Can restart after interruption
};

export class TurnController {
  private _state: TurnState = "IDLE";
  private _startTime: number;
  private _metrics: TurnMetrics = {};
  private _history: Array<{ state: TurnState; timestamp: number; reason?: string }> = [];

  constructor(
    public readonly turnId: string,
    public readonly sessionId: string
  ) {
    this._startTime = Date.now();
    this._history.push({ state: "IDLE", timestamp: this._startTime });
  }

  /**
   * Get current state
   */
  get state(): TurnState {
    return this._state;
  }

  /**
   * Get turn metrics
   */
  get metrics(): TurnMetrics {
    return this._metrics;
  }

  /**
   * Get state history
   */
  get history(): Array<{ state: TurnState; timestamp: number; reason?: string }> {
    return [...this._history];
  }

  /**
   * Get turn duration in milliseconds
   */
  get duration(): number {
    return Date.now() - this._startTime;
  }

  /**
   * Transition to a new state
   */
  transit(nextState: TurnState, reason?: string): void {
    const currentState = this._state;
    
    // Validate transition
    if (!this.isValidTransition(currentState, nextState)) {
      throw new InvalidStateTransitionError(currentState, nextState);
    }

    // Update state
    this._state = nextState;
    const timestamp = Date.now();
    
    // Record transition
    this._history.push({ 
      state: nextState, 
      timestamp, 
      reason 
    });

    // Update metrics based on state
    this.updateMetrics(nextState, timestamp);

    // Emit state change event
    emit("state_changed", {
      turnId: this.turnId,
      sessionId: this.sessionId,
      from: currentState,
      to: nextState,
      reason,
      timestamp
    });

    // Log transition
    logNDJSON({
      event: "state_transition",
      timestamp,
      turnId: this.turnId,
      sessionId: this.sessionId,
      from: currentState,
      to: nextState,
      reason,
      duration_ms: timestamp - this._startTime
    });

    console.log(`🔄 Turn ${this.turnId}: ${currentState} → ${nextState}${reason ? ` (${reason})` : ""}`);
  }

  /**
   * Check if a state transition is valid
   */
  private isValidTransition(from: TurnState, to: TurnState): boolean {
    return VALID_TRANSITIONS[from].includes(to);
  }

  /**
   * Update metrics based on state changes
   */
  private updateMetrics(state: TurnState, timestamp: number): void {
    const duration = timestamp - this._startTime;

    switch (state) {
      case "TOLKAR":
        // Record time to start processing
        if (!this._metrics.first_partial_ms) {
          this._metrics.first_partial_ms = duration;
        }
        break;

      case "TAL":
        // Record time to start TTS
        if (!this._metrics.tts_first_chunk_ms) {
          this._metrics.tts_first_chunk_ms = duration;
        }
        break;

      case "KLAR":
        // Record total latency
        this._metrics.total_latency_ms = duration;
        break;

      case "AVBRUTEN":
        // Record barge-in cut time
        this._metrics.barge_in_cut_ms = duration;
        break;
    }
  }

  /**
   * Set specific metric value
   */
  setMetric(key: keyof TurnMetrics, value: number): void {
    this._metrics[key] = value;
    
    logNDJSON({
      event: "metric_set",
      timestamp: Date.now(),
      turnId: this.turnId,
      metric: key,
      value
    });
  }

  /**
   * Get turn summary for logging/monitoring
   */
  getSummary(): {
    turnId: string;
    sessionId: string;
    state: TurnState;
    duration: number;
    metrics: TurnMetrics;
    history: Array<{ state: TurnState; timestamp: number; reason?: string }>;
  } {
    return {
      turnId: this.turnId,
      sessionId: this.sessionId,
      state: this._state,
      duration: this.duration,
      metrics: { ...this._metrics },
      history: [...this._history]
    };
  }

  /**
   * Check if turn is in a terminal state
   */
  isComplete(): boolean {
    return this._state === "KLAR" || this._state === "AVBRUTEN";
  }

  /**
   * Check if turn can be interrupted
   */
  canInterrupt(): boolean {
    return !["KLAR", "AVBRUTEN"].includes(this._state);
  }

  /**
   * Force transition (for error handling)
   */
  forceTransition(to: TurnState, reason: string = "forced"): void {
    console.warn(`⚠️ Force transition: ${this._state} → ${to} (${reason})`);
    this._state = to;
    this._history.push({ 
      state: to, 
      timestamp: Date.now(), 
      reason: `FORCED: ${reason}` 
    });
  }

  /**
   * Reset turn to listening state (for barge-in recovery)
   */
  reset(): void {
    this.transit("LYSSNAR", "reset_after_interruption");
  }
}

/**
 * Session Manager - Manages multiple turns within a session
 */
export class SessionManager {
  private sessions = new Map<string, TurnController[]>();
  private sessionSettings = new Map<string, any>();

  /**
   * Create a new session
   */
  createSession(sessionId: string, settings?: any): void {
    this.sessions.set(sessionId, []);
    if (settings) {
      this.sessionSettings.set(sessionId, settings);
    }
  }

  /**
   * Start a new turn in a session
   */
  startTurn(sessionId: string, turnId: string): TurnController {
    if (!this.sessions.has(sessionId)) {
      this.createSession(sessionId);
    }

    const turn = new TurnController(turnId, sessionId);
    this.sessions.get(sessionId)!.push(turn);
    
    return turn;
  }

  /**
   * Get all turns for a session
   */
  getSessionTurns(sessionId: string): TurnController[] {
    return this.sessions.get(sessionId) || [];
  }

  /**
   * Get active turns (not complete)
   */
  getActiveTurns(sessionId: string): TurnController[] {
    return this.getSessionTurns(sessionId).filter(turn => !turn.isComplete());
  }

  /**
   * Clean up completed sessions
   */
  cleanupSessions(maxAge: number = 24 * 60 * 60 * 1000): void {
    const now = Date.now();
    
    for (const [sessionId, turns] of this.sessions.entries()) {
      const lastActivity = Math.max(...turns.map(t => t.duration));
      
      if (now - lastActivity > maxAge) {
        this.sessions.delete(sessionId);
        this.sessionSettings.delete(sessionId);
        console.log(`🧹 Cleaned up old session: ${sessionId}`);
      }
    }
  }

  /**
   * Get session statistics
   */
  getStats(): {
    totalSessions: number;
    totalTurns: number;
    activeTurns: number;
  } {
    let totalTurns = 0;
    let activeTurns = 0;

    for (const turns of this.sessions.values()) {
      totalTurns += turns.length;
      activeTurns += turns.filter(t => !t.isComplete()).length;
    }

    return {
      totalSessions: this.sessions.size,
      totalTurns,
      activeTurns
    };
  }
}

// Export singleton session manager
export const sessionManager = new SessionManager();
export default sessionManager;
