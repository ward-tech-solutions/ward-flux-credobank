# 🚀 WARD TECH SOLUTIONS - Deployment Guide

**Enterprise Network Monitoring Platform - Production Deployment**

---

## 📋 Overview

WARD TECH SOLUTIONS is a **ready-to-deploy** network monitoring platform that connects to your existing Zabbix infrastructure. Deploy it like **Grafana** - one command, then configure through the web interface.

### 🎯 Key Features

- ✅ **Zero Configuration Deployment** - Docker-based single command install
- ✅ **Setup Wizard** - Guided configuration on first access
- ✅ **Multi-Tenant Ready** - Each company gets isolated configuration
- ✅ **Persistent Storage** - All data saved in Docker volumes
- ✅ **Auto-Restart** - Self-healing container configuration
- ✅ **Health Monitoring** - Built-in health checks

---

## 🔧 Prerequisites

### Required
- **Docker** 20.10 or higher
- **Docker Compose** 1.29 or higher
- **Zabbix Server** 5.0 or higher (accessible from deployment server)
- **4GB RAM** minimum
- **10GB Disk** for application + logs

### Network Requirements
- Port **5001** available (can be changed in `docker-compose.yml`)
- Access to Zabbix API endpoint (http://your-zabbix-server/api_jsonrpc.php)

### Zabbix Requirements
- **Zabbix User Account** with API access
- **Read Permissions** for:
  - Hosts
  - Host Groups
  - Items
  - Triggers
  - Events

---

## 🚀 Quick Start Deployment

### Option 1: Docker Compose (Recommended)

**Step 1: Download the platform**
```bash
# Clone or download the repository
git clone https://github.com/wardtechsolutions/network-monitor.git
cd network-monitor

# Or use wget/curl to download release
wget https://github.com/wardtechsolutions/network-monitor/releases/latest/ward-monitor.tar.gz
tar -xzf ward-monitor.tar.gz
cd ward-monitor
```

**Step 2: Deploy with one command**
```bash
docker-compose up -d
```

**Step 3: Access the Setup Wizard**
```bash
# Open your browser
http://your-server-ip:5001/setup
```

**That's it!** 🎉 The setup wizard will guide you through the rest.

---

### Option 2: Docker Run (Single Container)

```bash
docker run -d \
  --name ward-tech-solutions \
  -p 5001:5001 \
  -v ward-data:/app/data \
  -v ward-logs:/app/logs \
  -e SETUP_MODE=enabled \
  --restart unless-stopped \
  wardtechsolutions/network-monitor:latest
```

Then access: `http://your-server-ip:5001/setup`

---

## 🎨 Setup Wizard Walkthrough

### Step 1: Welcome Screen
- Review platform features
- Click **Next** to begin

### Step 2: Zabbix Configuration
Fill in your Zabbix details:

| Field | Example | Description |
|-------|---------|-------------|
| **Company Name** | Acme Corporation | Your organization name |
| **Zabbix URL** | http://10.30.25.34:8080/api_jsonrpc.php | Full API endpoint |
| **Zabbix Username** | monitoring | API user account |
| **Zabbix Password** | ********** | API user password |

**Important:** Click **Test Connection** before proceeding!

### Step 3: Host Groups Selection
- Platform loads all Zabbix host groups
- Select groups you want to monitor
- Multiple selections allowed
- Example: `Switches`, `Routers`, `Servers`

### Step 4: Admin Account
Create your platform admin:

| Field | Example | Notes |
|-------|---------|-------|
| **Username** | admin | Login username |
| **Email** | admin@acme.com | For password recovery |
| **Password** | *Strong password* | Min 8 characters |

### Step 5: Complete
- Review configuration summary
- Click **Go to Dashboard**
- Login with admin credentials
- Start monitoring!

---

## 🔐 Security Best Practices

### 1. Change Default Port
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5001"  # Use 8080 instead of 5001
```

### 2. Use HTTPS (Production)
Set up reverse proxy (Nginx/Apache):

**Nginx Example:**
```nginx
server {
    listen 443 ssl;
    server_name monitor.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Firewall Configuration
```bash
# Allow only from specific IPs
ufw allow from 10.0.0.0/8 to any port 5001

# Or use nginx + allow public HTTPS only
ufw allow 443/tcp
ufw deny 5001/tcp
```

### 4. Environment Variables
Never commit `.env` files to Git. The platform stores sensitive data in database.

---

## 📊 Post-Deployment Configuration

### Access the Platform
```
http://your-server-ip:5001
```

### Default Features Available Immediately:
- ✅ Dashboard with device statistics
- ✅ Device list with live status
- ✅ Geographic map visualization
- ✅ Excel report generation
- ✅ Real-time WebSocket updates
- ✅ Dark/Light theme switching

### Optional Configurations (Settings Page):
1. **Company Branding**
   - Upload logo
   - Change primary color
   - Custom subdomain

2. **Email Notifications**
   - SMTP server configuration
   - Alert thresholds
   - Notification recipients

3. **Backup Schedule**
   - Automated database backups
   - Export to external storage

---

## 🔄 Updates and Maintenance

### Update to Latest Version
```bash
# Pull latest image
docker-compose pull

# Restart with new version
docker-compose up -d

# Check logs
docker-compose logs -f ward-app
```

### Backup Data
```bash
# Backup database
docker run --rm -v ward-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/ward-data-$(date +%Y%m%d).tar.gz /data

# Backup logs
docker run --rm -v ward-logs:/logs -v $(pwd):/backup \
  ubuntu tar czf /backup/ward-logs-$(date +%Y%m%d).tar.gz /logs
```

### Restore from Backup
```bash
# Stop container
docker-compose down

# Restore data
docker run --rm -v ward-data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/ward-data-20251004.tar.gz -C /

# Start container
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Issue: Setup wizard not showing
**Solution:**
```bash
# Check if setup is marked complete in database
docker exec -it ward-tech-solutions sqlite3 /app/data/ward_ops.db \
  "SELECT * FROM setup_wizard_state;"

# Reset if needed
docker exec -it ward-tech-solutions sqlite3 /app/data/ward_ops.db \
  "UPDATE setup_wizard_state SET is_complete = 0;"

# Restart
docker-compose restart
```

### Issue: Cannot connect to Zabbix
**Solution:**
1. Verify Zabbix URL is accessible from container:
   ```bash
   docker exec -it ward-tech-solutions curl http://your-zabbix-server/api_jsonrpc.php
   ```

2. Check Zabbix user permissions in Zabbix UI

3. Verify firewall allows connection

### Issue: Container keeps restarting
**Solution:**
```bash
# Check logs for errors
docker logs ward-tech-solutions --tail 100

# Common fixes:
# 1. Check port 5001 not in use
lsof -i :5001

# 2. Check disk space
df -h

# 3. Check memory
free -m
```

### Issue: Data not persisting
**Solution:**
```bash
# Verify volumes are created
docker volume ls | grep ward

# Check volume mounts
docker inspect ward-tech-solutions | grep -A 10 Mounts

# Recreate volumes if needed
docker-compose down -v
docker-compose up -d
```

---

## 📈 Scaling for Large Deployments

### For 1000+ Devices

**Increase Workers:**
Edit `Dockerfile`:
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "8"]
```

**Increase Container Resources:**
Edit `docker-compose.yml`:
```yaml
services:
  ward-app:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### Database Optimization
For very large deployments, consider:
- Migration from SQLite to PostgreSQL
- Redis caching layer
- Read replicas

---

## 🌐 Multi-Company Deployment

### Option 1: Multiple Containers (Isolated)
```bash
# Company A
docker run -d --name ward-companyA -p 5001:5001 ...

# Company B
docker run -d --name ward-companyB -p 5002:5001 ...
```

### Option 2: Subdomain Routing (Shared Infrastructure)
Use nginx to route by subdomain:
```nginx
# companyA.monitor.yourservice.com → container 1
# companyB.monitor.yourservice.com → container 2
```

---

## 📞 Support and Documentation

### Quick Reference
- **Health Check:** `http://your-server:5001/api/v1/health`
- **API Docs:** `http://your-server:5001/docs`
- **Database Location:** `/app/data/ward_ops.db` (in container)
- **Logs Location:** `/app/logs/` (in container)

### Getting Help
1. Check logs: `docker logs ward-tech-solutions`
2. Review this guide
3. Contact: support@wardops.tech

---

## 🎯 Customer Onboarding Checklist

When deploying for a new customer:

- [ ] Obtain Zabbix API credentials from customer
- [ ] Verify network connectivity to Zabbix server
- [ ] Deploy Docker container
- [ ] Complete setup wizard with customer
- [ ] Test device visibility (should see devices immediately)
- [ ] Configure email notifications (if needed)
- [ ] Upload company logo (if provided)
- [ ] Train customer admin on platform usage
- [ ] Provide admin credentials securely
- [ ] Schedule follow-up for feedback

**Average Deployment Time:** 15-20 minutes

---

## 🚢 Deployment Automation (For Service Providers)

### Terraform Example
```hcl
resource "docker_container" "ward_monitor" {
  name  = "ward-${var.company_name}"
  image = "wardtechsolutions/network-monitor:latest"

  ports {
    internal = 5001
    external = var.port
  }

  volumes {
    volume_name    = "ward-${var.company_name}-data"
    container_path = "/app/data"
  }
}
```

### Ansible Playbook Example
```yaml
- name: Deploy WARD Monitor
  hosts: monitoring_servers
  tasks:
    - name: Pull latest image
      docker_image:
        name: wardtechsolutions/network-monitor
        tag: latest

    - name: Start container
      docker_container:
        name: "ward-{{ company_name }}"
        image: wardtechsolutions/network-monitor:latest
        ports:
          - "5001:5001"
        volumes:
          - "ward-data:/app/data"
        restart_policy: unless-stopped
```

---

## ✅ Deployment Verification

After deployment, verify these endpoints:

```bash
# Health check
curl http://localhost:5001/api/v1/health
# Expected: {"status":"healthy","timestamp":"..."}

# Setup wizard
curl -I http://localhost:5001/setup
# Expected: 200 OK (if not setup) or redirect (if complete)

# API documentation
curl http://localhost:5001/docs
# Expected: OpenAPI documentation page
```

---

## 🏆 Production Checklist

Before going live:

- [ ] HTTPS configured (reverse proxy)
- [ ] Firewall rules applied
- [ ] Backups configured
- [ ] Monitoring alerts set
- [ ] Admin credentials documented
- [ ] Customer training completed
- [ ] Support contact provided
- [ ] Documentation delivered

---

## 📦 What's Included

When you deploy WARD TECH SOLUTIONS, you get:

✅ **Web Application** - Modern responsive UI
✅ **REST API** - Full API access (documented at `/docs`)
✅ **WebSocket** - Real-time device updates
✅ **Geographic Map** - Leaflet-based visualization
✅ **Excel Reports** - One-click report generation
✅ **Dark/Light Mode** - Automatic theme switching
✅ **Role-Based Access** - Admin, User, Viewer roles
✅ **Rate Limiting** - Built-in security
✅ **Health Monitoring** - Self-health checks
✅ **Auto-Restart** - Fault tolerance

---

## 🎉 Success!

Your WARD TECH SOLUTIONS platform is now deployed and ready to monitor your network infrastructure!

**Next Steps:**
1. Login to the platform
2. Explore the dashboard
3. Generate your first report
4. Configure additional users
5. Customize branding

**Need Help?** Contact: support@wardops.tech

---

*WARD TECH SOLUTIONS - Enterprise Network Monitoring Made Simple*
