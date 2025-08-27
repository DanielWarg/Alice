/**
 * Rate Limiting Middleware for Alice APIs
 * Protects against abuse and ensures fair usage
 */

interface RateLimit {
  count: number;
  resetTime: number;
}

interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  keyGenerator?: (request: Request) => string;
}

class RateLimiter {
  private store = new Map<string, RateLimit>();
  private configs: Map<string, RateLimitConfig> = new Map();

  constructor() {
    // Default configurations per endpoint
    this.configs.set('/api/agent', {
      windowMs: 60 * 1000, // 1 minute
      maxRequests: 60 // 1 req/second
    });

    this.configs.set('/api/tools', {
      windowMs: 60 * 1000, // 1 minute  
      maxRequests: 120 // 2 req/second
    });

    this.configs.set('/api/health', {
      windowMs: 10 * 1000, // 10 seconds
      maxRequests: 30 // 3 req/second
    });

    // Cleanup old entries every 5 minutes
    setInterval(() => this.cleanup(), 5 * 60 * 1000);
  }

  async isAllowed(request: Request, endpoint: string): Promise<{
    allowed: boolean;
    limit: number;
    remaining: number;
    resetTime: number;
  }> {
    const config = this.configs.get(endpoint);
    if (!config) {
      // No rate limit configured, allow
      return {
        allowed: true,
        limit: Infinity,
        remaining: Infinity,
        resetTime: 0
      };
    }

    const key = this.getKey(request, endpoint, config);
    const now = Date.now();
    const currentLimit = this.store.get(key);

    if (!currentLimit || now >= currentLimit.resetTime) {
      // First request or window expired
      this.store.set(key, {
        count: 1,
        resetTime: now + config.windowMs
      });

      return {
        allowed: true,
        limit: config.maxRequests,
        remaining: config.maxRequests - 1,
        resetTime: now + config.windowMs
      };
    }

    if (currentLimit.count >= config.maxRequests) {
      // Rate limit exceeded
      return {
        allowed: false,
        limit: config.maxRequests,
        remaining: 0,
        resetTime: currentLimit.resetTime
      };
    }

    // Increment counter
    currentLimit.count++;
    
    return {
      allowed: true,
      limit: config.maxRequests,
      remaining: config.maxRequests - currentLimit.count,
      resetTime: currentLimit.resetTime
    };
  }

  private getKey(request: Request, endpoint: string, config: RateLimitConfig): string {
    if (config.keyGenerator) {
      return config.keyGenerator(request);
    }

    // Default: IP-based rate limiting
    const url = new URL(request.url);
    const ip = request.headers.get('x-forwarded-for') || 
               request.headers.get('x-real-ip') || 
               'unknown';
    
    return `${endpoint}:${ip}`;
  }

  private cleanup(): void {
    const now = Date.now();
    for (const [key, limit] of this.store.entries()) {
      if (now >= limit.resetTime) {
        this.store.delete(key);
      }
    }
  }

  // Configuration methods
  setConfig(endpoint: string, config: RateLimitConfig): void {
    this.configs.set(endpoint, config);
  }

  getStatus(): { totalKeys: number; endpoints: string[] } {
    return {
      totalKeys: this.store.size,
      endpoints: Array.from(this.configs.keys())
    };
  }
}

// Global rate limiter instance
export const rateLimiter = new RateLimiter();

/**
 * Rate limiting middleware function
 */
export async function withRateLimit(
  request: Request,
  endpoint: string,
  handler: () => Promise<Response>
): Promise<Response> {
  const result = await rateLimiter.isAllowed(request, endpoint);

  if (!result.allowed) {
    return new Response(JSON.stringify({
      error: {
        code: 'RATE_LIMIT_EXCEEDED',
        message: 'Too many requests. Please try again later.',
        retry_after_ms: result.resetTime - Date.now()
      }
    }), {
      status: 429,
      headers: {
        'Content-Type': 'application/json',
        'X-RateLimit-Limit': result.limit.toString(),
        'X-RateLimit-Remaining': result.remaining.toString(),
        'X-RateLimit-Reset': result.resetTime.toString(),
        'Retry-After': Math.ceil((result.resetTime - Date.now()) / 1000).toString()
      }
    });
  }

  // Add rate limit headers to successful responses
  const response = await handler();
  
  // Clone response to add headers
  const newResponse = new Response(response.body, response);
  newResponse.headers.set('X-RateLimit-Limit', result.limit.toString());
  newResponse.headers.set('X-RateLimit-Remaining', result.remaining.toString());
  newResponse.headers.set('X-RateLimit-Reset', result.resetTime.toString());

  return newResponse;
}