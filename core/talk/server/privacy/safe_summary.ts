/**
 * Safe Summary Privacy Gate
 * Filters PII and creates safe content summaries for cloud processing
 */

export interface SafeSummaryConfig {
  max_length: number;
  remove_names: boolean;
  remove_addresses: boolean;
  remove_phone_numbers: boolean;
  remove_emails: boolean;
  remove_financial: boolean;
  preserve_context: boolean;
}

export class SafeSummary {
  private config: SafeSummaryConfig;
  
  // PII detection patterns (Swedish context aware)
  private piiPatterns = {
    email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    phone_swedish: /\b(?:\+46|0)[\s-]?7[\s-]?\d{8}\b/g,
    phone_international: /\b(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}\b/g,
    ssn_swedish: /\b\d{6}[\s-]?\d{4}\b/g,
    credit_card: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
    iban: /\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b/g,
    ip_address: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
    url: /https?:\/\/(?:[-\w.])+(?:[:\d]+)?(?:\/(?:[\w\._~!$&'()*+,;=:@]|%\d{2})*)*(?:\?(?:[\w\._~!$&'()*+,;=:@/?]|%\d{2})*)?(?:#(?:[\w\._~!$&'()*+,;=:@/?]|%\d{2})*)?/g,
    address: /\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|gata|väg|Boulevard|Blvd)\b/gi,
    postal_code: /\b\d{3}\s?\d{2}\b/g
  };

  // Name detection patterns  
  private namePatterns = {
    explicit_names: /\b(?:my name is|i'm called|jag heter|mitt namn är|this is|det här är)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/gi,
    contact_names: /\b(?:contact|ring|call|kontakta|email|mejla)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/gi,
    mr_mrs: /\b(?:Mr|Mrs|Ms|Dr|Prof|Herr|Fru)\s+([A-Z][a-z]+)/gi,
    quoted_names: /[""]([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[""]/g
  };

  // Safe replacement templates
  private replacements = {
    '[EMAIL]': 'email address',
    '[PHONE]': 'phone number', 
    '[PERSON]': 'person',
    '[ADDRESS]': 'address',
    '[CARD]': 'payment card',
    '[SSN]': 'personal number',
    '[IP]': 'IP address',
    '[URL]': 'web address',
    '[IBAN]': 'bank account',
    '[POSTAL]': 'postal code'
  };

  constructor(config: SafeSummaryConfig) {
    this.config = config;
  }

  public summarize(text: string): string {
    let safeSummary = text;
    
    // Remove PII based on configuration
    if (this.config.remove_emails) {
      safeSummary = safeSummary.replace(this.piiPatterns.email, '[EMAIL]');
    }
    
    if (this.config.remove_phone_numbers) {
      safeSummary = safeSummary.replace(this.piiPatterns.phone_swedish, '[PHONE]');
      safeSummary = safeSummary.replace(this.piiPatterns.phone_international, '[PHONE]');
    }
    
    if (this.config.remove_names) {
      safeSummary = safeSummary.replace(this.namePatterns.explicit_names, 'person mentioned name');
      safeSummary = safeSummary.replace(this.namePatterns.contact_names, 'contact person');
      safeSummary = safeSummary.replace(this.namePatterns.mr_mrs, '[PERSON]');
      safeSummary = safeSummary.replace(this.namePatterns.quoted_names, '[PERSON]');
    }
    
    if (this.config.remove_addresses) {
      safeSummary = safeSummary.replace(this.piiPatterns.address, '[ADDRESS]');
      safeSummary = safeSummary.replace(this.piiPatterns.postal_code, '[POSTAL]');
    }
    
    if (this.config.remove_financial) {
      safeSummary = safeSummary.replace(this.piiPatterns.credit_card, '[CARD]');
      safeSummary = safeSummary.replace(this.piiPatterns.iban, '[IBAN]');
      safeSummary = safeSummary.replace(this.piiPatterns.ssn_swedish, '[SSN]');
    }
    
    // Remove other sensitive data
    safeSummary = safeSummary.replace(this.piiPatterns.ip_address, '[IP]');
    safeSummary = safeSummary.replace(this.piiPatterns.url, '[URL]');
    
    // Preserve context by replacing markers with contextual descriptions
    if (this.config.preserve_context) {
      Object.entries(this.replacements).forEach(([marker, replacement]) => {
        safeSummary = safeSummary.replace(new RegExp(`\\${marker}`, 'g'), replacement);
      });
    }
    
    // Truncate to maximum length
    if (safeSummary.length > this.config.max_length) {
      safeSummary = safeSummary.substring(0, this.config.max_length - 3) + '...';
    }
    
    return safeSummary;
  }
  
  public isSafe(text: string): boolean {
    // Check if text contains any PII patterns
    const patterns = [
      ...Object.values(this.piiPatterns),
      ...Object.values(this.namePatterns)
    ];
    
    for (const pattern of patterns) {
      if (pattern.test(text)) {
        return false;
      }
    }
    
    return true;
  }
  
  public detectPII(text: string): string[] {
    const detectedTypes: string[] = [];
    
    Object.entries(this.piiPatterns).forEach(([type, pattern]) => {
      if (pattern.test(text)) {
        detectedTypes.push(type);
      }
    });
    
    Object.entries(this.namePatterns).forEach(([type, pattern]) => {
      if (pattern.test(text)) {
        detectedTypes.push(type);
      }
    });
    
    return detectedTypes;
  }

  public shouldUseLocalRoute(text: string): boolean {
    // If any PII is detected, force local processing
    return !this.isSafe(text);
  }

  public createSafeSummary(text: string, intent: string): string {
    const safeSummary = this.summarize(text);
    
    // Add intent context for better routing
    const contextualSummary = `Intent: ${intent}\nContent: ${safeSummary}`;
    
    return contextualSummary;
  }
}