/**
 * Voice Metrics Reset API - Clear metrics buffer for testing
 */
import { NextResponse } from 'next/server';

// Import the metrics store (we'll need to modify the main route to export it)
// For now, we'll create a simple in-memory store

let metricsStore: any[] = [];

// This is a simplified approach - in production you'd want a shared store
export async function POST() {
  try {
    const previousCount = metricsStore.length;
    metricsStore.length = 0; // Clear the array
    
    return NextResponse.json({
      success: true,
      message: `Cleared ${previousCount} metrics from buffer`,
      timestamp: Date.now()
    });
    
  } catch (error) {
    console.error('Failed to reset metrics:', error);
    return NextResponse.json(
      { error: 'Failed to reset metrics' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    count: metricsStore.length,
    message: 'Use POST to reset metrics buffer'
  });
}