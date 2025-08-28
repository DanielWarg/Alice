# 🔄 Token Rotation & Break Glass Procedures

**Comprehensive guide for managing API keys, tokens, and emergency access procedures**

---

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [🔑 Token Inventory](#-token-inventory)
- [🔄 Regular Rotation Procedures](#-regular-rotation-procedures)
- [🚨 Break Glass Emergency Procedures](#-break-glass-emergency-procedures)
- [🔐 Secure Storage Integration](#-secure-storage-integration)
- [📊 Monitoring & Alerting](#-monitoring--alerting)
- [🛠️ Automation Tools](#-automation-tools)
- [📞 Emergency Contacts](#-emergency-contacts)

---

## 🎯 Overview

### Why Token Rotation Matters

- **Security**: Minimize impact of compromised credentials
- **Compliance**: Meet security policy requirements
- **Access Control**: Maintain principle of least privilege
- **Audit Trail**: Track credential usage and changes

### Rotation Schedule

| Token Type | Rotation Frequency | Emergency Rotation | Owner |
|------------|-------------------|-------------------|--------|
| OpenAI API Keys | 90 days | Immediate | DevOps Team |
| Spotify Credentials | 180 days | 24 hours | Backend Team |
| Google OAuth | 365 days | 4 hours | Security Team |
| Session Secrets | 30 days | Immediate | Backend Team |
| Database Passwords | 90 days | 2 hours | Database Team |

---

## 🔑 Token Inventory

### 🤖 OpenAI API Keys

**Current Tokens**:
- `PROD_OPENAI_API_KEY`: Production voice/chat features
- `STAGING_OPENAI_API_KEY`: Staging environment testing
- `DEV_OPENAI_API_KEY`: Development and testing

**Usage**: Voice pipeline, chat completions, embeddings

**Rotation Impact**: 
- ⚠️ HIGH - Voice features will stop working
- Users will lose real-time voice capabilities
- Chat responses may degrade to local models

### 🎵 Spotify API Credentials

**Current Tokens**:
- `PROD_SPOTIFY_CLIENT_ID` + `PROD_SPOTIFY_CLIENT_SECRET`
- `STAGING_SPOTIFY_CLIENT_ID` + `STAGING_SPOTIFY_CLIENT_SECRET`
- `DEV_SPOTIFY_CLIENT_ID` + `DEV_SPOTIFY_CLIENT_SECRET`

**Usage**: Music control, playlist management, device discovery

**Rotation Impact**:
- 🟡 MEDIUM - Music features affected
- Users lose music control capabilities
- Existing sessions require re-authentication

### 📧 Google OAuth Credentials

**Current Tokens**:
- Calendar API credentials (`calendar_credentials.json`)
- Gmail API credentials (`gmail_credentials.json`)
- User refresh tokens (`calendar_token.pickle`, `gmail_token.pickle`)

**Usage**: Calendar integration, email management

**Rotation Impact**:
- 🟡 MEDIUM - Calendar/email features affected
- Users must re-authorize Google access
- Scheduled events may be missed

### 🔐 Session & Security Tokens

**Current Tokens**:
- `SESSION_SECRET`: Session encryption
- `CSRF_TOKEN`: Cross-site request forgery protection
- `JWT_SECRET`: JSON Web Token signing

**Usage**: User authentication, security

**Rotation Impact**:
- 🔴 HIGH - All users logged out
- Active sessions invalidated immediately
- Re-authentication required

---

## 🔄 Regular Rotation Procedures

### 🤖 OpenAI API Key Rotation

#### Monthly Rotation (Recommended)

```bash
#!/bin/bash
# rotate_openai_keys.sh

set -e

echo "🔄 Starting OpenAI API Key Rotation"

# 1. Generate new API key (manual step)
echo "1. Go to https://platform.openai.com/account/api-keys"
echo "2. Create new API key with name: alice-prod-$(date +%Y%m%d)"
echo "3. Copy the new key and enter below:"
read -s NEW_OPENAI_KEY

# 2. Validate new key
echo "🔍 Validating new API key..."
curl -s -H "Authorization: Bearer $NEW_OPENAI_KEY" \
     https://api.openai.com/v1/models > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ New API key is valid"
else
    echo "❌ New API key is invalid!"
    exit 1
fi

# 3. Update secure storage
echo "🔐 Updating secure storage..."
# Store in 1Password/Vault
op item edit "alice-openai-prod" password="$NEW_OPENAI_KEY"

# 4. Deploy to staging first
echo "🧪 Deploying to staging..."
kubectl set env deployment/alice-backend OPENAI_API_KEY="$NEW_OPENAI_KEY" -n staging

# 5. Wait and verify staging
echo "⏳ Waiting 2 minutes for staging verification..."
sleep 120

# 6. Test staging voice pipeline
echo "🧪 Testing staging voice features..."
curl -X POST "https://staging-api.your-domain.com/voice/test" \
     -H "Content-Type: application/json" \
     -d '{"test": "voice_pipeline"}'

# 7. Deploy to production if staging passes
read -p "✅ Staging tests passed. Deploy to production? (y/N): " confirm
if [ "$confirm" = "y" ]; then
    echo "🚀 Deploying to production..."
    kubectl set env deployment/alice-backend OPENAI_API_KEY="$NEW_OPENAI_KEY" -n production
    
    # 8. Monitor production for 10 minutes
    echo "📊 Monitoring production for 10 minutes..."
    sleep 600
    
    # 9. Revoke old key
    echo "🗑️ Old key can now be revoked manually at OpenAI dashboard"
    echo "🎉 OpenAI key rotation completed successfully!"
else
    echo "❌ Production deployment cancelled"
    exit 1
fi
```

### 🎵 Spotify Credentials Rotation

```bash
#!/bin/bash
# rotate_spotify_creds.sh

set -e

echo "🔄 Starting Spotify Credentials Rotation"

# 1. Create new Spotify app (manual)
echo "1. Go to https://developer.spotify.com/dashboard"
echo "2. Create new app: alice-prod-$(date +%Y%m%d)"
echo "3. Set redirect URI: https://your-domain.com/spotify/callback"
echo "4. Enter new Client ID and Secret:"
read -p "Client ID: " NEW_CLIENT_ID
read -s -p "Client Secret: " NEW_CLIENT_SECRET
echo

# 2. Update secure storage
op item edit "alice-spotify-prod" \
    CLIENT_ID="$NEW_CLIENT_ID" \
    CLIENT_SECRET="$NEW_CLIENT_SECRET"

# 3. Deploy with blue/green strategy
echo "🚀 Deploying new credentials..."
kubectl patch configmap alice-config \
    --patch='{"data":{"SPOTIFY_CLIENT_ID":"'$NEW_CLIENT_ID'","SPOTIFY_CLIENT_SECRET":"'$NEW_CLIENT_SECRET'"}}'

# 4. Restart pods to pick up new config
kubectl rollout restart deployment/alice-backend

# 5. Wait for rollout
kubectl rollout status deployment/alice-backend

# 6. Test Spotify integration
curl -X POST "https://api.your-domain.com/spotify/test" \
     -H "Content-Type: application/json" \
     -d '{"test": "auth_flow"}'

echo "✅ Spotify credentials rotation completed!"
echo "ℹ️ Users will need to re-authenticate with Spotify"
```

### 📧 Google OAuth Rotation

```bash
#!/bin/bash
# rotate_google_oauth.sh

set -e

echo "🔄 Starting Google OAuth Rotation"

# 1. Create new OAuth credentials (manual)
echo "1. Go to https://console.cloud.google.com/apis/credentials"
echo "2. Create new OAuth 2.0 Client ID"
echo "3. Download credentials JSON"
read -p "Path to new credentials file: " NEW_CREDS_FILE

# 2. Validate credentials file
if [ ! -f "$NEW_CREDS_FILE" ]; then
    echo "❌ Credentials file not found!"
    exit 1
fi

# 3. Update credentials in deployment
kubectl create secret generic alice-google-creds \
    --from-file=credentials.json="$NEW_CREDS_FILE" \
    --dry-run=client -o yaml | kubectl apply -f -

# 4. Restart services
kubectl rollout restart deployment/alice-backend

echo "✅ Google OAuth rotation completed!"
echo "⚠️ All users must re-authorize Google access"
```

---

## 🚨 Break Glass Emergency Procedures

### 🚨 When to Trigger Break Glass

- **Compromised API keys** detected in logs/monitoring
- **Unauthorized access** to user accounts
- **Data breach** involving Alice systems
- **Security vulnerability** requiring immediate action
- **Insider threat** or employee departure

### 🆘 Emergency Response Runbook

#### Immediate Response (0-15 minutes)

```bash
#!/bin/bash
# BREAK_GLASS_IMMEDIATE.sh
# Run this script immediately upon security incident

set -e

echo "🚨 BREAK GLASS PROCEDURE ACTIVATED"
echo "⏰ Started at: $(date)"

# 1. IMMEDIATELY disable all external integrations
echo "🛑 Step 1: Disabling external integrations..."

# Disable OpenAI by removing API key
kubectl patch secret alice-secrets \
    -p='{"data":{"OPENAI_API_KEY":""}}'

# Disable Spotify
kubectl patch secret alice-secrets \
    -p='{"data":{"SPOTIFY_CLIENT_ID":"","SPOTIFY_CLIENT_SECRET":""}}'

# 2. Invalidate all user sessions
echo "🔒 Step 2: Invalidating all user sessions..."
kubectl exec -it deployment/alice-backend -- \
    python -c "from memory import MemoryStore; MemoryStore().clear_all_sessions()"

# 3. Put Alice in maintenance mode
echo "🚧 Step 3: Enabling maintenance mode..."
kubectl patch configmap alice-config \
    -p='{"data":{"MAINTENANCE_MODE":"true"}}'

# 4. Scale down to minimum replicas
echo "📉 Step 4: Scaling down services..."
kubectl scale deployment alice-backend --replicas=1

# 5. Create incident ticket
echo "🎫 Step 5: Creating incident ticket..."
curl -X POST "https://your-ticketing-system.com/api/incidents" \
    -H "Authorization: Bearer $INCIDENT_API_TOKEN" \
    -d '{
        "title": "SECURITY INCIDENT - Alice Break Glass Activated",
        "priority": "P0",
        "description": "Break glass procedure activated at $(date)",
        "assignee": "security-team"
    }'

echo "✅ Immediate response completed"
echo "📞 Next: Call security team lead immediately"
echo "📋 Next: Run BREAK_GLASS_INVESTIGATE.sh"
```

#### Investigation Phase (15-60 minutes)

```bash
#!/bin/bash
# BREAK_GLASS_INVESTIGATE.sh

set -e

echo "🔍 Starting Security Investigation"

# 1. Capture system state
echo "📸 Capturing system state..."
mkdir -p /tmp/incident-$(date +%Y%m%d%H%M)
cd /tmp/incident-$(date +%Y%m%d%H%M)

# Export logs
kubectl logs deployment/alice-backend --since=24h > alice-backend.log
kubectl logs deployment/alice-frontend --since=24h > alice-frontend.log

# Database snapshot
kubectl exec -it deployment/alice-db -- \
    pg_dump alice > database-snapshot.sql

# Current configuration
kubectl get configmap alice-config -o yaml > current-config.yaml
kubectl get secret alice-secrets -o yaml > current-secrets.yaml

# 2. Check for indicators of compromise
echo "🕵️ Checking for compromise indicators..."

# Unusual API usage patterns
grep -i "unauthorized\|forbidden\|suspicious" alice-backend.log > suspicious-activity.log || true

# Failed authentication attempts
grep -i "auth.*failed\|login.*failed" alice-backend.log > failed-auth.log || true

# Unusual geographic access
grep -E "ip.*[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" alice-backend.log | \
    awk '{print $NF}' | sort | uniq -c | sort -nr > ip-analysis.txt

# 3. Generate investigation report
cat > investigation-report.md << EOF
# Security Incident Investigation Report

**Incident ID**: $(uuidgen)
**Started**: $(date)
**Investigator**: $(whoami)

## Timeline
- **$(date -u -d '1 hour ago')**: Suspicious activity first detected
- **$(date -u)**: Break glass procedure activated

## Evidence Collected
- System logs: alice-backend.log, alice-frontend.log
- Database snapshot: database-snapshot.sql
- Configuration state: current-config.yaml
- Suspicious activity: suspicious-activity.log
- Failed authentication: failed-auth.log
- IP analysis: ip-analysis.txt

## Next Steps
1. Analyze logs for root cause
2. Determine scope of compromise
3. Plan recovery procedures
4. Coordinate with legal/compliance teams

## Status: UNDER INVESTIGATION
EOF

echo "📄 Investigation report created: investigation-report.md"
echo "📧 Email incident-response@your-company.com with findings"
```

#### Recovery Phase (1-24 hours)

```bash
#!/bin/bash
# BREAK_GLASS_RECOVERY.sh

set -e

echo "🔧 Starting System Recovery"

read -p "Has investigation completed and recovery been approved? (y/N): " confirm
if [ "$confirm" != "y" ]; then
    echo "❌ Recovery not approved. Exiting."
    exit 1
fi

# 1. Rotate ALL credentials
echo "🔄 Step 1: Rotating all credentials..."
./rotate_openai_keys.sh
./rotate_spotify_creds.sh  
./rotate_google_oauth.sh

# Generate new session secrets
NEW_SESSION_SECRET=$(openssl rand -hex 32)
kubectl patch secret alice-secrets \
    -p='{"data":{"SESSION_SECRET":"'$(echo -n $NEW_SESSION_SECRET | base64)'"}}'

# 2. Update all user tokens
echo "🗝️ Step 2: Invalidating user tokens..."
kubectl exec -it deployment/alice-backend -- \
    python -c "
from core.calendar_service import CalendarService
from core.gmail_service import GmailService

# Force re-authentication for all users
CalendarService().revoke_all_tokens()
GmailService().revoke_all_tokens()
"

# 3. Enhanced security configuration
echo "🛡️ Step 3: Applying enhanced security..."
kubectl patch configmap alice-config \
    -p='{"data":{
        "ENABLE_SECURITY_HEADERS":"true",
        "RATE_LIMIT_REQUESTS":"30", 
        "RATE_LIMIT_WINDOW":"60",
        "SESSION_TIMEOUT":"900",
        "ENABLE_AUDIT_LOGGING":"true"
    }}'

# 4. Scale back up
echo "📈 Step 4: Scaling services back up..."
kubectl scale deployment alice-backend --replicas=3
kubectl scale deployment alice-frontend --replicas=2

# 5. Disable maintenance mode
echo "🟢 Step 5: Disabling maintenance mode..."
kubectl patch configmap alice-config \
    -p='{"data":{"MAINTENANCE_MODE":"false"}}'

# 6. Health checks
echo "🏥 Step 6: Running health checks..."
sleep 30

for i in {1..5}; do
    if curl -f -s https://api.your-domain.com/health; then
        echo "✅ Health check $i passed"
    else
        echo "❌ Health check $i failed"
        exit 1
    fi
    sleep 10
done

echo "🎉 System recovery completed successfully!"
echo "📧 Notify users of service restoration"
echo "📝 Complete post-incident review within 48 hours"
```

### 🔐 Emergency Contacts

| Role | Name | Phone | Email | Backup |
|------|------|-------|-------|--------|
| **Security Lead** | [Name] | [Phone] | security@company.com | [Backup] |
| **DevOps Lead** | [Name] | [Phone] | devops@company.com | [Backup] |
| **CTO** | [Name] | [Phone] | cto@company.com | [Backup] |
| **Legal** | [Name] | [Phone] | legal@company.com | [Backup] |

### 📞 Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| **P0 - Critical** | 15 minutes | Security Lead → CTO → CEO |
| **P1 - High** | 1 hour | DevOps Lead → Security Lead |  
| **P2 - Medium** | 4 hours | Team Lead → DevOps Lead |
| **P3 - Low** | 24 hours | Developer → Team Lead |

---

## 🔐 Secure Storage Integration

### 🗝️ 1Password Integration

```bash
#!/bin/bash
# Setup 1Password CLI for credential management

# Install 1Password CLI
curl -sSfO https://downloads.1password.com/linux/tar/stable/x86_64/op.tar.gz
tar -xzf op.tar.gz && sudo mv op /usr/local/bin/

# Setup Alice secrets vault
op vault create "Alice Secrets"

# Store production secrets
op item create --vault="Alice Secrets" --category="API Credential" \
    title="Alice OpenAI Production" \
    api_key="$PROD_OPENAI_API_KEY" \
    environment="production"

# Retrieve secrets in deployment
export OPENAI_API_KEY=$(op item get "Alice OpenAI Production" --field api_key)
```

### 🏦 HashiCorp Vault Integration

```bash
# Configure Vault integration
vault auth -method=aws
vault write secret/alice/prod/openai api_key="$PROD_OPENAI_API_KEY"

# Retrieve in Kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alice-backend
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "alice-prod"
        vault.hashicorp.com/agent-inject-secret-openai: "secret/alice/prod/openai"
```

---

## 📊 Monitoring & Alerting

### 🚨 Token Expiry Alerts

```yaml
# monitoring/token-alerts.yml
groups:
  - name: alice-tokens
    rules:
      - alert: OpenAITokenExpiry
        expr: (openai_token_expires_days < 30)
        for: 1d
        labels:
          severity: warning
        annotations:
          summary: "OpenAI API token expires in {{ $value }} days"
          description: "Rotate OpenAI token before expiry"

      - alert: SpotifyTokenExpiry  
        expr: (spotify_token_expires_days < 60)
        for: 1d
        labels:
          severity: warning
        annotations:
          summary: "Spotify token expires in {{ $value }} days"

      - alert: SessionSecretAge
        expr: (session_secret_age_days > 30)
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Session secret is {{ $value }} days old"
          description: "Rotate session secret immediately"
```

### 📈 Usage Monitoring

```python
# monitoring/token_monitor.py
import os
import requests
from prometheus_client import Gauge, Counter

# Metrics
openai_requests = Counter('openai_api_requests_total', 'Total OpenAI API requests')
openai_errors = Counter('openai_api_errors_total', 'OpenAI API errors')
token_age = Gauge('token_age_days', 'Age of tokens in days', ['token_type'])

def monitor_openai_usage():
    """Monitor OpenAI API usage and token health"""
    try:
        response = requests.get(
            'https://api.openai.com/v1/usage',
            headers={'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'}
        )
        
        if response.status_code == 200:
            openai_requests.inc()
            usage = response.json()
            
            # Check if approaching quota
            if usage.get('usage_percent', 0) > 90:
                send_alert("OpenAI quota approaching limit")
        else:
            openai_errors.inc()
            
    except Exception as e:
        openai_errors.inc()
        send_alert(f"OpenAI monitoring failed: {e}")

if __name__ == "__main__":
    monitor_openai_usage()
```

---

## 🛠️ Automation Tools

### 🔄 Automated Rotation Script

```python
#!/usr/bin/env python3
# automation/rotate_tokens.py

import os
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List

class TokenRotator:
    """Automated token rotation system"""
    
    def __init__(self):
        self.rotation_schedule = {
            'openai': {'days': 90, 'last_rotated': None},
            'spotify': {'days': 180, 'last_rotated': None},
            'session_secret': {'days': 30, 'last_rotated': None}
        }
    
    def check_rotation_needed(self, token_type: str) -> bool:
        """Check if token needs rotation"""
        config = self.rotation_schedule[token_type]
        if not config['last_rotated']:
            return True
            
        last_rotated = datetime.fromisoformat(config['last_rotated'])
        days_since = (datetime.now() - last_rotated).days
        
        return days_since >= config['days']
    
    def rotate_openai_token(self):
        """Rotate OpenAI API token"""
        print("🔄 Rotating OpenAI token...")
        
        # This would integrate with OpenAI API to create new token
        # For now, prompt for manual entry
        new_token = input("Enter new OpenAI API token: ")
        
        # Update 1Password
        subprocess.run([
            'op', 'item', 'edit', 'Alice OpenAI Production',
            f'api_key={new_token}'
        ])
        
        # Update Kubernetes secret
        subprocess.run([
            'kubectl', 'patch', 'secret', 'alice-secrets',
            f'-p={{"data":{{"OPENAI_API_KEY":"{self._base64_encode(new_token)}"}}}}'
        ])
        
        # Update rotation timestamp
        self.rotation_schedule['openai']['last_rotated'] = datetime.now().isoformat()
        self._save_schedule()
        
        print("✅ OpenAI token rotated successfully")
    
    def rotate_session_secret(self):
        """Rotate session encryption secret"""
        print("🔄 Rotating session secret...")
        
        # Generate new secret
        new_secret = subprocess.run(['openssl', 'rand', '-hex', '32'], 
                                  capture_output=True, text=True).stdout.strip()
        
        # Update Kubernetes secret
        subprocess.run([
            'kubectl', 'patch', 'secret', 'alice-secrets',
            f'-p={{"data":{{"SESSION_SECRET":"{self._base64_encode(new_secret)}"}}}}'
        ])
        
        # Restart pods to pick up new secret
        subprocess.run(['kubectl', 'rollout', 'restart', 'deployment/alice-backend'])
        
        # Update timestamp
        self.rotation_schedule['session_secret']['last_rotated'] = datetime.now().isoformat()
        self._save_schedule()
        
        print("✅ Session secret rotated successfully")
        print("⚠️ All user sessions have been invalidated")
    
    def _base64_encode(self, value: str) -> str:
        """Base64 encode a value"""
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def _save_schedule(self):
        """Save rotation schedule to file"""
        with open('/etc/alice/rotation_schedule.json', 'w') as f:
            json.dump(self.rotation_schedule, f, indent=2)
    
    def run_scheduled_rotation(self):
        """Run scheduled token rotation"""
        print("🔍 Checking for tokens needing rotation...")
        
        for token_type in self.rotation_schedule:
            if self.check_rotation_needed(token_type):
                print(f"⏰ {token_type} needs rotation")
                
                if token_type == 'openai':
                    self.rotate_openai_token()
                elif token_type == 'session_secret':
                    self.rotate_session_secret()
                # Add other token types as needed
        
        print("✅ Scheduled rotation check completed")

if __name__ == "__main__":
    rotator = TokenRotator()
    
    # Check if running in automated mode
    if '--auto' in sys.argv:
        rotator.run_scheduled_rotation()
    else:
        # Interactive mode
        print("Alice Token Rotation Tool")
        print("1. Check rotation status")
        print("2. Rotate OpenAI token")
        print("3. Rotate session secret")
        print("4. Run scheduled check")
        
        choice = input("Select option: ")
        
        if choice == '1':
            for token_type, config in rotator.rotation_schedule.items():
                needs_rotation = rotator.check_rotation_needed(token_type)
                status = "⚠️ NEEDS ROTATION" if needs_rotation else "✅ OK"
                print(f"{token_type}: {status}")
        
        elif choice == '2':
            rotator.rotate_openai_token()
        
        elif choice == '3':
            rotator.rotate_session_secret()
            
        elif choice == '4':
            rotator.run_scheduled_rotation()
```

### 📅 Cron Job Setup

```bash
# Setup automated token rotation
# /etc/cron.d/alice-token-rotation

# Check for token rotation daily at 2 AM
0 2 * * * alice python3 /opt/alice/automation/rotate_tokens.py --auto

# Weekly security audit
0 3 * * 0 alice /opt/alice/scripts/security_audit.sh

# Monthly break glass procedure test
0 4 1 * * alice /opt/alice/scripts/test_break_glass.sh --dry-run
```

---

## 📝 Documentation & Compliance

### 📊 Audit Trail

All token rotations must be logged with:

- **Timestamp**: When rotation occurred
- **Token Type**: Which credential was rotated  
- **Operator**: Who performed the rotation
- **Reason**: Scheduled or emergency rotation
- **Scope**: Which environments affected

### 📋 Compliance Checklist

- [ ] Token rotation schedule documented and followed
- [ ] Break glass procedures tested quarterly
- [ ] Emergency contacts list kept current
- [ ] Incident response times meet SLA requirements
- [ ] All rotations logged in audit system
- [ ] Regular security reviews conducted
- [ ] Staff trained on emergency procedures

### 🎓 Training Requirements

All team members must complete:

1. **Security Awareness Training** (Annual)
2. **Token Management Procedures** (Quarterly)  
3. **Break Glass Response Drill** (Quarterly)
4. **Incident Response Training** (Semi-annual)

---

**🚨 Emergency Hotline**: +1-XXX-XXX-XXXX  
**📧 Security Email**: security@your-company.com  
**🔗 Incident Portal**: https://incidents.your-company.com  

**Last Updated**: January 2025  
**Version**: 1.0  
**Next Review**: April 2025