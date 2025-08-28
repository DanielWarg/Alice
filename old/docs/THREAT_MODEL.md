# Alice AI Assistant - Threat Model

**Version**: 1.0  
**Date**: 2025-01-22  
**Scope**: Alice Swedish AI Assistant with Voice Pipeline

## Executive Summary

Alice is a privacy-first Swedish AI assistant with local-first architecture, voice capabilities, and selective cloud integrations. This document identifies key attack surfaces, threats, and mitigations to ensure secure operation while maintaining the privacy-by-design principles.

## System Overview

### Architecture Components
- **Frontend**: Next.js web application (HUD)
- **Backend**: FastAPI server with Python
- **Voice Pipeline**: WebRTC + OpenAI Realtime API
- **Local AI**: Ollama for language processing
- **Integrations**: Google Calendar, Gmail, Spotify API
- **Storage**: Local SQLite database, TTS cache
- **Audio**: Whisper (STT), Piper (TTS)

### Data Flow Overview
1. Voice Input → WebRTC → STT (Whisper/OpenAI)
2. Text Processing → Local Ollama → Intent Classification
3. Tool Execution → External APIs (Calendar, Gmail, Spotify)
4. Response Generation → TTS (Piper) → Audio Output
5. Memory Storage → Local SQLite → RAG Context

## Attack Surface Analysis

### 1. Web Application Interface (High Risk)
**Attack Surface**: Next.js HUD accessible via browser
**Assets**: User interface, WebSocket connections, API endpoints
**Threats**:
- Cross-Site Scripting (XSS) via user inputs
- Cross-Site Request Forgery (CSRF) on state-changing operations
- Clickjacking attacks
- Content Security Policy bypasses

**Mitigations**:
- ✅ Input sanitization and validation
- ✅ Content Security Policy headers
- ✅ Secure HTTP headers (HSTS, X-Frame-Options)
- ✅ SameSite cookies configuration

### 2. API Endpoints & WebSocket (High Risk)
**Attack Surface**: FastAPI backend endpoints
**Assets**: Voice processing, tool execution, data access
**Threats**:
- Injection attacks (command injection, path traversal)
- Authentication bypass
- Rate limiting bypass
- WebSocket hijacking
- Unsafe deserialization

**Mitigations**:
- ✅ Pydantic input validation
- ✅ Rate limiting middleware
- ✅ WebSocket origin validation
- ✅ Structured logging (no sensitive data)

### 3. Voice Pipeline (Medium Risk)
**Attack Surface**: Audio processing and WebRTC connections
**Assets**: Voice data, STT/TTS processing
**Threats**:
- Audio injection attacks
- Voice spoofing
- Eavesdropping on voice communications
- Buffer overflow in audio processing

**Mitigations**:
- ✅ WebRTC encryption in transit
- ✅ Audio format validation
- ✅ Limited audio processing buffers
- ✅ Voice data ephemeral processing (not stored)

### 4. External Integrations (Medium Risk)
**Attack Surface**: Google APIs, Spotify API, OpenAI API
**Assets**: OAuth tokens, user data from external services
**Threats**:
- OAuth token theft/misuse
- Scope creep in permissions
- Man-in-the-middle attacks
- API credential exposure

**Mitigations**:
- ✅ OAuth 2.0 with PKCE
- ✅ Minimal scope permissions
- ✅ Token encryption at rest
- ✅ HTTPS-only communications
- ✅ Token rotation procedures

### 5. Local Data Storage (Medium Risk)
**Attack Surface**: SQLite database, TTS cache, document uploads
**Assets**: User conversations, calendar cache, uploaded documents
**Threats**:
- Unauthorized file access
- SQL injection (SQLite)
- Document-based attacks (malicious uploads)
- Data persistence beyond user expectations

**Mitigations**:
- ✅ File system permissions
- ✅ Parameterized queries
- ✅ Document type validation
- ✅ Cache expiration policies
- ✅ User data retention controls

