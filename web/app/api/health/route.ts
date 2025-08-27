/**
 * Health Check API - System Status and Readiness
 * Used for load balancer health checks and monitoring
 */
import { NextRequest, NextResponse } from 'next/server';
import { FeatureFlag } from '@/lib/feature-flags';

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  uptime_seconds: number;
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn';
      duration_ms?: number;
      message?: string;
      last_updated?: string;
    };
  };
  feature_flags?: Record<string, boolean>;
}

const startTime = Date.now();

/**
 * Test database connectivity
 */
async function checkDatabase(): Promise<{ status: 'pass' | 'fail', duration_ms: number, message?: string }> {
  const start = Date.now();
  
  try {
    // Test Alice backend connection (check if feature-flag enabled)
    const backendUrl = process.env.NEXT_PUBLIC_ALICE_BACKEND_URL || 'http://localhost:8000';
    const shouldCheckBackend = FeatureFlag.isDevelopment() || process.env.HEALTH_CHECK_BACKEND === 'true';
    
    if (!shouldCheckBackend) {
      return { status: 'pass', duration_ms: 0, message: 'Backend check disabled' };
    }
    
    const response = await fetch(`${backendUrl}/health`, {
      method: 'GET',
      headers: { 'User-Agent': 'Alice-Web-HealthCheck/1.0' },
      signal: AbortSignal.timeout(2000)
    });
    
    const duration = Date.now() - start;
    
    if (response.ok) {
      return { status: 'pass', duration_ms: duration };
    } else {
      return { 
        status: 'fail', 
        duration_ms: duration, 
        message: `Backend returned ${response.status}` 
      };
    }
  } catch (error) {
    const duration = Date.now() - start;
    return { 
      status: 'fail', 
      duration_ms: duration, 
      message: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}

/**
 * Test OpenAI API connectivity
 */
async function checkOpenAI(): Promise<{ status: 'pass' | 'fail', duration_ms: number, message?: string }> {
  const start = Date.now();
  
  if (!process.env.OPENAI_API_KEY) {
    return { 
      status: 'fail', 
      duration_ms: 0, 
      message: 'OPENAI_API_KEY not configured' 
    };
  }
  
  try {
    const response = await fetch('https://api.openai.com/v1/models', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
        'User-Agent': 'Alice-Web-HealthCheck/1.0'
      },
      signal: AbortSignal.timeout(3000)
    });
    
    const duration = Date.now() - start;
    
    if (response.ok) {
      return { status: 'pass', duration_ms: duration };
    } else if (response.status === 401) {
      return { 
        status: 'fail', 
        duration_ms: duration, 
        message: 'Invalid API key' 
      };
    } else {
      return { 
        status: 'fail', 
        duration_ms: duration, 
        message: `OpenAI API returned ${response.status}` 
      };
    }
  } catch (error) {
    const duration = Date.now() - start;
    return { 
      status: 'fail', 
      duration_ms: duration, 
      message: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}

/**
 * Check voice metrics API
 */
async function checkMetrics(): Promise<{ status: 'pass' | 'fail', duration_ms: number, message?: string }> {
  const start = Date.now();
  
  try {
    const response = await fetch('http://localhost:3001/api/metrics/voice', {
      method: 'HEAD',
      signal: AbortSignal.timeout(1000)
    });
    
    const duration = Date.now() - start;
    
    if (response.ok) {
      const metricsCount = response.headers.get('X-Metrics-Count');
      return { 
        status: 'pass', 
        duration_ms: duration,
        message: `${metricsCount || '0'} metrics stored`
      };
    } else {
      return { 
        status: 'fail', 
        duration_ms: duration, 
        message: `Metrics API returned ${response.status}` 
      };
    }
  } catch (error) {
    const duration = Date.now() - start;
    return { 
      status: 'fail', 
      duration_ms: duration, 
      message: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}

/**
 * Comprehensive health check
 */
async function performHealthCheck(): Promise<HealthStatus> {
  const timestamp = new Date().toISOString();
  const uptime_seconds = Math.floor((Date.now() - startTime) / 1000);
  
  // Run health checks in parallel
  const [dbCheck, openaiCheck, metricsCheck] = await Promise.all([
    checkDatabase(),
    checkOpenAI(),
    checkMetrics()
  ]);
  
  const checks = {
    database: dbCheck,
    openai: openaiCheck,
    metrics: metricsCheck,
    memory: {
      status: 'pass' as const,
      duration_ms: 0,
      message: `${Math.round(process.memoryUsage().heapUsed / 1024 / 1024)}MB used`
    }
  };
  
  // Determine overall status
  const failedChecks = Object.values(checks).filter(check => check.status === 'fail');
  const warnedChecks = Object.values(checks).filter(check => check.status === 'warn');
  
  let status: 'healthy' | 'degraded' | 'unhealthy';
  if (failedChecks.length > 0) {
    status = 'unhealthy';
  } else if (warnedChecks.length > 0) {
    status = 'degraded';
  } else {
    status = 'healthy';
  }
  
  return {
    status,
    timestamp,
    version: process.env.npm_package_version || '1.0.0',
    uptime_seconds,
    checks,
    ...(FeatureFlag.isDevelopment() && {
      feature_flags: FeatureFlag.getAllFlags()
    })
  };
}

/**
 * GET /api/health - Full health check
 */
export async function GET(request: NextRequest) {
  try {
    const healthStatus = await performHealthCheck();
    
    const statusCode = healthStatus.status === 'healthy' ? 200 : 
                      healthStatus.status === 'degraded' ? 200 : 503;
    
    return NextResponse.json(healthStatus, { 
      status: statusCode,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Health-Status': healthStatus.status,
        'X-Health-Timestamp': healthStatus.timestamp
      }
    });
    
  } catch (error) {
    console.error('Health check failed:', error);
    
    return NextResponse.json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: process.env.npm_package_version || '1.0.0',
      uptime_seconds: Math.floor((Date.now() - startTime) / 1000),
      checks: {
        system: {
          status: 'fail',
          message: error instanceof Error ? error.message : 'Unknown health check error'
        }
      }
    }, { 
      status: 503,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Health-Status': 'unhealthy'
      }
    });
  }
}

/**
 * HEAD /api/health - Lightweight health check for load balancers
 */
export async function HEAD(request: NextRequest) {
  try {
    // Quick checks only for HEAD requests
    const uptime_seconds = Math.floor((Date.now() - startTime) / 1000);
    const memoryUsage = process.memoryUsage().heapUsed / 1024 / 1024;
    
    // Simple readiness check
    const isReady = uptime_seconds > 5 && memoryUsage < 512; // Ready if up >5s and <512MB
    
    return new NextResponse(null, {
      status: isReady ? 200 : 503,
      headers: {
        'X-Health-Status': isReady ? 'healthy' : 'degraded',
        'X-Uptime-Seconds': uptime_seconds.toString(),
        'X-Memory-MB': Math.round(memoryUsage).toString(),
        'Cache-Control': 'no-cache'
      }
    });
  } catch (error) {
    return new NextResponse(null, { 
      status: 503,
      headers: {
        'X-Health-Status': 'unhealthy'
      }
    });
  }
}