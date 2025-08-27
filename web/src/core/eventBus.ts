/**
 * FAS 2 - Central Event Bus for Alice System
 * All system events flow through this bus and are logged
 */

import { EventEmitter } from "events";
import { logNDJSON } from "./metrics";
import type { EventEnvelope, EventType } from "../types/events";

export const bus = new EventEmitter();

export function emit<T = any>(type: EventType, payload: T) {
  const ev: EventEnvelope<T> = { 
    type, 
    ts: Date.now(), 
    payload 
  };
  
  // Emit to listeners
  bus.emit(type, ev);
  
  // Log to NDJSON for metrics
  logNDJSON(ev);
  
  // Optional: console log in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[EventBus] ${type}:`, payload);
  }
}

export function on<T = any>(type: EventType, handler: (ev: EventEnvelope<T>) => void) {
  bus.on(type, handler);
}

export function off<T = any>(type: EventType, handler: (ev: EventEnvelope<T>) => void) {
  bus.off(type, handler);
}