/**
 * Privacy Validator for Voice Pipeline Testing
 * Ensures no PII leakage in voice responses and routing
 */

import { VoiceMetrics } from '../../types/events';
import { SafeSummary } from '../../server/privacy/safe_summary';
import { TestLogger } from '../utils/test_logger';

interface PrivacyValidationConfig {
  strict_mode: boolean;
  check_transcriptions: boolean;
  check_responses: boolean;
  check_logs: boolean;
  allowed_pii_types: string[];
}

interface PIIViolation {
  type: string;
  content: string;
  location: 'transcription' | 'response' | 'log' | 'routing';
  severity: 'low' | 'medium' | 'high' | 'critical';
  context: string;
}

interface PrivacyValidationResult {
  passed: boolean;
  violations: PIIViolation[];
  warnings: string[];
  pii_score: number; // 0-100, higher is safer
  safe_summary_applied: boolean;
  route_appropriate: boolean;
}

export class PrivacyValidator {
  private config: PrivacyValidationConfig;
  private safeSummary: SafeSummary;
  private validationHistory: PrivacyValidationResult[] = [];
  private logger?: TestLogger;

  // Enhanced PII detection patterns
  private piiPatterns = {
    // Personal identifiers
    email: {
      pattern: /\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b/g,
      severity: 'high' as const
    },
    phone_swedish: {
      pattern: /\\b(?:\\+46|0)[\\s-]?7[\\s-]?\\d{8}\\b/g,
      severity: 'high' as const
    },
    phone_international: {
      pattern: /\\b(?:\\+\\d{1,3}[\\s-]?)?\\(?\\d{3}\\)?[\\s-]?\\d{3}[\\s-]?\\d{4}\\b/g,
      severity: 'high' as const
    },
    ssn_swedish: {
      pattern: /\\b\\d{6}[\\s-]?\\d{4}\\b/g,
      severity: 'critical' as const
    },
    
    // Financial information
    credit_card: {
      pattern: /\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b/g,
      severity: 'critical' as const
    },
    iban: {
      pattern: /\\b[A-Z]{2}\\d{2}[A-Z0-9]{4}\\d{7}([A-Z0-9]?){0,16}\\b/g,
      severity: 'critical' as const
    },
    bank_account: {
      pattern: /\\b\\d{4}[\\s-]?\\d{7}[\\s-]?\\d{1}\\b/g,
      severity: 'high' as const
    },
    
    // Location data
    address: {
      pattern: /\\b\\d+\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\s+(?:Street|St|Avenue|Ave|Road|Rd|gata|väg|Boulevard|Blvd)\\b/gi,
      severity: 'medium' as const
    },
    postal_code: {
      pattern: /\\b\\d{3}\\s?\\d{2}\\b/g,
      severity: 'medium' as const
    },
    coordinates: {
      pattern: /\\b[-+]?([1-8]?\\d(\\.\\d+)?|90(\\.0+)?)\\s*,\\s*[-+]?(180(\\.0+)?|((1[0-7]\\d)|([1-9]?\\d))(\\.\\d+)?)\\b/g,
      severity: 'high' as const
    },
    
    // Technical identifiers
    ip_address: {
      pattern: /\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b/g,
      severity: 'medium' as const
    },
    mac_address: {
      pattern: /\\b[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}\\b/g,
      severity: 'medium' as const
    },
    uuid: {
      pattern: /\\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\\b/g,
      severity: 'low' as const
    },
    
    // Names (Swedish context)
    explicit_names: {
      pattern: /\\b(?:my name is|i'm called|jag heter|mitt namn är|this is|det här är)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)/gi,
      severity: 'high' as const
    },
    contact_names: {
      pattern: /\\b(?:contact|ring|call|kontakta|email|mejla)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)/gi,
      severity: 'medium' as const
    }
  };

  constructor(config: Partial<PrivacyValidationConfig> = {}) {
    const defaultConfig: PrivacyValidationConfig = {
      strict_mode: true,
      check_transcriptions: true,
      check_responses: true,
      check_logs: true,
      allowed_pii_types: [] // No PII allowed by default
    };
    
    this.config = { ...defaultConfig, ...config };
    this.safeSummary = new SafeSummary({
      max_length: 300,
      remove_names: true,
      remove_addresses: true,
      remove_phone_numbers: true,
      remove_emails: true,
      remove_financial: true,
      preserve_context: true
    });
  }

  public setLogger(logger: TestLogger): void {
    this.logger = logger;
  }

