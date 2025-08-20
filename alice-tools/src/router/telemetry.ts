import fs from 'node:fs';
import path from 'node:path';
import pino from 'pino';

const log = pino({ level: "info" });

export type RouterTelemetry = {
  timestamp: string;
  input: string;
  intent: string;
  matchedPhrase: string;
  isExactMatch: boolean;
  confidence: number;
  latencyMs: number;
  success: boolean;
  error?: string;
};

const telemetryPath = path.join(process.cwd(), 'data', 'router_telemetry.jsonl');

export function logRouterTelemetry(telemetry: RouterTelemetry) {
  try {
    // Ensure directory exists
    fs.mkdirSync(path.dirname(telemetryPath), { recursive: true });
    
    // Append telemetry as JSON line
    fs.appendFileSync(telemetryPath, JSON.stringify(telemetry) + '\n');
    
    // Also log to pino for real-time monitoring
    log.info({ type: 'router_telemetry', ...telemetry }, 'Router telemetry');
  } catch (err) {
    log.error({ err }, 'Failed to log router telemetry');
  }
}
