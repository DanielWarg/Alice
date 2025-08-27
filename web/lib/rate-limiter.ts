/**
 * Rate Limiter - Production-grade request throttling
 * Prevents abuse and ensures service stability
 */

import { FeatureFlag } from './feature-flags';

export interface RateLimitConfig {
  windowMs: number;        // Time window in milliseconds
  maxRequests: number;     // Max requests per window
  skipSuccessfulRequests?: boolean;  // Don't count successful requests
  skipFailedRequests?: boolean;      // Don't count failed requests
  keyGenerator?: (request: Request) => string;
  onLimitReached?: (key: string) => void;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetTime: number;
  totalHits: number;
  retryAfter?: number;
}

class InMemoryStore {
  private store: Map<string, { count: number; resetTime: number }> = new Map();
  
  get(key: string): { count: number; resetTime: number } | undefined {
    const entry = this.store.get(key);
    if (entry && Date.now() > entry.resetTime) {
      this.store.delete(key);
      return undefined;
    }
    return entry;
  }
  
  set(key: string, count: number, resetTime: number) {
    this.store.set(key, { count, resetTime });
  }
  
  increment(key: string, windowMs: number): { count: number; resetTime: number } {
    const now = Date.now();
    const existing = this.get(key);
    
    if (!existing) {
      const entry = { count: 1, resetTime: now + windowMs };
      this.set(key, 1, now + windowMs);
      return entry;
    }
    
    existing.count++;
    this.set(key, existing.count, existing.resetTime);
    return existing;
  }
  
  cleanup() {
    const now = Date.now();
    for (const [key, entry] of this.store) {
      if (now > entry.resetTime) {
        this.store.delete(key);
      }
    }
  }
}

export class RateLimiter {
  private store = new InMemoryStore();
  private cleanupInterval: NodeJS.Timeout | null = null;
  
  constructor() {
    // Cleanup expired entries every 5 minutes
    this.cleanupInterval = setInterval(() => {
      this.store.cleanup();
    }, 5 * 60 * 1000);
  }
  
  destroy() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }
  
  private getClientKey(request: Request, keyGenerator?: (request: Request) => string): string {
    if (keyGenerator) {
      return keyGenerator(request);
    }
    
    // Try to get real IP from headers (for reverse proxy setups)
    const url = new URL(request.url);
    const forwarded = request.headers.get('x-forwarded-for');
    const realIp = request.headers.get('x-real-ip');
    const remoteAddr = request.headers.get('x-remote-addr');
    
    const clientIp = forwarded?.split(',')[0]?.trim() || 
                    realIp || 
                    remoteAddr || 
                    'unknown';
    
    return `${clientIp}:${url.pathname}`;
  }
  
  async checkRateLimit(request: Request, config: RateLimitConfig): Promise<RateLimitResult> {
    // Skip rate limiting in development or when bypassed
    if (FeatureFlag.isDevelopment() && FeatureFlag.isBypassRateLimitsEnabled()) {
      return {
        allowed: true,
        remaining: config.maxRequests,
        resetTime: Date.now() + config.windowMs,
        totalHits: 0
      };
    }
    
    const key = this.getClientKey(request, config.keyGenerator);
    const entry = this.store.increment(key, config.windowMs);
    
    const allowed = entry.count <= config.maxRequests;
    const remaining = Math.max(0, config.maxRequests - entry.count);
    
    if (!allowed && config.onLimitReached) {
      config.onLimitReached(key);
    }
    
    const result: RateLimitResult = {
      allowed,
      remaining,
      resetTime: entry.resetTime,
      totalHits: entry.count
    };
    
    if (!allowed) {
      result.retryAfter = Math.ceil((entry.resetTime - Date.now()) / 1000);
    }
    
    return result;
  }
}

// Global rate limiter instance
const globalRateLimiter = new RateLimiter();

/**
 * Rate limit configurations for different endpoints
 */
export const RATE_LIMITS = {
  // Voice endpoints - more restrictive
  voice: {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 20,     // 20 requests per minute
  },
  
  // Agent endpoints - moderate restrictions
  agent: {
    windowMs: 60 * 1000, // 1 minute  
    maxRequests: 10,     // 10 requests per minute
  },
  
  // Tool endpoints - strict limits
  tools: {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 30,     // 30 tool calls per minute
  },
  
  // Health checks - very permissive
  health: {
    windowMs: 10 * 1000, // 10 seconds
    maxRequests: 100,    // 100 requests per 10 seconds
  },
  
  // Metrics - moderate restrictions
  metrics: {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 60,     // 60 requests per minute (1 per second)
  },
  
  // General API - default limits
  general: {
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 60,     // 60 requests per minute
  }
};

/**
 * Express-like middleware for Next.js API routes
 */
export async function withRateLimit<T>(
  request: Request,
  config: RateLimitConfig,
  handler: () => Promise<T>
): Promise<T> {
  const rateLimitResult = await globalRateLimiter.checkRateLimit(request, config);
  
  if (!rateLimitResult.allowed) {
    throw new RateLimitError(
      'Rate limit exceeded',
      rateLimitResult.retryAfter || 60,
      rateLimitResult
    );
  }
  
  return await handler();
}

/**
 * Rate limit error class
 */
export class RateLimitError extends Error {
  constructor(
    message: string,
    public retryAfter: number,
    public rateLimitInfo: RateLimitResult
  ) {
    super(message);
    this.name = 'RateLimitError';
  }
}

/**
 * Helper to create rate limit headers
 */
export function createRateLimitHeaders(result: RateLimitResult): Record<string, string> {
  return {
    'X-RateLimit-Limit': result.totalHits.toString(),
    'X-RateLimit-Remaining': result.remaining.toString(),
    'X-RateLimit-Reset': Math.ceil(result.resetTime / 1000).toString(),
    ...(result.retryAfter && { 'Retry-After': result.retryAfter.toString() })
  };
}

/**
 * Next.js API route wrapper with rate limiting
 */
export function rateLimited(config: RateLimitConfig) {
  return function <T>(
    handler: (request: Request) => Promise<Response>
  ) {
    return async (request: Request): Promise<Response> => {
      try {
        const rateLimitResult = await globalRateLimiter.checkRateLimit(request, config);
        
        if (!rateLimitResult.allowed) {
          return new Response(
            JSON.stringify({
              error: {
                code: 'RATE_LIMIT_EXCEEDED',
                message: 'Too many requests. Please try again later.',
                retry_after_seconds: rateLimitResult.retryAfter
              }
            }),
            {
              status: 429,
              headers: {
                'Content-Type': 'application/json',
                ...createRateLimitHeaders(rateLimitResult)
              }
            }
          );
        }
        
        // Call original handler
        const response = await handler(request);
        
        // Add rate limit headers to successful responses
        const headers = new Headers(response.headers);
        Object.entries(createRateLimitHeaders(rateLimitResult)).forEach(([key, value]) => {
          headers.set(key, value);
        });
        
        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers
        });
        
      } catch (error) {
        // Handle errors while preserving rate limit info
        if (error instanceof RateLimitError) {
          return new Response(
            JSON.stringify({
              error: {
                code: 'RATE_LIMIT_EXCEEDED',
                message: error.message,
                retry_after_seconds: error.retryAfter
              }
            }),
            {
              status: 429,
              headers: {
                'Content-Type': 'application/json',
                ...createRateLimitHeaders(error.rateLimitInfo)
              }
            }
          );
        }
        
        throw error;
      }
    };
  };
}

// Export the global instance for manual use
export { globalRateLimiter };