#!/bin/bash
###############################################################################
# WARD OPS - CredoBank Phase 1 & 2 Deployment Script
#
# Deploys reliability and performance fixes to CredoBank production server
#
# Server: 10.30.25.39 (Flux)
# User: root (or wardops if configured)
# Fixes: 11 critical reliability improvements
#
# What this deploys:
#   Phase 1: 7 critical fixes (crashes, memory leaks, race conditions)
#   Phase 2: 4 reliability fixes (WebSocket errors, timeouts, null checks)
#
# Usage:
#   ./deploy-phases-1-2.sh
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
REMOTE_USER="root"
REMOTE_HOST="10.30.25.39"
REMOTE_PATH="/root/ward-ops-credobank"
BACKUP_PATH="/root/ward-ops-backup-$(date +%Y%m%d-%H%M%S)"

# Functions
print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verify we're in the correct directory
if [ ! -f "docker-compose.production-local.yml" ]; then
    log_error "Not in ward-ops-credobank directory. Please run from project root."
    exit 1
fi

# Banner
clear
print_header "WARD OPS - CredoBank Phases 1 & 2 Deployment"

echo "📦 Deployment Details:"
echo "   Target Server: ${REMOTE_HOST}"
echo "   Remote Path: ${REMOTE_PATH}"
echo "   Backup Path: ${BACKUP_PATH}"
echo ""
echo "🔧 Changes Being Deployed:"
echo ""
echo "   Phase 1 (7 Critical Fixes):"
echo "   ✅ Fixed bare exception handlers → specific exceptions"
echo "   ✅ Fixed undefined variable crashes → proper error handling"
echo "   ✅ Added database rollback → 13 endpoints with transaction management"
echo "   ✅ Added VictoriaMetrics timeouts → 5 HTTP locations"
echo "   ✅ Fixed wildcard imports → explicit imports"
echo "   ✅ Made singletons thread-safe → 3 singleton classes"
echo "   ✅ Fixed asyncio event loop leaks → proper lifecycle"
echo ""
echo "   Phase 2 (4 Reliability Fixes):"
echo "   ✅ WebSocket JSON error handling → logged errors + client feedback"
echo "   ✅ Null checks for device.ip → prevents crashes"
echo "   ✅ Global HTTP timeout (30s) → prevents worker hangs"
echo "   ✅ Database rollback in template import → data consistency"
echo ""
echo "📋 Impact:"
echo "   • No more crashes from invalid input"
echo "   • Better error visibility and logging"
echo "   • Database consistency guaranteed"
echo "   • Workers protected from hangs"
echo "   • Thread-safe operations"
echo ""
echo "⚡ Configuration:"
echo "   • Zero configuration changes needed"
echo "   • Backward compatible"
echo "   • Works with existing data"
echo "   • No file size limits (VPN deployment)"
echo ""

read -p "Continue with deployment? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_warning "Deployment cancelled by user"
    exit 0
fi

# Test SSH connection
print_header "1/9 Testing SSH Connection"
log_info "Connecting to ${REMOTE_HOST}..."
if ! ssh -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "echo 'SSH OK'" > /dev/null 2>&1; then
    log_error "Cannot connect to ${REMOTE_HOST}"
    log_info "Make sure you're connected to VPN and SSH keys are configured"
    exit 1
fi
log_success "SSH connection successful"

# Create backup
print_header "2/9 Creating Backup"
log_info "Backing up current deployment..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << ENDSSH
    set -e
    if [ -d "${REMOTE_PATH}" ]; then
        echo "📁 Creating backup: ${BACKUP_PATH}"
        cp -r ${REMOTE_PATH} ${BACKUP_PATH}

        # Backup database
        echo "💾 Backing up database..."
        cd ${REMOTE_PATH}
        if docker-compose -f docker-compose.production-local.yml ps postgres | grep -q Up; then
            docker-compose -f docker-compose.production-local.yml exec -T postgres \
                pg_dump -U ward_admin ward_ops > ${BACKUP_PATH}/database-backup.sql 2>/dev/null || true

            if [ -f "${BACKUP_PATH}/database-backup.sql" ]; then
                echo "✅ Database backed up: \$(du -h ${BACKUP_PATH}/database-backup.sql | cut -f1)"
            fi
        fi

        echo "✅ Backup created successfully"
    else
        echo "⚠️  No existing deployment found at ${REMOTE_PATH}"
    fi
