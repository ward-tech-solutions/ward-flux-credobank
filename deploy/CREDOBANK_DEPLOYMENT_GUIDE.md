# CredoBank WARD FLUX Deployment Guide

## 🎯 Overview

This guide provides step-by-step instructions for deploying WARD FLUX Network Monitoring Platform to the CredoBank server.

**Deployment Method:** GitHub Container Registry (GHCR) + Docker Compose
**Access Method:** Jump Server / Bastion Host
**Installation Time:** ~10 minutes

---

## 📦 What Gets Deployed

- **Pre-seeded PostgreSQL 15** database with CredoBank network data
- **FastAPI Backend** with React frontend (embedded)
- **Redis** for task queue and caching
- **Celery Worker** for SNMP polling (standalone mode)
- **Celery Beat** for task scheduling

**Docker Images:**
- `ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest` - Application
- `ghcr.io/ward-tech-solutions/ward-flux-v2/credobank-postgres:latest` - Database

---

## 🔧 Prerequisites on CredoBank Server

### Required Software

1. **Docker Engine** (20.10+)
2. **Docker Compose** plugin (v2+)
3. **Git**
4. **Python 3** with `cryptography` module
5. **Internet access** to GitHub and ghcr.io

### Quick Check

```bash
# Check Docker
docker --version
docker compose version

# Check Git
git --version

# Check Python
python3 --version
python3 -c "from cryptography.fernet import Fernet; print('OK')"
```

### Install Prerequisites (if needed)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Git
sudo apt-get update && sudo apt-get install -y git

# Install Python dependencies
sudo apt-get install -y python3 python3-pip
sudo pip3 install cryptography
```

---

## 🚀 Deployment Steps

### Option 1: One-Command Deployment (Recommended)

**Step 1: SSH to CredoBank server through jump host**

```bash
ssh -J jumpuser@jump.credobank.com username@credobank-server
```

**Step 2: Run deployment command**

```bash
curl -fsSL https://raw.githubusercontent.com/ward-tech-solutions/ward-flux-v2/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**Step 3: Follow prompts**

- Enter admin password (or press Enter for default: `admin123`)
- Choose whether to enable auto-start on boot (recommended: `y`)

**That's it!** The script will:
- Clone the repository
- Generate secure secrets
- Pull Docker images from GHCR
- Start all services
- Run health checks

---

### Option 2: Manual Deployment (More Control)

**Step 1: SSH to server**

```bash
ssh -J jumpuser@jump.credobank.com username@credobank-server
```

**Step 2: Download deployment script**

```bash
curl -fsSL https://raw.githubusercontent.com/ward-tech-solutions/ward-flux-v2/client/credo-bank/deploy/deploy-from-github.sh -o deploy.sh
chmod +x deploy.sh
```

**Step 3: Review script (optional)**

```bash
less deploy.sh
```

**Step 4: Run deployment**

```bash
sudo ./deploy.sh
```

**Step 5: Verify deployment**

```bash
cd /opt/wardops
sudo ./verify.sh
```

---

## 🔐 Configuration

After deployment, the system is configured at `/opt/wardops/.env.prod`:

```bash
# View configuration (requires sudo)
sudo cat /opt/wardops/.env.prod
```

### Key Configuration Values

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Pre-configured |
| `REDIS_URL` | Redis connection | Auto-generated password |
| `SECRET_KEY` | JWT signing key | Auto-generated |
| `ENCRYPTION_KEY` | Fernet encryption key | Auto-generated |
| `DEFAULT_ADMIN_PASSWORD` | Admin user password | `admin123` or user-provided |
| `MONITORING_MODE` | Monitoring mode | `hybrid` (standalone) |
| `LOG_LEVEL` | Application log level | `INFO` |

### Update Configuration

```bash
cd /opt/wardops
sudo nano .env.prod
sudo docker compose restart
```

---

## ✅ Post-Deployment Verification

### Check Service Status

```bash
cd /opt/wardops
sudo docker compose ps
```

**Expected output:**
```
NAME              STATUS
wardops-api       Up (healthy)
wardops-beat      Up
wardops-db        Up (healthy)
wardops-redis     Up (healthy)
wardops-worker    Up
```

### Run Health Checks

```bash
cd /opt/wardops
sudo ./verify.sh
```

### Test API Endpoint

```bash
curl http://localhost:5001/api/v1/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "2.0.0"
}
```

### Test Web Interface

Open in browser:
```
http://<server-ip>:5001
```

**Default credentials:**
- Username: `admin`
- Password: `admin123` (or what you set during deployment)

---

## 📊 Accessing the Application

### Network Access

The application listens on port **5001**. Ensure this port is:
- Open in server firewall
- Accessible from your network
- Routed through any necessary load balancers

### Firewall Configuration (if needed)

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 5001/tcp

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### Reverse Proxy (optional)

For production, consider using Nginx or Apache as reverse proxy:

```nginx
# Example Nginx configuration
server {
    listen 80;
    server_name wardops.credobank.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔄 Operations

### View Logs

```bash
# All services
cd /opt/wardops
sudo docker compose logs -f

