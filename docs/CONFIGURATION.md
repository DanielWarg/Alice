# 🔧 Alice Configuration Guide

**Complete guide for configuring Alice AI Assistant across all environments**

---

## 📋 Table of Contents

- [🏗️ Environment Overview](#-environment-overview)
- [🔑 Core Configuration](#-core-configuration)
- [🌍 Environment-Specific Setup](#-environment-specific-setup)
- [🔒 Security Best Practices](#-security-best-practices)
- [🔄 Configuration Management](#-configuration-management)
- [📊 Monitoring & Validation](#-monitoring--validation)
- [🛠️ Troubleshooting](#-troubleshooting)

---

## 🏗️ Environment Overview

Alice supports three deployment environments, each with specific configuration requirements:

| Environment | Purpose | Security Level | Monitoring | Debug Features |
|-------------|---------|----------------|------------|----------------|
| **Development** | Local development & testing | Basic | Optional | Full debug enabled |
| **Staging** | Pre-production testing | High | Required | Limited debug |
| **Production** | Live user deployment | Maximum | Critical | Minimal debug |

---

## 🔑 Core Configuration

### Base Configuration Files

```bash
# Core configuration files
.env.example                 # Template with all options
.env                        # Active environment (never commit!)
.env.development            # Development overrides
.env.staging               # Staging overrides  
.env.production            # Production overrides
```

### Configuration Hierarchy

1. **Base defaults** from `.env.example`
2. **Environment file** (`.env.development`, `.env.staging`, `.env.production`)
3. **Local overrides** from `.env`
4. **Runtime environment variables**

---

## 🌍 Environment-Specific Setup

### 🛠️ Development Environment

**File: `.env.development`**

```bash
# =============================================================================
# ALICE DEVELOPMENT ENVIRONMENT
# =============================================================================

# Environment identification
ENVIRONMENT=development
NODE_ENV=development
PYTHON_ENV=development

# =============================================================================
# API KEYS & INTEGRATIONS (Development)
# =============================================================================

# OpenAI (Development API key - separate from production)
OPENAI_API_KEY=sk-proj-dev-your-development-key-here
OPENAI_MODEL=gpt-4o-mini                     # Cost-effective for dev

# Spotify (Development app credentials)
SPOTIFY_CLIENT_ID=dev_spotify_client_id
SPOTIFY_CLIENT_SECRET=dev_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:3000/spotify/callback

# Google Services (Development project)
GOOGLE_CALENDAR_CREDENTIALS_PATH=server/dev_calendar_credentials.json
GOOGLE_GMAIL_CREDENTIALS_PATH=server/dev_gmail_credentials.json

# =============================================================================
# FEATURE FLAGS & DEBUGGING
# =============================================================================

# Debug features enabled
DEBUG_MODE=true
VOICE_DEBUG=true
PROFILE_PERFORMANCE=true
SHOW_DEBUG_INFO=true

# Development-friendly settings
LOG_LEVEL=debug
STRUCTURED_LOGS=true
LOG_FILE=logs/alice-dev.log

# Demo and testing features
ENABLE_DEMO_MODE=true
ENABLE_FIRST_RUN_TOUR=true

# =============================================================================
# VOICE PIPELINE (Development)
# =============================================================================

# Full voice pipeline for testing
VOICE_PIPELINE_MODE=dual
ENABLE_WEBRTC=true
TTS_CACHE_SIZE=100                           # Smaller cache for dev

# Swedish models (development)
STT_MODEL=whisper
TTS_MODEL=piper
PIPER_VOICE=sv_SE-nst-medium

# =============================================================================
# BACKEND CONFIGURATION
# =============================================================================

# Development server settings
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3100

# Database (local SQLite)
DATABASE_URL=sqlite:///data/alice-dev.db
ENABLE_MEMORY_PERSISTENCE=true
MEMORY_RETENTION_DAYS=7                      # Shorter retention for dev

# =============================================================================
# FRONTEND (Next.js)
# =============================================================================

NEXT_PUBLIC_VOICE_MODE=dual
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_ENABLE_ANALYTICS=false

# =============================================================================
# SECURITY (Development)
# =============================================================================

# Relaxed security for development
ENABLE_RATE_LIMITING=false
ENABLE_SECURITY_HEADERS=false
SESSION_SECRET=dev-session-secret-change-in-prod

# =============================================================================
# MONITORING (Optional for dev)
# =============================================================================

ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_ERROR_REPORTING=false
```

### 🧪 Staging Environment

**File: `.env.staging`**

```bash
# =============================================================================
# ALICE STAGING ENVIRONMENT
# =============================================================================

# Environment identification
ENVIRONMENT=staging
NODE_ENV=production
PYTHON_ENV=staging

# =============================================================================
# API KEYS & INTEGRATIONS (Staging)
# =============================================================================

# OpenAI (Staging API key)
OPENAI_API_KEY=sk-proj-staging-your-staging-key-here
OPENAI_MODEL=gpt-4o-mini                     # Cost-effective for staging

# Spotify (Staging app credentials)
SPOTIFY_CLIENT_ID=staging_spotify_client_id
SPOTIFY_CLIENT_SECRET=staging_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://staging.your-domain.com/spotify/callback

# Google Services (Staging project)
GOOGLE_CALENDAR_CREDENTIALS_PATH=server/staging_calendar_credentials.json
GOOGLE_GMAIL_CREDENTIALS_PATH=server/staging_gmail_credentials.json

# =============================================================================
# FEATURE FLAGS & DEBUGGING
# =============================================================================

# Limited debug features
DEBUG_MODE=false
VOICE_DEBUG=false
PROFILE_PERFORMANCE=true                     # Keep performance monitoring
SHOW_DEBUG_INFO=false

# Production-like logging
LOG_LEVEL=info
STRUCTURED_LOGS=true
LOG_FILE=logs/alice-staging.log

# Testing features
ENABLE_DEMO_MODE=true                        # Allow demo mode in staging
ENABLE_FIRST_RUN_TOUR=false

# =============================================================================
# VOICE PIPELINE (Staging)
# =============================================================================

# Optimized voice pipeline
VOICE_PIPELINE_MODE=voiceclient
ENABLE_WEBRTC=true
TTS_CACHE_SIZE=500                           # Medium cache size

# Swedish models (production-ready)
STT_MODEL=whisper
TTS_MODEL=piper
PIPER_VOICE=sv_SE-nst-medium

# =============================================================================
# BACKEND CONFIGURATION
# =============================================================================

# Staging server settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://staging.your-domain.com

# Database (staging)
DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/alice_staging
ENABLE_MEMORY_PERSISTENCE=true
MEMORY_RETENTION_DAYS=14

# =============================================================================
# FRONTEND (Next.js)
# =============================================================================

NEXT_PUBLIC_VOICE_MODE=voiceclient
NEXT_PUBLIC_ALICE_BACKEND_URL=https://staging-api.your-domain.com
NEXT_PUBLIC_ENABLE_ANALYTICS=true

# =============================================================================
# SECURITY (Staging - Production-like)
# =============================================================================

# Production security settings
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
ENABLE_SECURITY_HEADERS=true
SESSION_SECRET=${STAGING_SESSION_SECRET}      # From secure storage

# =============================================================================
# MONITORING (Required for staging)
# =============================================================================

ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30
ENABLE_ERROR_REPORTING=true
SENTRY_DSN=${STAGING_SENTRY_DSN}             # From secure storage
```

### 🚀 Production Environment

**File: `.env.production`**

```bash
# =============================================================================
# ALICE PRODUCTION ENVIRONMENT
# =============================================================================

# Environment identification
ENVIRONMENT=production
NODE_ENV=production
PYTHON_ENV=production

# =============================================================================
# API KEYS & INTEGRATIONS (Production)
# =============================================================================

# OpenAI (Production API key - high usage limits)
OPENAI_API_KEY=${PROD_OPENAI_API_KEY}        # From secure storage
OPENAI_MODEL=gpt-4o                          # Best quality for production

# Spotify (Production app credentials)
SPOTIFY_CLIENT_ID=${PROD_SPOTIFY_CLIENT_ID}
SPOTIFY_CLIENT_SECRET=${PROD_SPOTIFY_CLIENT_SECRET}
SPOTIFY_REDIRECT_URI=https://your-domain.com/spotify/callback

# Google Services (Production project)
GOOGLE_CALENDAR_CREDENTIALS_PATH=server/prod_calendar_credentials.json
GOOGLE_GMAIL_CREDENTIALS_PATH=server/prod_gmail_credentials.json

# =============================================================================
# FEATURE FLAGS & DEBUGGING
# =============================================================================

# No debug features in production
DEBUG_MODE=false
VOICE_DEBUG=false
PROFILE_PERFORMANCE=false
SHOW_DEBUG_INFO=false

# Minimal logging
LOG_LEVEL=warning
STRUCTURED_LOGS=true
LOG_FILE=logs/alice-prod.log

# Production features only
ENABLE_DEMO_MODE=false
ENABLE_FIRST_RUN_TOUR=true                   # For new users

# =============================================================================
# VOICE PIPELINE (Production)
# =============================================================================

# Optimized voice pipeline
VOICE_PIPELINE_MODE=voiceclient
ENABLE_WEBRTC=true
TTS_CACHE_SIZE=2000                          # Large cache for production

# Swedish models (highest quality)
STT_MODEL=whisper
TTS_MODEL=openai                             # Best quality TTS
PIPER_VOICE=sv_SE-nst-high                   # Fallback voice

# =============================================================================
# BACKEND CONFIGURATION
# =============================================================================

# Production server settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://your-domain.com

# Database (production)
DATABASE_URL=${PROD_DATABASE_URL}            # From secure storage
ENABLE_MEMORY_PERSISTENCE=true
MEMORY_RETENTION_DAYS=90                     # Longer retention for prod

# =============================================================================
# FRONTEND (Next.js)
# =============================================================================

NEXT_PUBLIC_VOICE_MODE=voiceclient
NEXT_PUBLIC_ALICE_BACKEND_URL=https://api.your-domain.com
NEXT_PUBLIC_ENABLE_ANALYTICS=true

# =============================================================================
# SECURITY (Maximum)
# =============================================================================

# Maximum security settings
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=60                       # Stricter limits
RATE_LIMIT_WINDOW=60
ENABLE_SECURITY_HEADERS=true
SESSION_SECRET=${PROD_SESSION_SECRET}        # From secure storage

# Additional security
CSP_REPORT_URI=https://your-domain.com/csp-report
SESSION_TIMEOUT=1800                         # 30 minutes

# =============================================================================
# MONITORING (Critical)
# =============================================================================

ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=15                     # More frequent checks
ENABLE_ERROR_REPORTING=true
SENTRY_DSN=${PROD_SENTRY_DSN}               # From secure storage

# Performance monitoring
PERFORMANCE_MONITORING=true
ALERT_THRESHOLDS=true
```

---

## 🔒 Security Best Practices

### 🔑 Credential Management

#### Separate Credentials by Environment

```bash
# ❌ NEVER do this (shared credentials)
OPENAI_API_KEY=sk-proj-shared-across-all-envs

# ✅ DO this (separate credentials)
# Development
OPENAI_API_KEY=sk-proj-dev-key-for-development-only

# Staging  
OPENAI_API_KEY=sk-proj-staging-key-for-testing-only

# Production
OPENAI_API_KEY=sk-proj-prod-key-for-live-users-only
```

#### Environment Variable Sources

| Environment | Source | Example |
|-------------|--------|---------|
| Development | Local `.env` file | Manual entry |
| Staging | CI/CD secrets | GitHub Secrets |
| Production | Secure vault | 1Password/Vault |

### 🛡️ Security Configuration Matrix

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Rate Limiting | Disabled | Enabled | Strict |
| Security Headers | Optional | Enabled | Required |
| Debug Mode | Full | Limited | None |
| Error Reporting | Console | Limited | Full |
| Session Timeout | Long | Medium | Short |
| CORS Origins | Permissive | Restricted | Strict |

### 🔐 Google OAuth Setup

#### Development Setup
```bash
# 1. Create Google Cloud Project (dev)
gcloud projects create alice-dev-project

# 2. Enable APIs
gcloud services enable calendar-json.googleapis.com
gcloud services enable gmail-json.googleapis.com

# 3. Create OAuth credentials
# - Web application
# - Redirect URI: http://localhost:3000/auth/callback
# - Download credentials to server/dev_calendar_credentials.json
```

#### Staging/Production Setup
```bash
# Separate projects for each environment
gcloud projects create alice-staging-project
gcloud projects create alice-prod-project

# Different redirect URIs
# Staging: https://staging.your-domain.com/auth/callback  
# Production: https://your-domain.com/auth/callback
```

---

## 🔄 Configuration Management

### 📁 File Structure

```
alice/
├── .env.example              # Template (committed)
├── .env                      # Active config (never commit)
├── .env.development         # Dev defaults (committed)
├── .env.staging            # Staging defaults (committed) 
├── .env.production         # Prod defaults (committed)
├── server/
│   ├── dev_calendar_credentials.json      # Dev OAuth (never commit)
│   ├── staging_calendar_credentials.json  # Staging OAuth (never commit)
│   └── prod_calendar_credentials.json     # Prod OAuth (never commit)
└── docs/
    └── CONFIGURATION.md     # This file
```

### 🔄 Configuration Loading Order

1. **Base template**: `.env.example` values
2. **Environment defaults**: `.env.{environment}` 
3. **Local overrides**: `.env` file
4. **System environment**: Runtime variables

### 🧰 Configuration Validation

```bash
# Validate configuration for each environment
make validate-config ENV=development
make validate-config ENV=staging  
make validate-config ENV=production
```

### 📋 Configuration Checklist

#### Pre-deployment Checklist

- [ ] All required environment variables set
- [ ] API keys are environment-specific (not shared)
- [ ] Database connections use correct endpoints
- [ ] CORS origins match deployment URLs
- [ ] Security settings appropriate for environment
- [ ] Logging levels configured correctly
- [ ] Monitoring and alerting enabled
- [ ] Backup configurations in place

---

## 📊 Monitoring & Validation

### 🏥 Health Checks

```bash
# Development
curl http://localhost:8000/health

# Staging  
curl https://staging-api.your-domain.com/health

# Production
curl https://api.your-domain.com/health
```

### 📈 Configuration Metrics

Monitor these configuration-related metrics:

- **API Key Usage**: Track OpenAI/Spotify API consumption
- **Authentication Success Rate**: OAuth flow completion
- **Environment Variable Coverage**: Missing configurations
- **Security Header Compliance**: Security policy adherence

### 🚨 Alerting Thresholds

| Metric | Development | Staging | Production |
|--------|-------------|---------|------------|
| API Errors | > 50% | > 20% | > 5% |
| Response Time | > 5s | > 2s | > 1s |
| Memory Usage | > 80% | > 70% | > 60% |
| API Key Quota | > 90% | > 80% | > 70% |

---

## 🛠️ Troubleshooting

### Common Configuration Issues

#### 1. Missing Environment Variables

**Error**: `Environment variable OPENAI_API_KEY is not set`

**Solution**:
```bash
# Check current environment
echo $ENVIRONMENT

# Verify variable exists
echo $OPENAI_API_KEY

# Load correct environment file
cp .env.development .env
```

#### 2. Wrong API Endpoints

**Error**: `Connection refused to localhost:8000`

**Solution**: Check environment-specific URLs
```bash
# Development
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000

# Staging
NEXT_PUBLIC_ALICE_BACKEND_URL=https://staging-api.your-domain.com

# Production  
NEXT_PUBLIC_ALICE_BACKEND_URL=https://api.your-domain.com
```

#### 3. OAuth Redirect Mismatch

**Error**: `redirect_uri_mismatch`

**Solution**: Verify redirect URIs match Google Cloud Console:
```bash
# Development
SPOTIFY_REDIRECT_URI=http://localhost:3000/spotify/callback

# Production
SPOTIFY_REDIRECT_URI=https://your-domain.com/spotify/callback
```

### 🔍 Debug Commands

```bash
# Check all environment variables
printenv | grep -E "(OPENAI|SPOTIFY|ALICE|NODE_ENV)"

# Validate configuration files
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.development')
print(f'Environment: {os.getenv(\"ENVIRONMENT\")}')
print(f'OpenAI Key: {os.getenv(\"OPENAI_API_KEY\", \"NOT SET\")[:10]}...')
"

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

### 📞 Getting Help

- **Configuration Issues**: Check `TROUBLESHOOTING.md`
- **API Problems**: Check individual service documentation
- **Security Questions**: Review `SECURITY.md`
- **Deployment Issues**: Check `DEPLOYMENT.md`

---

## 🎯 Quick Start Commands

### Development Setup
```bash
cp .env.example .env
cp .env.development .env.local
# Edit with your development keys
make dev
```

### Staging Deployment
```bash
cp .env.staging .env
# Set staging secrets via CI/CD
make deploy ENV=staging
```

### Production Deployment
```bash
cp .env.production .env  
# Set production secrets via vault
make deploy ENV=production
```

---

**Last Updated**: January 2025  
**Version**: 1.0  
**Maintainer**: Alice Development Team

For the most up-to-date configuration information, see the `.env.example` file in the repository root.