#!/bin/bash
# Emergency fix for CredoBank - PostgreSQL maxed out

set -e

echo "🚨 EMERGENCY FIX - Restarting PostgreSQL..."
echo "=============================================="

# 1. Stop all services that use PostgreSQL
echo "⏹️  Step 1: Stopping services..."
docker-compose -f docker-compose.production-local.yml stop celery-worker celery-beat api

# 2. Restart PostgreSQL to clear connections
echo "♻️  Step 2: Restarting PostgreSQL..."
docker-compose -f docker-compose.production-local.yml restart postgres
sleep 10

# 3. Increase max_connections before starting services
echo "📊 Step 3: Increasing max_connections to 300..."
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d postgres -c "ALTER SYSTEM SET max_connections = 300;"
docker-compose -f docker-compose.production-local.yml restart postgres
sleep 15

# 4. Rebuild API with frontend fixes
echo "🔨 Step 4: Rebuilding API container (includes frontend)..."
docker-compose -f docker-compose.production-local.yml build api celery-worker

# 5. Start services one by one
echo "🚀 Step 5: Starting services..."
docker-compose -f docker-compose.production-local.yml up -d api
sleep 10
docker-compose -f docker-compose.production-local.yml up -d celery-worker
sleep 5
docker-compose -f docker-compose.production-local.yml up -d celery-beat

echo "⏳ Waiting for services to stabilize..."
sleep 20

# 6. Verify services
echo "✅ Step 6: Checking service status..."
docker-compose -f docker-compose.production-local.yml ps

echo ""
echo "✅ Emergency fix complete!"
echo ""
echo "📋 Verify:"
echo "1. Frontend: http://10.30.25.39:5001/devices - Check Add/Edit device modals"
echo "2. Logs: docker logs -f --tail=50 wardops-worker-prod"
echo "3. Database: docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c 'SHOW max_connections;'"
