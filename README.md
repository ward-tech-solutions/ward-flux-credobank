# WARD FLUX - Network Monitoring Platform

A modern, enterprise-grade network monitoring platform built with FastAPI, React, and VictoriaMetrics. WARD FLUX provides comprehensive network device monitoring, SNMP polling, real-time alerts, and advanced analytics.

## Features

### Core Monitoring Capabilities
- **Multi-Protocol Support**: Native SNMP polling and optional Zabbix integration
- **Real-Time Monitoring**: Live device status updates via WebSockets
- **Geographic Visualization**: Interactive network topology with map-based device locations
- **Advanced Analytics**: Historical metrics storage and analysis with VictoriaMetrics
- **Bulk Operations**: Import/export devices via CSV/Excel with validation

### Network Management
- **Device Discovery**: Automated network device discovery and classification
- **SNMP Polling**: Asynchronous SNMP v2c/v3 polling with configurable intervals
- **Alert Management**: Real-time alerting with customizable thresholds
- **Performance Metrics**: CPU, memory, bandwidth, and interface statistics
- **Topology Mapping**: Automated network topology discovery and visualization

### Security & Administration
- **Role-Based Access Control (RBAC)**: Admin, Manager, and Technician roles
- **JWT Authentication**: Secure token-based authentication
- **Encrypted Credentials**: AES-256 encryption for sensitive data
- **Audit Logging**: Comprehensive activity tracking
- **Multi-Tenancy**: Separate user workspaces and permissions

### Integration & Extensibility
- **Zabbix Integration**: Optional hybrid monitoring mode with existing Zabbix servers
- **REST API**: Complete API for automation and third-party integrations
- **Grafana Support**: Pre-configured dashboards for metrics visualization
- **Webhook Support**: Custom alert notifications and integrations
- **CSV/Excel Import**: Bulk device management capabilities

## Technology Stack

### Backend
- **FastAPI**: Modern async Python web framework
- **SQLAlchemy**: ORM with PostgreSQL/SQLite support
- **Celery**: Distributed task queue for SNMP polling
- **Redis**: Task queue backend and caching layer
- **VictoriaMetrics**: High-performance time-series database

### Frontend
- **React 18**: Modern UI with TypeScript
- **Vite**: Fast development and optimized builds
- **TailwindCSS**: Utility-first CSS framework
- **Recharts**: Interactive data visualization
- **React Leaflet**: Geographic mapping and topology

### Infrastructure
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and SSL termination (optional)
- **PostgreSQL**: Production database
- **Grafana**: Advanced metrics visualization

## Prerequisites

### For Docker Deployment (Recommended)
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

### For Manual Installation
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or SQLite for development)
- Redis 7+
- VictoriaMetrics (optional, for production)

## Quick Start with Docker

### 1. Clone the Repository
```bash
git clone https://github.com/ward-tech-solutions/ward-flux.git
cd ward-flux
```

### 2. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required Environment Variables:**
```bash
# Database
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://ward:your_secure_password@postgres:5432/ward_flux

# Redis
REDIS_PASSWORD=your_redis_password
REDIS_URL=redis://:your_redis_password@redis:6379/0

# Security (IMPORTANT: Generate these!)
ENCRYPTION_KEY=<generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
SECRET_KEY=<generate with: openssl rand -base64 32>

# Zabbix (Optional - only if using Zabbix integration)
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_USER=your_zabbix_username
ZABBIX_PASSWORD=your_zabbix_password

# Grafana
GRAFANA_PASSWORD=your_grafana_password
```

### 3. Launch the Stack
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service health
docker-compose ps
```

### 4. Access the Platform
- **Web Interface**: http://localhost:5001
- **API Documentation**: http://localhost:5001/docs
- **Grafana**: http://localhost:3000
- **VictoriaMetrics**: http://localhost:8428

**Default Credentials:**
- Username: `admin`
- Password: `admin123` (change immediately after first login)

## Prebuilt Container Image

Production images are published automatically to GitHub Container Registry. Pull the latest build directly:

```bash
docker pull ghcr.io/ward-tech-solutions/ward-flux-v2:latest
```

Run the container with persistent volumes and required secrets:

```bash
docker run -d \
  --name ward-flux \
  -p 5001:5001 \
  -v ward-flux-data:/data \
  -v ward-flux-logs:/logs \
  -e SECRET_KEY="$(openssl rand -base64 32)" \
  -e ENCRYPTION_KEY="$(python3 - <<'PY';from cryptography.fernet import Fernet;print(Fernet.generate_key().decode());PY)" \
  -e DEFAULT_ADMIN_PASSWORD="admin123" \
  -e DATABASE_URL="sqlite:////data/ward_flux.db" \
  ghcr.io/ward-tech-solutions/ward-flux-v2:latest
```

Additional environment variables (e.g., `REDIS_URL`, `ZABBIX_URL`, `ZABBIX_USER`, `ZABBIX_PASSWORD`) can be supplied to enable advanced features. On first launch the platform creates an admin account (`admin` / `admin123`); update the password immediately after logging in.

## Manual Installation

### 1. Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Initialize Database
```bash
# Set environment variables
export DATABASE_URL="sqlite:///./data/ward_flux.db"
export ENCRYPTION_KEY="<generate your key>"

# Create database tables
python3 -c "from database import init_db; init_db()"
```

### 4. Start Services
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start VictoriaMetrics (optional)
victoria-metrics

# Terminal 3: Start Celery Worker
celery -A celery_app worker --loglevel=info

# Terminal 4: Start Celery Beat
celery -A celery_app beat --loglevel=info

# Terminal 5: Start API Server
uvicorn main:app --host 0.0.0.0 --port 5001
```

