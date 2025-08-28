/**
 * Content Filter - Anti-impersonation and policy compliance
 * Prevents misuse while maintaining natural conversation flow
 */

import { ConsentStore } from './consent-store';

export interface FilterResult {
  allowed: boolean;
  reason?: string;
  category?: 'impersonation' | 'harmful' | 'sensitive' | 'technical';
  suggestion?: string;
}

export class ContentFilter {
  
  // Patterns for potential impersonation (Swedish and English)
  private static readonly IMPERSONATION_PATTERNS = [
    /(?:låtsas|imitera|härma)\s+(?:vara|som)\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)/i,
    /(?:pretend|act|speak|sound)\s+(?:like|as|to be)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i,
    /(?:jag är|detta är|mitt namn är)\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)/i,
    /(?:i am|this is|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i,
    /(?:säg som|tala som|låt som)\s+([A-ZÅÄÖ][a-zåäö]+)/i,
    /(?:voice of|in the voice of|as)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i
  ];
  
  // Harmful content patterns
  private static readonly HARMFUL_PATTERNS = [
    /(?:begå|utföra|planera)\s+(?:brott|våld|skada)/i,
    /(?:commit|perform|plan)\s+(?:crime|violence|harm)/i,
    /(?:hur|var)\s+(?:köper|skaffar|tillverkar)\s+(?:droger|vapen|explosiv)/i,
    /(?:how|where)\s+(?:to buy|get|make)\s+(?:drugs|weapons|explosiv)/i
  ];
  
  // Sensitive personal information patterns
  private static readonly SENSITIVE_PATTERNS = [
    /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/, // Credit card
    /\b\d{6}-\d{4}\b/, // Swedish personal number
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email
    /\b(?:\+46|0)[0-9\s-]{8,12}\b/ // Swedish phone
  ];
  
  // Known public figures (basic list - expand as needed)
  private static readonly PUBLIC_FIGURES = [
    'stefan löfven', 'magdalena andersson', 'ulf kristersson',
    'barack obama', 'joe biden', 'donald trump', 'elon musk',
    'zlatan ibrahimović', 'greta thunberg'
  ];
  
  static async filterText(text: string): Promise<FilterResult> {
    const normalizedText = text.toLowerCase().trim();
    
    // Skip filtering if content filter is off
    const filterLevel = ConsentStore.getContentFilter();
    if (filterLevel === 'off') {
      return { allowed: true };
    }
    
    // Check for impersonation attempts
    if (ConsentStore.blockImpersonation()) {
      const impersonationResult = this.checkImpersonation(normalizedText);
      if (!impersonationResult.allowed) {
        await ConsentStore.logTTSBlocked('impersonation', text);
        return impersonationResult;
      }
    }
    
    // Check harmful content (always active in strict mode)
    if (filterLevel === 'strict') {
      const harmfulResult = this.checkHarmfulContent(normalizedText);
      if (!harmfulResult.allowed) {
        await ConsentStore.logTTSBlocked('harmful_content', text);
        return harmfulResult;
      }
      
      // Check sensitive information
      const sensitiveResult = this.checkSensitiveContent(normalizedText);
      if (!sensitiveResult.allowed) {
        await ConsentStore.logTTSBlocked('sensitive_info', text);
        return sensitiveResult;
      }
    }
    
    // Check technical limitations (length, etc.)
    const technicalResult = this.checkTechnicalLimits(text);
    if (!technicalResult.allowed) {
      await ConsentStore.logTTSBlocked('technical_limits', text);
      return technicalResult;
    }
    
    return { allowed: true };
  }
  
  private static checkImpersonation(text: string): FilterResult {
    // Check if user has voice cloning consent
    const hasVoiceCloningConsent = ConsentStore.hasValidConsent(['voice_clone']);
    
    // Check for impersonation patterns
    for (const pattern of this.IMPERSONATION_PATTERNS) {
      const match = pattern.exec(text);
      if (match) {
        const suspectedName = match[1];
        
        // Check if it's a known public figure
        const isPublicFigure = this.PUBLIC_FIGURES.some(figure => 
          suspectedName.toLowerCase().includes(figure) || 
          figure.includes(suspectedName.toLowerCase())
        );
        
        if (isPublicFigure && !hasVoiceCloningConsent) {
          return {
            allowed: false,
            reason: `Vi kan inte skapa röst som imiterar ${suspectedName}. Röstkloning kräver uttryckligt samtycke från röstägaren.`,
            category: 'impersonation',
            suggestion: 'Välj en standardröst eller lägg till dokumenterat samtycke.'
          };
        } else if (!hasVoiceCloningConsent) {
          // General impersonation attempt without specific person
          return {
            allowed: false,
            reason: 'Vi kunde inte fortsätta eftersom begäran innebär röst-imitering utan samtycke.',
            category: 'impersonation',
            suggestion: 'Välj en annan röst eller läs våra riktlinjer om röstkloning och samtycke.'
          };
        }
      }
    }
    
    return { allowed: true };
  }
  
  private static checkHarmfulContent(text: string): FilterResult {
    for (const pattern of this.HARMFUL_PATTERNS) {
      if (pattern.test(text)) {
        return {
          allowed: false,
          reason: 'Uppläsning stoppad enligt riktlinjer för skadligt innehåll.',
          category: 'harmful',
          suggestion: 'Vi kan inte läsa upp detta innehåll med syntetisk röst. Justera texten och försök igen.'
        };
      }
    }
    
    return { allowed: true };
  }
  
  private static checkSensitiveContent(text: string): FilterResult {
    for (const pattern of this.SENSITIVE_PATTERNS) {
      if (pattern.test(text)) {
        return {
          allowed: false,
          reason: 'Uppläsning stoppad för att skydda personlig integritet.',
          category: 'sensitive',
          suggestion: 'Ta bort känsliga uppgifter som personnummer, telefon eller e-post'
        };
      }
    }
    
    return { allowed: true };
  }
  
  private static checkTechnicalLimits(text: string): FilterResult {
    const MAX_LENGTH = 1000; // Characters
    const MIN_LENGTH = 1;
    
    if (text.length > MAX_LENGTH) {
      return {
        allowed: false,
        reason: `Text för lång (${text.length}/${MAX_LENGTH} tecken)`,
        category: 'technical',
        suggestion: 'Dela upp i kortare meddelanden'
      };
    }
    
    if (text.length < MIN_LENGTH) {
      return {
        allowed: false,
        reason: 'Text för kort',
        category: 'technical',
        suggestion: 'Skriv minst ett tecken'
      };
    }
    
    return { allowed: true };
  }
  
  static getFilterStats(): {
    filterLevel: string;
    impersonationEnabled: boolean;
    totalBlocked: number;
    blockedByCategory: Record<string, number>;
  } {
    const logs = ConsentStore.getComplianceLogs();
    const blockedLogs = logs.filter(l => l.event === 'tts_blocked');
    
    const blockedByCategory: Record<string, number> = {};
    blockedLogs.forEach(log => {
      const reason = log.details?.reason || 'unknown';
      blockedByCategory[reason] = (blockedByCategory[reason] || 0) + 1;
    });
    
    return {
      filterLevel: ConsentStore.getContentFilter(),
      impersonationEnabled: ConsentStore.blockImpersonation(),
      totalBlocked: blockedLogs.length,
      blockedByCategory
    };
  }
}