/**
 * Privacy Gate - Safe Summary and No-Cloud Guard
 * 
 * Implements privacy protection for Alice's orchestrator.
 * Filters PII, generates safe summaries, and enforces no-cloud policies.
 */

import { logNDJSON } from "./metrics";
import { PrivacyCheck, PIIPattern, PrivacyViolationError } from "./types";

// PII detection patterns
const PII_PATTERNS: PIIPattern[] = [
  // Email addresses
  {
    type: "email",
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: "[email]",
    riskLevel: "high"
  },
  
  // Swedish personal numbers (personnummer)
  {
    type: "personnummer",
    pattern: /\b\d{6}[-\s]?\d{4}\b/g,
    replacement: "[personnummer]",
    riskLevel: "high"
  },
  
  // Phone numbers (Swedish format)
  {
    type: "phone",
    pattern: /\b(\+46|0)[1-9]\d{1,8}\b/g,
    replacement: "[telefon]",
    riskLevel: "medium"
  },
  
  // Credit card numbers
  {
    type: "credit_card",
    pattern: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
    replacement: "[kortnummer]",
    riskLevel: "high"
  },
  
  // Swedish addresses
  {
    type: "address",
    pattern: /\b[A-ZÅÄÖa-zåäö]+\s+gatan\s+\d+[A-Z]?\b/g,
    replacement: "[adress]",
    riskLevel: "medium"
  },
  
  // Names (common Swedish names)
  {
    type: "name",
    pattern: /\b(Erik|Anna|Johan|Maria|Anders|Karin|Lars|Eva|Per|Birgitta|Mikael|Lena|Gustav|Sofia|Daniel|Kerstin|Andreas|Helena|Mats|Ingrid|Björn|Monika|Magnus|Anita|Jörgen|Susanne|Henrik|Katarina|Fredrik|Elisabeth|Peter|Christina|Niklas|Britt|Christian|Ulla|Marcus|Marie|Patrik|Annika|Martin|Karin|Jens|Camilla|Ola|Jenny|Robert|Malin|Jonas|Sara|Emil|Emma|David|Linda|Tobias|Johanna|Simon|Elin|Mattias|Anna|Anton|Sofia|Filip|Ida|Alexander|Eva|Viktor|Maria|Sebastian|Karin|Johan|Elin|Erik|Anna|Johan|Maria|Anders|Karin|Lars|Eva|Per|Birgitta|Mikael|Lena|Gustav|Sofia|Daniel|Kerstin|Andreas|Helena|Mats|Ingrid|Björn|Monika|Magnus|Anita|Jörgen|Susanne|Henrik|Katarina|Fredrik|Elisabeth|Peter|Christina|Niklas|Britt|Christian|Ulla|Marcus|Marie|Patrik|Annika|Martin|Karin|Jens|Camilla|Ola|Jenny|Robert|Malin|Jonas|Sara|Emil|Emma|David|Linda|Tobias|Johanna|Simon|Elin|Mattias|Anna|Anton|Sofia|Filip|Ida|Alexander|Eva|Viktor|Maria|Sebastian|Karin|Johan|Elin)\b/gi,
    replacement: "[namn]",
    riskLevel: "low"
  },
  
  // IP addresses
  {
    type: "ip_address",
    pattern: /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g,
    replacement: "[ip-adress]",
    riskLevel: "medium"
  },
  
  // URLs
  {
    type: "url",
    pattern: /\bhttps?:\/\/[^\s<>"{}|\\^`\[\]]+\b/g,
    replacement: "[url]",
    riskLevel: "low"
  }
];

// Configuration
const PRIVACY_CONFIG = {
  maxSummaryLength: 300,
  allowPartialPII: false,
  logPIIAttempts: true,
  strictMode: true
};

/**
 * Check input for PII and generate safe summary
 */
export function toSafeSummary(raw: any): string {
  if (!raw) return "";
  
  let input = String(raw);
  let hasPII = false;
  let piiTypes: string[] = [];
  
  // Check for PII patterns
  for (const pattern of PII_PATTERNS) {
    if (pattern.pattern.test(input)) {
      hasPII = true;
      piiTypes.push(pattern.type);
      
      // Replace PII with safe placeholders
      input = input.replace(pattern.pattern, pattern.replacement);
    }
  }
  
  // Additional safety checks
  if (containsSensitiveKeywords(input)) {
    hasPII = true;
    piiTypes.push("sensitive_keywords");
    input = sanitizeSensitiveKeywords(input);
  }
  
  // Truncate if too long
  if (input.length > PRIVACY_CONFIG.maxSummaryLength) {
    input = input.slice(0, PRIVACY_CONFIG.maxSummaryLength - 3) + "...";
  }
  
  // Log PII detection if enabled
  if (hasPII && PRIVACY_CONFIG.logPIIAttempts) {
    logNDJSON({
      event: "pii_detected",
      timestamp: Date.now(),
      piiTypes,
      originalLength: String(raw).length,
      safeLength: input.length
    });
  }
  
  return input;
}

/**
 * Check if input contains sensitive keywords
 */
function containsSensitiveKeywords(input: string): boolean {
  const sensitiveWords = [
    "lösenord", "password", "hemlig", "secret", "privat", "private",
    "konfidentiell", "confidential", "intern", "internal", "klassificerad",
    "classified", "top secret", "hemligstämplad", "sekretessbelagd"
  ];
  
  const lowerInput = input.toLowerCase();
  return sensitiveWords.some(word => lowerInput.includes(word));
}

/**
 * Sanitize sensitive keywords
 */
function sanitizeSensitiveKeywords(input: string): string {
  const sensitiveWords = [
    "lösenord", "password", "hemlig", "secret", "privat", "private",
    "konfidentiell", "confidential", "intern", "internal", "klassificerad",
    "classified", "top secret", "hemligstämplad", "sekretessbelagd"
  ];
  
  let sanitized = input;
  for (const word of sensitiveWords) {
    const regex = new RegExp(`\\b${word}\\b`, "gi");
    sanitized = sanitized.replace(regex, "[hemlig]");
  }
  
  return sanitized;
}

/**
 * Comprehensive privacy check
 */
export function performPrivacyCheck(input: any): PrivacyCheck {
  const originalInput = String(input);
  const safeSummary = toSafeSummary(input);
  
  const hasPII = safeSummary !== originalInput;
  const piiTypes = hasPII ? detectPIITypes(originalInput) : [];
  
  // Determine risk level
  let riskLevel: "low" | "medium" | "high" = "low";
  if (piiTypes.includes("credit_card") || piiTypes.includes("personnummer")) {
    riskLevel = "high";
  } else if (piiTypes.includes("email") || piiTypes.includes("phone")) {
    riskLevel = "medium";
  } else if (piiTypes.includes("name") || piiTypes.includes("address")) {
    riskLevel = "low";
  }
  
  const result: PrivacyCheck = {
    input: originalInput,
    hasPII,
    piiTypes,
    safeSummary,
    riskLevel
  };
  
  // Log privacy check
  logNDJSON({
    event: "privacy_check",
    timestamp: Date.now(),
    hasPII,
    piiTypes,
    riskLevel,
    originalLength: originalInput.length,
    safeLength: safeSummary.length
  });
  
  return result;
}

/**
 * Detect specific PII types in input
 */
function detectPIITypes(input: string): string[] {
  const detectedTypes: string[] = [];
  
  for (const pattern of PII_PATTERNS) {
    if (pattern.pattern.test(input)) {
      detectedTypes.push(pattern.type);
    }
  }
  
  if (containsSensitiveKeywords(input)) {
    detectedTypes.push("sensitive_keywords");
  }
  
  return detectedTypes;
}

/**
 * Enforce no-cloud policy
 */
export function enforceNoCloud(payload: { no_cloud?: boolean; egress?: "network" | "local" }): void {
  if (payload?.no_cloud && payload?.egress === "network") {
    const error = new PrivacyViolationError("no_cloud guard: blocked network egress");
    
    logNDJSON({
      event: "cloud_blocked",
      timestamp: Date.now(),
      reason: "no_cloud policy violation",
      payload: { ...payload }
    });
    
    throw error;
  }
}

/**
 * Check if content can be sent to cloud
 */
export function canSendToCloud(content: any, privacyLevel: "strict" | "normal" | "permissive" = "normal"): boolean {
  const privacyCheck = performPrivacyCheck(content);
  
  // Strict mode: no PII allowed
  if (privacyLevel === "strict" && privacyCheck.hasPII) {
    return false;
  }
  
  // Normal mode: low-risk PII allowed
  if (privacyLevel === "normal" && privacyCheck.riskLevel === "high") {
    return false;
  }
  
  // Permissive mode: all content allowed
  return true;
}

/**
 * Generate privacy report for monitoring
 */
export function generatePrivacyReport(): {
  totalChecks: number;
  piiDetections: number;
  blockedAttempts: number;
  riskLevels: Record<string, number>;
} {
  // This would typically read from a metrics database
  // For now, return mock data
  return {
    totalChecks: 0,
    piiDetections: 0,
    blockedAttempts: 0,
    riskLevels: {
      low: 0,
      medium: 0,
      high: 0
    }
  };
}

/**
 * Privacy policy validation
 */
export function validatePrivacyPolicy(policy: any): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Check required fields
  if (!policy.dataRetention) {
    errors.push("Missing data retention policy");
  }
  
  if (!policy.piiHandling) {
    errors.push("Missing PII handling policy");
  }
  
  if (!policy.cloudUsage) {
    errors.push("Missing cloud usage policy");
  }
  
  // Check policy consistency
  if (policy.strictMode && policy.allowCloud) {
    warnings.push("Strict mode with cloud access may cause conflicts");
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Privacy-aware content filtering
 */
export class PrivacyFilter {
  private blockedPatterns: RegExp[] = [];
  private allowedPatterns: RegExp[] = [];
  
  constructor(private strictMode: boolean = true) {}
  
  /**
   * Add blocked pattern
   */
  addBlockedPattern(pattern: RegExp): void {
    this.blockedPatterns.push(pattern);
  }
  
  /**
   * Add allowed pattern (overrides blocked patterns)
   */
  addAllowedPattern(pattern: RegExp): void {
    this.allowedPatterns.push(pattern);
  }
  
  /**
   * Check if content is allowed
   */
  isAllowed(content: string): boolean {
    // Check allowed patterns first
    for (const pattern of this.allowedPatterns) {
      if (pattern.test(content)) {
        return true;
      }
    }
    
    // Check blocked patterns
    for (const pattern of this.blockedPatterns) {
      if (pattern.test(content)) {
        return false;
      }
    }
    
    // Default behavior based on strict mode
    return !this.strictMode;
  }
  
  /**
   * Filter content based on patterns
   */
  filterContent(content: string): string {
    if (this.isAllowed(content)) {
      return content;
    }
    
    // Apply privacy filtering
    return toSafeSummary(content);
  }
}

// Export default privacy filter instance
export const defaultPrivacyFilter = new PrivacyFilter(true);
export default defaultPrivacyFilter;
