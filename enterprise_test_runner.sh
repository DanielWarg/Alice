#!/bin/bash
# Alice Enterprise Test Runner
# ===========================
# 
# Automated test runner för 14-dagars enterprise validation
# Kör kontinuerlig belastning och analyserar production readiness

set -euo pipefail

# Enterprise test configuration
TEST_DURATION_DAYS=${TEST_DURATION_DAYS:-14}
LOG_DIR="./enterprise_logs"
METRICS_DIR="./enterprise_metrics" 
ALERT_THRESHOLD_P95=2000  # 2s enterprise SLA
ALERT_THRESHOLD_P99=3000  # 3s enterprise SLA
ALERT_THRESHOLD_ERROR_RATE=0.01  # 1% max error rate

# Colors för output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Alice Enterprise 14-Day Test Runner${NC}"
echo -e "${BLUE}======================================${NC}"

# Create directories
mkdir -p "$LOG_DIR" "$METRICS_DIR"

# Function: Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking enterprise prerequisites...${NC}"
    
    # Check k6 installation
    if ! command -v k6 &> /dev/null; then
        echo -e "${RED}❌ k6 not installed. Install: brew install k6${NC}"
        exit 1
    fi
    
    # Check Python dependencies
    if ! python3 -c "import numpy, statistics" &> /dev/null; then
        echo -e "${RED}❌ Missing Python dependencies. Install: pip install numpy${NC}"
        exit 1
    fi
    
    # Check system health
    echo "📊 Checking Alice system health..."
    
    if ! curl -s http://localhost:8000/health | grep -q "ok"; then
        echo -e "${RED}❌ Alice backend unhealthy at localhost:8000${NC}"
        exit 1
    fi
    
    if ! curl -s http://localhost:8787/health | grep -q "normal\\|ok"; then
        echo -e "${RED}❌ Guardian unhealthy at localhost:8787${NC}"
        exit 1
    fi
    
    # Test actual AI response (not mock)
    echo "🧠 Testing real AI integration..."
    response=$(curl -s -X POST http://localhost:8000/api/chat \
        -H "Content-Type: application/json" \
        -d '{"text":"Enterprise test - är detta riktig AI?"}')
    
    if echo "$response" | grep -q "mock\\|echo\\|test"; then
        echo -e "${YELLOW}⚠️ WARNING: AI response looks like mock - enterprise test may not be realistic${NC}"
        echo "Response: $response"
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function: Start enterprise monitoring
start_monitoring() {
    echo -e "${YELLOW}📊 Starting enterprise monitoring...${NC}"
    
    # Start Alice logs collection
    timestamp=$(date +%Y%m%d_%H%M%S)
    alice_log_file="$LOG_DIR/alice_enterprise_${timestamp}.ndjson"
    guardian_log_file="$LOG_DIR/guardian_enterprise_${timestamp}.ndjson"
    
    # Background log collection (NDJSON structured logging expected)
    echo "📝 Collecting Alice logs -> $alice_log_file"
    tail -f /tmp/alice.log 2>/dev/null | grep -E '^\{.*\}$' > "$alice_log_file" &
    ALICE_LOG_PID=$!
    
    echo "📝 Collecting Guardian logs -> $guardian_log_file"  
    tail -f /tmp/guardian.log 2>/dev/null | grep -E '^\{.*\}$' > "$guardian_log_file" &
    GUARDIAN_LOG_PID=$!
    
    # Store PIDs för cleanup
    echo $ALICE_LOG_PID > "$LOG_DIR/alice_log.pid"
    echo $GUARDIAN_LOG_PID > "$LOG_DIR/guardian_log.pid"
    
    echo -e "${GREEN}✅ Enterprise monitoring started${NC}"
}

# Function: Run k6 enterprise soak test
run_enterprise_soak_test() {
    echo -e "${BLUE}🧪 Starting ${TEST_DURATION_DAYS}-day enterprise soak test...${NC}"
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    k6_output="$METRICS_DIR/k6_enterprise_${timestamp}.json"
    
    # Start k6 test in background with JSON output
    echo "🚀 Running k6 enterprise test -> $k6_output"
    k6 run --out json="$k6_output" ./k6_enterprise_soak.js &
    K6_PID=$!
    
    echo $K6_PID > "$METRICS_DIR/k6.pid"
    echo -e "${GREEN}✅ k6 enterprise test started (PID: $K6_PID)${NC}"
    
    return $K6_PID
}