# Specific service
sudo docker compose logs -f api
sudo docker compose logs -f celery-worker
```

### Restart Services

```bash
cd /opt/wardops

# Restart all
sudo docker compose restart

# Restart specific service
sudo docker compose restart api
```

### Stop Services

```bash
cd /opt/wardops
sudo docker compose stop
```

### Start Services

```bash
cd /opt/wardops
sudo docker compose up -d
```

### Update to New Version

When a new version is released:

```bash
cd /opt/wardops

# Pull new images
sudo docker compose pull

# Restart with new images
sudo docker compose up -d

# Verify
sudo ./verify.sh
```

---

## 💾 Backup & Restore

### Backup Database

```bash
cd /opt/wardops
sudo docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backup-$(date +%Y%m%d).dump
```

### Backup Configuration

```bash
cd /opt/wardops
sudo cp .env.prod ~/wardops-env-backup-$(date +%Y%m%d).env
sudo chmod 600 ~/wardops-env-backup-*.env
```

### Restore Database

```bash
cd /opt/wardops
sudo docker compose exec -T db pg_restore -U fluxdb -d ward_ops -c < backup-20250101.dump
```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
cd /opt/wardops
sudo docker compose logs

# Check disk space
df -h

# Check Docker daemon
sudo systemctl status docker
```

### Database connection errors

```bash
# Verify database is running
cd /opt/wardops
sudo docker compose ps db

# Check database logs
sudo docker compose logs db

# Restart database
sudo docker compose restart db
```

### Can't pull images

```bash
# Check network connectivity
ping ghcr.io

# Try manual pull
docker pull ghcr.io/ward-tech-solutions/ward-flux-v2/credobank:latest

# Check rate limits (shouldn't be an issue with GHCR)
```

### Performance issues

```bash
# Check resource usage
docker stats

# View system resources
htop
free -h
df -h

# Adjust Celery worker concurrency in docker-compose.yml
# Default is 4, can be reduced for smaller servers
```

### Port already in use

```bash
# Check what's using port 5001
sudo lsof -i :5001

# Change port in docker-compose.yml if needed
cd /opt/wardops
sudo nano docker-compose.yml
# Change "5001:5001" to "5002:5001" (or other port)
sudo docker compose up -d
```

---

## 🔒 Security Best Practices

### 1. Change Default Password

**Immediately** after first login, change the admin password:

1. Login to web interface
2. Go to Settings → User Profile
3. Change password

Or via API:
```bash
curl -X POST http://localhost:5001/api/v1/auth/change-password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"old_password": "admin123", "new_password": "NewSecurePass123!"}'
```

### 2. Protect Configuration Files

```bash
sudo chmod 600 /opt/wardops/.env.prod
sudo chown root:root /opt/wardops/.env.prod
```

### 3. Regular Backups

Set up automated backups:

```bash
# Add to crontab
sudo crontab -e

# Backup database daily at 2 AM
0 2 * * * cd /opt/wardops && docker compose exec -T db pg_dump -U fluxdb -Fc ward_ops > /backups/ward_ops_$(date +\%Y\%m\%d).dump
```

### 4. Monitor Logs

```bash
# Set up log rotation
sudo nano /etc/logrotate.d/wardops

# Add:
/opt/wardops/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 5. Firewall Configuration

Only expose necessary ports:

```bash
# Allow SSH (22), HTTP (80), HTTPS (443), and WARD OPS (5001)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5001/tcp
sudo ufw enable
```

---

## 📞 Support & Documentation

### Installation Location

```
/opt/wardops/
├── docker-compose.yml    # Service definitions
├── .env.prod             # Configuration (sensitive)
├── verify.sh             # Health check script
├── logs/                 # Application logs
└── backups/              # Database backups
```

### Useful Commands Summary

```bash
# Status
cd /opt/wardops && sudo docker compose ps

# Logs
cd /opt/wardops && sudo docker compose logs -f

# Restart
cd /opt/wardops && sudo docker compose restart

# Update
cd /opt/wardops && sudo docker compose pull && sudo docker compose up -d

# Verify
cd /opt/wardops && sudo ./verify.sh

# Backup
cd /opt/wardops && sudo docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backup.dump
```

### API Documentation

Once deployed, interactive API documentation is available at:
```
http://<server-ip>:5001/docs
```

### Support Contact

For technical support or issues:
- **Email:** support@ward-ops.tech
- **Repository:** https://github.com/ward-tech-solutions/ward-flux-v2
- **Issues:** https://github.com/ward-tech-solutions/ward-flux-v2/issues

---

## 🎉 Deployment Complete!

Your WARD FLUX Network Monitoring Platform is now deployed and ready to use.

**Next Steps:**
1. ✅ Login to web interface
2. ✅ Change default admin password
3. ✅ Verify all devices are visible
4. ✅ Check SNMP polling is active
5. ✅ Review alert rules
6. ✅ Set up regular backups

**Deployed from:** GitHub Container Registry
**Branch:** client/credo-bank
**Images:** Automatically updated via CI/CD pipeline

---

*Last updated: January 2025*
*WARD FLUX v2.0 - Enterprise Network Monitoring*
