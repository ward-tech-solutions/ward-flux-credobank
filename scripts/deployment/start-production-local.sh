#!/bin/bash

# Quick Start Production Locally
# Builds images and starts production-like environment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🏭 Starting Production Environment Locally${NC}"
echo "=========================================="
echo ""

# Check Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running! Please start Docker Desktop."
    exit 1
fi

echo -e "${YELLOW}Step 1/3: Building Docker images...${NC}"
echo "This may take 5-10 minutes on first run..."
docker-compose -f docker-compose.production-local.yml build --no-cache

echo ""
echo -e "${YELLOW}Step 2/3: Starting services...${NC}"
docker-compose -f docker-compose.production-local.yml up -d

echo ""
echo -e "${YELLOW}Step 3/3: Waiting for services to be healthy...${NC}"
sleep 10

# Check status
RETRIES=30
for i in $(seq 1 $RETRIES); do
    if docker-compose -f docker-compose.production-local.yml ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Services are healthy!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Production Running Locally!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "🌐 Access the application:"
echo "   Frontend:  http://localhost:5001"
echo "   API Docs:  http://localhost:5001/docs"
echo "   Login:     admin / admin123"
echo ""
echo "📊 Container Status:"
docker-compose -f docker-compose.production-local.yml ps
echo ""
echo "📝 Useful commands:"
echo "   View logs:  docker-compose -f docker-compose.production-local.yml logs -f"
echo "   Stop:       docker-compose -f docker-compose.production-local.yml down"
echo "   Restart:    docker-compose -f docker-compose.production-local.yml restart"
echo ""
echo "💡 Note: This is using an empty database. To import production data:"
echo "   1. Export from server: ssh root@10.30.25.39 'cd /opt/wardops && docker compose exec -T postgres pg_dump -U ward_admin -Fc ward_ops' > backup.dump"
echo "   2. Import locally:     cat backup.dump | docker-compose -f docker-compose.production-local.yml exec -T postgres pg_restore -U ward_admin -d ward_ops -c --if-exists"
echo ""
echo "Or follow the complete guide in RUN_PRODUCTION_LOCALLY.md"
