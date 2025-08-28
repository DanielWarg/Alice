/**
 * Timer Tool - Start a timer with specified duration
 */
import { NextRequest, NextResponse } from 'next/server';

interface TimerRequest {
  minutes: number;
  seconds?: number;
  label?: string;
  start_at?: string;
  notify?: {
    speak?: boolean;
    screen?: boolean;
  };
}

interface TimerResponse {
  ok: boolean;
  id?: string;
  eta_sec?: number;
  expires_at?: string;
  error?: {
    code: string;
    message: string;
  };
}

// Simple in-memory timer store (in production, use Redis or database)
const activeTimers = new Map<string, {
  id: string;
  expires_at: Date;
  label?: string;
  notify: { speak: boolean; screen: boolean };
}>();

export async function POST(request: NextRequest) {
  try {
    const body: TimerRequest = await request.json();
    
    // Validate input
    if (typeof body.minutes !== 'number' || body.minutes < 0 || body.minutes > 24 * 60) {
      return NextResponse.json<TimerResponse>({
        ok: false,
        error: {
          code: 'BAD_REQUEST',
          message: 'minutes måste vara mellan 0 och 1440 (24 timmar)'
        }
      }, { status: 400 });
    }

    const seconds = body.seconds || 0;
    if (seconds < 0 || seconds > 59) {
      return NextResponse.json<TimerResponse>({
        ok: false,
        error: {
          code: 'BAD_REQUEST',
          message: 'seconds måste vara mellan 0 och 59'
        }
      }, { status: 400 });
    }

    // Calculate total duration
    const totalSeconds = (body.minutes * 60) + seconds;
    
    if (totalSeconds === 0) {
      return NextResponse.json<TimerResponse>({
        ok: false,
        error: {
          code: 'BAD_REQUEST',
          message: 'Timer måste vara minst 1 sekund'
        }
      }, { status: 400 });
    }

    // Create timer
    const timerId = `tmr_${Math.random().toString(36).substring(2, 9)}`;
    const startTime = body.start_at ? new Date(body.start_at) : new Date();
    const expiresAt = new Date(startTime.getTime() + totalSeconds * 1000);
    
    // Validate start time
    if (body.start_at && isNaN(startTime.getTime())) {
      return NextResponse.json<TimerResponse>({
        ok: false,
        error: {
          code: 'BAD_REQUEST',
          message: 'start_at måste vara giltig ISO8601 tidsstämpel'
        }
      }, { status: 400 });
    }

    // Store timer
    activeTimers.set(timerId, {
      id: timerId,
      expires_at: expiresAt,
      label: body.label,
      notify: {
        speak: body.notify?.speak !== false,
        screen: body.notify?.screen !== false
      }
    });

    // Set actual timer (for demonstration - in production, use job queue)
    setTimeout(() => {
      const timer = activeTimers.get(timerId);
      if (timer) {
        console.log(`⏰ Timer ${timerId} expired: "${timer.label || 'Timer'}"`);
        activeTimers.delete(timerId);
        
        // In production, this would trigger notifications
        if (timer.notify.speak) {
          console.log(`🔊 Would speak: "${timer.label || 'Timer'} är klar"`);
        }
        if (timer.notify.screen) {
          console.log(`📱 Would show notification: "${timer.label || 'Timer'} är klar"`);
        }
      }
    }, totalSeconds * 1000);

    const response: TimerResponse = {
      ok: true,
      id: timerId,
      eta_sec: totalSeconds,
      expires_at: expiresAt.toISOString()
    };

    console.log(`⏰ Timer created: ${timerId} for ${body.minutes}m${seconds > 0 ? `${seconds}s` : ''} ${body.label ? `"${body.label}"` : ''}`);
    
    return NextResponse.json(response);

  } catch (error) {
    console.error('Timer tool error:', error);
    
    return NextResponse.json<TimerResponse>({
      ok: false,
      error: {
        code: 'INTERNAL',
        message: 'Ett tekniskt fel uppstod med timern'
      }
    }, { status: 500 });
  }
}

// Get active timers (for debugging)
export async function GET() {
  const now = new Date();
  const active = Array.from(activeTimers.values())
    .filter(timer => timer.expires_at > now)
    .map(timer => ({
      id: timer.id,
      expires_at: timer.expires_at.toISOString(),
      label: timer.label,
      remaining_sec: Math.ceil((timer.expires_at.getTime() - now.getTime()) / 1000)
    }));

  return NextResponse.json({
    active_timers: active,
    count: active.length
  });
}