  public validate(metrics: VoiceMetrics, additionalData: any = {}): PrivacyValidationResult {
    const result: PrivacyValidationResult = {
      passed: true,
      violations: [],
      warnings: [],
      pii_score: 100,
      safe_summary_applied: false,
      route_appropriate: true
    };

    // Check if Safe Summary was properly applied
    result.safe_summary_applied = this.checkSafeSummaryApplication(metrics, additionalData);
    
    // Validate transcription for PII
    if (this.config.check_transcriptions && additionalData.transcription) {
      const transcriptionViolations = this.scanForPII(additionalData.transcription, 'transcription');
      result.violations.push(...transcriptionViolations);
    }

    // Validate response for PII leakage
    if (this.config.check_responses && additionalData.response) {
      const responseViolations = this.scanForPII(additionalData.response, 'response');
      result.violations.push(...responseViolations);
    }

    // Validate routing decisions
    const routingValidation = this.validateRoutingDecision(metrics, additionalData);
    result.route_appropriate = routingValidation.appropriate;
    if (!routingValidation.appropriate) {
      result.violations.push({
        type: 'inappropriate_routing',
        content: routingValidation.reason,
        location: 'routing',
        severity: 'high',
        context: `Route: ${metrics.route}, Contains PII: ${routingValidation.containsPII}`
      });
    }

    // Validate log safety
    if (this.config.check_logs && additionalData.logs) {
      const logViolations = this.scanLogsForPII(additionalData.logs);
      result.violations.push(...logViolations);
    }

    // Calculate privacy score
    result.pii_score = this.calculatePrivacyScore(result.violations);

    // Determine overall pass/fail
    const criticalViolations = result.violations.filter(v => v.severity === 'critical');
    const highViolations = result.violations.filter(v => v.severity === 'high');
    
    if (this.config.strict_mode) {
      result.passed = result.violations.length === 0;
    } else {
      result.passed = criticalViolations.length === 0 && highViolations.length <= 1;
    }

    // Add warnings for medium/low violations in non-strict mode
    if (!this.config.strict_mode) {
      const mediumLowViolations = result.violations.filter(v => 
        v.severity === 'medium' || v.severity === 'low'
      );
      
      for (const violation of mediumLowViolations) {
        result.warnings.push(`${violation.severity.toUpperCase()}: ${violation.type} detected in ${violation.location}`);
      }
    }

    // Track privacy leak attempts in metrics and log violations
    if (result.violations.length > 0) {
      console.error(`🚨 Privacy violations detected in ${metrics.sessionId}:`, result.violations);
      
      // Log each violation with proper categorization
      if (this.logger) {
        for (const violation of result.violations) {
          this.logger.logPrivacyViolation(metrics.sessionId, violation);
        }
      }
    }

    // Store validation result
    this.validationHistory.push(result);

    // Log validation result
    if (this.logger) {
      this.logger.logValidationResult(metrics.sessionId, 'privacy', result);
    }

    return result;
  }

  private scanForPII(text: string, location: 'transcription' | 'response' | 'log' | 'routing'): PIIViolation[] {
    const violations: PIIViolation[] = [];
    
    for (const [type, { pattern, severity }] of Object.entries(this.piiPatterns)) {
      // Skip if this PII type is allowed
      if (this.config.allowed_pii_types.includes(type)) {
        continue;
      }
      
      const matches = text.match(pattern);
      if (matches) {
        for (const match of matches) {
          violations.push({
            type,
            content: match,
            location,
            severity,
            context: this.getViolationContext(text, match)
          });
        }
      }
    }

    return violations;
  }

  private scanLogsForPII(logs: string[]): PIIViolation[] {
    const violations: PIIViolation[] = [];
    
    for (const logEntry of logs) {
      const logViolations = this.scanForPII(logEntry, 'log');
      violations.push(...logViolations);
    }
    
    return violations;
  }

  private getViolationContext(text: string, match: string): string {
    const index = text.indexOf(match);
    const start = Math.max(0, index - 20);
    const end = Math.min(text.length, index + match.length + 20);
    
    return '...' + text.substring(start, end) + '...';
  }

  private checkSafeSummaryApplication(metrics: VoiceMetrics, additionalData: any): boolean {
    // Check if route that should use Safe Summary actually did
    const shouldUseSafeSummary = 
      metrics.route === 'cloud_complex' || 
      (additionalData.tool_used && additionalData.tool_used.length > 0);
      
    if (shouldUseSafeSummary) {
      // Check if response shows signs of Safe Summary filtering
      const response = additionalData.response || '';
      const hasSafeSummaryMarkers = 
        response.includes('[EMAIL]') ||
        response.includes('[PHONE]') ||
        response.includes('[PERSON]') ||
        response.includes('[ADDRESS]') ||
        response.length <= 300; // Safe Summary length limit
        
      return hasSafeSummaryMarkers || this.safeSummary.isSafe(response);
    }
    
    return true; // Not required for local_fast route
  }

