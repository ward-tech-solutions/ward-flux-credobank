#!/bin/bash

# WARD OPS - Run Production Setup Locally
# This script sets up the exact production environment on your local machine

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏭 WARD OPS - Production Environment Locally${NC}"
echo "=============================================="
echo ""

# Configuration
PROD_SERVER="10.30.25.39"
PROD_USER="root"
BACKUP_FILE="prod_backup_$(date +%Y%m%d_%H%M%S).dump"
LOCAL_BACKUP_PATH="./backups/$BACKUP_FILE"

# Check prerequisites
echo "📦 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is ready${NC}"
echo ""

# Create backups directory
mkdir -p backups

# Main menu
echo "What would you like to do?"
echo ""
echo "1) 🔄 Full Setup (Export DB from production + Start locally)"
echo "2) 🗄️  Only Export Database from Production"
echo "3) 🚀 Start with Existing Database Backup"
echo "4) 🧹 Clean Everything and Start Fresh"
echo "5) 📊 View Status"
echo "6) 🛑 Stop Services"
echo "7) 📝 View Logs"
echo "8) ❌ Exit"
echo ""
read -p "Enter choice [1-8]: " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        echo -e "${BLUE}   Full Production Setup Locally${NC}"
        echo -e "${BLUE}════════════════════════════════════════${NC}"
        echo ""

        # Step 1: Export database
        echo -e "${YELLOW}Step 1/4: Exporting database from production...${NC}"
        echo "Server: $PROD_SERVER"
        echo ""

        read -p "Enter production server password: " -s PROD_PASSWORD
        echo ""

        echo "Connecting to production server and exporting database..."
        sshpass -p "$PROD_PASSWORD" ssh $PROD_USER@$PROD_SERVER "cd /opt/wardops && docker compose exec -T postgres pg_dump -U ward_admin -Fc ward_ops" > "$LOCAL_BACKUP_PATH"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Database exported successfully!${NC}"
            echo "   Backup saved to: $LOCAL_BACKUP_PATH"
            echo "   Size: $(du -h $LOCAL_BACKUP_PATH | cut -f1)"
        else
            echo -e "${RED}❌ Failed to export database${NC}"
            exit 1
        fi
        echo ""

        # Step 2: Stop existing containers
        echo -e "${YELLOW}Step 2/4: Stopping existing containers...${NC}"
        docker-compose down 2>/dev/null || true
        echo -e "${GREEN}✅ Stopped${NC}"
        echo ""

        # Step 3: Start PostgreSQL
        echo -e "${YELLOW}Step 3/4: Starting PostgreSQL...${NC}"
        docker-compose up -d postgres redis

        echo "Waiting for PostgreSQL to be ready..."
        sleep 5

        # Check if postgres is ready
        for i in {1..30}; do
            if docker-compose exec -T postgres pg_isready -U ward_admin &>/dev/null; then
                echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
                break
            fi
            echo -n "."
            sleep 1
        done
        echo ""

        # Step 4: Import database
        echo -e "${YELLOW}Step 4/4: Importing database...${NC}"
        docker-compose exec -T postgres dropdb -U ward_admin --if-exists ward_ops 2>/dev/null || true
        docker-compose exec -T postgres createdb -U ward_admin ward_ops

        cat "$LOCAL_BACKUP_PATH" | docker-compose exec -T postgres pg_restore -U ward_admin -d ward_ops -c --if-exists 2>&1 | grep -v "WARNING" || true

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Database imported successfully!${NC}"
        else
            echo -e "${YELLOW}⚠️  Database imported with warnings (this is normal)${NC}"
        fi
        echo ""

        # Start all services
        echo -e "${YELLOW}Starting all services...${NC}"
        docker-compose up -d
        echo ""

        echo -e "${GREEN}════════════════════════════════════════${NC}"
        echo -e "${GREEN}   ✅ Production Setup Complete!${NC}"
        echo -e "${GREEN}════════════════════════════════════════${NC}"
        echo ""
        echo "🌐 Access the application:"
        echo "   Frontend: http://localhost:5001"
        echo "   API Docs: http://localhost:5001/docs"
        echo ""
        echo "📊 Container Status:"
        docker-compose ps
        echo ""
        echo "📝 View logs: docker-compose logs -f"
        ;;

    2)
        echo ""
        echo -e "${BLUE}Exporting database from production...${NC}"

        read -p "Enter production server password: " -s PROD_PASSWORD
        echo ""

        sshpass -p "$PROD_PASSWORD" ssh $PROD_USER@$PROD_SERVER "cd /opt/wardops && docker compose exec -T postgres pg_dump -U ward_admin -Fc ward_ops" > "$LOCAL_BACKUP_PATH"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Database exported!${NC}"
            echo "   Backup: $LOCAL_BACKUP_PATH"
            echo "   Size: $(du -h $LOCAL_BACKUP_PATH | cut -f1)"
        else
            echo -e "${RED}❌ Export failed${NC}"
            exit 1
        fi
        ;;

    3)
        echo ""
        echo "Available backups:"
        ls -lh backups/ 2>/dev/null || echo "No backups found"
        echo ""
        read -p "Enter backup filename (e.g., prod_backup_20250101_120000.dump): " BACKUP_NAME

        if [ ! -f "backups/$BACKUP_NAME" ]; then
            echo -e "${RED}❌ Backup file not found!${NC}"
            exit 1
        fi

        echo "Starting PostgreSQL..."
        docker-compose up -d postgres redis
        sleep 5

        echo "Importing database..."
        docker-compose exec -T postgres dropdb -U ward_admin --if-exists ward_ops 2>/dev/null || true
        docker-compose exec -T postgres createdb -U ward_admin ward_ops
        cat "backups/$BACKUP_NAME" | docker-compose exec -T postgres pg_restore -U ward_admin -d ward_ops -c --if-exists

        echo "Starting all services..."
        docker-compose up -d

        echo -e "${GREEN}✅ Services started with backup: $BACKUP_NAME${NC}"
        docker-compose ps
        ;;

    4)
        echo ""
        echo -e "${RED}⚠️  This will delete all local data!${NC}"
        read -p "Are you sure? [y/N]: " confirm

        if [[ $confirm == "y" || $confirm == "Y" ]]; then
            echo "Stopping and removing everything..."
            docker-compose down -v
            echo -e "${GREEN}✅ Cleaned${NC}"
        fi
        ;;

    5)
        echo ""
        echo "📊 Container Status:"
        docker-compose ps
        echo ""
        echo "💾 Disk Usage:"
        docker system df
        ;;

    6)
        echo ""
        echo "Stopping services..."
        docker-compose down
        echo -e "${GREEN}✅ Stopped${NC}"
        ;;

    7)
        echo ""
        echo "📝 Logs (Ctrl+C to exit):"
        docker-compose logs -f
        ;;

    8)
        echo "Goodbye! 👋"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice!${NC}"
        exit 1
        ;;
esac

echo ""
echo "💡 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Container status: docker-compose ps"
echo "   Stop services:    docker-compose down"
echo "   Shell into API:   docker-compose exec api bash"