# Function: Monitor test progress
monitor_enterprise_test() {
    local k6_pid=$1
    echo -e "${YELLOW}📊 Monitoring enterprise test progress...${NC}"
    
    # Monitor k6 process
    while kill -0 $k6_pid 2>/dev/null; do
        echo "📈 Enterprise soak test running... (PID: $k6_pid)"
        
        # Check disk space (enterprise requirement)
        disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
        if [ "$disk_usage" -gt 85 ]; then
            echo -e "${RED}🚨 DISK USAGE ALERT: ${disk_usage}% - enterprise test may fail${NC}"
        fi
        
        # Check if we have recent log data
        if [ -f "$LOG_DIR"/*.ndjson ]; then
            recent_logs=$(find "$LOG_DIR" -name "*.ndjson" -newermt "5 minutes ago" | wc -l)
            if [ "$recent_logs" -eq 0 ]; then
                echo -e "${YELLOW}⚠️ WARNING: No recent logs detected - monitoring may be broken${NC}"
            fi
        fi
        
        sleep 300  # Check every 5 minutes
    done
    
    echo -e "${BLUE}🏁 Enterprise soak test completed${NC}"
}

# Function: Analyze enterprise results
analyze_enterprise_results() {
    echo -e "${YELLOW}📊 Analyzing enterprise test results...${NC}"
    
    # Find latest log files
    latest_alice_log=$(ls -t "$LOG_DIR"/alice_enterprise_*.ndjson | head -1)
    latest_k6_output=$(ls -t "$METRICS_DIR"/k6_enterprise_*.json | head -1)
    
    if [ ! -f "$latest_alice_log" ]; then
        echo -e "${RED}❌ No Alice logs found for analysis${NC}"
        return 1
    fi
    
    # Run enterprise metrics analysis
    timestamp=$(date +%Y%m%d_%H%M%S)
    report_file="$METRICS_DIR/enterprise_report_${timestamp}.json"
    
    echo "📊 Running enterprise metrics analysis..."
    python3 ./enterprise_metrics_analyzer.py "$latest_alice_log" --output "$report_file"
    
    # Parse key metrics från report
    if [ -f "$report_file" ]; then
        production_ready=$(jq -r '.enterprise_summary.production_ready' "$report_file")
        availability=$(jq -r '.enterprise_summary.availability_percent' "$report_file")
        p95_latency=$(jq -r '.response_time_metrics.p95_ms' "$report_file")
        p99_latency=$(jq -r '.response_time_metrics.p99_ms' "$report_file")
        error_rate=$(jq -r '.reliability_metrics.error_rate_percent' "$report_file")
        
        # Enterprise assessment
        echo -e "\n${BLUE}🎯 ENTERPRISE PRODUCTION READINESS ASSESSMENT${NC}"
        echo "=================================================="
        
        if [ "$production_ready" = "true" ]; then
            echo -e "Status: ${GREEN}✅ PRODUCTION READY${NC}"
        else
            echo -e "Status: ${RED}❌ NOT PRODUCTION READY${NC}"
        fi
        
        echo "Availability: ${availability}%"
        echo "p95 Latency: ${p95_latency}ms (SLA: ≤2000ms)"
        echo "p99 Latency: ${p99_latency}ms (SLA: ≤3000ms)" 
        echo "Error Rate: ${error_rate}%"
        
        # SLA compliance check
        if (( $(echo "$p95_latency <= $ALERT_THRESHOLD_P95" | bc -l) )); then
            echo -e "p95 SLA: ${GREEN}✅ PASS${NC}"
        else
            echo -e "p95 SLA: ${RED}❌ FAIL${NC}"
        fi
        
        if (( $(echo "$p99_latency <= $ALERT_THRESHOLD_P99" | bc -l) )); then
            echo -e "p99 SLA: ${GREEN}✅ PASS${NC}"  
        else
            echo -e "p99 SLA: ${RED}❌ FAIL${NC}"
        fi
        
        if (( $(echo "$error_rate <= 1.0" | bc -l) )); then
            echo -e "Error Rate SLA: ${GREEN}✅ PASS${NC}"
        else
            echo -e "Error Rate SLA: ${RED}❌ FAIL${NC}"
        fi
        
        echo -e "\n📊 Detailed report: $report_file"
    fi
}

# Function: Cleanup background processes
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up enterprise test processes...${NC}"
    
    # Stop log collection
    if [ -f "$LOG_DIR/alice_log.pid" ]; then
        kill $(cat "$LOG_DIR/alice_log.pid") 2>/dev/null || true
        rm "$LOG_DIR/alice_log.pid"
    fi
    
    if [ -f "$LOG_DIR/guardian_log.pid" ]; then
        kill $(cat "$LOG_DIR/guardian_log.pid") 2>/dev/null || true
        rm "$LOG_DIR/guardian_log.pid"
    fi
    
    # Stop k6 if running
    if [ -f "$METRICS_DIR/k6.pid" ]; then
        k6_pid=$(cat "$METRICS_DIR/k6.pid")
        kill $k6_pid 2>/dev/null || true
        rm "$METRICS_DIR/k6.pid"
        echo "🛑 Stopped k6 enterprise test (PID: $k6_pid)"
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Function: Main enterprise test runner
main() {
    trap cleanup EXIT
    
    echo -e "${BLUE}Starting Alice Enterprise ${TEST_DURATION_DAYS}-Day Validation${NC}"
    echo "Start time: $(date)"
    echo "Expected completion: $(date -d "+${TEST_DURATION_DAYS} days")"
    
    # Enterprise test phases
    check_prerequisites
    start_monitoring
    
    # Start enterprise soak test
    run_enterprise_soak_test
    k6_pid=$!
    
    # Monitor test (will block until completion)
    monitor_enterprise_test $k6_pid
    
    # Analyze results
    analyze_enterprise_results
    
    echo -e "${GREEN}🎉 Enterprise validation complete!${NC}"
    echo "Results available in: $METRICS_DIR/"
    echo "Logs available in: $LOG_DIR/"
}

# Run main function if script executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi