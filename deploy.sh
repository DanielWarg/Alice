#!/bin/bash
# Alice Voice System - Production Deployment Script
# Deploys to production with health checks and rollback capability

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/deploy_$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="${SCRIPT_DIR}/backups"
DOCKER_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)  echo -e "${BLUE}[INFO]${NC} $message" | tee -a "$LOG_FILE" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $message" | tee -a "$LOG_FILE" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Create necessary directories
mkdir -p logs backups

log INFO "🚀 Starting Alice deployment..."

# Pre-deployment checks
pre_deployment_checks() {
    log INFO "🔍 Running pre-deployment checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log ERROR "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f .env ]]; then
        log WARN ".env file not found - using environment variables"
    fi
    
    # Check required environment variables
    local required_vars=("OPENAI_API_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log ERROR "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check disk space
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local required_space=1000000  # 1GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log ERROR "Insufficient disk space (available: ${available_space}KB, required: ${required_space}KB)"
        exit 1
    fi
    
    log SUCCESS "Pre-deployment checks passed"
}

# Backup current deployment
backup_current() {
    log INFO "💾 Creating backup of current deployment..."
    
    local backup_name="alice_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    mkdir -p "$backup_path"
    
    # Backup database if running
    if docker-compose ps alice-backend &> /dev/null; then
        log INFO "Backing up database..."
        docker-compose exec -T alice-backend python -c "
import sqlite3
import shutil
import os
if os.path.exists('/app/data/alice.db'):
    shutil.copy('/app/data/alice.db', '/app/data/alice_backup.db')
    print('Database backup created')
" || log WARN "Database backup failed"
    fi
    
    # Backup configuration
    cp -r docker-compose.yml docker/ "$backup_path/" 2>/dev/null || true
    
    log SUCCESS "Backup created at $backup_path"
    echo "$backup_name" > "${BACKUP_DIR}/latest"
}

# Build and deploy
deploy() {
    log INFO "🔨 Building and deploying Alice..."
    
    # Pull latest images and build
    docker-compose pull || log WARN "Failed to pull some images"
    docker-compose build --no-cache
    
    # Deploy with rolling update strategy
    log INFO "Starting deployment..."
    docker-compose up -d --force-recreate --remove-orphans
    
    # Wait for services to be healthy
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        log INFO "Checking service health (attempt $((attempt + 1))/$max_attempts)..."
        
        if docker-compose exec -T alice-backend curl -f http://localhost:8000/health &> /dev/null; then
            log SUCCESS "Backend is healthy"
            break
        fi
        
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log ERROR "Deployment health check failed"
        return 1
    fi
    
    # Run post-deployment tests
    post_deployment_tests
    
    log SUCCESS "Deployment completed successfully"
}

# Post-deployment tests
post_deployment_tests() {
    log INFO "🧪 Running post-deployment tests..."
    
    local base_url="http://localhost:${FRONTEND_PORT:-3000}"
    local api_url="http://localhost:${BACKEND_PORT:-8000}"
    
    # Test health endpoints
    if curl -f "$api_url/health" &> /dev/null; then
        log SUCCESS "Backend health check passed"
    else
        log ERROR "Backend health check failed"
        return 1
    fi
    
    # Test API endpoints
    if curl -f "$api_url/api/agent" -X POST \
        -H "Content-Type: application/json" \
        -d '{"session_id":"deploy_test","messages":[{"role":"user","content":"test"}]}' &> /dev/null; then
        log SUCCESS "API endpoint test passed"
    else
        log WARN "API endpoint test failed (may be due to OpenAI API key)"
    fi
    
    # Test frontend
    if curl -f "$base_url" &> /dev/null; then
        log SUCCESS "Frontend test passed"
    else
        log ERROR "Frontend test failed"
        return 1
    fi
    
    log SUCCESS "Post-deployment tests completed"
}

# Rollback function
rollback() {
    log WARN "🔄 Initiating rollback..."
    
    if [[ ! -f "${BACKUP_DIR}/latest" ]]; then
        log ERROR "No backup found for rollback"
        exit 1
    fi
    
    local backup_name=$(cat "${BACKUP_DIR}/latest")
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    if [[ ! -d "$backup_path" ]]; then
        log ERROR "Backup directory not found: $backup_path"
        exit 1
    fi
    
    log INFO "Rolling back to backup: $backup_name"
    
    # Stop current services
    docker-compose down
    
    # Restore backup
    cp "$backup_path/docker-compose.yml" .
    cp -r "$backup_path/docker/" .
    
    # Restart services
    docker-compose up -d
    
    log SUCCESS "Rollback completed"
}

# Cleanup old backups (keep last 5)
cleanup_backups() {
    log INFO "🧹 Cleaning up old backups..."
    
    cd "$BACKUP_DIR"
    ls -t alice_backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true
    
    log SUCCESS "Backup cleanup completed"
}

# Main deployment flow
main() {
    # Handle command line arguments
    case "${1:-deploy}" in
        "rollback")
            rollback
            exit 0
            ;;
        "logs")
            docker-compose logs -f
            exit 0
            ;;
        "status")
            docker-compose ps
            exit 0
            ;;
        "stop")
            docker-compose down
            exit 0
            ;;
        "deploy"|*)
            # Continue with deployment
            ;;
    esac
    
    # Run deployment
    pre_deployment_checks
    backup_current
    
    if deploy; then
        cleanup_backups
        log SUCCESS "🎉 Alice deployment completed successfully!"
        log INFO "📊 Access monitoring at: http://localhost:9090"
        log INFO "🌐 Access Alice at: http://localhost:3000"
    else
        log ERROR "Deployment failed"
        read -p "Do you want to rollback? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        fi
        exit 1
    fi
}

# Signal handlers for cleanup
cleanup() {
    log WARN "Deployment interrupted"
    exit 1
}

trap cleanup INT TERM

# Run main function
main "$@"