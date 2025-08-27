/**
 * FAS 2 - Event System Types
 * Defines all possible events in the Alice system
 */

export type EventType =
  | "asr_final" | "agent_response" | "tool_call" | "tool_result"
  | "brain_compose" | "tts_start" | "tts_end"
  | "vision_event" | "ha_state_changed";

export interface EventEnvelope<T = any> {
  type: EventType;
  ts: number;
  payload: T;
}