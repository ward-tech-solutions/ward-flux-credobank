#!/bin/bash
set -e

echo "🚀 Deploying to CredoBank Server"
echo "=================================="
echo ""

# This script should be run ON THE SERVER after SSH through jump server
# Working directory on server: /root/ward-ops-credobank
# Repository: ward-flux-credobank

# Backup current state
BACKUP_DIR="../ward-ops-backup-$(date +%Y%m%d-%H%M%S)"
echo "📦 Creating backup at: $BACKUP_DIR"
cp -r . "$BACKUP_DIR"
echo "✅ Backup created"
echo ""

# Pull latest code
echo "⬇️  Pulling latest code from ward-flux-credobank..."
git stash save "Auto-stash $(date)" 2>/dev/null || true
git fetch origin
git pull origin main
echo "✅ Code updated"
echo ""

# Rebuild and restart containers
echo "🏗️  Rebuilding Docker images (with --no-cache for frontend)..."
docker-compose -f docker-compose.production-local.yml build --no-cache wardops-api-prod
echo "✅ Images rebuilt"
echo ""

echo "🔄 Restarting containers..."
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d
echo "✅ Containers restarted"
echo ""

# Wait for containers to be ready
echo "⏳ Waiting for containers to be ready..."
sleep 15

# Check health
echo "🏥 Checking system health..."
docker-compose -f docker-compose.production-local.yml ps
echo ""

echo "✅ Deployment complete!"
echo ""
echo "📝 Latest fixes deployed:"
echo "   - Downtime calculation now uses accurate 'down_since' timestamp"
echo "   - No more timezone mismatch with actual device outage times"
echo "   - Monitor page shows correct downtime duration"
echo ""
echo "🧪 Verification steps:"
echo "   1. Open Monitor page in browser"
echo "   2. Check down devices - downtime should match actual outage time"
echo "   3. Verify no more discrepancies with real-world outage times"
echo ""
echo "🔙 Rollback (if needed):"
echo "   cp -r $BACKUP_DIR/* ."
echo "   docker-compose -f docker-compose.production-local.yml restart"
echo ""
echo "📊 View logs:"
echo "   docker logs wardops-worker-prod -f    # Worker logs"
echo "   docker logs wardops-api-prod -f       # API logs"
