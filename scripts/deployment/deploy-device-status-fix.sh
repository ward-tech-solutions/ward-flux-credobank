#!/bin/bash

# CRITICAL FIX: Device Status Display Bug
# Devices showing as DOWN even when they're UP because down_since not clearing
# Root cause: State transition logic was using PostgreSQL ping_results which we stopped writing in Phase 4

set -e

echo "🔧 CRITICAL FIX: Device Status Display Bug"
echo "=========================================="
echo ""
echo "Bug: Devices permanently show as DOWN even when ping succeeds"
echo "Root cause: State transition logic used PostgreSQL ping_results"
echo "            but Phase 4 disabled PostgreSQL writes"
echo ""
echo "Fix: Changed to use device.down_since field directly"
echo "     - previous_state = device.down_since is None"
echo "     - No longer queries ping_results table"
echo ""

# Rebuild monitoring worker with the fix
echo "📦 Building monitoring worker..."
docker-compose -f docker-compose.production-priority-queues.yml build celery-worker-monitoring

# Restart monitoring worker
echo "🔄 Restarting monitoring worker..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-worker-monitoring

# Wait for healthy status
echo "⏳ Waiting for worker to become healthy..."
sleep 5

# Check health
echo "🏥 Checking worker health..."
docker ps | grep wardops-worker-monitoring

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Verification steps:"
echo "1. Watch logs for 'came UP' messages:"
echo "   docker logs -f wardops-worker-monitoring-prod | grep -i 'came UP\\|went DOWN\\|RECOVERED'"
echo ""
echo "2. Wait 1-2 minutes and check UI - devices should start showing as UP"
echo ""
echo "3. Verify down_since cleared in database:"
echo "   docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT name, ip, down_since FROM standalone_devices WHERE down_since IS NULL LIMIT 10;\""
echo ""