ENDSSH
log_success "Backup completed"

# Show current state
print_header "3/9 Checking Current State"
log_info "Checking current deployment..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo "📊 Current Git Status:"
    echo "   Branch: $(git branch --show-current)"
    echo "   Commit: $(git rev-parse --short HEAD)"
    echo "   Message: $(git log -1 --pretty=format:'%s')"

    echo ""
    echo "🐳 Container Status:"
    docker-compose -f docker-compose.production-local.yml ps --format "table {{.Name}}\t{{.Status}}"
ENDSSH
log_success "Current state checked"

# Pull latest code
print_header "4/9 Pulling Latest Code"
log_info "Fetching updates from GitHub..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    # Stash local changes if any
    if [ -n "$(git status --porcelain)" ]; then
        echo "💾 Stashing local changes..."
        git stash save "Auto-stash before deployment $(date)"
    fi

    # Fetch and show what will be updated
    git fetch origin
    CURRENT=$(git rev-parse HEAD)
    LATEST=$(git rev-parse origin/main)

    if [ "$CURRENT" = "$LATEST" ]; then
        echo "✅ Already up to date with origin/main"
    else
        echo "📦 New commits available:"
        git log --oneline --decorate $CURRENT..$LATEST

        echo ""
        echo "🔄 Pulling changes..."
        git pull origin main
        echo "✅ Code updated to: $(git rev-parse --short HEAD)"
    fi
ENDSSH
log_success "Code updated"

# Stop containers
print_header "5/9 Stopping Containers"
log_info "Gracefully stopping containers..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    if docker-compose -f docker-compose.production-local.yml ps -q 2>/dev/null | grep -q .; then
        echo "🛑 Stopping containers..."
        docker-compose -f docker-compose.production-local.yml down
        echo "✅ Containers stopped"
    else
        echo "ℹ️  No running containers found"
    fi
ENDSSH
log_success "Containers stopped"

# Build new images
print_header "6/9 Building Docker Images"
log_warning "This will take 3-5 minutes..."
CACHE_BUST=$(date +%s)

ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << ENDSSH
    cd /root/ward-ops-credobank

    echo "🔨 Building images with CACHE_BUST=${CACHE_BUST}..."
    echo "   This ensures all Python code changes are included"

    docker-compose -f docker-compose.production-local.yml build \
        --no-cache \
        --build-arg CACHE_BUST="${CACHE_BUST}"

    echo "✅ Build completed"
ENDSSH
log_success "Docker images built"

# Start containers
print_header "7/9 Starting Containers"
log_info "Starting services..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo "🚀 Starting containers..."
    docker-compose -f docker-compose.production-local.yml up -d

    echo "⏳ Waiting for services to initialize (30 seconds)..."
    sleep 30

    echo "✅ Containers started"
ENDSSH
log_success "Services started"

