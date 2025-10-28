#!/bin/bash
#############################################
# WARD FLUX - CredoBank Server Deployment
# Deploys all 7 fixes to production server
#############################################

set -e  # Exit on any error

echo "============================================"
echo "   WARD FLUX - CredoBank Server Deployment"
echo "============================================"
echo ""

COMPOSE_FILE="docker-compose.production-priority-queues.yml"
MIGRATION_FILE="migrations/postgres/014_isp_alert_separation.sql"

# Step 1: Run database migration
echo "Step 1: Running database migration..."
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo "Found migration file"

# Check if PostgreSQL container is running
if ! docker ps | grep -q wardops-postgres-prod; then
    echo "❌ PostgreSQL container is not running"
    exit 1
fi

echo "PostgreSQL container is running"

# Copy migration file to container and execute
echo "Copying migration file to container..."
docker cp "$MIGRATION_FILE" wardops-postgres-prod:/tmp/migration.sql

echo "Executing migration..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -f /tmp/migration.sql

if [ $? -eq 0 ]; then
    echo "✅ Database migration completed"
else
    echo "⚠️  Migration had warnings but may have succeeded (check output above)"
fi

echo ""

# Step 2: Rebuild and restart API container (includes frontend build)
echo "Step 2: Rebuilding API container (includes frontend)..."
echo "This will:"
echo "  - Build frontend inside Docker (npm install + vite build)"
echo "  - Rebuild API with new backend changes"
echo "  - Restart the API service"
echo ""

docker-compose -f $COMPOSE_FILE up -d --build --no-deps api

if [ $? -eq 0 ]; then
    echo "✅ API container rebuilt and restarted"
else
    echo "❌ Failed to rebuild API container"
    exit 1
fi

echo ""

# Step 3: Wait for API to be healthy
echo "Step 3: Waiting for API to be healthy..."
MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -f http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    fi
    echo "Waiting for API... ($WAITED/$MAX_WAIT seconds)"
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "⚠️  API health check timed out, but it may still be starting"
    echo "Check logs: docker logs wardops-api-prod"
fi

echo ""

# Step 4: Verify deployment
echo "Step 4: Verifying deployment..."
echo ""

# Check container status
echo "Container status:"
docker-compose -f $COMPOSE_FILE ps | grep -E "api|worker|beat"

echo ""

# Check for errors in API logs
echo "Recent API logs (last 20 lines):"
docker logs wardops-api-prod --tail=20

echo ""
echo "============================================"
echo "   DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "✅ Database migration executed"
echo "✅ API container rebuilt (frontend + backend)"
echo "✅ Services restarted"
echo ""
echo "🔍 Next Steps:"
echo "1. Clear browser cache (Ctrl+Shift+Delete)"
echo "2. Hard refresh (Ctrl+Shift+R)"
echo "3. Test the following fixes:"
echo "   - Device Details Modal: MTTR calculation visible"
echo "   - Device Details Modal: 'Hide Resolved / Show All' button"
echo "   - Monitor Page: Green glow on device recovery"
echo "   - Reports Page: 'Export PDF' button"
echo "   - API endpoint: /api/v1/interfaces/isp-interface-history/{ip}"
echo ""
echo "📊 Check API logs:"
echo "   docker logs -f wardops-api-prod"
echo ""
echo "📊 Check worker logs:"
echo "   docker logs -f wardops-worker-snmp-prod"
echo "   docker logs -f wardops-worker-monitoring-prod"
echo ""
echo "🔄 If issues occur, rollback with:"
echo "   git reset --hard db48c90"
echo "   docker-compose -f $COMPOSE_FILE down"
echo "   docker-compose -f $COMPOSE_FILE build --no-cache"
echo "   docker-compose -f $COMPOSE_FILE up -d"
echo ""
