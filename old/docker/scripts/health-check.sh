#!/bin/bash
# Alice AI Assistant - Comprehensive Health Check Script
# Validates all critical system components and services

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"
readonly API_BASE_URL="http://localhost:${ALICE_PORT:-8000}"
readonly MAX_RETRIES="${HEALTH_CHECK_MAX_RETRIES:-3}"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Health check status
OVERALL_HEALTH=0
COMPONENT_RESULTS=()

# Logging functions
log() {
    local level="$1"
    shift
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${SCRIPT_NAME}: $*" >&2
}

log_info() { log "${BLUE}INFO${NC}" "$@"; }
log_warn() { log "${YELLOW}WARN${NC}" "$@"; }
log_error() { log "${RED}ERROR${NC}" "$@"; }
log_success() { log "${GREEN}SUCCESS${NC}" "$@"; }

# Helper functions
check_component() {
    local component_name="$1"
    local check_function="$2"
    
    log_info "Checking $component_name..."
    
    if $check_function; then
        log_success "$component_name: HEALTHY"
        COMPONENT_RESULTS+=("$component_name:HEALTHY")
        return 0
    else
        log_error "$component_name: UNHEALTHY"
        COMPONENT_RESULTS+=("$component_name:UNHEALTHY")
        OVERALL_HEALTH=1
        return 1
    fi
}

# HTTP request with timeout
http_request() {
    local url="$1"
    local expected_status="${2:-200}"
    local timeout="${3:-$HEALTH_CHECK_TIMEOUT}"
    
    if command -v curl >/dev/null 2>&1; then
        local response
        response=$(curl -s -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo "000")
        local status_code="${response: -3}"
        
        if [[ "$status_code" == "$expected_status" ]]; then
            return 0
        else
            log_warn "HTTP request to $url returned status $status_code (expected $expected_status)"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget --timeout="$timeout" --tries=1 --spider --quiet "$url" 2>/dev/null; then
            return 0
        else
            log_warn "HTTP request to $url failed (wget)"
            return 1
        fi
    else
        log_error "Neither curl nor wget available for HTTP health checks"
        return 1
    fi
}

