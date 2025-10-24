#!/bin/bash

##############################################################################
# Simple Frontend Deployment (Build Locally, Deploy to Server)
##############################################################################
#
# This script:
# 1. Builds the frontend on your LOCAL machine (Mac)
# 2. Creates a tar.gz package
# 3. Provides instructions to copy to production server
#
# Use this if Node.js is not installed on production server
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "=========================================================================="
echo -e "${GREEN}🚀 BUILDING FRONTEND OPTIMIZATIONS LOCALLY${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Step 1: Verify Environment
##############################################################################
echo -e "${BLUE}[1/5] Verifying local environment...${NC}"
echo ""

# Check if in correct directory
if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Error: frontend directory not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if node is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Error: Node.js is not installed${NC}"
    echo "Please install Node.js first: https://nodejs.org/"
    exit 1
fi

echo "✅ Environment check passed"
echo "   Node version: $(node --version)"
echo "   npm version: $(npm --version)"
echo ""

##############################################################################
# Step 2: Install Dependencies
##############################################################################
echo -e "${BLUE}[2/5] Installing dependencies...${NC}"
echo ""

cd frontend

# Install dependencies
echo "Installing npm packages..."
npm install

# Install optimization libraries
echo "Installing optimization libraries..."
npm install --save @tanstack/react-virtual react-intersection-observer

echo ""
echo "✅ Dependencies installed"
echo ""

##############################################################################
# Step 3: Build Production Bundle
##############################################################################
echo -e "${BLUE}[3/5] Building production bundle...${NC}"
echo ""

echo "Building with Vite..."
npm run build

echo ""
echo "✅ Build complete"
echo ""

# Show build stats
if [ -d "dist" ]; then
    DIST_SIZE=$(du -sh dist 2>/dev/null | cut -f1 || echo "unknown")
    echo "Bundle size: $DIST_SIZE"

    JS_FILES=$(find dist -name "*.js" 2>/dev/null | wc -l | tr -d ' ')
    CSS_FILES=$(find dist -name "*.css" 2>/dev/null | wc -l | tr -d ' ')
    echo "Files: $JS_FILES JavaScript, $CSS_FILES CSS"
fi

echo ""

##############################################################################
# Step 4: Create Deployment Package
##############################################################################
echo -e "${BLUE}[4/5] Creating deployment package...${NC}"
echo ""

# Go back to project root
cd ..

# Create package
PACKAGE_NAME="ward-ops-frontend-$(date +%Y%m%d-%H%M%S).tar.gz"
echo "Creating package: $PACKAGE_NAME"
tar -czf "$PACKAGE_NAME" -C frontend/dist .

PACKAGE_SIZE=$(du -sh "$PACKAGE_NAME" 2>/dev/null | cut -f1 || echo "unknown")
echo "Package size: $PACKAGE_SIZE"

echo ""
echo "✅ Package created: $PACKAGE_NAME"
echo ""

##############################################################################
# Step 5: Deployment Instructions
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ BUILD COMPLETE! READY TO DEPLOY${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}📦 DEPLOYMENT PACKAGE:${NC}"
echo ""
echo "  File: $PACKAGE_NAME"
echo "  Size: $PACKAGE_SIZE"
echo "  Location: $(pwd)/$PACKAGE_NAME"
echo ""

echo -e "${CYAN}🚀 DEPLOYMENT STEPS:${NC}"
echo ""

echo -e "${YELLOW}Step 1: Copy package to production server${NC}"
echo ""
echo "  scp $PACKAGE_NAME root@10.30.25.46:/tmp/"
echo ""

echo -e "${YELLOW}Step 2: On production server, extract and deploy${NC}"
echo ""
echo "  # SSH to production server"
echo "  ssh root@10.30.25.46"
echo ""
echo "  # Extract package"
echo "  cd /tmp"
echo "  mkdir -p ward-ops-frontend"
echo "  tar -xzf $PACKAGE_NAME -C ward-ops-frontend/"
echo ""
echo "  # Find where frontend is served from"
echo "  # Common locations:"
echo "  # - /var/www/html/ward-ops"
echo "  # - /usr/share/nginx/html/ward-ops"
echo "  # - /opt/ward-ops/frontend"
echo ""
echo "  # Example: Copy to nginx"
echo "  sudo cp -r ward-ops-frontend/* /var/www/html/ward-ops/"
echo ""
echo "  # Or if using specific user"
echo "  sudo cp -r ward-ops-frontend/* /home/wardops/frontend/"
echo ""
echo "  # Set permissions"
echo "  sudo chown -R www-data:www-data /var/www/html/ward-ops/"
echo "  # OR"
echo "  sudo chown -R wardops:wardops /home/wardops/frontend/"
echo ""
echo "  # Restart web server (if needed)"
echo "  sudo systemctl restart nginx"
echo "  # OR"
echo "  sudo systemctl restart apache2"
echo ""

echo -e "${YELLOW}Step 3: Verify deployment${NC}"
echo ""
echo "  # Open browser to your Ward-Ops URL"
echo "  # Press Ctrl+Shift+R to clear cache"
echo "  # Open DevTools (F12) → Network tab"
echo "  # Verify:"
echo "    - Initial load <500ms ✅"
echo "    - <20 network requests ✅"
echo "    - Search doesn't trigger requests on every keystroke ✅"
echo ""

echo -e "${CYAN}📝 ALTERNATIVE: One-line deployment${NC}"
echo ""
echo "  # If you know the frontend path, run this:"
echo "  scp $PACKAGE_NAME root@10.30.25.46:/tmp/ && \\"
echo "  ssh root@10.30.25.46 'cd /tmp && rm -rf ward-ops-frontend && mkdir ward-ops-frontend && tar -xzf $PACKAGE_NAME -C ward-ops-frontend && sudo cp -r ward-ops-frontend/* /var/www/html/ward-ops/ && sudo systemctl restart nginx'"
echo ""

echo -e "${CYAN}🔍 FIND FRONTEND LOCATION:${NC}"
echo ""
echo "  # SSH to production server and run:"
echo "  ssh root@10.30.25.46"
echo ""
echo "  # Check where Ward-Ops frontend is served from:"
echo "  sudo find / -name 'index.html' -path '*/ward*' 2>/dev/null | grep -v node_modules"
echo ""
echo "  # Check nginx config:"
echo "  sudo cat /etc/nginx/sites-enabled/default | grep root"
echo ""
echo "  # Check apache config:"
echo "  sudo cat /etc/apache2/sites-enabled/*.conf | grep DocumentRoot"
echo ""

echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

echo -e "${GREEN}Package ready: $PACKAGE_NAME${NC}"
echo ""

exit 0
