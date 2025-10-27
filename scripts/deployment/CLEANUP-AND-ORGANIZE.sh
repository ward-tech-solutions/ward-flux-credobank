#!/bin/bash
# Clean up and organize WARD OPS project structure
# Move documentation and old files to organized directories

set -e

echo "==========================================="
echo "🧹 ORGANIZING WARD OPS PROJECT STRUCTURE"
echo "==========================================="
echo ""

# Create organized directory structure
echo "📁 Creating organized directories..."
mkdir -p docs/deployment-history
mkdir -p docs/troubleshooting
mkdir -p docs/architecture
mkdir -p docs/old-compose-files
mkdir -p scripts/deployment
mkdir -p scripts/diagnostics
mkdir -p scripts/migration

# Move deployment-related documentation
echo "📚 Organizing deployment documentation..."
mv -f *DEPLOY*.md docs/deployment-history/ 2>/dev/null || true
mv -f *DEPLOYMENT*.md docs/deployment-history/ 2>/dev/null || true
mv -f *-COMPLETE.md docs/deployment-history/ 2>/dev/null || true
mv -f *PHASES*.md docs/deployment-history/ 2>/dev/null || true

# Move troubleshooting and diagnostic docs
echo "🔍 Organizing troubleshooting docs..."
mv -f *FIX*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *ISSUE*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *BUG*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *CRITICAL*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *DIAGNOSTIC*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *ROOT-CAUSE*.md docs/troubleshooting/ 2>/dev/null || true

# Move architecture and optimization docs
echo "🏗️  Organizing architecture docs..."
mv -f *OPTIMIZATION*.md docs/architecture/ 2>/dev/null || true
mv -f *SCALING*.md docs/architecture/ 2>/dev/null || true
mv -f *ARCHITECTURE*.md docs/architecture/ 2>/dev/null || true
mv -f *INTEGRATION*.md docs/architecture/ 2>/dev/null || true
mv -f *UPGRADE*.md docs/architecture/ 2>/dev/null || true

# Move old docker-compose files (keep only production one)
echo "🐳 Organizing Docker Compose files..."
mv -f docker-compose.local.yml docs/old-compose-files/ 2>/dev/null || true
mv -f docker-compose.monitoring.yml docs/old-compose-files/ 2>/dev/null || true
mv -f docker-compose.yml docs/old-compose-files/ 2>/dev/null || true
mv -f docker-compose.production-1500-devices.yml docs/old-compose-files/ 2>/dev/null || true
mv -f docker-compose.production-local.yml docs/old-compose-files/ 2>/dev/null || true
# Keep only docker-compose.production-priority-queues.yml as main

# Move deployment scripts
echo "📜 Organizing deployment scripts..."
mv -f deploy*.sh scripts/deployment/ 2>/dev/null || true
mv -f DEPLOY*.sh scripts/deployment/ 2>/dev/null || true
mv -f FINAL*.sh scripts/deployment/ 2>/dev/null || true
mv -f FIX*.sh scripts/deployment/ 2>/dev/null || true

# Move diagnostic scripts
echo "🔧 Organizing diagnostic scripts..."
mv -f check*.sh scripts/diagnostics/ 2>/dev/null || true
mv -f test*.sh scripts/diagnostics/ 2>/dev/null || true
mv -f verify*.sh scripts/diagnostics/ 2>/dev/null || true
mv -f detect*.py scripts/diagnostics/ 2>/dev/null || true
mv -f *diagnostic*.sh scripts/diagnostics/ 2>/dev/null || true

# Move migration scripts
echo "🔄 Organizing migration scripts..."
mv -f apply*.sh scripts/migration/ 2>/dev/null || true
mv -f migrate*.sh scripts/migration/ 2>/dev/null || true
mv -f update*.sh scripts/migration/ 2>/dev/null || true

# Move analysis documents
echo "📊 Moving analysis documents..."
mv -f *ANALYSIS*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *FLAPPING*.md docs/troubleshooting/ 2>/dev/null || true
mv -f *CACHE*.md docs/troubleshooting/ 2>/dev/null || true

# Keep only essential files in root
echo ""
echo "✅ Keeping essential files in root:"
echo "  - README.md"
echo "  - CLAUDE-QUICK-REFERENCE.md"
echo "  - .env.production"
echo "  - docker-compose.production-priority-queues.yml"
echo "  - Dockerfile"
echo "  - requirements.txt"
echo "  - main.py"
echo ""

# Create a clean README if it doesn't exist
if [ ! -f README.md ]; then
cat > README.md << 'EOF'
# WARD OPS - Credobank Monitoring System

Production monitoring system for Credobank's network infrastructure.

## 🚀 Quick Start

```bash
# Deploy to production
docker-compose -f docker-compose.production-priority-queues.yml up -d

# Check status
docker ps | grep wardops
```

## 📊 System Features

- **Real-time Monitoring**: 10-second device detection
- **ISP Link Priority**: Special monitoring for .5 octet IPs
- **Flapping Detection**: Automatic alert suppression for unstable devices
- **875+ Devices**: Scalable architecture with batched processing

## 📁 Project Structure

```
ward-ops-credobank/
├── monitoring/         # Core monitoring logic
├── routers/           # API endpoints
├── models/            # Database models
├── utils/             # Utility functions
├── migrations/        # Database migrations
├── docs/              # Documentation
│   ├── deployment-history/
│   ├── troubleshooting/
│   └── architecture/
├── scripts/           # Operational scripts
│   ├── deployment/
│   ├── diagnostics/
│   └── migration/
└── docker-compose.production-priority-queues.yml
```

## 🔧 Key Commands

See `CLAUDE-QUICK-REFERENCE.md` for detailed commands.

## 📈 Monitoring

- Web UI: http://10.30.25.46:5001
- API Health: http://10.30.25.46:5001/api/v1/health
- VictoriaMetrics: http://10.30.25.46:8428

## 🆘 Support

WARD Tech Solutions - Banking Infrastructure Team
EOF
fi

# Show final structure
echo "📁 Final project structure:"
echo "=========================="
ls -la | grep -E "^d|\.yml$|\.md$|\.py$|\.txt$|Dockerfile" | head -20

echo ""
echo "📊 Cleanup Summary:"
echo "==================="
find docs -type f | wc -l | xargs echo "  Documentation files organized:"
find scripts -type f | wc -l | xargs echo "  Script files organized:"
ls -1 *.md 2>/dev/null | wc -l | xargs echo "  README files in root:"
ls -1 *.yml 2>/dev/null | wc -l | xargs echo "  Docker Compose files in root:"

echo ""
echo "✅ Project structure cleaned and organized!"
echo ""
echo "Next steps:"
echo "1. Review docs/ directory for historical documentation"
echo "2. Review scripts/ directory for operational scripts"
echo "3. Commit the organized structure to git"
echo ""