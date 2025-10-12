# CredoBank WARD OPS - Deployment Package

> **Complete monitoring solution for CredoBank's network infrastructure**
> Pre-configured, production-ready, one-command deployment

---

## 📋 What's Included

This deployment package contains everything needed to run WARD OPS monitoring platform:

- **Pre-seeded Database**: PostgreSQL with CredoBank-specific configuration and data
- **Application Stack**: FastAPI backend + React frontend
- **Background Workers**: Celery for SNMP polling and alert evaluation
- **Task Queue**: Redis for job management
- **Automated Setup**: One-command deployment script

---

## 🚀 Quick Start (5 Minutes)

### For System Administrators

**On the target server, run these commands:**

```bash
# 1. Transfer this folder to the server
scp -r deploy/ user@server-ip:/tmp/

# 2. SSH into the server
ssh user@server-ip

# 3. Run the deployment script
cd /tmp/deploy
sudo ./deploy.sh
```

That's it! The script will:
- Check prerequisites
- Generate secure secrets
- Pull Docker images
- Configure services
- Start the monitoring platform

**Access the application:**
- Web Interface: `http://your-server-ip:3000`
- API Endpoint: `http://your-server-ip:5001`

**Default Login:**
- Username: `admin`
- Password: `admin123` (change immediately after login)

---

## 📦 What You Need

### Server Requirements

**Minimum:**
- **OS**: Ubuntu 22.04 LTS (or RHEL 8+/Debian 11+)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 20 GB free space
- **Network**: Internet access to pull Docker images

**Recommended:**
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Disk**: 50 GB (with SSD for database)

### Software Prerequisites

The deployment script will check these, but you need:

1. **Docker Engine 20.10+**
2. **Docker Compose v2.0+**
3. **Python 3.8+** (for secret generation)

---

## 📁 Package Contents

```
deploy/
├── deploy.sh                   # Automated deployment script
├── docker-compose.yml          # Service orchestration
├── .env.prod.example           # Configuration template
├── README.md                   # This file
└── DEPLOYMENT.md               # Detailed technical guide
```

---

## 🔧 Installation Methods

### Method 1: Automated (Recommended)

**Run the deployment script with sudo:**

```bash
sudo ./deploy.sh
```

The script will:
1. ✅ Check prerequisites (Docker, Docker Compose, Python)
2. ✅ Create installation directory at `/opt/wardops`
3. ✅ Generate secure random secrets automatically
4. ✅ Prompt for admin password
5. ✅ Pull Docker images from registry
6. ✅ Start all services
7. ✅ Optionally enable auto-start on boot

**Interactive prompts:**
- Admin password (default: admin123)
- Enable systemd auto-start (recommended: yes)

---

### Method 2: Manual (Advanced)

If you prefer manual control:

#### Step 1: Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for group changes
```

#### Step 2: Prepare Files

```bash
# Create installation directory
sudo mkdir -p /opt/wardops
sudo cp docker-compose.yml /opt/wardops/
sudo cp .env.prod.example /opt/wardops/.env.prod
cd /opt/wardops
```

#### Step 3: Configure Environment

```bash
# Edit .env.prod and set these variables
sudo nano /opt/wardops/.env.prod
```

**Required changes:**
- `SECRET_KEY` - Generate with: `python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`
- `ENCRYPTION_KEY` - Generate with: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `REDIS_PASSWORD` - Use: `openssl rand -base64 24`
- `DEFAULT_ADMIN_PASSWORD` - Set your admin password

#### Step 4: Pull Images

```bash
# Log in to registry (if using private registry)
docker login

# Pull images
docker pull ward_flux/wardops-app:credobank-latest
docker pull ward_flux/wardops-postgres-seeded:credobank-latest
```

#### Step 5: Start Services

```bash
cd /opt/wardops
docker compose up -d
```

---

## 🔐 Security Checklist

**After deployment, complete these security steps:**

- [ ] Change admin password from default `admin123`
- [ ] Review `.env.prod` and ensure secrets are unique
- [ ] Configure firewall to restrict access:
  ```bash
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 5001/tcp  # API (or use reverse proxy)
  sudo ufw allow 3000/tcp  # Frontend (or use reverse proxy)
  sudo ufw enable
  ```
- [ ] Set up reverse proxy (Nginx/Caddy) with SSL/TLS
- [ ] Backup `.env.prod` to secure location
- [ ] Configure regular database backups
- [ ] Review and configure CORS_ORIGINS in `.env.prod`

---

## 🔄 Day 2 Operations

### View Logs

```bash
cd /opt/wardops

# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f celery-worker
docker compose logs -f db
```

### Restart Services

```bash
cd /opt/wardops

# Restart all
docker compose restart

# Restart specific service
docker compose restart api
```

### Stop Services

```bash
cd /opt/wardops
docker compose down
```

### Update to New Version

```bash
cd /opt/wardops

# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Verify
docker compose ps
```

### Backup Database

```bash
# Create backup
docker compose exec db pg_dump -U fluxdb ward_ops > /opt/wardops/backups/ward_ops_$(date +%Y%m%d).sql