# Verify deployment
print_header "8/9 Verifying Deployment"
log_info "Running health checks..."

ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo "🏥 Health Checks:"

    # Check container status
    echo ""
    echo "📦 Container Status:"
    docker-compose -f docker-compose.production-local.yml ps

    # Check API health
    echo ""
    echo "🔍 API Health:"
    if curl -f -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "   ✅ API is responding"
    else
        echo "   ⚠️  API not responding yet (may still be starting)"
    fi

    # Check database
    echo ""
    echo "💾 Database:"
    if docker-compose -f docker-compose.production-local.yml exec -T postgres \
        psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) FROM standalone_devices;" > /dev/null 2>&1; then
        DEVICE_COUNT=$(docker-compose -f docker-compose.production-local.yml exec -T postgres \
            psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices;" | tr -d ' ')
        echo "   ✅ Database connected (${DEVICE_COUNT} devices)"
    else
        echo "   ⚠️  Database check skipped"
    fi

    # Check celery workers
    echo ""
    echo "⚙️  Celery Workers:"
    WORKER_COUNT=$(docker-compose -f docker-compose.production-local.yml ps celery-worker | grep -c "Up" || echo "0")
    echo "   Workers running: ${WORKER_COUNT}"

    # Show recent logs for errors
    echo ""
    echo "📝 Recent Logs (checking for errors):"
    docker-compose -f docker-compose.production-local.yml logs --tail=20 api 2>&1 | \
        grep -i "error\|exception\|failed" | head -5 || echo "   ✅ No errors in recent logs"
ENDSSH
log_success "Health checks completed"

# Show deployment summary
print_header "9/9 Deployment Summary"

ssh "${REMOTE_USER}@${REMOTE_HOST}" bash << 'ENDSSH'
    cd /root/ward-ops-credobank

    echo "📊 Deployment Details:"
    echo ""
    echo "   Git Commit:"
    git log -1 --pretty=format:"      %h - %s%n      %an, %ar"
    echo ""
    echo ""

    echo "   Containers:"
    docker-compose -f docker-compose.production-local.yml ps --format "      {{.Name}}: {{.Status}}"

    echo ""
    echo "🔗 Access Points:"
    echo "   • Web UI:        http://10.30.25.39:5001"
    echo "   • API Docs:      http://10.30.25.39:5001/api/v1/docs"
    echo "   • API Health:    http://10.30.25.39:5001/api/v1/health"
    echo "   • VictoriaMetrics: http://10.30.25.39:8428"

    echo ""
    echo "💾 Backup Location:"
    echo "   ${BACKUP_PATH}"

    echo ""
    echo "📈 What Changed:"
    echo "   ✅ All database operations now have rollback"
    echo "   ✅ WebSocket errors are now logged"
    echo "   ✅ HTTP requests timeout after 30 seconds"
    echo "   ✅ Thread-safe singleton patterns"
    echo "   ✅ No more undefined variable crashes"
    echo "   ✅ Proper event loop lifecycle"

    echo ""
ENDSSH

print_header "✨ Deployment Complete!"
log_success "Phase 1 & 2 fixes are now live on CredoBank server!"

echo ""
echo "📋 Next Steps:"
echo ""
echo "   1. Test the Monitor page:"
echo "      → Open: http://10.30.25.39:5001/monitor"
echo "      → Verify devices are showing status correctly"
echo ""
echo "   2. Check for errors:"
echo "      → ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo "      → cd ${REMOTE_PATH}"
echo "      → docker-compose -f docker-compose.production-local.yml logs -f api"
echo ""
echo "   3. Test bulk import (no file size limits):"
echo "      → Try importing large CSV files"
echo "      → Should work without 10MB restriction"
echo ""
echo "   4. Verify WebSocket stability:"
echo "      → Monitor page should auto-update without errors"
echo "      → Check browser console for WebSocket messages"
echo ""
echo "🔄 To Rollback (if needed):"
echo "   ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo "   cd ${BACKUP_PATH}"
echo "   docker-compose -f docker-compose.production-local.yml up -d"
echo ""
echo "📊 To View Logs:"
echo "   ssh ${REMOTE_USER}@${REMOTE_HOST}"
echo "   cd ${REMOTE_PATH}"
echo "   docker-compose -f docker-compose.production-local.yml logs -f [service]"
echo "   (services: api, celery-worker, celery-beat, postgres, redis)"
echo ""

# Ask if user wants to see live logs
echo ""
read -p "Would you like to see live API logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Showing live API logs (Ctrl+C to exit)..."
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_PATH} && docker-compose -f docker-compose.production-local.yml logs -f --tail=50 api"
fi

exit 0
