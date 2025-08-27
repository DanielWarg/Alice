/**
 * Alice Voice Router
 * Intelligent routing between local_fast, local_reason, and cloud_complex paths
 */

export type VoiceRoute = 'local_fast' | 'local_reason' | 'cloud_complex';

interface RouterConfig {
  allow_cloud: boolean;
  cloud_ttfa_degrade_ms: number;
  local_reason_threshold_tokens: number;
  pii_detection_enabled: boolean;
}

const DEFAULT_ROUTER_CONFIG: RouterConfig = {
  allow_cloud: false,
  cloud_ttfa_degrade_ms: 600,
  local_reason_threshold_tokens: 60,
  pii_detection_enabled: true
};

interface RouteDecision {
  route: VoiceRoute;
  reason: string;
  confidence: number;
  estimated_tokens: number;
}

interface SessionState {
  sessionId: string;
  cloudFailures: number;
  lastCloudFailure: number;
  cloudLockUntil: number;
}

export class VoiceRouter {
  private config: RouterConfig;
  private sessionStates: Map<string, SessionState> = new Map();
  
  // PII detection patterns (basic implementation)
  private piiPatterns = [
    /\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b/, // Credit card
    /\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b/, // Email
    /\\b\\d{3}[\\s-]?\\d{2}[\\s-]?\\d{4}\\b/, // SSN pattern
    /\\b(?:\\+46|0)[\\s-]?7[\\s-]?\\d{8}\\b/, // Swedish phone number
    /\\b\\d{6}[\\s-]?\\d{4}\\b/, // Swedish personal number
  ];

  // Tool-requiring keywords
  private toolKeywords = [
    'email', 'mejl', 'skicka', 'send',
    'calendar', 'kalender', 'möte', 'meeting',
    'file', 'fil', 'dokument', 'document',
    'spotify', 'musik', 'music', 'spela',
    'home', 'hem', 'ljus', 'light'
  ];

  constructor(config: Partial<RouterConfig> = {}) {
    this.config = { ...DEFAULT_ROUTER_CONFIG, ...config };
  }

  public determineRoute(text: string, sessionId: string): VoiceRoute {
    const decision = this.analyzeInput(text, sessionId);
    
    console.log(`🧭 Route decision for "${text.substring(0, 50)}...": ${decision.route} (${decision.reason})`);
    
    return decision.route;
  }

  private analyzeInput(text: string, sessionId: string): RouteDecision {
    const session = this.getOrCreateSession(sessionId);
    const now = Date.now();

    // Check if cloud is locked due to previous failures
    if (now < session.cloudLockUntil) {
      return {
        route: 'local_fast',
        reason: `Cloud locked until ${new Date(session.cloudLockUntil).toISOString()}`,
        confidence: 1.0,
        estimated_tokens: this.estimateTokens(text)
      };
    }

    // Check for PII if enabled
    if (this.config.pii_detection_enabled && this.containsPII(text)) {
      return {
        route: 'local_fast', // Never send PII to cloud
        reason: 'PII detected - local processing required',
        confidence: 1.0,
        estimated_tokens: this.estimateTokens(text)
      };
    }

    // Check if tools are needed
    if (this.requiresTools(text)) {
      const estimatedTokens = this.estimateTokens(text);
      
      if (estimatedTokens > this.config.local_reason_threshold_tokens && this.config.allow_cloud) {
        return {
          route: 'cloud_complex',
          reason: 'Tools + long response - needs cloud reasoning',
          confidence: 0.8,
          estimated_tokens
        };
      } else {
        return {
          route: 'local_reason',
          reason: 'Tools required - using local reasoning',
          confidence: 0.9,
          estimated_tokens
        };
      }
    }

    // Estimate response complexity
    const estimatedTokens = this.estimateTokens(text);
    const complexity = this.assessComplexity(text);

    // Route based on estimated response length and complexity
    if (estimatedTokens <= 40 && complexity < 0.5) {
      return {
        route: 'local_fast',
        reason: 'Short, simple response - local fast path',
        confidence: 0.9,
        estimated_tokens
      };
    }

    if (estimatedTokens > this.config.local_reason_threshold_tokens && this.config.allow_cloud) {
      return {
        route: 'cloud_complex',
        reason: 'Long/complex response - cloud reasoning preferred',
        confidence: 0.7,
        estimated_tokens
      };
    }

    // Default to local_fast
    return {
      route: 'local_fast',
      reason: 'Default local processing',
      confidence: 0.6,
      estimated_tokens
    };
  }

