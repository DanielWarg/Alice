# 🚀 Alice Hybrid System Operations Guide

**Complete operations manual for Alice's hybrid AI architecture - monitoring, troubleshooting, and maintaining the perfect balance between OpenAI Realtime and local AI processing.**

> **🇸🇪 Svenska:** [sv/OPERATIONS.md](sv/OPERATIONS.md) - Full Swedish version available

---

## 📋 Table of Contents

- [🎯 Operations Overview](#-operations-overview)
- [📊 Monitoring Hybrid Systems](#-monitoring-hybrid-systems)
- [🔍 Troubleshooting Guide](#-troubleshooting-guide)
- [⚡ Performance Optimization](#-performance-optimization)
- [🔒 Security Operations](#-security-operations)
- [💰 Cost Management](#-cost-management)
- [🆘 Emergency Procedures](#-emergency-procedures)
- [📈 Capacity Planning](#-capacity-planning)

---

## 🎯 Operations Overview

Alice's hybrid architecture requires monitoring both cloud services (OpenAI Realtime API) and local infrastructure (gpt-oss:20B, voice processing, tools). This guide covers operational best practices for maintaining optimal performance, cost efficiency, and user experience.

### Key Operational Metrics

| Component | Primary Metrics | Target Values | Alert Thresholds |
|-----------|----------------|---------------|-----------------|
| **Intent Routing** | Classification latency, accuracy | <50ms, >90% | >100ms, <85% |
| **Fast Path (OpenAI)** | Response latency, error rate | <300ms, <1% | >500ms, >5% |
| **Think Path (Local)** | Processing time, queue depth | <2000ms, <5 | >5000ms, >20 |
| **Voice Gateway** | Connection stability, audio quality | >99%, >8/10 | <95%, <6/10 |
| **Tool Execution** | Success rate, execution time | >95%, <1000ms | <90%, >3000ms |

---

## 📊 Monitoring Hybrid Systems

### Real-Time Dashboards

#### 1. Hybrid Performance Dashboard
```yaml
# Grafana dashboard configuration
- title: "Alice Hybrid Performance"
  panels:
    - name: "Intent Routing Latency"
      query: "histogram_quantile(0.95, intent_routing_latency_ms)"
      thresholds: [50ms, 100ms]
    
    - name: "Fast vs Think Path Usage"
      query: "rate(fast_path_requests[5m]) / rate(total_requests[5m])"
      target: 60% # Optimal fast path usage
    
    - name: "OpenAI API Health"
      query: "openai_api_success_rate"
      thresholds: [95%, 99%]
    
    - name: "Local AI Performance"
      query: "histogram_quantile(0.95, local_ai_response_time_ms)"
      thresholds: [2000ms, 5000ms]
```

#### 2. Cost Optimization Dashboard
```yaml
- title: "Alice Cost Analysis"
  panels:
    - name: "OpenAI API Costs (Daily)"
      query: "increase(openai_api_cost_usd[1d])"
      
    - name: "Cost per User Session"
      query: "openai_api_cost_usd / active_sessions"
      
    - name: "Fast Path Efficiency"
      query: "(fast_path_requests / total_requests) * 100"
      target: "60-70%" # Optimal cost/performance balance
```

### Monitoring Commands

#### System Health Check
```bash
#!/bin/bash
# health_check.sh - Complete Alice system health verification

echo "🔍 Alice Hybrid System Health Check"
echo "=================================="

# Check OpenAI API connectivity
echo "☁️  Checking OpenAI Realtime API..."
if curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
   "https://api.openai.com/v1/models" > /dev/null; then
    echo "✅ OpenAI API: Connected"
else
    echo "❌ OpenAI API: Connection failed"
fi

# Check local AI (Ollama)
echo "🏠 Checking local AI (gpt-oss:20B)..."
if curl -s "http://localhost:11434/api/tags" | grep -q "gpt-oss:20b"; then
    echo "✅ Local AI: Model loaded and ready"
else
    echo "❌ Local AI: Model not available"
fi

# Check voice gateway
echo "🎤 Checking voice gateway..."
if curl -s "http://localhost:8001/health" > /dev/null; then
    echo "✅ Voice Gateway: Running"
else
    echo "❌ Voice Gateway: Not responding"
fi

# Check backend health
echo "⚙️  Checking Alice backend..."
health_response=$(curl -s "http://localhost:8000/api/health")
if echo "$health_response" | grep -q '"status":"healthy"'; then
    echo "✅ Backend: Healthy"
else
    echo "❌ Backend: Issues detected"
fi

# Performance metrics
echo "📊 Current Performance Metrics:"
echo "$(curl -s 'http://localhost:9090/api/v1/query?query=intent_routing_latency_ms' | jq -r '.data.result[0].value[1]') ms - Intent routing latency"
echo "$(curl -s 'http://localhost:9090/api/v1/query?query=rate(fast_path_requests[5m])' | jq -r '.data.result[0].value[1]') req/min - Fast path usage"
```

#### Real-Time Monitoring
```bash
# monitor.sh - Real-time Alice system monitoring
watch -n 5 '
echo "🎯 Alice Hybrid Monitoring - $(date)";
echo "=====================================";
echo "Intent Router:";
echo "  Latency (95th): $(curl -s "localhost:9090/api/v1/query?query=histogram_quantile(0.95,intent_routing_latency_ms)" | jq -r ".data.result[0].value[1]")ms";
echo "  Accuracy: $(curl -s "localhost:9090/api/v1/query?query=intent_classification_accuracy" | jq -r ".data.result[0].value[1]")";
echo "";
echo "OpenAI Fast Path:";
echo "  Success Rate: $(curl -s "localhost:9090/api/v1/query?query=rate(openai_api_success[5m])" | jq -r ".data.result[0].value[1]")";
echo "  Response Time: $(curl -s "localhost:9090/api/v1/query?query=histogram_quantile(0.95,openai_response_latency_ms)" | jq -r ".data.result[0].value[1]")ms";
echo "";
echo "Local Think Path:";
echo "  Queue Depth: $(curl -s "localhost:9090/api/v1/query?query=local_ai_queue_depth" | jq -r ".data.result[0].value[1]")";
echo "  Processing Time: $(curl -s "localhost:9090/api/v1/query?query=histogram_quantile(0.95,local_ai_processing_time_ms)" | jq -r ".data.result[0].value[1]")ms";
'
```

---

## 🔍 Troubleshooting Guide

### Common Issues and Solutions

#### 1. High OpenAI API Latency (>500ms)

**Symptoms:**
- Slow voice responses for simple queries
- User complaints about delayed interactions
- Fast path metrics showing high latency

**Diagnosis:**
```bash
# Check OpenAI API status
curl -w "%{time_total}ms" -s "https://status.openai.com/api/v2/status.json"

# Test direct API latency
time curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-realtime-preview-2024-10-01", "messages": [{"role": "user", "content": "test"}]}' \
  "https://api.openai.com/v1/chat/completions"

# Check network path
traceroute api.openai.com
```

**Solutions:**
1. **Immediate:** Increase fast path timeout from 300ms to 500ms
2. **Short-term:** Route more requests to Think Path (local AI)
3. **Long-term:** Implement geographic API routing or CDN

**Configuration Changes:**
```bash
# Temporary mitigation - route more to local
export FAST_PATH_THRESHOLD=0.95  # Increase confidence threshold
export FAST_RESPONSE_TIMEOUT_MS=500  # Increase timeout

# Restart services
docker-compose restart alice-voice-gateway
```

#### 2. Local AI Performance Degradation

**Symptoms:**
- Think path responses taking >5000ms
- High CPU usage on local machine
- Users experiencing delays on complex queries

**Diagnosis:**
```bash
# Check Ollama performance
curl -X POST "http://localhost:11434/api/generate" \
  -d '{"model": "gpt-oss:20b", "prompt": "test", "stream": false}' \
  -w "Time: %{time_total}s\n"

# Monitor system resources
htop
nvidia-smi  # If using GPU

# Check model memory usage
curl "http://localhost:11434/api/ps"
```

**Solutions:**
1. **Immediate:** Increase local AI timeout, scale down complex requests
2. **Short-term:** Optimize model parameters, add memory
3. **Long-term:** Implement model quantization or upgrade hardware

#### 3. Intent Classification Accuracy Drop (<85%)

**Symptoms:**
- Wrong routing decisions (complex queries to fast path, simple to think path)
- User frustration with incorrect responses
- Increased API costs due to misrouting

**Diagnosis:**
```bash
# Run accuracy benchmark
cd tests && python test_intent_accuracy.py --gold-set nlu_sv.jsonl

# Check recent classification logs
tail -f logs/intent_router.log | grep "confidence.*0\.[0-7]"

# Analyze routing patterns
curl "localhost:9090/api/v1/query?query=rate(fast_path_requests[1h])/rate(total_requests[1h])"
```

**Solutions:**
1. **Immediate:** Lower confidence threshold temporarily
2. **Short-term:** Retrain classification model with recent data
3. **Long-term:** Implement adaptive classification with user feedback

#### 4. WebSocket Connection Issues

**Symptoms:**
- Voice gateway disconnections
- Audio streaming failures
- HUD not updating in real-time

**Diagnosis:**
```bash
# Test WebSocket connectivity
wscat -c "ws://localhost:8001/ws/voice/test"

# Check connection pool status
curl "http://localhost:8001/api/connections/status"

# Monitor WebSocket metrics
curl "localhost:9090/api/v1/query?query=websocket_connections_active"
```

**Solutions:**
1. **Immediate:** Restart voice gateway, check firewall settings
2. **Short-term:** Increase connection pool size, tune timeouts
3. **Long-term:** Implement connection health checks and auto-recovery

---

## ⚡ Performance Optimization

### Response Time Optimization

#### Fast Path Optimization
```yaml
# Optimal OpenAI configuration for speed
openai_settings:
  model: "gpt-4o-realtime-preview-2024-10-01"
  max_tokens: 150  # Limit for fast responses
  temperature: 0.3  # Lower for consistency
  timeout_ms: 300  # Strict timeout
  
  # Connection optimization
  connection_pool_size: 10
  keep_alive: true
  http_version: "2.0"
```

#### Think Path Optimization
```yaml
# Local AI optimization
local_ai_settings:
  model: "gpt-oss:20b"
  max_tokens: 2048
  temperature: 0.7
  timeout_ms: 2000
  
  # Performance tuning
  num_ctx: 4096  # Context window
  num_threads: 8  # CPU threads
  num_gpu_layers: 35  # GPU acceleration
```

### Cost Optimization Strategies

#### 1. Smart Intent Routing
```python
# Optimize routing for cost efficiency
class CostOptimizedRouter:
    def __init__(self):
        self.fast_path_intents = {
            'GREETING', 'ACKNOWLEDGMENT', 'TIME_DATE', 
            'WEATHER', 'SIMPLE_MATH', 'TRANSLATION'
        }
        self.cost_per_token = 0.00002  # OpenAI pricing
        self.daily_budget = 10.0  # USD
        
    async def route_with_budget(self, intent, current_cost):
        if current_cost >= self.daily_budget * 0.8:  # 80% of budget
            return 'think'  # Route to local to save costs
        
        if intent.name in self.fast_path_intents:
            return 'fast'
        return 'think'
```

#### 2. Usage Analytics
```bash
# Daily cost analysis
echo "💰 Daily OpenAI Cost Analysis"
echo "============================="

# Total requests today
fast_requests=$(curl -s 'localhost:9090/api/v1/query?query=increase(fast_path_requests[1d])' | jq -r '.data.result[0].value[1]')
echo "Fast Path Requests: $fast_requests"

# Estimated cost (assuming average response length)
avg_tokens=75
cost_per_1k_tokens=0.02
daily_cost=$(echo "scale=4; $fast_requests * $avg_tokens * $cost_per_1k_tokens / 1000" | bc)
echo "Estimated Daily Cost: \$$daily_cost"

# Cost per user session
active_sessions=$(curl -s 'localhost:9090/api/v1/query?query=active_sessions' | jq -r '.data.result[0].value[1]')
cost_per_session=$(echo "scale=4; $daily_cost / $active_sessions" | bc)
echo "Cost per Session: \$$cost_per_session"
```

---

## 🔒 Security Operations

### API Key Management

#### OpenAI API Key Rotation
```bash
#!/bin/bash
# rotate_openai_key.sh - Secure API key rotation

echo "🔄 Rotating OpenAI API Key"

# Validate new key before switching
NEW_KEY="$1"
if curl -s -H "Authorization: Bearer $NEW_KEY" \
   "https://api.openai.com/v1/models" > /dev/null; then
    echo "✅ New API key validated"
else
    echo "❌ New API key validation failed"
    exit 1
fi

# Update configuration
sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$NEW_KEY/" .env

# Rolling restart of services
docker-compose up -d --no-deps alice-voice-gateway
sleep 10
docker-compose up -d --no-deps alice-backend

echo "✅ API key rotation completed"
```

#### Security Monitoring
```bash
# security_monitor.sh - Monitor for security issues
echo "🛡️  Alice Security Status"
echo "======================="

# Check for API key exposure
if grep -r "sk-" logs/ 2>/dev/null; then
    echo "⚠️  WARNING: Potential API key exposure in logs"
fi

# Monitor authentication failures
auth_failures=$(curl -s 'localhost:9090/api/v1/query?query=increase(auth_failures[1h])' | jq -r '.data.result[0].value[1]')
if (( $(echo "$auth_failures > 10" | bc -l) )); then
    echo "⚠️  WARNING: High authentication failure rate: $auth_failures/hour"
fi

# Check SSL certificate expiry
ssl_days=$(openssl s_client -servername alice.local -connect localhost:443 </dev/null 2>/dev/null | 
           openssl x509 -noout -dates | grep notAfter | 
           awk -F= '{print $2}' | xargs -I {} date -d {} +%s)
current_time=$(date +%s)
days_until_expiry=$(( (ssl_days - current_time) / 86400 ))

if (( days_until_expiry < 30 )); then
    echo "⚠️  WARNING: SSL certificate expires in $days_until_expiry days"
fi

echo "✅ Security check completed"
```

---

## 💰 Cost Management

### Budget Monitoring

#### Daily Cost Tracking
```python
# cost_monitor.py - Track and alert on API costs
import requests
import json
from datetime import datetime, timedelta

class CostMonitor:
    def __init__(self):
        self.daily_budget = 10.0  # USD
        self.weekly_budget = 50.0  # USD
        
    def get_openai_usage(self):
        """Get usage from OpenAI API (requires API key with usage access)"""
        headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
        
        # Get current usage
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        response = requests.get(
            "https://api.openai.com/v1/usage",
            headers=headers,
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
        
        return response.json()
    
    def check_budget_alerts(self, usage_data):
        """Check if usage exceeds budget thresholds"""
        daily_cost = usage_data.get('total_cost', 0)
        
        if daily_cost > self.daily_budget * 0.8:
            return {
                "level": "warning",
                "message": f"Daily cost ${daily_cost:.2f} exceeds 80% of budget"
            }
        
        if daily_cost > self.daily_budget:
            return {
                "level": "critical", 
                "message": f"Daily cost ${daily_cost:.2f} exceeds budget!"
            }
            
        return None

# Usage
monitor = CostMonitor()
usage = monitor.get_openai_usage()
alert = monitor.check_budget_alerts(usage)

if alert:
    print(f"💰 {alert['level'].upper()}: {alert['message']}")
```

### Cost Optimization Rules

#### Automatic Cost Controls
```yaml
# cost_controls.yml
cost_management:
  daily_budget: 10.0
  hourly_limit: 2.0
  
  thresholds:
    warning: 0.8  # 80% of budget
    critical: 0.95  # 95% of budget
    
  actions:
    warning:
      - route_more_to_local: 0.8  # Route 80% to local AI
      - reduce_fast_path_timeout: 200ms
      
    critical:
      - route_to_local_only: true
      - notify_administrators: true
      - enable_cost_saver_mode: true
```

---

## 🆘 Emergency Procedures

### Service Recovery Procedures

#### 1. OpenAI API Outage
```bash
#!/bin/bash
# openai_outage_response.sh - Handle OpenAI API outages

echo "🚨 OpenAI API Outage Detected - Initiating Emergency Response"

# Switch to local-only mode
export VOICE_ARCHITECTURE=local_only
export FAST_PATH_ENABLED=false

# Restart services with local-only configuration
docker-compose -f docker-compose.local-only.yml up -d

# Update HUD to show offline mode
curl -X POST localhost:8000/api/admin/set-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "offline", "message": "Running in offline mode due to service interruption"}'

# Notify users
curl -X POST localhost:8000/api/admin/broadcast \
  -H "Content-Type: application/json" \
  -d '{"type": "info", "message": "Alice is running in offline mode. All features available using local AI."}'

echo "✅ Emergency response complete - Alice running in offline mode"
```

#### 2. Local AI Failure
```bash
#!/bin/bash
# local_ai_failure_response.sh - Handle local AI failures

echo "🚨 Local AI Failure - Switching to Cloud-First Mode"

# Route everything to OpenAI (with higher token limits)
export FAST_PATH_ENABLED=true
export FAST_PATH_CONFIDENCE_THRESHOLD=0.1  # Route almost everything to OpenAI
export OPENAI_MAX_TOKENS=1000  # Increase token limit for complex queries

# Disable local AI dependent features temporarily
export TOOLS_ENABLED=false
export DOCUMENT_RAG_ENABLED=false

# Restart with cloud-first configuration
docker-compose -f docker-compose.cloud-first.yml up -d

echo "✅ Running in cloud-first mode - some features temporarily unavailable"
```

#### 3. Complete System Recovery
```bash
#!/bin/bash
# full_recovery.sh - Complete system recovery procedure

echo "🔄 Initiating Full Alice System Recovery"

# Stop all services
docker-compose down

# Clear potentially corrupted caches
rm -rf cache/tts/*
rm -rf cache/embeddings/*

# Reset database connections
docker-compose exec database sqlite3 alice.db ".vacuum"

# Restart core services in order
docker-compose up -d redis-cache
sleep 5
docker-compose up -d local-ai
sleep 30  # Wait for model loading
docker-compose up -d alice-backend
sleep 10
docker-compose up -d voice-gateway
sleep 5
docker-compose up -d alice-frontend

# Verify all services
./health_check.sh

echo "✅ Full system recovery completed"
```

---

## 📈 Capacity Planning

### Resource Planning Guidelines

#### Scaling Recommendations

| User Load | Voice Gateway | Backend | Local AI Memory | OpenAI Budget |
|-----------|---------------|---------|----------------|---------------|
| **1-10 users** | 1 instance | 1 instance | 8GB RAM | $5-10/day |
| **10-50 users** | 2-3 instances | 2 instances | 16GB RAM | $15-30/day |
| **50-100 users** | 3-5 instances | 3-4 instances | 32GB RAM | $50-100/day |
| **100+ users** | 5+ instances | 5+ instances | 64GB+ RAM | $100+/day |

#### Infrastructure Monitoring
```bash
# capacity_monitor.sh - Monitor resource usage and scaling needs
echo "📊 Alice Capacity Analysis"
echo "========================"

# Current resource usage
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100.0}')
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)

echo "CPU Usage: ${cpu_usage}%"
echo "Memory Usage: ${memory_usage}%"  
echo "Disk Usage: ${disk_usage}%"

# Active sessions
active_sessions=$(curl -s 'localhost:9090/api/v1/query?query=active_sessions' | jq -r '.data.result[0].value[1]')
echo "Active Sessions: $active_sessions"

# Request rates
fast_path_rate=$(curl -s 'localhost:9090/api/v1/query?query=rate(fast_path_requests[5m])' | jq -r '.data.result[0].value[1]')
think_path_rate=$(curl -s 'localhost:9090/api/v1/query?query=rate(think_path_requests[5m])' | jq -r '.data.result[0].value[1]')

echo "Fast Path Rate: $fast_path_rate req/min"
echo "Think Path Rate: $think_path_rate req/min"

# Scaling recommendations
total_requests=$(echo "$fast_path_rate + $think_path_rate" | bc)
if (( $(echo "$total_requests > 100" | bc -l) )); then
    echo "⚠️  HIGH LOAD: Consider scaling up"
elif (( $(echo "$total_requests < 10" | bc -l) )); then
    echo "💡 LOW LOAD: Consider scaling down"
else
    echo "✅ NORMAL LOAD: Current capacity adequate"
fi
```

---

## 📚 Operations Runbooks

### Daily Operations Checklist

```markdown
## Daily Alice Operations Checklist

### Morning Health Check (10 minutes)
- [ ] Run `./health_check.sh` - all services green
- [ ] Check overnight alerts in monitoring dashboard  
- [ ] Verify OpenAI API key balance and usage
- [ ] Review error logs for any issues
- [ ] Validate backup completion status

### Performance Review (5 minutes)
- [ ] Check average response times (Fast: <300ms, Think: <2000ms)
- [ ] Review intent classification accuracy (target: >90%)
- [ ] Monitor resource usage (CPU <70%, Memory <80%)
- [ ] Verify WebSocket connection stability

### Cost Management (5 minutes)  
- [ ] Review daily OpenAI API spend vs. budget
- [ ] Check fast/think path ratio (target: 60/40)
- [ ] Analyze cost per user session trends
- [ ] Adjust routing if approaching budget limits

### User Experience (5 minutes)
- [ ] Test voice interaction end-to-end in Swedish
- [ ] Verify HUD displays correctly  
- [ ] Check tool integrations (Calendar/Spotify/Gmail)
- [ ] Review user feedback or support tickets
```

### Weekly Operations Tasks

```markdown
## Weekly Alice Operations Tasks

### System Maintenance (30 minutes)
- [ ] Update dependencies and security patches
- [ ] Run comprehensive test suite
- [ ] Clean up old logs and temporary files
- [ ] Validate backup/restore procedures
- [ ] Review and rotate API keys if needed

### Performance Analysis (45 minutes)
- [ ] Generate weekly performance report
- [ ] Analyze response time trends and patterns
- [ ] Review cost optimization opportunities  
- [ ] Check capacity utilization and scaling needs
- [ ] Validate monitoring alert thresholds

### Documentation Updates (15 minutes)
- [ ] Update operations documentation
- [ ] Document any configuration changes
- [ ] Review troubleshooting procedures
- [ ] Update capacity planning estimates
- [ ] Maintain runbook accuracy
```

---

For additional support and operational questions, see [SUPPORT.md](../SUPPORT.md) or create an issue in the repository.

**Note on Hybrid Operations:** Alice's hybrid architecture requires monitoring both cloud and local components. Focus on maintaining the balance between performance (fast responses) and cost efficiency (local processing). The privacy-first design ensures that while simple queries may use OpenAI for speed, all sensitive data and complex reasoning remains local.

---

> **Last Updated**: 2025-01-23  
> **Version**: 1.0  
> **Review Status**: ✅ Production Ready