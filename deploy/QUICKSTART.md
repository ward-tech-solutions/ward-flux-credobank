# CredoBank WARD OPS - Quick Start (5 Minutes)

> **TL;DR**: One script, one command, production monitoring deployed.

---

## 🎯 Goal

Get WARD OPS monitoring platform running on your server in 5 minutes.

---

## ⚡ Super Quick Start

### On the target server:

```bash
# 1. Transfer deployment package
scp -r deploy/ user@your-server:/tmp/

# 2. SSH into server
ssh user@your-server

# 3. Run deployment
cd /tmp/deploy
sudo ./deploy.sh

# 4. Wait ~3 minutes (downloading images)

# 5. Access the UI
# Open: http://your-server-ip:3000
# Login: admin / admin123
```

**Done!** 🎉

---

## 📋 What You Need

Before running the script:

- **Server**: Ubuntu 22.04 (or similar)
- **Access**: SSH with sudo privileges
- **Hardware**: 4GB RAM, 20GB disk minimum
- **Software**: Docker (script will check and prompt if missing)

---

## 🚀 Step-by-Step

### Step 1: Prepare the Server

```bash
# Install Docker if not present
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Step 2: Copy Files

```bash
# From your local machine
scp -r deploy/ user@server-ip:/tmp/

# Or use any file transfer method you prefer
```

### Step 3: Run Deployment

```bash
# SSH into server
ssh user@server-ip

# Navigate to deployment folder
cd /tmp/deploy

# Make script executable (if needed)
chmod +x deploy.sh

# Run deployment with sudo
sudo ./deploy.sh
```

### Step 4: Follow Prompts

The script will ask:

1. **Admin password** - Press Enter for default (`admin123`) or type your own
2. **Auto-start on boot** - Type `y` for yes (recommended)

### Step 5: Verify

```bash
# Check all services are running
./verify.sh

# Or manually
cd /opt/wardops
docker compose ps
```

Expected output:
```
NAME              STATUS              PORTS
wardops-api       Up (healthy)        0.0.0.0:5001->5001/tcp
wardops-beat      Up
wardops-db        Up (healthy)
wardops-redis     Up
wardops-worker    Up
```

---

## 🌐 Access the Application

**Web Interface:**
```
http://your-server-ip:3000
```

**API Endpoint:**
```
http://your-server-ip:5001/docs
```

**Default Login:**
- Username: `admin`
- Password: `admin123` (or what you set during deployment)

**⚠️ IMPORTANT:** Change the admin password immediately after first login!

---

## 🔧 Common Commands

### View Logs
```bash
cd /opt/wardops
docker compose logs -f
```

### Restart Services
```bash
cd /opt/wardops
docker compose restart
```

### Stop Services
```bash
cd /opt/wardops
docker compose down
```

### Update to New Version
```bash
cd /opt/wardops
docker compose pull
docker compose up -d
```

---

## ❓ Troubleshooting

### Issue: "Permission denied"

**Solution:**
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Issue: "Port already in use"

**Solution:**
```bash
# Check what's using the port
sudo lsof -i :5001

# Kill it or change ports in docker-compose.yml
```

### Issue: Services keep restarting

**Solution:**
```bash
# Check logs
cd /opt/wardops
docker compose logs --tail=50

# Verify resources
free -h  # Check memory
df -h    # Check disk
```

### Issue: Cannot access from browser

**Solution:**
```bash
# Check firewall
sudo ufw status

# Allow ports
sudo ufw allow 5001/tcp
sudo ufw allow 3000/tcp
```

---

## 📞 Need Help?

**Check deployment:**
```bash
cd /opt/wardops
./verify.sh
```

**View detailed logs:**
```bash
cd /opt/wardops
docker compose logs -f api
```

**Test API health:**
```bash
curl http://localhost:5001/api/v1/health
```

**Contact:** Ward Tech Solutions support team

---

## 🎓 Next Steps

After deployment:

1. ✅ Change admin password
2. ✅ Add your network devices
3. ✅ Configure alert rules
4. ✅ Set up SNMP credentials
5. ✅ Configure monitoring intervals
6. ✅ Review dashboard and metrics

**Full documentation:** See [README.md](README.md) for comprehensive guide

---

## 📦 What Was Installed?

The deployment created:

```
/opt/wardops/
├── docker-compose.yml          # Service orchestration
├── .env.prod                   # Configuration (sensitive)
├── logs/                       # Application logs
└── backups/                    # Database backup location

Docker Volumes:
├── db-data                     # PostgreSQL data (persistent)
├── redis-data                  # Redis data
├── api-data                    # API application data
├── worker-data                 # Celery worker data
└── beat-data                   # Celery beat data
```

**Backup `.env.prod`** - It contains your secrets!

---

## 🔒 Security Checklist

After deployment:

- [ ] Change admin password
- [ ] Review `.env.prod` secrets
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS (if exposing to internet)
- [ ] Backup `.env.prod` securely
- [ ] Test database backups
- [ ] Configure CORS_ORIGINS in `.env.prod`

---

**Ready to monitor!** 🎉

For detailed documentation, see [README.md](README.md)