  private containsPII(text: string): boolean {
    for (const pattern of this.piiPatterns) {
      if (pattern.test(text)) {
        return true;
      }
    }
    
    // Additional heuristics for PII detection
    if (this.containsPersonalNames(text) || this.containsAddresses(text)) {
      return true;
    }
    
    return false;
  }

  private containsPersonalNames(text: string): boolean {
    // Look for patterns like "My name is..." or "I'm called..."
    const namePatterns = [
      /\\b(?:my name is|i'm called|jag heter|mitt namn är)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)/i,
      /\\b(?:contact|ring|call|kontakta)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)/i
    ];
    
    return namePatterns.some(pattern => pattern.test(text));
  }

  private containsAddresses(text: string): boolean {
    // Basic address pattern detection
    const addressPatterns = [
      /\\b\\d+\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\s+(?:Street|St|Avenue|Ave|Road|Rd|gata|väg)/i,
      /\\b\\d{3}\\s?\\d{2}\\b/, // Swedish postal code
    ];
    
    return addressPatterns.some(pattern => pattern.test(text));
  }

  private requiresTools(text: string): boolean {
    const lowerText = text.toLowerCase();
    
    return this.toolKeywords.some(keyword => {
      return lowerText.includes(keyword);
    });
  }

  private estimateTokens(text: string): number {
    // Rough token estimation: ~4 characters per token for Swedish
    const baseTokens = Math.ceil(text.length / 4);
    
    // Adjust based on complexity
    const complexity = this.assessComplexity(text);
    const responseMultiplier = 1 + (complexity * 2); // Complex questions need longer answers
    
    return Math.ceil(baseTokens * responseMultiplier);
  }

  private assessComplexity(text: string): number {
    let complexity = 0.0;
    
    // Question complexity indicators
    const complexityIndicators = [
      { pattern: /\\b(?:why|varför|how|hur|explain|förklara)\\b/i, weight: 0.3 },
      { pattern: /\\b(?:analyze|analysera|compare|jämför|evaluate|utvärdera)\\b/i, weight: 0.4 },
      { pattern: /\\b(?:multiple|flera|various|olika|complex|komplex)\\b/i, weight: 0.2 },
      { pattern: /[?].*[?]/, weight: 0.2 }, // Multiple questions
      { pattern: /\\b(?:and|och|but|men|however|dock|therefore|därför)\\b/gi, weight: 0.1 } // Conjunctions
    ];
    
    for (const indicator of complexityIndicators) {
      const matches = text.match(indicator.pattern);
      if (matches) {
        complexity += indicator.weight * (matches.length / text.split(' ').length);
      }
    }
    
    // Length-based complexity
    const wordCount = text.split(/\\s+/).length;
    if (wordCount > 20) {
      complexity += 0.2;
    }
    
    return Math.min(complexity, 1.0);
  }

  public recordCloudFailure(sessionId: string, ttfa_ms: number): void {
    const session = this.getOrCreateSession(sessionId);
    
    if (ttfa_ms > this.config.cloud_ttfa_degrade_ms) {
      session.cloudFailures++;
      session.lastCloudFailure = Date.now();
      
      console.warn(`⚠️ Cloud TTFA failure: ${ttfa_ms}ms (${session.cloudFailures} failures)`);
      
      // Lock cloud for 5 minutes after 2 failures
      if (session.cloudFailures >= 2) {
        session.cloudLockUntil = Date.now() + (5 * 60 * 1000); // 5 minutes
        console.warn(`🔒 Cloud locked for session ${sessionId} until ${new Date(session.cloudLockUntil).toISOString()}`);
      }
    }
  }

  public recordCloudSuccess(sessionId: string): void {
    const session = this.getOrCreateSession(sessionId);
    
    // Reset failure count on successful fast response
    session.cloudFailures = Math.max(0, session.cloudFailures - 1);
    
    if (session.cloudFailures === 0) {
      session.cloudLockUntil = 0; // Unlock if no recent failures
    }
  }

  private getOrCreateSession(sessionId: string): SessionState {
    if (!this.sessionStates.has(sessionId)) {
      this.sessionStates.set(sessionId, {
        sessionId,
        cloudFailures: 0,
        lastCloudFailure: 0,
        cloudLockUntil: 0
      });
    }
    
    return this.sessionStates.get(sessionId)!;
  }

  public updateConfig(config: Partial<RouterConfig>): void {
    this.config = { ...this.config, ...config };
    console.log('🔧 Router config updated:', this.config);
  }

  public getSessionStats(sessionId: string): SessionState | null {
    return this.sessionStates.get(sessionId) || null;
  }

  public cleanup(sessionId?: string): void {
    if (sessionId) {
      this.sessionStates.delete(sessionId);
    } else {
      this.sessionStates.clear();
    }
  }
}