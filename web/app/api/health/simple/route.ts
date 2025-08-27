/**
 * Simple Health Check - Bara grundläggande system readiness
 * Används för integration tests
 */
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const timestamp = new Date().toISOString();
    
    // Basic system checks
    const memoryUsage = process.memoryUsage();
    const uptime = process.uptime();
    
    return NextResponse.json({
      ok: true,
      timestamp,
      uptime_seconds: Math.floor(uptime),
      memory_mb: Math.round(memoryUsage.heapUsed / 1024 / 1024),
      status: 'healthy'
    });
    
  } catch (error) {
    return NextResponse.json({
      ok: false,
      error: 'Health check failed',
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}