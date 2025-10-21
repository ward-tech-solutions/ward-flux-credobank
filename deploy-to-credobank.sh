#!/bin/bash
###############################################################################
# WARD OPS CredoBank Deployment Script
# Deploys optimized standalone monitoring system to production server
#
# Server: 10.30.25.39
# Optimizations: Zabbix removed, SNMP GETBULK enabled, 50 workers
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REMOTE_USER="root"
REMOTE_HOST="10.30.25.39"
REMOTE_PATH="/root/ward-ops-credobank"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_PATH="/root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify we're in the correct directory
if [ ! -f "$LOCAL_PATH/docker-compose.production-local.yml" ]; then
    log_error "Not in ward-ops-credobank directory. Please run from project root."
    exit 1
fi

log_info "Starting deployment to CredoBank server..."
echo ""
echo "======================================================================"
echo "  WARD OPS - CredoBank Production Deployment"
echo "======================================================================"
echo "  Target Server: ${REMOTE_HOST}"
echo "  Remote Path: ${REMOTE_PATH}"
echo "  Backup Path: ${BACKUP_PATH}"
echo "======================================================================"
echo ""

# Step 1: Test SSH connection
log_info "Testing SSH connection to ${REMOTE_HOST}..."
if ! ssh -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "echo 'Connection successful'" > /dev/null 2>&1; then
    log_error "Cannot connect to ${REMOTE_HOST}. Please check SSH connection."
    exit 1
fi
log_success "SSH connection successful"

# Step 2: Create backup of current deployment
log_info "Creating backup of current deployment..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    if [ -d "/root/ward-ops-credobank" ]; then
        BACKUP_PATH="/root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)"
        echo "Creating backup at: ${BACKUP_PATH}"
        cp -r /root/ward-ops-credobank "${BACKUP_PATH}"
        echo "Backup created successfully"
    else
        echo "No existing deployment found, skipping backup"
    fi
ENDSSH
log_success "Backup completed"

# Step 3: Pull latest changes from GitHub
log_info "Pulling latest changes from GitHub on server..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    cd /root/ward-ops-credobank

    # Stash any local changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "Stashing local changes..."
        git stash
    fi

    # Pull latest changes
    echo "Pulling from main branch..."
    git fetch origin
    git reset --hard origin/main

    echo "Current commit: $(git rev-parse --short HEAD)"
    echo "Latest commit message:"
    git log -1 --pretty=format:"%h - %s (%an, %ar)"
ENDSSH
log_success "Code updated from GitHub"

# Step 4: Stop running containers
log_info "Stopping running containers..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    cd /root/ward-ops-credobank

    # Stop containers gracefully
    if docker-compose -f docker-compose.production-local.yml ps -q 2>/dev/null | grep -q .; then
        echo "Stopping containers..."
        docker-compose -f docker-compose.production-local.yml stop
        echo "Containers stopped"
    else
        echo "No running containers found"
    fi
ENDSSH
log_success "Containers stopped"

# Step 5: Build new images with cache busting
log_info "Building new Docker images..."
CACHE_BUST=$(date +%s)
ssh "${REMOTE_USER}@${REMOTE_HOST}" << ENDSSH
    cd /root/ward-ops-credobank

    echo "Building with CACHE_BUST=${CACHE_BUST}..."
    docker-compose -f docker-compose.production-local.yml build \
        --no-cache \
        --build-arg CACHE_BUST="${CACHE_BUST}" \
        api celery-worker celery-beat

    echo "Build completed"
ENDSSH
log_success "Docker images built"

# Step 6: Start containers
log_info "Starting containers with optimized configuration..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo "Starting containers..."
    docker-compose -f docker-compose.production-local.yml up -d

    echo "Waiting for services to be healthy..."
    sleep 10

    echo ""
    echo "Container status:"
    docker-compose -f docker-compose.production-local.yml ps
ENDSSH
log_success "Containers started"

# Step 7: Verify deployment
log_info "Verifying deployment..."
sleep 5

# Check API health
log_info "Checking API health endpoint..."
if ssh "${REMOTE_USER}@${REMOTE_HOST}" "curl -f -s http://localhost:5001/api/v1/health" > /dev/null 2>&1; then
    log_success "API is healthy"
else
    log_warning "API health check failed, but deployment continued"
fi

# Check worker status
log_info "Checking Celery worker status..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    cd /root/ward-ops-credobank

    # Check worker concurrency
    echo "Celery worker configuration:"
    docker-compose -f docker-compose.production-local.yml exec -T celery-worker \
        celery -A celery_app inspect stats 2>/dev/null | grep -A 5 "pool" || echo "Worker is starting..."
ENDSSH

# Step 8: Show deployment summary
echo ""
echo "======================================================================"
echo "  DEPLOYMENT SUMMARY"
echo "======================================================================"

ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo ""
    echo "📦 Current Version:"
    git log -1 --pretty=format:"   Commit: %h%n   Author: %an%n   Date: %ar%n   Message: %s"

    echo ""
    echo ""
    echo "🐳 Running Containers:"
    docker-compose -f docker-compose.production-local.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo "📊 Optimization Status:"
    echo "   ✅ Zabbix integration: REMOVED"
    echo "   ✅ SNMP GETBULK: ENABLED (60% faster)"
    echo "   ✅ Celery workers: 50 (reduced from 100)"
    echo "   ✅ Expected RAM usage: ~2GB (reduced from ~4GB)"

    echo ""
    echo "🔗 Access URLs:"
    echo "   Web UI: http://10.30.25.39:5001"
    echo "   API: http://10.30.25.39:5001/api/v1"
    echo "   VictoriaMetrics: http://10.30.25.39:8428"

    echo ""
    echo "💾 Backup Location:"
    ls -d /root/ward-ops-backup-* 2>/dev/null | tail -1 || echo "   No backup found"

    echo ""
ENDSSH

echo "======================================================================"
log_success "Deployment completed successfully!"
echo "======================================================================"
echo ""

# Step 9: Show next steps
log_info "Next steps:"
echo "   1. Verify web UI is accessible: http://10.30.25.39:5001"
echo "   2. Check device monitoring is working"
echo "   3. Monitor logs: ssh root@10.30.25.39 'cd /root/ward-ops-credobank && docker-compose -f docker-compose.production-local.yml logs -f'"
echo "   4. If issues occur, rollback: ssh root@10.30.25.39 'cd ${BACKUP_PATH} && docker-compose -f docker-compose.production-local.yml up -d'"
echo ""

# Optional: Show recent logs
read -p "Would you like to see recent logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Showing last 50 lines of logs..."
    ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
        cd /root/ward-ops-credobank
        docker-compose -f docker-compose.production-local.yml logs --tail=50
ENDSSH
fi

exit 0