  private validateRoutingDecision(metrics: VoiceMetrics, additionalData: any): { appropriate: boolean, reason: string, containsPII: boolean } {
    const transcription = additionalData.transcription || '';
    const containsPII = this.scanForPII(transcription, 'transcription').length > 0;
    
    // PII should NEVER go to cloud
    if (containsPII && metrics.route === 'cloud_complex') {
      return {
        appropriate: false,
        reason: 'PII detected but routed to cloud_complex',
        containsPII: true
      };
    }
    
    // PII should use local processing with Safe Summary
    if (containsPII && metrics.route !== 'local_fast' && metrics.route !== 'local_reason') {
      return {
        appropriate: false,
        reason: 'PII detected but not using local route',
        containsPII: true
      };
    }
    
    return {
      appropriate: true,
      reason: 'Routing decision appropriate for content',
      containsPII
    };
  }

  private calculatePrivacyScore(violations: PIIViolation[]): number {
    let score = 100;
    
    for (const violation of violations) {
      switch (violation.severity) {
        case 'critical':
          score -= 40; // Major penalty for critical PII
          break;
        case 'high':
          score -= 25;
          break;
        case 'medium':
          score -= 10;
          break;
        case 'low':
          score -= 5;
          break;
      }
    }
    
    return Math.max(0, score);
  }

  public validateBatch(metricsList: VoiceMetrics[], additionalDataList: any[] = []): BatchPrivacyResult {
    const results = metricsList.map((metrics, index) => 
      this.validate(metrics, additionalDataList[index] || {})
    );
    
    const passed = results.filter(r => r.passed).length;
    const totalViolations = results.reduce((sum, r) => sum + r.violations.length, 0);
    const avgPrivacyScore = results.reduce((sum, r) => sum + r.pii_score, 0) / results.length;
    
    // Categorize violations by severity
    const violationsBySeverity = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0
    };
    
    for (const result of results) {
      for (const violation of result.violations) {
        violationsBySeverity[violation.severity]++;
      }
    }
    
    return {
      overall_passed: passed === metricsList.length,
      privacy_success_rate: passed / metricsList.length,
      total_tested: metricsList.length,
      total_violations: totalViolations,
      violations_by_severity: violationsBySeverity,
      average_privacy_score: avgPrivacyScore,
      safe_summary_compliance: results.filter(r => r.safe_summary_applied).length / results.length,
      routing_compliance: results.filter(r => r.route_appropriate).length / results.length,
      individual_results: results
    };
  }

  public getPrivacyStats(): PrivacyStats {
    if (this.validationHistory.length === 0) {
      return {
        total_validations: 0,
        success_rate: 0,
        average_privacy_score: 0,
        common_violations: [],
        trend: 'stable'
      };
    }
    
    const recentResults = this.validationHistory.slice(-100); // Last 100 validations
    const successRate = recentResults.filter(r => r.passed).length / recentResults.length;
    const avgScore = recentResults.reduce((sum, r) => sum + r.pii_score, 0) / recentResults.length;
    
    // Find most common violation types
    const violationCounts: Record<string, number> = {};
    for (const result of recentResults) {
      for (const violation of result.violations) {
        violationCounts[violation.type] = (violationCounts[violation.type] || 0) + 1;
      }
    }
    
    const commonViolations = Object.entries(violationCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([type, count]) => ({ type, count }));
    
    // Calculate trend (simple comparison of first vs last half)
    const firstHalf = recentResults.slice(0, Math.floor(recentResults.length / 2));
    const secondHalf = recentResults.slice(Math.floor(recentResults.length / 2));
    
    const firstHalfSuccess = firstHalf.filter(r => r.passed).length / firstHalf.length;
    const secondHalfSuccess = secondHalf.filter(r => r.passed).length / secondHalf.length;
    
    let trend: 'improving' | 'declining' | 'stable' = 'stable';
    if (secondHalfSuccess > firstHalfSuccess + 0.05) trend = 'improving';
    else if (secondHalfSuccess < firstHalfSuccess - 0.05) trend = 'declining';
    
    return {
      total_validations: this.validationHistory.length,
      success_rate: successRate,
      average_privacy_score: avgScore,
      common_violations: commonViolations,
      trend
    };
  }

  public reset(): void {
    this.validationHistory = [];
    console.log('🔄 Privacy validator reset');
  }
}

interface BatchPrivacyResult {
  overall_passed: boolean;
  privacy_success_rate: number;
  total_tested: number;
  total_violations: number;
  violations_by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  average_privacy_score: number;
  safe_summary_compliance: number;
  routing_compliance: number;
  individual_results: PrivacyValidationResult[];
}

interface PrivacyStats {
  total_validations: number;
  success_rate: number;
  average_privacy_score: number;
  common_violations: { type: string; count: number }[];
  trend: 'improving' | 'declining' | 'stable';
}