# Or use custom format (recommended)
docker compose exec db pg_dump -U fluxdb -Fc ward_ops > /opt/wardops/backups/ward_ops_$(date +%Y%m%d).backup
```

### Restore Database

```bash
# Stop services
docker compose down

# Start only database
docker compose up -d db

# Restore
docker compose exec -T db psql -U fluxdb ward_ops < /opt/wardops/backups/ward_ops_YYYYMMDD.sql

# Or from custom format
docker compose exec db pg_restore -U fluxdb -d ward_ops /backups/ward_ops_YYYYMMDD.backup

# Start all services
docker compose up -d
```

---

## 🌐 Access URLs

Once deployed, access these URLs (replace `your-server-ip` with actual IP):

| Service | URL | Purpose |
|---------|-----|---------|
| **Web UI** | `http://your-server-ip:3000` | Main dashboard and interface |
| **API** | `http://your-server-ip:5001` | REST API endpoints |
| **Health Check** | `http://your-server-ip:5001/api/v1/health` | Service health status |
| **API Docs** | `http://your-server-ip:5001/docs` | Interactive API documentation |

---

## 🩺 Health Check & Troubleshooting

### Check Service Status

```bash
cd /opt/wardops
docker compose ps
```

**Expected output:**
```
NAME                 STATUS              PORTS
wardops-api          Up (healthy)        0.0.0.0:5001->5001/tcp
wardops-beat         Up
wardops-db           Up (healthy)        5432/tcp
wardops-frontend     Up                  0.0.0.0:3000->3000/tcp
wardops-redis        Up                  6379/tcp
wardops-worker       Up
```

### Test API Health

```bash
curl http://localhost:5001/api/v1/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Common Issues

#### Issue: "Cannot connect to Docker daemon"
**Solution:**
```bash
# Start Docker service
sudo systemctl start docker

# Enable auto-start
sudo systemctl enable docker
```

#### Issue: "Port already in use"
**Solution:**
```bash
# Check what's using the port
sudo lsof -i :5001
sudo lsof -i :3000

# Kill the process or change ports in docker-compose.yml
```

#### Issue: "Permission denied"
**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
```

#### Issue: Services keep restarting
**Solution:**
```bash
# Check logs for errors
docker compose logs --tail=50

# Check disk space
df -h

# Check memory
free -h
```

---

## 📊 Monitoring & Alerts

### Configure Alert Rules

1. Log into web UI: `http://your-server-ip:3000`
2. Navigate to **Settings > Alert Rules**
3. Use pre-configured templates or create custom rules
4. Set thresholds for:
   - Device availability (ping)
   - CPU usage
   - Memory usage
   - Interface bandwidth

### View Active Alerts

- Dashboard shows active alerts
- Filter by severity: Critical, High, Warning, Info
- Acknowledge or resolve alerts

### SNMP Device Management

1. Navigate to **Devices** page
2. Click **Add Device** or **Bulk Import**
3. Configure SNMP credentials (v2c or v3)
4. Set polling interval (default: 120 seconds)

---

## 🔧 Advanced Configuration

### Enable Auto-Start on Boot

```bash
sudo systemctl enable wardops
sudo systemctl start wardops
```

### Set Up Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name ops.credobank.ge;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Scale Workers for Large Deployments

Edit `docker-compose.yml`:

```yaml
celery-worker:
  # ... existing config ...
  deploy:
    replicas: 4  # Run 4 worker instances
```

Then:
```bash
docker compose up -d --scale celery-worker=4
```

---

## 📞 Support

### Documentation
- Full deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- API documentation: `http://your-server-ip:5001/docs`
- Architecture overview: `/docs/ARCHITECTURE.md` (in main repo)

### Getting Help
- Check logs: `docker compose logs -f`
- Review health: `curl http://localhost:5001/api/v1/health`
- Contact: Ward Tech Solutions support team

### Reporting Issues
When reporting issues, include:
1. Output of `docker compose ps`
2. Relevant logs: `docker compose logs --tail=100`
3. Server specs and OS version
4. Steps to reproduce

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Client Browser                      │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│         Frontend (React + Vite)                  │
│         Port: 3000                               │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│         API Server (FastAPI)                     │
│         Port: 5001                               │
└────────────┬────────────┬───────────────────────┘
             │            │
             ↓            ↓
┌────────────────┐  ┌──────────────────┐
│   PostgreSQL   │  │      Redis       │
│   (with seed)  │  │   (Task Queue)   │
└────────────────┘  └────────┬─────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │  Celery Worker   │
                    │  (SNMP Polling)  │
                    └──────────────────┘
                              │
                              ↓
                    ┌──────────────────┐
                    │   Celery Beat    │
                    │   (Scheduler)    │
                    └──────────────────┘
```

---

## 📝 Changelog

### v2.0 - CredoBank Production Release
- Pre-seeded PostgreSQL database
- Alert rules management system
- SNMP standalone monitoring
- Hybrid Zabbix integration support
- Production-ready deployment automation
- Comprehensive documentation

---

## 📄 License

Copyright (c) 2025 WARD Tech Solutions
Deployed for CredoBank - Internal Use Only

---

**Questions?** Contact your Ward Tech Solutions representative.
