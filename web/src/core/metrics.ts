/**
 * FAS 2 - NDJSON Metrics Logging
 * Logs all events to structured log files for analysis
 */

import fs from "fs";
import path from "path";

const dir = path.join(process.cwd(), "logs");

// Ensure logs directory exists
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

const file = path.join(dir, "metrics.ndjson");

export function logNDJSON(obj: any) {
  try {
    const line = JSON.stringify({
      ...obj,
      timestamp: new Date().toISOString(),
      pid: process.pid
    });
    
    fs.appendFileSync(file, line + "\n", "utf8");
  } catch (e) {
    // Swallow logging errors to prevent cascading failures
    if (process.env.NODE_ENV === 'development') {
      console.error('[Metrics] Failed to log:', e);
    }
  }
}

// Helper function to get recent metrics
export function getRecentMetrics(limit: number = 1000): any[] {
  try {
    if (!fs.existsSync(file)) return [];
    
    const content = fs.readFileSync(file, "utf8");
    const lines = content.trim().split("\n").slice(-limit);
    
    return lines.map(line => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    }).filter(Boolean);
  } catch (e) {
    return [];
  }
}