## Configuration

### Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL or SQLite connection string | Yes | - |
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes (Docker) | - |
| `REDIS_URL` | Redis connection string | Yes | `redis://localhost:6379/0` |
| `REDIS_PASSWORD` | Redis password | Yes (Docker) | - |
| `VICTORIA_URL` | VictoriaMetrics endpoint | No | `http://victoriametrics:8428` |
| `ENCRYPTION_KEY` | AES encryption key for credentials | Yes | - |
| `SECRET_KEY` | JWT signing secret | Yes | - |
| `ZABBIX_URL` | Zabbix API endpoint | No | - |
| `ZABBIX_USER` | Zabbix username | No | - |
| `ZABBIX_PASSWORD` | Zabbix password | No | - |
| `GRAFANA_PASSWORD` | Grafana admin password | Yes (Docker) | - |
| `LOG_LEVEL` | Application log level | No | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins | No | `*` |

### Monitoring Modes

WARD FLUX supports three monitoring modes:

1. **SNMP Only** (Default): Native SNMP polling without Zabbix
2. **Zabbix Only**: Use existing Zabbix infrastructure
3. **Hybrid**: Combined SNMP + Zabbix monitoring

Set the mode in the UI under Settings > Configuration.

### SNMP Configuration

For SNMP monitoring, configure the following in the UI:
- **SNMP Version**: v2c or v3
- **Community String**: For v2c (e.g., "public")
- **Polling Interval**: 60-300 seconds recommended
- **Timeout/Retries**: Adjust based on network conditions

## Usage

### Adding Devices

**Single Device:**
1. Navigate to Dashboard > Add Device
2. Enter device details (hostname, IP, SNMP credentials)
3. Click "Save" to add the device

**Bulk Import:**
1. Download CSV/Excel template from Dashboard > Bulk Operations
2. Fill in device information
3. Upload and validate the file
4. Review and confirm the import

### Viewing Metrics

1. Click on any device to view detailed metrics
2. Select time range and metric type
3. Export data as needed

### Setting Up Alerts

1. Navigate to Settings > Alerts
2. Configure alert thresholds for CPU, memory, bandwidth
3. Set notification preferences (email, webhook)

### Generating Reports

1. Go to Reports section
2. Select report type (MTTR, uptime, performance)
3. Choose date range and devices
4. Export to PDF/Excel

## Development

### Running in Development Mode

```bash
# Backend with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 5001

# Frontend with hot reload
cd frontend
npm run dev
```

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend
npm run test
```

### Code Quality

```bash
# Python linting
ruff check .
black .

# Frontend linting
cd frontend
npm run lint
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:5001/docs
- **ReDoc**: http://localhost:5001/redoc

### Authentication

All API endpoints require JWT authentication (except `/auth/token`).

```bash
# Get access token
curl -X POST "http://localhost:5001/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Use token in requests
curl -X GET "http://localhost:5001/api/v1/devices" \
  -H "Authorization: Bearer <your_token>"
```

## Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

**SNMP Polling Failures:**
- Verify SNMP is enabled on target devices
- Check firewall rules (UDP port 161)
- Validate SNMP community string/credentials

**Frontend Build Errors:**
```bash
# Clear cache and rebuild
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

**Redis Connection Issues:**
```bash
# Test Redis connectivity
redis-cli -h localhost -p 6379 ping
```

### Logs

View application logs:
```bash
# Docker deployment
docker-compose logs -f api
docker-compose logs -f celery-worker

# Manual installation
tail -f logs/ward_flux.log
```

## Performance Tuning

### Recommended Settings

**For 100-500 devices:**
- Celery workers: 4
- Polling interval: 120s
- Redis memory: 512MB
- PostgreSQL shared_buffers: 256MB

**For 500-2000 devices:**
- Celery workers: 8
- Polling interval: 180s
- Redis memory: 2GB
- PostgreSQL shared_buffers: 1GB

### Scaling

For large deployments (2000+ devices):
1. Use dedicated PostgreSQL server
2. Scale Celery workers horizontally
3. Implement Redis clustering
4. Use external VictoriaMetrics cluster

## Security Best Practices

1. **Change Default Passwords**: Update admin password immediately
2. **Use Strong Encryption Keys**: Generate random keys for production
3. **Enable HTTPS**: Use Nginx with SSL certificates
4. **Restrict Network Access**: Firewall rules for production deployments
5. **Regular Updates**: Keep dependencies up to date
6. **Backup Database**: Implement automated backup strategy
7. **Monitor Logs**: Regular security audit log review

## Backup and Recovery

### Backup Database
```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U ward ward_flux > backup.sql

# SQLite backup
cp data/ward_flux.db data/ward_flux.db.backup
```

### Restore Database
```bash
# PostgreSQL restore
docker-compose exec -T postgres psql -U ward ward_flux < backup.sql

# SQLite restore
cp data/ward_flux.db.backup data/ward_flux.db
```

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/ward-tech-solutions/ward-flux/issues
- Documentation: https://github.com/ward-tech-solutions/ward-flux/wiki

## License

MIT License

Copyright (c) 2025 WARD Tech Solutions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- Built with FastAPI, React, and VictoriaMetrics
- Network monitoring powered by PySNMP
- Geographic visualization with Leaflet
- UI components styled with TailwindCSS

---

**WARD FLUX v2.0** - Enterprise Network Monitoring Platform
