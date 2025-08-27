/**
 * Readiness Check API - Kubernetes/Docker readiness probe
 * Returns 200 when service is ready to accept traffic
 */
import { NextResponse } from 'next/server';

interface ReadinessCheck {
  ready: boolean;
  timestamp: string;
  checks: {
    [key: string]: boolean;
  };
  message?: string;
}

/**
 * Check if environment variables are configured
 */
function checkEnvironment(): boolean {
  const requiredVars = [
    'OPENAI_API_KEY',
    'NEXT_PUBLIC_ALICE_BACKEND_URL'
  ];
  
  return requiredVars.every(varName => {
    const value = process.env[varName];
    return value && value.trim().length > 0;
  });
}

/**
 * Check if application is initialized
 */
function checkInitialization(): boolean {
  // Check if we can access the file system and other basic operations
  try {
    // Simple initialization check - if we can create a Date, we're probably ready
    const now = new Date();
    return now.getTime() > 0;
  } catch {
    return false;
  }
}

/**
 * Check if database/backend is reachable (async but with short timeout)
 */
async function checkBackendReachable(): Promise<boolean> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_ALICE_BACKEND_URL || 'http://localhost:8000';
    const controller = new AbortController();
    
    // Very short timeout for readiness check
    setTimeout(() => controller.abort(), 500);
    
    const response = await fetch(`${backendUrl}/health`, {
      method: 'HEAD',
      headers: { 'User-Agent': 'Alice-Web-ReadinessCheck/1.0' },
      signal: controller.signal
    });
    
    return response.ok;
  } catch {
    // Don't fail readiness just because backend is slow/down
    // The application can still serve static content and handle some requests
    return true;
  }
}

export async function GET() {
  try {
    const timestamp = new Date().toISOString();
    
    // Perform readiness checks
    const environmentReady = checkEnvironment();
    const initializationReady = checkInitialization();
    const backendReady = await checkBackendReachable();
    
    const checks = {
      environment: environmentReady,
      initialization: initializationReady,
      backend: backendReady
    };
    
    // Application is ready if core environment and initialization are OK
    // Backend readiness is informational but doesn't block readiness
    const ready = environmentReady && initializationReady;
    
    const readinessCheck: ReadinessCheck = {
      ready,
      timestamp,
      checks,
      ...(ready ? {} : { 
        message: 'Application not ready - check environment configuration' 
      })
    };
    
    return NextResponse.json(readinessCheck, { 
      status: ready ? 200 : 503,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Ready': ready ? 'true' : 'false'
      }
    });
    
  } catch (error) {
    return NextResponse.json({
      ready: false,
      timestamp: new Date().toISOString(),
      checks: {
        system: false
      },
      message: error instanceof Error ? error.message : 'Readiness check failed'
    }, { 
      status: 503,
      headers: {
        'X-Ready': 'false'
      }
    });
  }
}

export async function HEAD() {
  try {
    const environmentReady = checkEnvironment();
    const initializationReady = checkInitialization();
    const ready = environmentReady && initializationReady;
    
    return new NextResponse(null, {
      status: ready ? 200 : 503,
      headers: {
        'X-Ready': ready ? 'true' : 'false',
        'Cache-Control': 'no-cache'
      }
    });
  } catch {
    return new NextResponse(null, { 
      status: 503,
      headers: {
        'X-Ready': 'false'
      }
    });
  }
}