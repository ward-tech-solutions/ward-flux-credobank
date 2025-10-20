#!/bin/bash
# Final fix - Clean deployment without docker-compose recreate issues

set -e

echo "🚨 FINAL FIX - Clean Deployment"
echo "================================"

# 1. Stop all services
echo "⏹️  Step 1: Stopping all services..."
docker-compose -f docker-compose.production-local.yml down

# 2. Start PostgreSQL first and increase max_connections
echo "🗄️  Step 2: Starting PostgreSQL..."
docker-compose -f docker-compose.production-local.yml up -d postgres
sleep 15

echo "📊 Step 3: Increasing max_connections to 300..."
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d postgres -c "ALTER SYSTEM SET max_connections = 300;"
docker-compose -f docker-compose.production-local.yml restart postgres
sleep 15

# 3. Rebuild containers with latest code
echo "🔨 Step 4: Rebuilding containers..."
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker

# 4. Start all services fresh
echo "🚀 Step 5: Starting all services..."
docker-compose -f docker-compose.production-local.yml up -d

echo "⏳ Waiting for services to stabilize..."
sleep 30

# 5. Verify
echo "✅ Step 6: Verifying deployment..."
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.production-local.yml ps

echo ""
echo "📊 PostgreSQL max_connections:"
docker-compose -f docker-compose.production-local.yml exec -T postgres psql -U ward_admin -d ward_ops -c 'SHOW max_connections;'

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Frontend: http://10.30.25.39:5001/devices"
echo "   - Click 'Add Device' to see new UI"
echo "   - Click 'Edit' on any device to see new UI"
echo "2. Logs: docker logs -f --tail=50 wardops-worker-prod"
echo "3. VictoriaMetrics: http://10.30.25.39:8428"
