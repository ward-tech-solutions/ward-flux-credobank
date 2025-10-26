#!/bin/bash
# Deploy flapping detection system to production
# This script applies database migrations and deploys the new code

set -e  # Exit on error

echo "=================================================="
echo "🚀 DEPLOYING FLAPPING DETECTION SYSTEM"
echo "=================================================="
echo ""

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull origin main

# Apply database migrations
echo ""
echo "🗄️  Applying database migrations..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops << 'EOF'
-- Add flapping detection columns to standalone_devices table
ALTER TABLE standalone_devices
ADD COLUMN IF NOT EXISTS is_flapping BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS flap_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_flap_detected TIMESTAMP,
ADD COLUMN IF NOT EXISTS flapping_since TIMESTAMP,
ADD COLUMN IF NOT EXISTS status_change_times TIMESTAMP[] DEFAULT '{}';

-- Create index for faster flapping queries
CREATE INDEX IF NOT EXISTS idx_devices_flapping ON standalone_devices(is_flapping) WHERE is_flapping = true;

-- Create status history table for tracking changes
CREATE TABLE IF NOT EXISTS device_status_history (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL,
    old_status VARCHAR(10),
    new_status VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    response_time_ms FLOAT
);

-- Index for quick history lookups
CREATE INDEX IF NOT EXISTS idx_status_history_device_time
ON device_status_history(device_id, timestamp DESC);

-- Function to get status change count in time window
CREATE OR REPLACE FUNCTION get_status_change_count(
    p_device_id UUID,
    p_minutes INTEGER DEFAULT 5
) RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM device_status_history
        WHERE device_id = p_device_id
        AND timestamp > NOW() - INTERVAL '1 minute' * p_minutes
    );
END;
$$ LANGUAGE plpgsql;

-- Show current flapping devices (if any)
SELECT 'Current database state:' as status;
SELECT COUNT(*) as total_devices FROM standalone_devices;
SELECT COUNT(*) as flapping_devices FROM standalone_devices WHERE is_flapping = true;
EOF

echo ""
echo "✅ Database migration completed!"

# Build and deploy new containers
echo ""
echo "🔨 Building new containers..."
docker-compose -f docker-compose.production-priority-queues.yml build api celery-worker-monitoring

echo ""
echo "🔄 Stopping old containers..."
docker stop wardops-api-prod wardops-worker-monitoring-prod || true

echo ""
echo "🗑️  Removing old containers..."
docker rm wardops-api-prod wardops-worker-monitoring-prod || true

echo ""
echo "🚀 Starting new containers..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api celery-worker-monitoring

# Wait for containers to start
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Health check
echo ""
echo "🏥 Running health check..."
curl -s http://localhost:5001/api/v1/health | python3 -m json.tool || echo "⚠️  API not responding yet"

# Clear cache
echo ""
echo "🗑️  Clearing Redis cache..."
docker exec wardops-redis-prod redis-cli -a redispass FLUSHALL

# Show logs
echo ""
echo "📋 Recent monitoring logs:"
docker logs wardops-worker-monitoring-prod --tail 20 2>&1 | grep -E "FLAPPING|flap|✅|❌|🔄|⚠️" || echo "No flapping-related logs yet"

# Check specific device
echo ""
echo "🔍 Checking device 10.195.110.51 status:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip, down_since, is_flapping, flap_count, flapping_since
FROM standalone_devices
WHERE ip = '10.195.110.51';"

echo ""
echo "=================================================="
echo "✅ FLAPPING DETECTION DEPLOYED SUCCESSFULLY!"
echo "=================================================="
echo ""
echo "The system will now:"
echo "1. Detect devices flapping (3+ status changes in 5 minutes)"
echo "2. Suppress individual UP/DOWN alerts for flapping devices"
echo "3. Create single 'Device Flapping' alert instead"
echo "4. Show flapping status in API responses"
echo ""
echo "Monitor the logs to see flapping detection in action:"
echo "  docker logs -f wardops-worker-monitoring-prod 2>&1 | grep FLAPPING"
echo ""
echo "Check API for flapping status:"
echo "  curl http://localhost:5001/api/v1/devices | jq '.[] | select(.is_flapping == true)'"
echo ""