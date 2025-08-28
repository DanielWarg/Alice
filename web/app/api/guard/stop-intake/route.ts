import { NextResponse } from "next/server";

// Global state för intake blocking
export let INTAKE_BLOCKED = false;
let blockTimestamp: string | null = null;
let blockCount = 0;

export function GET() {
  return NextResponse.json({ 
    intakeBlocked: INTAKE_BLOCKED,
    blockTimestamp,
    blockCount,
    timestamp: new Date().toISOString()
  });
}

export async function POST() {
  INTAKE_BLOCKED = true;
  blockTimestamp = new Date().toISOString();
  blockCount++;
  
  console.log(`[GUARDIAN] Intake blocked by Guardian at ${blockTimestamp}`);
  
  return NextResponse.json({ 
    ok: true,
    intakeBlocked: INTAKE_BLOCKED,
    blockTimestamp,
    blockCount,
    message: "Request intake blocked by Guardian",
    timestamp: new Date().toISOString()
  });
}

// Reset endpoint (för recovery)
export async function DELETE() {
  INTAKE_BLOCKED = false;
  blockTimestamp = null;
  
  console.log(`[GUARDIAN] Intake unblocked - recovery mode`);
  
  return NextResponse.json({
    ok: true,
    intakeBlocked: INTAKE_BLOCKED,
    message: "Intake unblocked - system recovered",
    timestamp: new Date().toISOString()
  });
}