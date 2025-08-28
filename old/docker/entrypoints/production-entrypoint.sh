#!/bin/bash
# Alice AI Assistant - Production Entrypoint Script
# Comprehensive production initialization and startup management

set -euo pipefail

# Script configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_LEVEL="${ALICE_LOG_LEVEL:-INFO}"
readonly STARTUP_TIMEOUT="${ALICE_STARTUP_TIMEOUT:-300}"

# Color codes for logging
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

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

# Error handling
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "Error occurred in script at line $line_number (exit code: $exit_code)"
    log_error "Performing cleanup..."
    cleanup
    exit $exit_code
}

cleanup() {
    log_info "Cleaning up temporary resources..."
    # Kill background processes if any
    jobs -p | xargs -r kill 2>/dev/null || true
    # Remove temporary files
    rm -f /tmp/alice_*.tmp 2>/dev/null || true
}

# Set up error handling
trap 'handle_error ${LINENO}' ERR
trap cleanup EXIT

# Environment validation
validate_environment() {
    log_info "Validating production environment..."
    
    local errors=0
    
    # Check required environment variables
    local required_vars=(
        "ALICE_ENV"
        "DATABASE_URL"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            ((errors++))
        fi
    done
    
    # Validate ALICE_ENV
    if [[ "${ALICE_ENV}" != "production" ]] && [[ "${ALICE_ENV}" != "development" ]] && [[ "${ALICE_ENV}" != "testing" ]]; then
        log_error "ALICE_ENV must be 'production', 'development', or 'testing'"
        ((errors++))
    fi
    
    # Check API keys for production
    if [[ "${ALICE_ENV}" == "production" ]]; then
        local api_keys=(
            "OPENAI_API_KEY"
        )
        
        for key in "${api_keys[@]}"; do
            if [[ -z "${!key:-}" ]]; then
                log_warn "API key $key is not set - some features may be unavailable"
            fi
        done
    fi
    
    # Validate numeric values
    local numeric_vars=(
        "ALICE_PORT:1:65535"
        "ALICE_WORKERS:1:32"
        "DATABASE_POOL_SIZE:1:100"
        "TTS_CACHE_MAX_SIZE_MB:10:10000"
    )
    
    for var_def in "${numeric_vars[@]}"; do
        IFS=':' read -r var_name min_val max_val <<< "$var_def"
        local var_value="${!var_name:-}"
        
        if [[ -n "$var_value" ]]; then
            if ! [[ "$var_value" =~ ^[0-9]+$ ]] || [[ "$var_value" -lt "$min_val" ]] || [[ "$var_value" -gt "$max_val" ]]; then
                log_error "$var_name must be a number between $min_val and $max_val"
                ((errors++))
            fi
        fi
    done
    
    if [[ $errors -gt 0 ]]; then
        log_error "Environment validation failed with $errors error(s)"
        return 1
    fi
    
    log_success "Environment validation passed"
    return 0
}

# Directory setup
setup_directories() {
    log_info "Setting up application directories..."
    
    local directories=(
        "/app/data"
        "/app/data/performance_profiles"
        "/app/data/soak_test_results"
        "/app/data/tts_cache"
        "/app/logs"
        "/app/tmp"
        "/app/models"
        "/app/config"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
        
        # Ensure proper permissions
        if [[ ! -w "$dir" ]]; then
            log_error "Directory $dir is not writable"
            return 1
        fi
    done
    
    log_success "Directory setup completed"
}

# Database initialization
initialize_database() {
    log_info "Initializing database..."
    
    # Check if database is accessible
    if [[ "${DATABASE_URL}" == sqlite* ]]; then
        local db_file=$(echo "${DATABASE_URL}" | sed 's|sqlite:///||')
        local db_dir=$(dirname "$db_file")
        
        if [[ ! -d "$db_dir" ]]; then
            mkdir -p "$db_dir"
            log_info "Created database directory: $db_dir"
        fi
    fi
    
    # Run database initialization script
    if python -c "from database import init_db; init_db()" 2>/dev/null; then
        log_success "Database initialization completed"
    else
        log_warn "Database initialization failed - will retry during startup"
    fi
}

# Performance monitoring setup
setup_performance_monitoring() {
    if [[ "${PERFORMANCE_MONITORING_ENABLED:-true}" == "true" ]]; then
        log_info "Setting up performance monitoring..."
        
        # Initialize performance profiler
        python -c "
from performance_profiler import profiler
from b1_b2_performance_monitor import b1b2_performance_manager, integrate_with_main_profiler

# Initialize B1/B2 monitoring integration
integrate_with_main_profiler()

print('Performance monitoring initialized')
" 2>/dev/null || log_warn "Performance monitoring initialization failed"
        
        log_success "Performance monitoring setup completed"
    fi
}

# Model preparation
prepare_models() {
    log_info "Preparing AI models..."
    
    # Check for TTS models
    local tts_model_dir="/app/models/tts"
    if [[ -d "$tts_model_dir" ]]; then
        log_info "TTS models found in $tts_model_dir"
    else
        log_warn "TTS models not found - text-to-speech may not work"
    fi
    
    # Check for embedding models
    local embedding_model_dir="/app/models/embeddings"
    if [[ -d "$embedding_model_dir" ]]; then
        log_info "Embedding models found in $embedding_model_dir"
    else
        log_warn "Embedding models not found - semantic search may be limited"
    fi
    
    log_success "Model preparation completed"
}

# Health check setup
setup_health_checks() {
    log_info "Setting up health monitoring..."
    
    # Create health check script
    cat > /tmp/health_check_ready <<'EOF'
#!/bin/bash
# Internal health check indicator
echo "$(date): Alice is ready for health checks"
EOF
    
    chmod +x /tmp/health_check_ready
    log_success "Health monitoring setup completed"
}

# Application startup
start_application() {
    local mode="${1:-production}"
    
    log_info "Starting Alice AI Assistant in $mode mode..."
    
    case "$mode" in
        production)
            start_production_server
            ;;
        development)
            start_development_server
            ;;
        testing)
            run_tests
            ;;
        *)
            log_error "Unknown startup mode: $mode"
            return 1
            ;;
    esac
}