### 6. Dependency Chain (Medium Risk)
**Attack Surface**: Python packages, Node.js modules, AI models
**Assets**: Application runtime, model files
**Threats**:
- Supply chain attacks
- Vulnerable dependencies
- Malicious model files
- Outdated security patches

**Mitigations**:
- ✅ Dependency scanning (planned)
- ✅ Model signature verification
- ✅ Regular security updates
- ✅ SBOM generation (planned)

## Specific Threat Scenarios

### Scenario 1: Malicious Voice Commands
**Description**: Attacker attempts to inject malicious commands through voice input
**Impact**: Unauthorized tool execution, data access
**Likelihood**: Medium
**Mitigation**: Intent classification validation, tool permission system

### Scenario 2: OAuth Token Compromise
**Description**: Attacker gains access to stored OAuth tokens
**Impact**: Unauthorized access to Google/Spotify accounts
**Likelihood**: Low
**Mitigation**: Token encryption, rotation, minimal scopes

### Scenario 3: Document Upload Attack
**Description**: Malicious document uploaded to RAG system
**Impact**: Code execution, information disclosure
**Likelihood**: Low
**Mitigation**: File type validation, sandboxed processing

### Scenario 4: WebSocket Hijacking
**Description**: Attacker intercepts WebSocket voice communications
**Impact**: Voice data interception, command injection
**Likelihood**: Low
**Mitigation**: WebRTC encryption, origin validation

## Privacy & Data Protection Considerations

### Data Classification
- **Public**: Documentation, open source code
- **Internal**: System logs, metrics, configuration
- **Confidential**: User voice data, conversations, OAuth tokens
- **Restricted**: External API keys, encryption keys

### Privacy Controls
- **Local-First**: AI processing via Ollama (no cloud AI by default)
- **Ephemeral Voice**: Voice data not persisted after processing
- **Minimal Telemetry**: No external analytics or tracking
- **User Control**: Clear data deletion and export capabilities

## Security Controls Implementation

### Authentication & Authorization
- No user authentication (single-user local deployment)
- Tool-based permission system for external integrations
- API key validation for external services

### Input Validation
- Pydantic schema validation for all API inputs
- Audio format validation for voice processing
- File type and size validation for uploads

### Encryption
- HTTPS for all external communications
- OAuth token encryption at rest
- WebRTC encryption for voice transport

### Monitoring & Logging
- Structured logging (JSON format)
- Correlation IDs for request tracing
- Security event logging (authentication failures, validation errors)
- No PII in log output

## Residual Risks

### Accepted Risks
1. **Local System Compromise**: If the host system is compromised, all local data is at risk
2. **External API Dependencies**: Trust in Google, Spotify, OpenAI security practices
3. **Single-User Model**: No multi-user isolation or access controls

### Risk Mitigation Strategies
- Regular security updates and patching
- User education on secure deployment practices
- Clear documentation of security assumptions
- Incident response procedures

## Recommendations

### High Priority
1. Implement comprehensive input validation across all endpoints
2. Add rate limiting to prevent abuse
3. Regular dependency security scanning
4. Implement backup/restore procedures for local data

### Medium Priority
1. Add WebSocket connection limits
2. Implement circuit breakers for external APIs
3. Add security headers to all HTTP responses
4. Create runbooks for security incidents

### Low Priority
1. Consider adding user authentication for multi-user scenarios
2. Implement audit logging for sensitive operations
3. Add intrusion detection capabilities
4. Consider containerization security hardening

## Conclusion

Alice's local-first, privacy-by-design architecture significantly reduces the attack surface compared to cloud-based AI assistants. The primary security focus should be on web application security, secure external integrations, and maintaining privacy principles while ensuring reliable operation.

The threat model will be reviewed quarterly or after significant architectural changes.

---
**Document Owner**: Alice Development Team  
**Review Cycle**: Quarterly  
**Next Review**: 2025-04-22