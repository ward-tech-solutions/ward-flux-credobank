#!/bin/bash
###############################################################################
# WARD OPS - Simple Server-Side Deployment
# Run this DIRECTLY on CredoBank server after SSH
###############################################################################

set -e
BACKUP_DIR="../ward-ops-backup-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Starting deployment..."
echo ""

# 1. Backup
echo "📦 Creating backup at: $BACKUP_DIR"
cp -r . "$BACKUP_DIR"
echo "✅ Backup created"
echo ""

# 2. Pull code
echo "📥 Pulling latest code from GitHub..."
git stash save "Auto-stash $(date)" 2>/dev/null || true
git fetch origin
git pull origin main
echo "✅ Code updated"
echo ""

# 3. Rebuild and restart
echo "🔨 Rebuilding Docker images (3-5 minutes)..."
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml build --no-cache
docker-compose -f docker-compose.production-local.yml up -d
echo "✅ Services restarted"
echo ""

# 4. Wait and verify
echo "⏳ Waiting 30 seconds for services to start..."
sleep 30
echo ""

echo "🔍 Checking status..."
docker-compose -f docker-compose.production-local.yml ps
echo ""

# 5. Test API
if curl -f -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "⚠️  API not responding yet"
fi
echo ""

echo "✨ Deployment complete!"
echo ""
echo "📊 Access:"
echo "   Web UI: http://10.30.25.39:5001"
echo ""
echo "📝 View logs:"
echo "   docker-compose -f docker-compose.production-local.yml logs -f api"
echo ""
echo "🔄 Rollback:"
echo "   cd $BACKUP_DIR && docker-compose -f docker-compose.production-local.yml up -d"
echo ""