# Check if process is running
check_process_running() {
    local process_pattern="$1"
    
    if pgrep -f "$process_pattern" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Component health checks
check_basic_http() {
    local retries=0
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if http_request "$API_BASE_URL/health" 200 5; then
            return 0
        fi
        
        ((retries++))
        if [[ $retries -lt $MAX_RETRIES ]]; then
            log_info "Basic HTTP check failed, retrying ($retries/$MAX_RETRIES)..."
            sleep 2
        fi
    done
    
    return 1
}

check_api_endpoints() {
    local endpoints=(
        "/health:200"
        "/api/v1/health/simple:200"
    )
    
    for endpoint_def in "${endpoints[@]}"; do
        IFS=':' read -r endpoint expected_status <<< "$endpoint_def"
        
        if ! http_request "$API_BASE_URL$endpoint" "$expected_status" 3; then
            log_warn "API endpoint $endpoint failed health check"
            return 1
        fi
    done
    
    return 0
}

check_database_connectivity() {
    # Try to connect to database through API
    local db_health_url="$API_BASE_URL/api/v1/health/database"
    
    if http_request "$db_health_url" 200 8; then
        return 0
    else
        # Fallback: Check if database file exists (for SQLite)
        if [[ "${DATABASE_URL:-}" == sqlite* ]]; then
            local db_file=$(echo "${DATABASE_URL}" | sed 's|sqlite:///||')
            if [[ -f "$db_file" ]] && [[ -r "$db_file" ]]; then
                log_info "Database file accessible: $db_file"
                return 0
            fi
        fi
        
        return 1
    fi
}

check_memory_system() {
    # Check B1 (Ambient Memory) system
    local ambient_stats_url="$API_BASE_URL/api/memory/ambient/stats"
    
    if http_request "$ambient_stats_url" 200 5; then
        return 0
    else
        log_warn "Ambient memory system not responding"
        return 1
    fi
}

check_voice_system_readiness() {
    # Check if voice processing components are initialized
    local voice_health_url="$API_BASE_URL/api/v1/health/voice"
    
    if http_request "$voice_health_url" 200 5; then
        return 0
    else
        # Check if audio devices are available
        if command -v aplay >/dev/null 2>&1; then
            if aplay -l >/dev/null 2>&1; then
                log_info "Audio devices detected"
            else
                log_warn "No audio devices found"
            fi
        fi
        
        return 1
    fi
}

check_performance_monitoring() {
    if [[ "${PERFORMANCE_MONITORING_ENABLED:-true}" == "true" ]]; then
        # Check if performance monitoring is active
        local perf_status_url="$API_BASE_URL/api/v1/health/performance"
        
        if http_request "$perf_status_url" 200 3; then
            return 0
        else
            log_warn "Performance monitoring not responding"
            return 1
        fi
    else
        log_info "Performance monitoring disabled"
        return 0
    fi
}

check_system_resources() {
    local warnings=0
    
    # Check memory usage
    if command -v free >/dev/null 2>&1; then
        local mem_usage
        mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
        
        if (( $(echo "$mem_usage > 90" | bc -l 2>/dev/null || echo 0) )); then
            log_warn "High memory usage: ${mem_usage}%"
            ((warnings++))
        else
            log_info "Memory usage: ${mem_usage}%"
        fi
    fi
    
    # Check disk space
    if command -v df >/dev/null 2>&1; then
        local disk_usage
        disk_usage=$(df /app | awk 'NR==2{print $5}' | sed 's/%//')
        
        if [[ "$disk_usage" -gt 90 ]]; then
            log_warn "High disk usage: ${disk_usage}%"
            ((warnings++))
        else
            log_info "Disk usage: ${disk_usage}%"
        fi
    fi
    
    # Check if application process is running
    if ! check_process_running "python.*app"; then
        log_error "Alice application process not found"
        return 1
    fi
    
    # Consider warnings as non-critical
    if [[ $warnings -gt 0 ]]; then
        log_warn "System resources check completed with $warnings warning(s)"
    fi
    
    return 0
}

check_external_dependencies() {
    # This would check external API connectivity in production
    # For now, just verify network connectivity
    
    if command -v ping >/dev/null 2>&1; then
        if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
            log_info "Network connectivity confirmed"
            return 0
        else
            log_warn "Network connectivity issues detected"
            return 1
        fi
    fi
    
    return 0
}

# Startup readiness check
check_startup_readiness() {
    # Check if the ready indicator exists
    if [[ -f "/tmp/health_check_ready" ]]; then
        return 0
    else
        log_warn "Application startup not yet completed"
        return 1
    fi
}

# Main health check execution
run_health_checks() {
    log_info "Alice AI Assistant - Comprehensive Health Check"
    log_info "Timestamp: $(date -Iseconds)"
    log_info "Environment: ${ALICE_ENV:-unknown}"
    
    # Core health checks (critical)
    check_component "Startup Readiness" check_startup_readiness
    check_component "Basic HTTP" check_basic_http
    check_component "API Endpoints" check_api_endpoints
    check_component "Database Connectivity" check_database_connectivity
    
    # System health checks (important)
    check_component "Memory System (B1)" check_memory_system
    check_component "System Resources" check_system_resources
    
    # Optional health checks (non-critical)
    check_component "Voice System" check_voice_system_readiness || true
    check_component "Performance Monitoring" check_performance_monitoring || true
    check_component "External Dependencies" check_external_dependencies || true
    
    # Summary
    local healthy_count=0
    local unhealthy_count=0
    
    for result in "${COMPONENT_RESULTS[@]}"; do
        if [[ "$result" == *":HEALTHY" ]]; then
            ((healthy_count++))
        else
            ((unhealthy_count++))
        fi
    done
    
    log_info "Health check summary: $healthy_count healthy, $unhealthy_count unhealthy"
    
    if [[ $OVERALL_HEALTH -eq 0 ]]; then
        log_success "Overall health status: HEALTHY"
        
        # Write health status file
        cat > /tmp/alice_health_status <<EOF
{
    "status": "healthy",
    "timestamp": "$(date -Iseconds)",
    "components": [
$(printf '        "%s",' "${COMPONENT_RESULTS[@]}" | sed 's/,$//')
    ]
}
EOF
        
        return 0
    else
        log_error "Overall health status: UNHEALTHY"
        
        # Write health status file
        cat > /tmp/alice_health_status <<EOF
{
    "status": "unhealthy",
    "timestamp": "$(date -Iseconds)",
    "components": [
$(printf '        "%s",' "${COMPONENT_RESULTS[@]}" | sed 's/,$//')
    ]
}
EOF
        
        return 1
    fi
}

# Quick health check for frequent monitoring
quick_health_check() {
    if http_request "$API_BASE_URL/health" 200 3; then
        echo "healthy"
        return 0
    else
        echo "unhealthy"
        return 1
    fi
}

# Main execution
main() {
    local mode="${1:-full}"
    
    case "$mode" in
        quick)
            quick_health_check
            ;;
        full|*)
            run_health_checks
            ;;
    esac
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi