#!/bin/bash

# WARD OPS - Local Docker Setup Script
# This script automates the local Docker development environment setup

set -e

echo "🐳 WARD OPS Local Docker Setup"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
echo "📦 Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  brew install --cask docker"
    echo ""
    echo "Or install Colima (lightweight alternative):"
    echo "  brew install docker docker-compose colima"
    echo "  colima start --cpu 4 --memory 8"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo "  brew install docker-compose"
    exit 1
fi

echo -e "${GREEN}✅ Docker installed:${NC} $(docker --version)"
echo -e "${GREEN}✅ Docker Compose installed:${NC} $(docker-compose --version)"
echo ""

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo ""
    echo "Please start Docker Desktop from Applications"
    echo "Or start Colima: colima start"
    exit 1
fi

echo -e "${GREEN}✅ Docker daemon is running${NC}"
echo ""

# Ask user what to do
echo "What would you like to do?"
echo "1) Build and start local environment (fresh start)"
echo "2) Start existing environment"
echo "3) Stop environment"
echo "4) Clean restart (remove volumes and rebuild)"
echo "5) View logs"
echo "6) Shell into API container"
echo "7) Shell into database"
echo "8) Exit"
echo ""
read -p "Enter choice [1-8]: " choice

case $choice in
    1)
        echo ""
        echo "🔨 Building and starting services..."
        docker-compose -f docker-compose.local.yml up -d --build
        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        echo ""
        echo "📊 Container status:"
        docker-compose -f docker-compose.local.yml ps
        echo ""
        echo "🌐 Access the application:"
        echo "   Frontend: http://localhost:8001"
        echo "   API Docs: http://localhost:8001/docs"
        echo ""
        echo "📝 View logs:"
        echo "   docker-compose -f docker-compose.local.yml logs -f"
        echo ""
        read -p "Would you like to view logs now? [y/N]: " view_logs
        if [[ $view_logs == "y" || $view_logs == "Y" ]]; then
            docker-compose -f docker-compose.local.yml logs -f
        fi
        ;;

    2)
        echo ""
        echo "🚀 Starting services..."
        docker-compose -f docker-compose.local.yml up -d
        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        docker-compose -f docker-compose.local.yml ps
        echo ""
        echo "🌐 Access at: http://localhost:8001"
        ;;

    3)
        echo ""
        echo "🛑 Stopping services..."
        docker-compose -f docker-compose.local.yml down
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;

    4)
        echo ""
        echo -e "${YELLOW}⚠️  This will remove all volumes (database data will be lost!)${NC}"
        read -p "Are you sure? [y/N]: " confirm
        if [[ $confirm == "y" || $confirm == "Y" ]]; then
            echo "🧹 Stopping and removing containers, volumes..."
            docker-compose -f docker-compose.local.yml down -v
            echo "🔨 Rebuilding..."
            docker-compose -f docker-compose.local.yml up -d --build
            echo -e "${GREEN}✅ Clean restart complete!${NC}"
            docker-compose -f docker-compose.local.yml ps
        else
            echo "Cancelled."
        fi
        ;;

    5)
        echo ""
        echo "📝 Showing logs (Ctrl+C to exit)..."
        docker-compose -f docker-compose.local.yml logs -f
        ;;

    6)
        echo ""
        echo "🐚 Opening shell in API container..."
        docker-compose -f docker-compose.local.yml exec api bash
        ;;

    7)
        echo ""
        echo "🗄️  Opening PostgreSQL shell..."
        echo "Database: ward_ops"
        echo "User: ward_admin"
        docker-compose -f docker-compose.local.yml exec postgres psql -U ward_admin -d ward_ops
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
echo "💡 Tip: To see all available commands, run:"
echo "   docker-compose -f docker-compose.local.yml --help"
