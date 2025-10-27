#!/bin/bash

# Start Production Environment Locally with CredoBank Seed Data
# This uses the JSON seed files that are already in the project

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🏭 Starting Production with CredoBank Seed Data${NC}"
echo "================================================"
echo ""

# Check Docker
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running! Please start Docker Desktop.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1/5: Building Docker images...${NC}"
echo "This may take 5-10 minutes on first run..."
docker-compose -f docker-compose.production-local.yml build --no-cache

echo ""
echo -e "${YELLOW}Step 2/5: Starting PostgreSQL and Redis...${NC}"
docker-compose -f docker-compose.production-local.yml up -d postgres redis

echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for postgres to be healthy
for i in {1..30}; do
    if docker-compose -f docker-compose.production-local.yml exec -T postgres pg_isready -U ward_admin &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${YELLOW}Step 3/5: Running database migrations...${NC}"
docker-compose -f docker-compose.production-local.yml run --rm api python scripts/run_sql_migrations.py

echo ""
echo -e "${YELLOW}Step 4/5: Seeding CredoBank data...${NC}"
echo "Loading:"
echo "  - 128 branches"
echo "  - 873 devices"
echo "  - 4 alert rules"
echo "  - Georgian regions and cities"
echo ""

docker-compose -f docker-compose.production-local.yml run --rm api python scripts/seed_core.py
docker-compose -f docker-compose.production-local.yml run --rm api python scripts/seed_credobank.py

echo ""
echo -e "${YELLOW}Step 5/5: Starting all services...${NC}"
docker-compose -f docker-compose.production-local.yml up -d

echo "Waiting for API to be ready..."
sleep 10

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Production Running with Seed Data!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📊 Data loaded:"
echo "  ✓ 128 branches"
echo "  ✓ 873 devices (switches, routers, ATMs, etc.)"
echo "  ✓ 4 alert rules"
echo "  ✓ Georgian regions and cities"
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
echo "   View logs:     docker-compose -f docker-compose.production-local.yml logs -f"
echo "   Stop all:      docker-compose -f docker-compose.production-local.yml down"
echo "   Clean restart: docker-compose -f docker-compose.production-local.yml down -v && ./start-production-with-seeds.sh"
echo ""
echo "💡 This is the EXACT same data as on production server 10.30.25.39!"
echo ""
echo "🎉 Ready to test your changes!"
