/**
 * Alice Orchestrator - Main Public API
 * 
 * This is the central coordination system for Alice's voice pipeline.
 * Manages state machines, event routing, and tool execution.
 */

import { EventEmitter } from "events";
import { TurnController } from "./stateMachine";
import { bus, on, emit } from "./eventBus";
import { decideRoute } from "./router";
import { toSafeSummary, enforceNoCloud } from "./privacy";
import { logNDJSON } from "./metrics";
import { TurnState, TurnMetrics, ToolCall } from "./types";

export class Orchestrator {
  private sessions = new Map<string, TurnController>();
  private metrics = new Map<string, TurnMetrics>();

  constructor() {
    this.setupEventHandlers();
  }

  /**
   * Start a new conversation turn
   */
  async startTurn(sessionId: string, turnId: string): Promise<void> {
    const controller = new TurnController(turnId, sessionId);
    this.sessions.set(turnId, controller);
    
    controller.transit("LYSSNAR");
    emit("turn_started", { sessionId, turnId, state: "LYSSNAR" });
    
    logNDJSON({
      event: "turn_started",
      timestamp: Date.now(),
      sessionId,
      turnId,
      state: "LYSSNAR"
    });
  }

  /**
   * Process incoming audio/text and route appropriately
   */
  async processInput(turnId: string, input: string | Buffer): Promise<void> {
    const controller = this.sessions.get(turnId);
    if (!controller) {
      throw new Error(`Turn ${turnId} not found`);
    }

    controller.transit("TOLKAR");
    
    // Route decision logic
    const route = decideRoute({
      text: typeof input === "string" ? input : "[audio]",
      hasPII: false, // TODO: Implement PII detection
      needsTools: false, // TODO: Implement intent detection
      estTokens: 0, // TODO: Implement token estimation
      cloudEnabled: false, // TODO: Read from config
      cloudDegraded: false // TODO: Implement health check
    });

    // Execute route
    switch (route) {
      case "local_fast":
        await this.executeLocalFast(turnId, input);
        break;
      case "local_reason":
        await this.executeLocalReason(turnId, input);
        break;
      case "cloud_complex":
        await this.executeCloudComplex(turnId, input);
        break;
    }
  }

  /**
   * Execute fast local response (no tools needed)
   */
  private async executeLocalFast(turnId: string, input: any): Promise<void> {
    const controller = this.sessions.get(turnId);
    if (!controller) return;

    controller.transit("TAL");
    
    // TODO: Implement local LLM + TTS
    const response = "Hej! Jag förstod vad du sa.";
    
    controller.transit("KLAR");
    emit("turn_completed", { turnId, response });
  }

  /**
   * Execute local reasoning with tools
   */
  private async executeLocalReason(turnId: string, input: any): Promise<void> {
    const controller = this.sessions.get(turnId);
    if (!controller) return;

    controller.transit("PLANNER");
    // TODO: Implement intent detection and tool planning
    
    controller.transit("KÖR_VERKTYG");
    // TODO: Implement tool execution
    
    controller.transit("PRIVACY");
    // TODO: Implement safe summary generation
    
    controller.transit("TAL");
    // TODO: Implement TTS with safe summary
    
    controller.transit("KLAR");
  }

  /**
   * Execute complex cloud reasoning
   */
  private async executeCloudComplex(turnId: string, input: any): Promise<void> {
    const controller = this.sessions.get(turnId);
    if (!controller) return;

    // TODO: Implement cloud API integration
    controller.transit("KLAR");
  }

  /**
   * Handle barge-in (interruption)
   */
  async handleBargeIn(turnId: string): Promise<void> {
    const controller = this.sessions.get(turnId);
    if (!controller) return;

    controller.transit("AVBRUTEN");
    
    // TODO: Cancel ongoing LLM/TTS/tool execution
    emit("turn_interrupted", { turnId });
    
    logNDJSON({
      event: "barge_in",
      timestamp: Date.now(),
      turnId,
      barge_in_cut_ms: 0 // TODO: Measure actual cut time
    });
  }

  /**
   * Get current system status
   */
  getStatus(): { sessions: number; activeTurns: number } {
    const activeTurns = Array.from(this.sessions.values())
      .filter(c => c.state !== "KLAR" && c.state !== "AVBRUTEN")
      .length;

    return {
      sessions: this.sessions.size,
      activeTurns
    };
  }

  private setupEventHandlers(): void {
    on("turn_started", (data) => {
      console.log("🎯 Turn started:", data);
    });

    on("turn_completed", (data) => {
      console.log("✅ Turn completed:", data);
    });

    on("turn_interrupted", (data) => {
      console.log("⏹️ Turn interrupted:", data);
    });
  }
}

// Export singleton instance
export const orchestrator = new Orchestrator();
export default orchestrator;
