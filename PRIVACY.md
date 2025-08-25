# Privacy Policy - Alice B3 Always-On Voice System

**Effective Date:** August 25, 2025  
**Last Updated:** August 25, 2025  
**Version:** 1.0

## Overview

Alice B3 Always-On Voice System processes voice data continuously to provide intelligent assistance. This document explains how we handle your voice data, what we store, and your privacy controls.

## Data Collection & Processing

### What We Collect
- **Voice Audio**: Continuous microphone input when ambient mode is active
- **Transcriptions**: Speech-to-text conversion of your voice commands and conversations  
- **Usage Metrics**: System performance data (latency, error rates, session duration)
- **Device Information**: Audio settings, browser type, connection status

### What We DON'T Collect
- **Recordings**: Raw audio is processed in real-time and not permanently stored
- **Personal Identity**: No account creation or personal information required
- **Location Data**: No GPS or location tracking
- **Cross-Device Tracking**: Each session is independent

## Data Processing Pipeline

### 1. Audio Capture (Client-Side)
- Microphone captures 16kHz mono audio in 20ms frames
- Voice Activity Detection (VAD) filters out silence
- Audio is sent to server in real-time via WebSocket

### 2. Transcription (Server-Side)
- OpenAI Whisper API processes audio frames for Swedish speech recognition
- Fallback to local Whisper if API unavailable
- Confidence scoring determines transcription quality

### 3. Importance Filtering
- Only "important" content is stored in memory
- Casual background conversation is discarded
- User can adjust importance thresholds

### 4. Memory Storage
- Relevant summaries stored with Time-To-Live (TTL)
- Default: 168 hours (7 days) for normal content
- Sensitive content: 24 hours automatic deletion
- Personal data (emails, phone numbers) automatically masked

## Your Privacy Controls

### "Glöm Det Där" (Forget That)
Voice commands to delete data:
- "Alice, glöm det där" - Delete last conversation
- "Alice, glöm vad jag sa om [topic]" - Delete specific topic
- "Alice, rensa minnet" - Clear all stored memories

### Manual Privacy Controls
- **Hard Mute**: Immediately stops all audio processing
- **Session Mute**: Pauses processing but maintains connection
- **Memory Clear**: Delete all stored conversations via API
- **TTL Settings**: Configure how long memories are kept

### API Endpoints for Privacy
```bash
# Delete specific memories
POST /api/privacy/forget
{
  "query": "glöm det där",
  "time_range": "last_hour"
}

# Emergency memory wipe
POST /api/privacy/forget/all

# Check privacy settings
GET /api/privacy/status
```

## Data Storage & Retention

### Temporary Data (Deleted Immediately)
- Raw audio frames (never stored to disk)
- WebSocket messages (processed and discarded)
- ASR intermediate results

### Short-Term Storage (Auto-Deleted)
- **Transcription buffer**: 30 seconds, then processed/discarded
- **Session state**: Cleared when WebSocket disconnects
- **Error logs**: 24 hours for debugging

### Long-Term Storage (User Controlled)
- **Ambient summaries**: 7 days default (configurable 1-30 days)
- **Important conversations**: User-defined retention
- **Sensitive content**: Maximum 24 hours, then auto-deleted

### Automatic Cleanup
- Daily scan removes expired memories
- Sensitive content patterns trigger immediate short TTL
- System health checks purge orphaned data

## Third-Party Services

### OpenAI Whisper API
- **Purpose**: Speech-to-text transcription for Swedish
- **Data Sent**: Audio frames (temporary upload, no storage by OpenAI per their policy)
- **Retention**: OpenAI does not store audio for Whisper API calls
- **Fallback**: Local Whisper if API unavailable

### No Other Third Parties
- No analytics services (Google Analytics, etc.)
- No advertising networks
- No data brokers or selling
- No social media integration

## Technical Security Measures

### Data in Transit
- WebSocket connections (WSS) with TLS encryption
- HTTPS for all API endpoints
- No plain-text audio transmission

### Data at Rest
- Encrypted storage for persistent memories
- SQLite database with file-level encryption
- No cloud storage of voice data

### Access Controls
- Local-only processing (no remote access)
- Session-based isolation
- Rate limiting prevents abuse

## Sensitive Content Handling

### Automatic Detection & Masking
- **Email addresses**: Replaced with `[EMAIL]`
- **Phone numbers**: Replaced with `[PHONE]`
- **Swedish personnummer**: Replaced with `[SSN]`
- **Credit card patterns**: Replaced with `[CARD]`

### Reduced Retention
- Detected sensitive content gets 24-hour TTL
- Cannot be stored in long-term memory
- Automatic purging even if within retention period

## Your Rights (GDPR Compliance)

### Right to Information
- This privacy policy explains our practices
- Technical documentation available on request

### Right of Access
- View all stored memories via API: `GET /api/privacy/status`
- Dashboard shows what Alice knows about you

### Right of Rectification
- Correct inaccurate memories via "glöm det där" + new input
- Manual memory editing via API

### Right to Erasure ("Right to be Forgotten")
- "Glöm det där" voice command for immediate deletion
- `POST /api/privacy/forget/all` for complete wipe
- Automatic expiration via TTL

### Right to Restrict Processing
- Mute button pauses all processing
- Hard mute stops system completely
- Granular controls per feature

### Right to Data Portability
- Export your memories: `GET /api/memories/export`
- JSON format for easy migration

### Right to Object
- Opt out of any data processing
- Disable ambient mode completely
- Use command-only mode instead

## Children's Privacy

Alice B3 is designed for adult users. We do not:
- Knowingly collect data from children under 13
- Process children's voices differently
- Store family conversation data indefinitely

If a child's voice is detected, apply stricter retention (24-hour max TTL).

## Changes to Privacy Policy

We will notify users of material changes by:
- Updating this document with new effective date
- Displaying notice in Alice interface
- Requiring acknowledgment for major changes

## Contact & Data Protection Officer

For privacy questions or requests:
- **Privacy Settings**: Available at `/api/privacy/status`
- **Data Deletion**: Use "glöm det där" voice command
- **Technical Issues**: Create issue at project repository

## Compliance Certifications

Alice B3 implements privacy-by-design principles:
- **Data Minimization**: Only store necessary information
- **Purpose Limitation**: Data used only for stated purposes
- **Accuracy**: Mechanisms to correct inaccurate data
- **Storage Limitation**: Automatic TTL and deletion
- **Integrity & Confidentiality**: Encryption and access controls
- **Accountability**: Transparent practices and audit logs

## Development & Testing

During development:
- Test data is automatically deleted
- No production voice data in test environments
- Developers cannot access user conversation data
- Audit logs track all data access

---

**Summary**: Alice B3 processes your voice to provide assistance, stores only important summaries with automatic expiration, gives you full control via "glöm det där" commands, and never shares your data with third parties (except OpenAI Whisper API for transcription only).

For immediate privacy action, say: **"Alice, glöm det där"**