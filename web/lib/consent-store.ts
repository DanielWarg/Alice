/**
 * ConsentStore - GDPR/EU AI-Act compliant consent management
 * Lagrar endast nödvändig metadata för compliance utan rå-audio
 */

export interface ConsentRecord {
  userId: string;
  timestamp: number;
  version: string;
  scope: ('asr' | 'tts' | 'voice_clone')[];
  voiceIdentifierHash?: string; // For voice cloning - hashed, not raw audio
  country: string;
  userAgent: string;
}

export interface ComplianceLogEntry {
  event: 'consent_granted' | 'consent_revoked' | 'voice_used' | 'tts_blocked' | 'impersonation_blocked';
  timestamp: number;
  userId: string;
  provider: string;
  model?: string;
  consentVersion: string;
  country: string;
  details?: Record<string, any>;
}

export class ConsentStore {
  private static readonly CONSENT_VERSION = '1.0';
  private static readonly STORAGE_KEY = 'alice_voice_consent';
  private static readonly LOG_KEY = 'alice_compliance_log';
  
  static isConsentRequired(): boolean {
    return process.env.NEXT_PUBLIC_VOICE_REQUIRE_CONSENT === 'on';
  }
  
  static showSyntheticBadge(): boolean {
    return process.env.NEXT_PUBLIC_VOICE_SHOW_SYNTHETIC_BADGE !== 'off';
  }
  
  static blockImpersonation(): boolean {
    return process.env.NEXT_PUBLIC_VOICE_BLOCK_IMPERSONATION !== 'off';
  }
  
  static persistAudio(): boolean {
    return process.env.NEXT_PUBLIC_VOICE_PERSIST_AUDIO === 'on';
  }
  
  static getRetentionDays(): number {
    return parseInt(process.env.NEXT_PUBLIC_VOICE_RETENTION_DAYS || '0');
  }
  
  static getContentFilter(): 'strict' | 'moderate' | 'off' {
    return (process.env.NEXT_PUBLIC_VOICE_CONTENT_FILTER as any) || 'strict';
  }
  
  static generateUserId(): string {
    // Anonymous user ID for GDPR compliance
    let userId = localStorage.getItem('alice_user_id');
    if (!userId) {
      userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('alice_user_id', userId);
    }
    return userId;
  }
  
  static hasValidConsent(requiredScopes: ('asr' | 'tts' | 'voice_clone')[] = ['asr', 'tts']): boolean {
    if (!this.isConsentRequired()) return true;
    
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (!stored) return false;
      
      const consent: ConsentRecord = JSON.parse(stored);
      
      // Check version matches
      if (consent.version !== this.CONSENT_VERSION) return false;
      
      // Check required scopes are granted
      return requiredScopes.every(scope => consent.scope.includes(scope));
      
    } catch (error) {
      console.warn('Failed to check consent:', error);
      return false;
    }
  }
  
  static async grantConsent(scopes: ('asr' | 'tts' | 'voice_clone')[]): Promise<void> {
    const userId = this.generateUserId();
    const country = 'SE'; // Default to Sweden for EU compliance
    
    const consent: ConsentRecord = {
      userId,
      timestamp: Date.now(),
      version: this.CONSENT_VERSION,
      scope: scopes,
      country,
      userAgent: navigator.userAgent
    };
    
    // Store consent
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(consent));
    
    // Log compliance event
    await this.logComplianceEvent({
      event: 'consent_granted',
      timestamp: Date.now(),
      userId,
      provider: 'alice-voice',
      consentVersion: this.CONSENT_VERSION,
      country,
      details: { scopes }
    });
    
    console.log('✅ Consent granted for scopes:', scopes);
  }
  
  static async revokeConsent(): Promise<void> {
    const userId = this.generateUserId();
    
    // Log revocation
    await this.logComplianceEvent({
      event: 'consent_revoked',
      timestamp: Date.now(),
      userId,
      provider: 'alice-voice',
      consentVersion: this.CONSENT_VERSION,
      country: 'SE'
    });
    
    // Clear consent
    localStorage.removeItem(this.STORAGE_KEY);
    
    console.log('❌ Consent revoked');
  }
  
  static async logVoiceUsage(provider: string, model: string): Promise<void> {
    if (!this.isConsentRequired()) return;
    
    const userId = this.generateUserId();
    const consent = this.getCurrentConsent();
    
    await this.logComplianceEvent({
      event: 'voice_used',
      timestamp: Date.now(),
      userId,
      provider,
      model,
      consentVersion: consent?.version || 'unknown',
      country: consent?.country || 'SE'
    });
  }
  
  static async logTTSBlocked(reason: string, text?: string): Promise<void> {
    const userId = this.generateUserId();
    const consent = this.getCurrentConsent();
    
    await this.logComplianceEvent({
      event: 'tts_blocked',
      timestamp: Date.now(),
      userId,
      provider: 'alice-voice',
      consentVersion: consent?.version || 'unknown',
      country: consent?.country || 'SE',
      details: { 
        reason, 
        textLength: text?.length || 0,
        textPreview: text?.substring(0, 100) // Only first 100 chars for compliance
      }
    });
  }
  
  static getCurrentConsent(): ConsentRecord | null {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }
  
  private static async logComplianceEvent(entry: ComplianceLogEntry): Promise<void> {
    try {
      // Store locally for now - in production, send to compliance API
      const logs = this.getComplianceLogs();
      logs.push(entry);
      
      // Keep only last 100 entries for storage efficiency
      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }
      
      localStorage.setItem(this.LOG_KEY, JSON.stringify(logs));
      
      // In production: send to compliance API
      if (process.env.NEXT_PUBLIC_COMPLIANCE_ENDPOINT) {
        await fetch(process.env.NEXT_PUBLIC_COMPLIANCE_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(entry)
        }).catch(error => {
          console.warn('Failed to send compliance log:', error);
        });
      }
      
    } catch (error) {
      console.warn('Failed to log compliance event:', error);
    }
  }
  
  static getComplianceLogs(): ComplianceLogEntry[] {
    try {
      const stored = localStorage.getItem(this.LOG_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }
  
  static getComplianceStats(): {
    consentGranted: boolean;
    consentVersion: string | null;
    voiceUsageCount: number;
    blockedTTSCount: number;
    lastUsed: number | null;
  } {
    const consent = this.getCurrentConsent();
    const logs = this.getComplianceLogs();
    
    return {
      consentGranted: !!consent,
      consentVersion: consent?.version || null,
      voiceUsageCount: logs.filter(l => l.event === 'voice_used').length,
      blockedTTSCount: logs.filter(l => l.event === 'tts_blocked').length,
      lastUsed: Math.max(...logs.map(l => l.timestamp), 0) || null
    };
  }
}