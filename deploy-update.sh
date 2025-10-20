#!/bin/bash

# ================================================================
# WARD OPS - Deploy Updates to CredoBank Production Server
# ================================================================
# This script:
# 1. Pulls latest code from GitHub
# 2. Applies database migrations (including down_since column)
# 3. Rebuilds and restarts Docker containers
# ================================================================

set -e

echo "=========================================="
echo "WARD OPS - Deploying Updates"
echo "=========================================="
echo ""

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo "=========================================="
echo "Step 1: Pulling latest code from GitHub"
echo "=========================================="
git pull origin main

echo ""
echo "=========================================="
echo "Step 2: Applying database migrations"
echo "=========================================="

# Check if postgres container is running
if ! sudo docker ps | grep -q wardops-postgres-prod; then
    echo "⚠️  PostgreSQL container is not running. Starting it first..."
    sudo docker-compose -f docker-compose.production-local.yml up -d postgres
    echo "Waiting 10 seconds for PostgreSQL to start..."
    sleep 10
fi

# Apply down_since migration
echo "Applying down_since column migration..."
sudo docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops << 'EOF'
-- Check if column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'standalone_devices'
        AND column_name = 'down_since'
    ) THEN
        -- Add down_since column
        ALTER TABLE standalone_devices ADD COLUMN down_since TIMESTAMP;

        -- Add comment
        COMMENT ON COLUMN standalone_devices.down_since IS 'Timestamp when device first went down (NULL when up)';

        RAISE NOTICE 'down_since column added successfully';
    ELSE
        RAISE NOTICE 'down_since column already exists, skipping';
    END IF;
END $$;
EOF

echo "✓ Database migration completed"

echo ""
echo "=========================================="
echo "Step 3: Rebuilding and restarting containers"
echo "=========================================="

# Stop all containers gracefully
echo "Stopping containers..."
sudo docker-compose -f docker-compose.production-local.yml down

# Build new images
echo "Building updated images..."
sudo docker-compose -f docker-compose.production-local.yml build

# Start all containers
echo "Starting containers..."
sudo docker-compose -f docker-compose.production-local.yml up -d

echo ""
echo "=========================================="
echo "Waiting for services to be healthy..."
echo "=========================================="
sleep 15

# Check container status
echo ""
echo "Container Status:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep wardops

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Recent logs from API:"
sudo docker-compose -f docker-compose.production-local.yml logs --tail=20 api

echo ""
echo "Useful commands:"
echo "  📊 View API logs: sudo docker-compose -f docker-compose.production-local.yml logs -f api"
echo "  📊 View worker logs: sudo docker-compose -f docker-compose.production-local.yml logs -f celery-worker"
echo "  🔄 Restart service: sudo docker-compose -f docker-compose.production-local.yml restart <service>"
echo "  🛑 Stop all: sudo docker-compose -f docker-compose.production-local.yml down"
echo ""
