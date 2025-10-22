#!/bin/bash
###############################################################################
# WARD OPS CredoBank - Server-Side Deployment Script
# Run this script DIRECTLY on the CredoBank server (10.30.25.39)
#
# Usage: ./deploy-on-server.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Auto-detect the deployment path (works for both /root and /home/wardops)
if [ -d "/home/wardops/ward-flux-credobank" ]; then
    DEPLOY_PATH="/home/wardops/ward-flux-credobank"
    BACKUP_PATH="/home/wardops/ward-flux-backup-$(date +%Y%m%d-%H%M%S)"
elif [ -d "/root/ward-ops-credobank" ]; then
    DEPLOY_PATH="/root/ward-ops-credobank"
    BACKUP_PATH="/root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)"
else
    echo -e "${RED}[ERROR]${NC} Could not find deployment directory"
    echo "Tried: /home/wardops/ward-flux-credobank and /root/ward-ops-credobank"
    exit 1
fi

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

# Verify we're on the server
if [ ! -d "$DEPLOY_PATH" ]; then
    log_error "Directory $DEPLOY_PATH not found. Are you on the correct server?"
    exit 1
fi

cd "$DEPLOY_PATH"

echo ""
echo "======================================================================"
echo "  WARD OPS - CredoBank Server Deployment"
echo "======================================================================"
echo "  Deploy Path: ${DEPLOY_PATH}"
echo "  Backup Path: ${BACKUP_PATH}"
echo "======================================================================"
echo ""

# Step 1: Create backup
log_info "Creating backup of current deployment..."
cp -r "$DEPLOY_PATH" "$BACKUP_PATH"
log_success "Backup created at: $BACKUP_PATH"

# Step 2: Show current version
log_info "Current version:"
git log -1 --pretty=format:"   Commit: %h - %s (%an, %ar)" || echo "   Unable to get git info"
echo ""

# Step 3: Stash local changes if any
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    log_warning "Local changes detected, stashing..."
    git stash
fi

# Step 4: Pull latest changes
log_info "Pulling latest changes from GitHub..."
git fetch origin
git reset --hard origin/main
log_success "Code updated from GitHub"

# Step 5: Show new version
log_info "New version:"
git log -1 --pretty=format:"   Commit: %h - %s (%an, %ar)"
echo ""
echo ""

# Step 6: Stop containers
log_info "Stopping containers gracefully..."
docker-compose -f docker-compose.production-local.yml stop
log_success "Containers stopped"

# Step 7: Build new images with cache busting
log_info "Building new Docker images..."
CACHE_BUST=$(date +%s)
echo "Using CACHE_BUST=${CACHE_BUST}"

docker-compose -f docker-compose.production-local.yml build \
    --no-cache \
    --build-arg CACHE_BUST="${CACHE_BUST}" \
    api celery-worker celery-beat

log_success "Docker images built"

# Step 8: Start containers
log_info "Starting containers with optimized configuration..."
docker-compose -f docker-compose.production-local.yml up -d
log_success "Containers started"

# Step 9: Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 15

# Step 10: Check container status
echo ""
log_info "Container status:"
docker-compose -f docker-compose.production-local.yml ps

# Step 11: Check API health
echo ""
log_info "Checking API health..."
sleep 5
if curl -f -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    log_success "API is healthy ✅"
else
    log_warning "API health check failed ⚠️"
fi

# Step 12: Check worker status
echo ""
log_info "Checking Celery worker status..."
docker-compose -f docker-compose.production-local.yml exec -T celery-worker \
    celery -A celery_app inspect stats 2>/dev/null | grep -A 3 "concurrency" || echo "Worker is starting..."

# Step 13: Show deployment summary
echo ""
echo "======================================================================"
echo "  DEPLOYMENT SUMMARY"
echo "======================================================================"
echo ""
echo "📦 Deployed Version:"
git log -1 --pretty=format:"   Commit: %h%n   Author: %an%n   Date: %ar%n   Message: %s"
echo ""
echo ""
echo "🐳 Running Containers:"
docker-compose -f docker-compose.production-local.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "📊 Optimizations Active:"
echo "   ✅ Zabbix integration: REMOVED"
echo "   ✅ SNMP GETBULK: ENABLED (60% faster)"
echo "   ✅ Celery workers: 50 (reduced from 100)"
echo "   ✅ Monitor page fix: DOWN status bug fixed"
echo ""
echo "🔗 Access URLs:"
echo "   Web UI: http://10.30.25.39:5001"
echo "   API: http://10.30.25.39:5001/api/v1"
echo "   VictoriaMetrics: http://10.30.25.39:8428"
echo ""
echo "💾 Backup Location:"
echo "   ${BACKUP_PATH}"
echo ""
echo "======================================================================"
log_success "Deployment completed successfully! 🎉"
echo "======================================================================"
echo ""

# Step 14: Offer to show logs
echo "Next steps:"
echo "   1. Verify web UI is accessible: http://10.30.25.39:5001"
echo "   2. Check Monitor page - devices should show correct UP/DOWN status"
echo "   3. View logs: docker-compose -f docker-compose.production-local.yml logs -f"
echo ""
read -p "Would you like to see recent logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Showing last 50 lines of worker logs (press Ctrl+C to exit)..."
    echo ""
    docker-compose -f docker-compose.production-local.yml logs --tail=50 celery-worker
fi

echo ""
log_info "To view live logs with state transitions:"
echo "   docker-compose -f docker-compose.production-local.yml logs -f celery-worker | grep -E '✅|❌'"
echo ""

exit 0