start_production_server() {
    log_info "Launching production server with Gunicorn..."
    
    # Start performance monitoring in background if enabled
    if [[ "${PERFORMANCE_MONITORING_ENABLED:-true}" == "true" ]]; then
        python -c "
import asyncio
from b1_b2_performance_monitor import b1b2_performance_manager

async def start_monitoring():
    await b1b2_performance_manager.start_monitoring(${PERFORMANCE_MONITORING_INTERVAL:-30})

asyncio.run(start_monitoring())
" &
        local monitor_pid=$!
        log_info "Performance monitoring started (PID: $monitor_pid)"
    fi
    
    # Pre-flight checks
    log_info "Running pre-flight checks..."
    python -c "
import sys
try:
    from app import app
    print('✅ Application imports successful')
    
    # Test database connection
    from database import test_connection
    if test_connection():
        print('✅ Database connection successful')
    else:
        print('⚠️  Database connection failed')
    
    # Test essential components
    from services.ambient_memory import init_ambient_db
    init_ambient_db()
    print('✅ Ambient memory system initialized')
    
except Exception as e:
    print(f'❌ Pre-flight check failed: {e}')
    sys.exit(1)
"
    
    # Signal that we're ready for health checks
    /tmp/health_check_ready
    
    # Launch main application
    exec gunicorn app:app \
        --bind "${ALICE_HOST:-0.0.0.0}:${ALICE_PORT:-8000}" \
        --workers "${ALICE_WORKERS:-4}" \
        --worker-class "${ALICE_WORKER_CLASS:-uvicorn.workers.UvicornWorker}" \
        --worker-connections "${ALICE_WORKER_CONNECTIONS:-1000}" \
        --max-requests "${ALICE_MAX_REQUESTS:-1000}" \
        --max-requests-jitter "${ALICE_MAX_REQUESTS_JITTER:-100}" \
        --timeout "${ALICE_TIMEOUT:-120}" \
        --keepalive "${ALICE_KEEPALIVE:-5}" \
        --preload \
        --access-logfile - \
        --error-logfile - \
        --log-level "${ALICE_LOG_LEVEL,,}" \
        --capture-output
}

start_development_server() {
    log_info "Launching development server with hot reload..."
    
    # Start performance monitoring with shorter interval
    if [[ "${PERFORMANCE_MONITORING_ENABLED:-true}" == "true" ]]; then
        python -c "
import asyncio
from b1_b2_performance_monitor import b1b2_performance_manager

async def start_monitoring():
    await b1b2_performance_manager.start_monitoring(10)  # 10 second interval for development

asyncio.run(start_monitoring())
" &
        log_info "Development performance monitoring started"
    fi
    
    # Signal that we're ready
    /tmp/health_check_ready
    
    # Launch with uvicorn for hot reload
    exec uvicorn app:app \
        --host "${ALICE_HOST:-0.0.0.0}" \
        --port "${ALICE_PORT:-8000}" \
        --reload \
        --log-level "${ALICE_LOG_LEVEL,,}" \
        --access-log
}

run_tests() {
    log_info "Running test suite..."
    
    # Set testing environment
    export TESTING=1
    export DATABASE_URL="sqlite:///:memory:"
    
    # Run tests
    exec python -m pytest tests/ \
        --verbose \
        --cov=. \
        --cov-report=term-missing \
        --cov-report=xml \
        --junit-xml=/app/test-results.xml
}

# Main execution flow
main() {
    local mode="${1:-production}"
    
    log_info "Alice AI Assistant - Production Entrypoint"
    log_info "Mode: $mode"
    log_info "Environment: ${ALICE_ENV:-unknown}"
    log_info "Python version: $(python --version)"
    
    # Perform startup sequence
    validate_environment
    setup_directories
    initialize_database
    setup_performance_monitoring
    prepare_models
    setup_health_checks
    
    log_success "Initialization completed successfully"
    log_info "Starting application..."
    
    # Start the application
    start_application "$mode"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi