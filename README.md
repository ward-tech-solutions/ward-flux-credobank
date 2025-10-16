# WARD OPS - CredoBank Edition

**Production-ready network monitoring deployment for CredoBank with 875 devices across 128 branches.**

This is the CredoBank-specific deployment with pre-seeded data including all devices, branches, Georgian regions/cities, and alert configurations.

## 🏦 CredoBank Deployment

### Pre-seeded Data
- **875 standalone devices** across all CredoBank branches
- **128 branches** with complete information
- **Georgian regions and cities** database
- **Alert rules** configured for CredoBank infrastructure
- **Regional managers** with proper permissions

## 🚀 Quick Start

### Using Docker (Recommended)

\`\`\`bash
# Start the full stack with CredoBank seed data
docker-compose -f docker-compose.production-local.yml up -d

# Or use the convenience script
./start-production-with-seeds.sh

# Access the application
# Web UI: http://localhost:5001
# PostgreSQL: localhost:5432
# Redis: localhost:6379

# Default credentials
# Username: admin
# Password: admin123
\`\`\`

## 📁 Project Structure

\`\`\`
ward-ops-credobank/
├── frontend/              # React TypeScript frontend
├── routers/              # FastAPI backend routers  
├── monitoring/           # SNMP monitoring engine
├── seeds/
│   ├── core/            # Generic seed data
│   └── credobank/       # CredoBank-specific seed data
│       ├── devices.json
│       ├── branches.json
│       ├── georgian_regions.json
│       └── georgian_cities.json
├── scripts/
│   ├── seed_core.py
│   ├── seed_credobank.py          # CredoBank seeding script
│   └── export_credobank_data.py   # Data export utility
├── migrations/           # SQL schema migrations
└── docker-compose.production-local.yml
\`\`\`

## 🔧 Configuration

### Port Configuration (Production ports)

- **Web UI**: `5001`
- **PostgreSQL**: `5432`
- **Redis**: `6379`

### Environment Variables

The `.env.production.local` file contains production settings:

\`\`\`env
DATABASE_URL=postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
REDIS_URL=redis://:redispass@redis:6379/0
ENVIRONMENT=production
MONITORING_MODE=snmp_only
\`\`\`

## 📊 CredoBank Data

### Devices
- 875 devices monitored across all branches
- Device types: ATMs, PayBoxes, Switches, Routers, Servers
- Complete SNMP configuration for each device
- Organized by branch and region

### Branches
- 128 branches across Georgia
- Each branch linked to Georgian cities
- Regional organization (Tbilisi, Kutaisi, Batumi, etc.)
- Contact information and addresses

### Geographic Data
- Complete Georgian regions database
- All cities mapped to regions  
- Coordinates for map visualization
- Regional manager assignments

## 🐳 Docker Commands

\`\`\`bash
# Build and start with seeds
docker-compose -f docker-compose.production-local.yml up -d --build

# View logs
docker-compose -f docker-compose.production-local.yml logs -f api

# Stop all services
docker-compose -f docker-compose.production-local.yml down

# Export current data
./scripts/export_credobank_data.py
\`\`\`

## 🔄 Data Management

### Export Data
\`\`\`bash
# Export current database to JSON files
python scripts/export_credobank_data.py
\`\`\`

### Update Seed Data
1. Make changes in the web UI
2. Export to JSON: `python scripts/export_credobank_data.py`
3. Commit updated seed files to Git

## 📖 CredoBank-Specific Features

- **Regional Management**: Managers can only see their assigned regions
- **Georgian Language Support**: Full support for Georgian characters
- **Custom Alert Rules**: Tailored for CredoBank infrastructure
- **Branch Hierarchy**: Devices organized by branch structure

## 🔐 Security

- Production credentials should be rotated immediately
- SNMP community strings are encrypted
- Role-based access control (RBAC) enabled
- Regional data isolation for managers

## 📚 Documentation

- [Run Production Locally](RUN_PRODUCTION_LOCALLY.md)
- [CredoBank Data Seeding](CREDOBANK_DATA_SEED.md)
- [Deployment Guide](DEPLOYMENT_READY.md)
- [Quick Start](QUICK_START.md)

## 🆘 Support

For CredoBank-specific issues, contact the WARD OPS deployment team.

---

**WARD OPS CredoBank Edition** - Production deployment for CredoBank network monitoring
