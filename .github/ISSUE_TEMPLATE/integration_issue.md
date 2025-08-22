---
name: 🔗 Integration Issue
about: Report problems with API integrations (Google, Spotify, OpenAI, etc.)
title: '[INTEGRATION] '
labels: ['integration', 'api', 'needs-triage']
assignees: ''
---

## 🔗 Integration Issue Summary
A clear description of the integration problem you're experiencing.

## 🎯 Affected Integration
- [ ] 📅 **Google Calendar** - Calendar events and scheduling
- [ ] 📧 **Gmail** - Email management and search
- [ ] 🎵 **Spotify** - Music control and playlists
- [ ] 🧠 **OpenAI API** - AI features and voice processing
- [ ] 🤖 **Ollama** - Local AI model integration
- [ ] 🔧 **Custom API** - User-defined integrations
- [ ] 🌐 **WebRTC** - Real-time communication
- [ ] 📄 **Document RAG** - Document processing and retrieval
- [ ] 🏠 **IoT/Smart Home** - Connected devices (if applicable)

## 🚨 Issue Type
- [ ] 🔑 **Authentication** - Login, tokens, or permissions
- [ ] 📡 **API Connection** - Cannot connect to service
- [ ] 📊 **Data Retrieval** - Cannot fetch data from service
- [ ] 📝 **Data Sync** - Data not updating or syncing
- [ ] ⚡ **Rate Limiting** - Too many requests or throttling
- [ ] 🔒 **Permissions** - Insufficient access rights
- [ ] 📈 **Timeout** - Requests taking too long
- [ ] 🔄 **Refresh/Renewal** - Token or session refresh issues
- [ ] 🇸🇪 **Localization** - Swedish language/region issues

## 🔑 Authentication Details

### API Credentials Status
- [ ] API key/credentials configured
- [ ] OAuth flow completed successfully
- [ ] Tokens are valid and not expired
- [ ] Correct scopes/permissions requested

### Credentials Configuration
**Service:** ___________
**Authentication Type:** [API Key/OAuth 2.0/Service Account/Basic Auth]
**Scopes Requested:** ___________
**Token Expiry:** [Valid/Expired/Unknown]

## 📡 API Connection Details

### Service Information
**Service Name:** ___________
**API Version:** ___________
**Endpoint URL:** ___________
**Request Method:** [GET/POST/PUT/DELETE]

### Error Response
```json
{
  "error": "paste the actual API error response here"
}
```

### Request Details
**HTTP Status Code:** ___________
**Response Time:** ___________
**Request Headers:** [Included/Missing/Incorrect]
**Request Body:** [Valid/Invalid/Empty]

## 🔧 Configuration Details

### Environment Variables
```bash
# Please mask sensitive values with ***
SERVICE_API_KEY=***
SERVICE_CLIENT_ID=***
SERVICE_CLIENT_SECRET=***
# Add other relevant env vars
```

### Alice Configuration
**Integration Enabled:** [Yes/No]
**Configuration File:** [Found/Missing/Incorrect]
**Service Account File:** [Found/Missing/Incorrect]

## 🧪 Testing & Reproduction

### Steps to Reproduce
1. 
2. 
3. 

### Expected Behavior
What should happen when the integration works correctly:

### Actual Behavior
What actually happens:

### Voice Commands (if applicable)
**Swedish command used:** ___________
**Expected action:** ___________
**Actual result:** ___________

## 🇸🇪 Swedish Localization Issues
If this affects Swedish language or regional settings:
**Service Language:** [Swedish/English/Auto]
**Date/Time Format:** [Swedish/International]
**Regional Settings:** [Sweden/Other]
**Timezone:** [Europe/Stockholm/Other]

## 📊 Service-Specific Details

### Google Calendar (if applicable)
**Calendar Access:** [Read/Write/Both]
**Calendar Selection:** [Primary/Specific/All]
**Event Types:** [Regular/Recurring/All-day]
**Timezone Handling:** [Working/Broken]

### Gmail (if applicable)
**Mailbox Access:** [Read/Modify/Full]
**Search Functionality:** [Working/Broken]
**Label Management:** [Working/Broken]
**Thread Handling:** [Working/Broken]

### Spotify (if applicable)
**Premium Account:** [Yes/No]
**Device Control:** [Working/Broken]
**Playlist Access:** [Working/Broken]
**Search Functionality:** [Working/Broken]

### OpenAI API (if applicable)
**Model Used:** [gpt-4/gpt-3.5-turbo/whisper/tts]
**Feature Type:** [Chat/Voice/TTS/STT]
**Usage Limits:** [Within/Exceeded/Unknown]
**Response Quality:** [Good/Poor/Inconsistent]

### Ollama (if applicable)
**Model Name:** [gpt-oss:20b/Other]
**Model Status:** [Running/Stopped/Error]
**Memory Usage:** [Normal/High/Critical]
**Response Time:** [Fast/Slow/Timeout]

## 🌐 Network & Infrastructure

### Connection Details
**Network Type:** [WiFi/Ethernet/Mobile]
**Behind Firewall:** [Yes/No]
**Proxy Settings:** [None/HTTP/SOCKS]
**VPN Active:** [Yes/No]

### Service Availability
**Service Status:** [Online/Down/Degraded]
**Geographic Region:** [Sweden/EU/Global]
**CDN Issues:** [None/Suspected/Confirmed]

## 📝 Logs & Debug Information

### Alice Server Logs
```
Please paste relevant server logs here
```

### Browser Console
```
Please paste relevant browser console output
```

### Network Requests
```
Please paste relevant network request/response data (mask sensitive info)
```

## 🔧 Troubleshooting Attempted
- [ ] Restarted Alice server
- [ ] Refreshed browser/cleared cache
- [ ] Re-authenticated with service
- [ ] Checked service status page
- [ ] Verified credentials/API keys
- [ ] Tested with different account
- [ ] Checked firewall/network settings
- [ ] Reviewed API documentation
- [ ] Tested integration directly (outside Alice)

## ⚡ Performance Impact
**Response Time:** [Fast <1s/Normal 1-3s/Slow >3s/Timeout]
**CPU Usage:** [Normal/High during requests]
**Memory Usage:** [Normal/High during requests]
**Error Frequency:** [Always/Often/Sometimes/Rare]

## 🔄 Retry Behavior
**Automatic Retries:** [Working/Not working/Too many]
**Retry Strategy:** [Exponential backoff/Fixed interval/None]
**Circuit Breaker:** [Open/Closed/Half-open]

## 📱 Environment Information
**Alice Version:** ___________
**OS:** ___________
**Python Version:** ___________
**FastAPI Version:** ___________
**Requests Library Version:** ___________

## 🎯 Business Impact
**Affected Functionality:** ___________
**User Experience Impact:** [Critical/High/Medium/Low]
**Workaround Available:** [Yes/No]

## 📚 Additional Resources
**Service Documentation:** ___________
**Error Code References:** ___________
**Related Issues:** ___________

## ✅ Verification Checklist
- [ ] API credentials are correctly configured
- [ ] Service is operational (checked status page)
- [ ] Network connectivity is stable
- [ ] Alice has necessary permissions
- [ ] Integration worked previously
- [ ] Tested with minimal reproduction case
- [ ] Logs have been collected and reviewed