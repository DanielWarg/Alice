#!/bin/bash
"""
Alice System Startup - Production Ready
======================================

Startar Alice med Guardian 2.0 protection i rätt ordning:
1. Pre-flight checks (dependencies, ports, disk space)
2. Guardian 2.0 daemon startup  
3. Backend server (FastAPI med Guardian middleware)
4. Frontend development server
5. Health validation

För production: bygg frontend först, kör via systemd/Docker
"""

set -e  # Exit on error

# Colors för output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Project paths
ALICE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$ALICE_ROOT/server"
WEB_DIR="$ALICE_ROOT/web" 
GUARDIAN_DIR="$SERVER_DIR/guardian"

# PID file locations
GUARDIAN_PID="/tmp/alice_guardian.pid"
BACKEND_PID="/tmp/alice_backend.pid"
FRONTEND_PID="/tmp/alice_frontend.pid"

# Check if running
is_running() {
    local pidfile=$1
    [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null
}

# Pre-flight system checks
preflight_checks() {
    log_info "Running Alice pre-flight checks..."
    
    # Check required directories
    for dir in "$SERVER_DIR" "$WEB_DIR" "$GUARDIAN_DIR"; do
        if [ ! -d "$dir" ]; then
            log_error "Missing directory: $dir"
            exit 1
        fi
    done
    
    # Check disk space (min 2GB)
    available=$(df "$ALICE_ROOT" | tail -1 | awk '{print $4}')
    min_space=2097152  # 2GB in KB
    if [ "$available" -lt $min_space ]; then
        log_error "Insufficient disk space. Available: ${available}KB, Required: ${min_space}KB"
        exit 1
    fi
    log_success "Disk space OK: ${available}KB available"
    
    # Check if ports are free
    for port in 3000 8000 8787 11434; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            log_warning "Port $port is already in use"
            if [ "$port" = "11434" ]; then
                log_info "Ollama already running on port 11434 - this is OK"
            fi
        fi
    done
    
    # Check Python virtual environment
    if [ ! -f "$SERVER_DIR/.venv/bin/activate" ]; then
        log_error "Python virtual environment not found at $SERVER_DIR/.venv/"
        log_info "Run: cd $SERVER_DIR && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    
    # Check Node.js dependencies
    if [ ! -d "$WEB_DIR/node_modules" ]; then
        log_error "Node.js dependencies not installed"
        log_info "Run: cd $WEB_DIR && npm install"
        exit 1
    fi
    
    # Check Ollama availability
    if ! command -v ollama >/dev/null 2>&1; then
        log_warning "Ollama not found in PATH. Attempting to use system location..."
        if [ ! -f "/Applications/Ollama.app/Contents/Resources/ollama" ]; then
            log_error "Ollama not installed. Install from https://ollama.ai/"
            exit 1
        fi
    fi
    
    log_success "Pre-flight checks completed"
}

# Start Guardian daemon
start_guardian() {
    log_info "Starting Guardian 2.0 daemon..."
    
    if is_running "$GUARDIAN_PID"; then
        log_warning "Guardian already running (PID: $(cat $GUARDIAN_PID))"
        return 0
    fi
    
    cd "$SERVER_DIR"
    source .venv/bin/activate
    
    # Start Guardian in background
    nohup python -m guardian.guardian > /tmp/guardian.log 2>&1 &
    local guardian_pid=$!
    echo $guardian_pid > "$GUARDIAN_PID"
    
    # Wait for Guardian to be ready
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if curl -s http://localhost:8787/health >/dev/null 2>&1; then
            log_success "Guardian daemon started (PID: $guardian_pid, Port: 8787)"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    log_error "Guardian failed to start within 30 seconds"
    return 1
}

# Start Backend server
start_backend() {
    log_info "Starting Alice backend (FastAPI)..."
    
    if is_running "$BACKEND_PID"; then
        log_warning "Backend already running (PID: $(cat $BACKEND_PID))"
        return 0
    fi
    
    cd "$SERVER_DIR"
    source .venv/bin/activate
    
    # Start backend with Guardian middleware
    nohup python -c "
import uvicorn
from app_minimal import app

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
" > /tmp/backend.log 2>&1 &
    
    local backend_pid=$!
    echo $backend_pid > "$BACKEND_PID"
    
    # Wait for backend to be ready
    local attempts=0
    while [ $attempts -lt 20 ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log_success "Backend started (PID: $backend_pid, Port: 8000)"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    log_error "Backend failed to start within 20 seconds"
    return 1
}

# Start Frontend server
start_frontend() {
    log_info "Starting Alice frontend (Next.js)..."
    
    if is_running "$FRONTEND_PID"; then
        log_warning "Frontend already running (PID: $(cat $FRONTEND_PID))"
        return 0
    fi
    
    cd "$WEB_DIR"
    
    # Start frontend in development mode
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    local frontend_pid=$!
    echo $frontend_pid > "$FRONTEND_PID"
    
    # Wait for frontend to be ready (longer timeout for Next.js)
    local attempts=0
    while [ $attempts -lt 60 ]; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            log_success "Frontend started (PID: $frontend_pid, Port: 3000)"
            return 0
        fi
        sleep 2
        attempts=$((attempts + 2))
    done
    
    log_error "Frontend failed to start within 120 seconds"
    return 1
}

# Validate system health
validate_health() {
    log_info "Validating Alice system health..."
    
    local failed=0
    
    # Check Guardian
    if curl -s http://localhost:8787/health | grep -q "ok"; then
        log_success "✅ Guardian daemon healthy"
    else
        log_error "❌ Guardian daemon unhealthy"
        failed=1
    fi
    
    # Check Backend
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_success "✅ Backend API healthy" 
    else
        log_error "❌ Backend API unhealthy"
        failed=1
    fi
    
    # Check Frontend
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        log_success "✅ Frontend accessible"
    else
        log_error "❌ Frontend inaccessible"
        failed=1
    fi
    
    # Check Guardian integration
    if curl -s http://localhost:8000/api/v1/llm/status >/dev/null 2>&1; then
        log_success "✅ LLM status API responding"
    else
        log_warning "⚠️ LLM status API not responding"
    fi
    
    # Check Ollama connection
    if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
        log_success "✅ Ollama server reachable"
    else
        log_warning "⚠️ Ollama server not reachable"
    fi
    
    if [ $failed -eq 0 ]; then
        log_success "All system health checks passed!"
        return 0
    else
        log_error "Some health checks failed. Check logs for details."
        return 1
    fi
}

# Stop all services
stop_services() {
    log_info "Stopping Alice services..."
    
    for service in "Frontend:$FRONTEND_PID" "Backend:$BACKEND_PID" "Guardian:$GUARDIAN_PID"; do
        local name="${service%%:*}"
        local pidfile="${service##*:}"
        
        if is_running "$pidfile"; then
            local pid=$(cat "$pidfile")
            log_info "Stopping $name (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "Force killing $name (PID: $pid)"
                kill -9 "$pid" 2>/dev/null || true
            fi
            
            rm -f "$pidfile"
            log_success "$name stopped"
        else
            log_info "$name not running"
        fi
    done
}

# Show status
show_status() {
    echo
    log_info "Alice System Status:"
    echo "===================="
    
    for service in "Guardian:$GUARDIAN_PID:8787" "Backend:$BACKEND_PID:8000" "Frontend:$FRONTEND_PID:3000"; do
        local name="${service%%:*}"
        local pidfile="${service#*:}"
        pidfile="${pidfile%%:*}"
        local port="${service##*:}"
        
        if is_running "$pidfile"; then
            local pid=$(cat "$pidfile")
            echo -e "${GREEN}✅ $name${NC} - PID: $pid, Port: $port"
        else
            echo -e "${RED}❌ $name${NC} - Not running"
        fi
    done
    
    echo
    log_info "Endpoints:"
    echo "- Frontend:  http://localhost:3000"
    echo "- Backend:   http://localhost:8000"
    echo "- Guardian:  http://localhost:8787"
    echo "- Ollama:    http://localhost:11434"
    echo
    log_info "Logs:"
    echo "- Guardian:  /tmp/guardian.log"
    echo "- Backend:   /tmp/backend.log"
    echo "- Frontend:  /tmp/frontend.log"
}

# Main execution
case "${1:-start}" in
    "start")
        log_info "🚀 Starting Alice System with Guardian 2.0..."
        preflight_checks
        start_guardian
        start_backend
        start_frontend
        validate_health
        show_status
        
        log_success "🎉 Alice is ready!"
        log_info "Access the system at: http://localhost:3000"
        log_info "Run './start_alice.sh status' to check system status"
        log_info "Run './start_alice.sh stop' to stop all services"
        ;;
    
    "stop")
        stop_services
        log_success "Alice system stopped"
        ;;
    
    "restart")
        log_info "Restarting Alice system..."
        stop_services
        sleep 3
        $0 start
        ;;
    
    "status")
        show_status
        ;;
    
    "logs")
        log_info "Showing recent logs (press Ctrl+C to exit):"
        tail -f /tmp/guardian.log /tmp/backend.log /tmp/frontend.log
        ;;
    
    "health")
        validate_health
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health}"
        echo
        echo "Commands:"
        echo "  start   - Start all Alice services with Guardian protection"
        echo "  stop    - Stop all Alice services"
        echo "  restart - Restart all Alice services" 
        echo "  status  - Show service status"
        echo "  logs    - Follow logs from all services"
        echo "  health  - Run health checks"
        exit 1
        ;;
esac