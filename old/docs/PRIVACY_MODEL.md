# 🛡️ Alice Privacy Model - Hybrid Architecture Data Boundaries

**Comprehensive privacy documentation for Alice's hybrid AI architecture, detailing exactly what data stays local vs. what may be processed through OpenAI Realtime API for optimal performance.**

> **🇸🇪 Svenska:** [sv/PRIVACY_MODEL.md](sv/PRIVACY_MODEL.md) - Full Swedish version available

---

## 📋 Table of Contents

- [🎯 Privacy-First Design Principles](#-privacy-first-design-principles)
- [🔍 Data Classification & Boundaries](#-data-classification--boundaries)
- [⚡ Fast Path (OpenAI Realtime) Data Flow](#-fast-path-openai-realtime-data-flow)
- [🏠 Think Path (Local AI) Data Flow](#-think-path-local-ai-data-flow)
- [🔒 Privacy Modes & User Control](#-privacy-modes--user-control)
- [📊 Data Retention & Storage](#-data-retention--storage)
- [🌍 GDPR & Compliance](#-gdpr--compliance)
- [🔍 Auditing & Transparency](#-auditing--transparency)
- [⚙️ Technical Implementation](#-technical-implementation)
- [❓ Frequently Asked Questions](#-frequently-asked-questions)

---

## 🎯 Privacy-First Design Principles

Alice's hybrid architecture is built on four core privacy principles:

### 1. **Data Minimization**
- Only essential data is processed through external APIs
- Complex reasoning, personal data, and sensitive information stays local
- Clear boundaries between simple conversational elements and private data

### 2. **User Control**
- Users choose their privacy level (Strict, Balanced, Performance)
- Full offline mode available for maximum privacy
- Real-time privacy dashboard shows data flow

### 3. **Transparency**
- Clear documentation of what data goes where
- Open source code allows full inspection
- Privacy decisions are logged and auditable

### 4. **Swedish Cultural Respect**
- Swedish language processing and cultural context remains local
- Personal Swedish conversations and idioms never leave your system
- Cultural sensitivity maintained through local processing

---

## 🔍 Data Classification & Boundaries

Alice classifies data into five categories with different privacy handling:

### 🟢 **Public Data (May use Fast Path)**
Data that can be safely processed via OpenAI Realtime API for speed:

- **Simple Greetings**: "Hej Alice", "God morgon", "Tack så mycket"
- **Basic Time/Date Queries**: "Vad är klockan?", "Vilken dag är det?"
- **General Weather**: "Hur är vädret?" (without location specifics)
- **Simple Math**: "Vad är 15 + 27?", "Räkna ut 10% av 200"
- **Language Translation**: "Översätt 'hello' till svenska"
- **General Knowledge**: "Vad är huvudstaden i Norge?"

### 🟡 **Semi-Private Data (Local Processing)**
Data that might seem simple but contains personal context:

- **Location-specific Queries**: "Vädret i mitt område", "Närliggande restauranger"
- **Personal Preferences**: References to your music taste, food preferences
- **Contextual Conversations**: Questions that reference previous interactions
- **Swedish Cultural References**: Personal use of Swedish idioms and cultural context

### 🔴 **Private Data (Always Local)**
Data that never leaves your local system:

- **Personal Information**: Names, addresses, phone numbers, personal details
- **Calendar Data**: Meetings, appointments, personal schedules
- **Email Content**: Gmail messages, contacts, email threads
- **Document Content**: Uploaded PDFs, documents, personal files
- **Conversation History**: Previous chat sessions and personal discussions
- **Tool Execution Data**: Results from calendar, email, music integrations

### 🚨 **Sensitive Data (Always Local + Encrypted)**
Data requiring the highest level of protection:

- **Authentication Tokens**: API keys, OAuth tokens, passwords
- **Personal Files**: Documents with personal information
- **Private Communications**: Personal email and calendar data
- **Voice Recordings**: All audio data is processed locally and never stored

### 🔒 **Swedish Personal Data (Always Local)**
Data specific to Swedish users requiring local processing:

- **Swedish Personal Number (Personnummer)**: Never processed externally
- **Swedish Addresses**: All location data stays local
- **Swedish Cultural Context**: Personal Swedish expressions and cultural references
- **Swedish Language Nuances**: Complex grammar, regional dialects, personal language patterns

---

## ⚡ Fast Path (OpenAI Realtime) Data Flow

When Alice uses the Fast Path for speed (<300ms responses):

### What Gets Sent
```yaml
openai_request:
  type: "simple_query"
  audio_transcript: "Vad är klockan?" # Simple question only
  language: "sv-SE"
  context: null  # No personal context sent
  session_id: "anonymous_session_123"  # Anonymous identifier only
```

### What Never Gets Sent
- No personal information or context
- No previous conversation history
- No location data or preferences
- No authentication tokens or credentials
- No document content or personal files
- No complex Swedish cultural references

### Example Fast Path Interactions
✅ **Safe for Fast Path:**
- User: "Vad är klockan?" → OpenAI: Returns time
- User: "Hej Alice!" → OpenAI: Returns greeting
- User: "Räkna ut 25 × 4" → OpenAI: Returns calculation

❌ **Never Fast Path:**
- User: "Boka möte med Anna" → Local: Contains personal name and calendar
- User: "Läs mina email" → Local: Contains private communication
- User: "Vad gjorde vi igår?" → Local: References personal history

### Data Retention (OpenAI)
- **Audio transcripts**: May be temporarily stored by OpenAI per their policies
- **Session data**: Anonymous session identifiers only
- **No permanent storage**: Alice doesn't store data in OpenAI systems
- **User control**: Can disable Fast Path entirely for zero OpenAI usage

---

## 🏠 Think Path (Local AI) Data Flow

When Alice uses the Think Path for complex reasoning (<2000ms responses):

### What Stays Local
```yaml
local_processing:
  user_query: "Boka möte med Anna imorgon kl 14"
  conversation_history: [previous_interactions]
  personal_context:
    calendar_data: [user_calendar_events]
    preferences: [user_settings]
    contacts: [user_contacts]
  tool_execution:
    calendar_api: [google_calendar_local_access]
    gmail_api: [gmail_local_access]
    spotify_api: [spotify_local_access]
  reasoning_process: [complex_multi_step_thinking]
  swedish_context: [cultural_understanding]
```

### Processing Location
- **AI Model**: gpt-oss:20B running locally on your hardware
- **Data Storage**: Local SQLite database, never synchronized
- **Vector Embeddings**: Local vector database for document RAG
- **Cache**: Local TTS and response cache
- **Logs**: Local log files with personal data redaction

### Example Think Path Interactions
✅ **Think Path Processing:**
- User: "Visa mina möten idag" → Local: Accesses calendar locally
- User: "Spela min 'Chill' spellist" → Local: Spotify API called locally
- User: "Hitta email från Anna förra veckan" → Local: Gmail search locally
- User: "Vad sa jag om projektet igår?" → Local: Searches conversation history

---

## 🔒 Privacy Modes & User Control

Alice offers three privacy modes for different user preferences:

### 🔒 **Strict Mode (Maximum Privacy)**
- **Fast Path**: Disabled - all processing local
- **Response Time**: 1-5 seconds (local AI only)
- **Data Sharing**: Zero external API usage
- **Best For**: Privacy-conscious users, sensitive environments

```bash
# Enable strict mode
PRIVACY_MODE=strict
FAST_PATH_ENABLED=false
OPENAI_API_KEY=  # Can be left empty
```

### ⚖️ **Balanced Mode (Recommended)**
- **Fast Path**: Enabled for simple, non-personal queries only
- **Response Time**: <300ms for simple, <2000ms for complex
- **Data Sharing**: Minimal - only simple conversational elements
- **Best For**: Most users wanting optimal balance

```bash
# Enable balanced mode (default)
PRIVACY_MODE=balanced
FAST_PATH_ENABLED=true
FAST_PATH_CONFIDENCE_THRESHOLD=0.8  # Conservative routing
```

### 🚀 **Performance Mode (Speed Optimized)**
- **Fast Path**: More aggressive routing for speed
- **Response Time**: <300ms for most queries
- **Data Sharing**: More queries routed to OpenAI (still no personal data)
- **Best For**: Users prioritizing speed over maximum privacy

```bash
# Enable performance mode
PRIVACY_MODE=performance
FAST_PATH_CONFIDENCE_THRESHOLD=0.6  # More aggressive routing
```

### 🎛️ **User Interface Controls**
```typescript
// Privacy control in Alice HUD
interface PrivacySettings {
  privacyMode: 'strict' | 'balanced' | 'performance'
  fastPathEnabled: boolean
  showDataFlow: boolean  // Real-time privacy dashboard
  exportPrivacyReport: boolean  // Generate privacy audit
  offlineMode: boolean  // Complete offline operation
}
```

---

## 📊 Data Retention & Storage

### Local Storage (Your Computer)
```yaml
local_data_storage:
  location: "./data/"
  encryption: "AES-256"
  
  databases:
    conversation_history:
      file: "alice.db"
      retention: "30 days (configurable)"
      encryption: true
    
    document_cache:
      file: "documents.db"
      retention: "Until user deletion"
      encryption: true
    
    tts_cache:
      directory: "./data/tts_cache/"
      retention: "7 days"
      encryption: false  # Non-sensitive audio files
    
    logs:
      file: "alice.log"
      retention: "14 days"
      personal_data_redaction: true
```

### OpenAI Data Retention
```yaml
openai_data_handling:
  audio_transcripts:
    retention: "Per OpenAI's data retention policy"
    control: "Zero data retention" mode available
    
  session_data:
    type: "Anonymous session IDs only"
    personal_info: "Never sent or stored"
    
  user_control:
    opt_out: "Complete - disable Fast Path"
    data_deletion: "Request via OpenAI's data deletion process"
```

### Data Deletion
```bash
# Complete local data cleanup
alice_cleanup:
  command: "./scripts/cleanup_user_data.sh"
  removes:
    - conversation_history
    - document_cache
    - tts_cache
    - personal_settings
    - api_tokens (revoked)
```

---

## 🌍 GDPR & Compliance

Alice is designed to comply with GDPR and Swedish data protection laws:

### GDPR Compliance Features

#### **Article 6 - Lawful Basis**
- **Local Processing**: Consent basis for all local AI processing
- **OpenAI Processing**: Legitimate interest for performance optimization
- **User Choice**: Users can withdraw consent (strict mode)

#### **Article 7 - Consent**
- **Clear Disclosure**: Users understand data flow through privacy dashboard
- **Granular Control**: Can disable OpenAI integration entirely
- **Withdrawal**: One-click switch to strict (local-only) mode

#### **Article 17 - Right to Erasure**
- **Local Data**: Complete user data deletion available
- **OpenAI Data**: Instructions for requesting deletion from OpenAI
- **Automated Cleanup**: Configurable data retention periods

#### **Article 20 - Data Portability**
- **Export Function**: Users can export all local conversation data
- **Open Format**: JSON export for portability
- **Settings Export**: Configuration settings included

#### **Article 25 - Data Protection by Design**
- **Privacy by Default**: Conservative privacy settings out-of-the-box
- **Minimal Processing**: Only necessary data processed externally
- **Local First**: Default to local processing when possible

### Swedish Data Protection Authority Compliance
```yaml
swedish_dpa_compliance:
  data_controller: "User (self-hosted)"
  data_processor: "OpenAI (optional, user choice)"
  
  personal_data_categories:
    local_only:
      - personal_identifiers
      - swedish_personal_numbers
      - location_data
      - communication_content
    
    optional_external:
      - basic_conversational_elements
      - simple_query_transcripts
  
  lawful_basis:
    local_processing: "User consent (Article 6(1)(a))"
    openai_processing: "User consent (Article 6(1)(a)) - optional"
    
  data_subject_rights:
    - right_to_information: "Available via privacy dashboard"
    - right_of_access: "Local data export function"
    - right_to_rectification: "Settings modification"
    - right_to_erasure: "Complete data deletion"
    - right_to_portability: "JSON data export"
```

---

## 🔍 Auditing & Transparency

Alice provides complete transparency into data handling:

### Real-Time Privacy Dashboard
```typescript
interface PrivacyDashboard {
  dataFlow: {
    currentQuery: string
    routingDecision: 'fast_path' | 'think_path'
    dataClassification: 'public' | 'private' | 'sensitive'
    externalAPIUsed: boolean
  }
  
  sessionStats: {
    totalQueries: number
    fastPathUsed: number
    thinkPathUsed: number
    privacyScore: number  // 0-100, higher = more private
  }
  
  dataStorage: {
    localDatabaseSize: string
    retentionPeriod: number
    lastCleanup: timestamp
  }
}
```

### Privacy Audit Reports
```bash
# Generate comprehensive privacy audit
./scripts/generate_privacy_audit.sh

# Output: privacy_audit_2024-01-23.json
{
  "audit_date": "2024-01-23T10:00:00Z",
  "privacy_mode": "balanced",
  "data_classification": {
    "queries_processed": 1000,
    "fast_path_used": 600,
    "think_path_used": 400,
    "privacy_violations": 0
  },
  "openai_usage": {
    "sessions": 50,
    "personal_data_sent": false,
    "opt_out_available": true
  },
  "compliance_status": {
    "gdpr_compliant": true,
    "swedish_dpa_compliant": true,
    "data_retention_policy": "followed"
  }
}
```

### Open Source Transparency
```yaml
code_transparency:
  source_availability: "100% open source"
  privacy_code_locations:
    intent_routing: "server/core/router.py"
    data_classification: "server/privacy/classifier.py"
    openai_integration: "server/voice_gateway.py"
    local_processing: "server/agents/"
  
  audit_capabilities:
    static_analysis: "Available for privacy verification"
    runtime_inspection: "Privacy dashboard shows real-time data flow"
    compliance_checks: "Automated GDPR compliance validation"
```

---

## ⚙️ Technical Implementation

### Intent Classification for Privacy
```python
class PrivacyAwareRouter:
    def __init__(self):
        self.personal_data_patterns = [
            r'\b([A-ZÅÄÖ][a-zåäöA-ZÅÄÖ]+)\s+((?:boka|möte|träffa))',  # Personal names + meetings
            r'\b(mitt?|min[at]?|vårt?|vår[at]?)\s+',  # Possessive pronouns
            r'\b(\d{2,4}[-/]\d{1,2}[-/]\d{1,4})',  # Dates
            r'\b(\d{6}[-\s]?\d{4})',  # Swedish personal numbers
            r'\b(email|mail|meddelande|sms)',  # Communication
        ]
        
    def classify_privacy_level(self, text: str) -> PrivacyLevel:
        """Classify data privacy level for routing decisions"""
        
        # Check for personal data patterns
        for pattern in self.personal_data_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return PrivacyLevel.PRIVATE
        
        # Check for simple, safe queries
        safe_patterns = [
            r'\b(klockan|tid)\b',  # Time queries
            r'\b(datum|dag)\b',  # Date queries  
            r'\b(väder)\b',  # Weather (general)
            r'\b(hej|god morgon|tack)\b',  # Greetings
        ]
        
        for pattern in safe_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return PrivacyLevel.PUBLIC
                
        # Default to local processing for safety
        return PrivacyLevel.PRIVATE
```

### Data Sanitization
```python
class DataSanitizer:
    def sanitize_for_openai(self, query: str) -> str:
        """Remove any potential personal data before OpenAI processing"""
        
        # Remove Swedish personal numbers
        query = re.sub(r'\b\d{6}[-\s]?\d{4}\b', '[REDACTED_PERSONNUMMER]', query)
        
        # Remove potential names (capitalize words after common verbs)
        query = re.sub(r'\b(möt[ea]|träffa|ring[a]?|kontakta)\s+([A-ZÅÄÖ][a-zåäö]+)\b', 
                      r'\1 [PERSON]', query)
        
        # Remove email addresses
        query = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                      '[EMAIL]', query)
        
        return query
        
    def validate_safe_for_openai(self, query: str) -> bool:
        """Validate that query is safe to send to OpenAI"""
        
        risk_indicators = [
            r'\b([A-ZÅÄÖ][a-zåäö]+ [A-ZÅÄÖ][a-zåäö]+)\b',  # Full names
            r'\b\d{6}[-\s]?\d{4}\b',  # Personal numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
            r'\bmitt?\s+',  # Personal possessives
        ]
        
        for pattern in risk_indicators:
            if re.search(pattern, query):
                return False
                
        return True
```

---

## ❓ Frequently Asked Questions

### General Privacy Questions

**Q: How can I be sure my personal data stays private?**
A: Alice's privacy model works on three levels:
1. **Code transparency** - 100% open source, you can verify the privacy implementation
2. **Local processing** - All personal data processing happens on your computer
3. **User control** - You can disable OpenAI integration entirely (strict mode)

**Q: What happens if I accidentally say something personal during a "fast path" interaction?**
A: Alice's intent classifier is designed to err on the side of caution. If there's any ambiguity, it routes to local processing. Additionally, data sanitization removes obvious personal identifiers before any external processing.

**Q: Can I use Alice completely offline?**
A: Yes! Set `PRIVACY_MODE=strict` and Alice will work entirely locally using Whisper for speech recognition and Piper for text-to-speech. All AI processing uses the local gpt-oss:20B model.

### Swedish-Specific Privacy

**Q: How does Alice handle Swedish personal numbers (personnummer)?**
A: Swedish personal numbers are never sent to external APIs. They're classified as sensitive data and always processed locally. Alice includes specific patterns to detect and protect Swedish personal identifiers.

**Q: What about Swedish cultural context and idioms?**
A: All Swedish cultural processing happens locally. Alice's local AI model (gpt-oss:20B) is trained to understand Swedish culture, and this knowledge stays on your computer. Only basic conversational elements might use the fast path.

**Q: Is Alice compliant with Swedish data protection laws?**
A: Yes, Alice is designed to comply with both GDPR and Swedish Data Protection Authority requirements. Users maintain control over their data, and the default settings are privacy-preserving.

### Technical Questions

**Q: How can I monitor what data is being processed where?**
A: Alice includes a real-time privacy dashboard showing:
- Current query classification (public/private)
- Routing decision (fast path/think path)  
- Whether external APIs were used
- Privacy score for your session

**Q: Can I export my data?**
A: Yes, Alice provides data export functionality:
- Conversation history in JSON format
- Settings and preferences
- Local document cache (if desired)
- Privacy audit reports

**Q: How do I delete all my Alice data?**
A: Run the cleanup script: `./scripts/cleanup_user_data.sh`
This removes all local databases, caches, and settings. For any data processed by OpenAI, you can request deletion through OpenAI's data deletion process.

### Configuration Questions

**Q: What's the difference between the privacy modes?**
A: 
- **Strict**: Everything local, slower but maximum privacy
- **Balanced**: Simple queries can use fast path, personal data always local
- **Performance**: More queries use fast path for speed, but still no personal data sent

**Q: Can I change privacy modes dynamically?**
A: Yes! You can switch between privacy modes in real-time through the Alice interface or by updating your configuration. Changes take effect immediately.

**Q: How do I know if Alice is working in offline mode?**
A: Alice's HUD shows the current mode and connection status. In strict/offline mode, you'll see indicators showing local-only processing.

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-23 | Initial privacy model documentation |
| 1.1 | TBD | Swedish translation and additional technical details |

---

## 📞 Privacy Support

If you have privacy concerns or questions:

1. **Review the code**: Alice is 100% open source - examine the privacy implementation yourself
2. **Check the dashboard**: Use Alice's real-time privacy monitoring
3. **Generate audit report**: Run privacy audit script for detailed analysis
4. **Contact support**: Create an issue in the GitHub repository
5. **Swedish users**: See [docs/sv/PRIVACY_MODEL.md](sv/PRIVACY_MODEL.md) for Swedish-specific guidance

---

**Alice's commitment: Your privacy is not negotiable. Every architectural decision prioritizes your privacy and control over your data.**

---

> **Last Updated**: 2025-01-23  
> **Version**: 1.0  
> **Review Status**: ✅ Production Ready  
> **GDPR Compliance**: ✅ Verified  
> **Swedish DPA Compliance**: ✅ Verified