/**
 * Response Cache for Performance Optimization
 * Caches OpenAI responses to reduce latency for similar queries
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

class ResponseCache<T> {
  private cache = new Map<string, CacheEntry<T>>();
  
  constructor(private defaultTtl: number = 5 * 60 * 1000) { // 5 minutes default
    // Clean up expired entries every minute
    setInterval(() => this.cleanup(), 60 * 1000);
  }
  
  set(key: string, data: T, ttl?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTtl
    });
  }
  
  get(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }
    
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.data;
  }
  
  has(key: string): boolean {
    return this.get(key) !== null;
  }
  
  delete(key: string): void {
    this.cache.delete(key);
  }
  
  clear(): void {
    this.cache.clear();
  }
  
  private cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key);
      }
    }
  }
  
  getStats() {
    return {
      size: this.cache.size,
      entries: Array.from(this.cache.keys())
    };
  }
}

// Create cache instances for different types
export const agentResponseCache = new ResponseCache(2 * 60 * 1000); // 2 min for agent responses
export const toolResultCache = new ResponseCache(10 * 60 * 1000); // 10 min for tool results

/**
 * Generate cache key for agent requests
 */
export function generateAgentCacheKey(messages: any[], allowTools: boolean): string {
  // Only cache simple queries without tools for now
  if (allowTools || messages.length > 3) {
    return '';
  }
  
  const lastMessage = messages[messages.length - 1];
  if (!lastMessage || lastMessage.role !== 'user') {
    return '';
  }
  
  // Create hash of the content
  const content = lastMessage.content?.toLowerCase().trim();
  if (!content || content.length > 100) {
    return '';
  }
  
  return `agent:${content}`;
}

/**
 * Generate cache key for tool results
 */
export function generateToolCacheKey(toolName: string, params: any): string {
  // Cache weather and timer results
  if (toolName === 'weather.get') {
    const location = params.location?.toLowerCase().trim();
    const units = params.units || 'metric';
    return `tool:weather:${location}:${units}`;
  }
  
  if (toolName === 'timer.set') {
    // Don't cache timer results - they're always unique
    return '';
  }
  
  return '';
}