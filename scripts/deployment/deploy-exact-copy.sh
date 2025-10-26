#!/bin/bash

# ================================================================
# WARD OPS - Deploy Exact Copy of Local Setup to CredoBank Server
# ================================================================

set -e

echo "=========================================="
echo "WARD OPS - CredoBank Server Deployment"
echo "=========================================="
echo ""
echo "This will deploy the EXACT same setup currently running locally:"
echo "  ✓ PostgreSQL with 875 devices across 128 branches"
echo "  ✓ Redis cache"
echo "  ✓ FastAPI backend on port 5001"
echo "  ✓ 60 Celery workers for SNMP monitoring"
echo "  ✓ Celery Beat scheduler"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  Please do not run as root. Run as regular user with sudo access."
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker..."
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "✓ Docker installed successfully"
else
    echo "✓ Docker is already installed"
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing docker-compose..."
    sudo apt install -y docker-compose
    echo "✓ docker-compose installed"
else
    echo "✓ docker-compose is already installed"
fi

echo ""
echo "=========================================="
echo "Creating production environment file..."
echo "=========================================="

# Create .env file with production settings
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops

# Redis Configuration
REDIS_URL=redis://:redispass@redis:6379/0

# Security & Encryption
SECRET_KEY=local-prod-test-secret-key-change-me
ENCRYPTION_KEY=T8gn87i4YOSDqxFG2_Cx9U1UXzuZuPhwfXdE_wqBBY8=

# Admin Configuration
DEFAULT_ADMIN_PASSWORD=admin123

# Application Settings
ENVIRONMENT=production
MONITORING_MODE=snmp_only
API_HOST=0.0.0.0
API_PORT=5001
LOG_LEVEL=INFO

# Celery Worker Configuration
CELERY_WORKER_CONCURRENCY=60

# SNMP Polling Configuration
SNMP_TIMEOUT=5
SNMP_RETRIES=3
SNMP_MAX_BULK_SIZE=25
EOF

echo "✓ Environment file created"

echo ""
echo "=========================================="
echo "Stopping any existing containers..."
echo "=========================================="
sudo docker-compose -f docker-compose.production-local.yml down 2>/dev/null || true

echo ""
echo "=========================================="
echo "Pulling base images..."
echo "=========================================="
sudo docker-compose -f docker-compose.production-local.yml pull postgres redis

echo ""
echo "=========================================="
echo "Building application images..."
echo "=========================================="
sudo docker-compose -f docker-compose.production-local.yml build

echo ""
echo "=========================================="
echo "Starting all services..."
echo "=========================================="
sudo docker-compose -f docker-compose.production-local.yml up -d

echo ""
echo "=========================================="
echo "Waiting for services to be healthy..."
echo "=========================================="
sleep 10

# Check container status
echo ""
echo "Container Status:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep wardops || echo "Waiting for containers..."

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Access your system:"
echo "  🌐 URL: http://$(hostname -I | awk '{print $1}'):5001"
echo "  👤 Username: admin"
echo "  🔑 Password: admin123"
echo ""
echo "Useful commands:"
echo "  📊 View logs: sudo docker-compose -f docker-compose.production-local.yml logs -f"
echo "  🔄 Restart: sudo docker-compose -f docker-compose.production-local.yml restart"
echo "  🛑 Stop: sudo docker-compose -f docker-compose.production-local.yml down"
echo ""
echo "The system will automatically:"
echo "  ✓ Seed 875 devices across 128 CredoBank branches"
echo "  ✓ Start SNMP monitoring"
echo "  ✓ Begin health checks"
echo ""
echo "Check logs with: sudo docker-compose -f docker-compose.production-local.yml logs -f api"
echo ""
