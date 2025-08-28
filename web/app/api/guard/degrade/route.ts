import { NextResponse } from "next/server";

// Global state för concurrency management
let maxConcurrent = 2;
let degradeCount = 0;

export function GET() {
  return NextResponse.json({ 
    maxConcurrent,
    degradeCount,
    timestamp: new Date().toISOString()
  });
}

export async function POST() {
  // Minska samtidighet med 1, men aldrig under 1
  maxConcurrent = Math.max(1, maxConcurrent - 1);
  degradeCount++;
  
  console.log(`[GUARDIAN] Degrade triggered: concurrency ${maxConcurrent + 1} → ${maxConcurrent}`);
  
  return NextResponse.json({ 
    ok: true, 
    maxConcurrent,
    degradeCount,
    message: "Concurrency degraded by Guardian",
    timestamp: new Date().toISOString()
  });
}