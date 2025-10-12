# Pre-Deployment Checklist - CredoBank WARD OPS

**Date:** _____________
**Deployment Method:** ☐ GitHub (Jump Server) ☐ Direct
**Deploying To:** _____________

---

## ✅ Before You Start

### 1. GitHub Repository Setup

- [ ] Update GitHub repo URL in [deploy/deploy-from-github.sh](deploy/deploy-from-github.sh) (line 16)
- [ ] Decide: Public or Private repository?
  - If Private: Set up deploy key or PAT (see [DEPLOY_VIA_GITHUB.md](deploy/DEPLOY_VIA_GITHUB.md))
- [ ] Test: Can you access the repo from client server?

### 2. Local Changes Ready

- [ ] All code changes committed
- [ ] Deployment scripts updated (if needed)
- [ ] CI/CD pipeline tested (optional but recommended)
- [ ] Documentation reviewed

### 3. Client Server Access

- [ ] Jump server credentials: Username: _________ Host: _________
- [ ] Client server credentials: Username: _________ Host: _________
- [ ] SSH config updated (optional, see [JUMP_SERVER_GUIDE.md](deploy/JUMP_SERVER_GUIDE.md))
- [ ] Test SSH access: `ssh -J jump@host client@host`

### 4. Client Server Prerequisites

Check these on the client server (or plan to install):

- [ ] Docker Engine 20.10+ installed (or will install)
- [ ] Docker Compose v2.0+ installed (or will install)
- [ ] Git installed (or will install)
- [ ] Python 3.8+ installed (or will install)
- [ ] Python cryptography module (or will install)
- [ ] Internet access to GitHub
- [ ] Internet access to Docker Hub (or your registry)

### 5. Secrets & Configuration

- [ ] Decided on admin password (not default!)
- [ ] Reviewed [.env.prod.example](deploy/.env.prod.example)
- [ ] Planned where to backup `.env.prod` after deployment
- [ ] Identified who needs access credentials

### 6. Network & Firewall

- [ ] Client server IP address: _____________
- [ ] Required ports accessible:
  - [ ] 5001 (API)
  - [ ] 5432 (PostgreSQL) - optional, for external tools
- [ ] Firewall rules planned (if needed)
- [ ] Reverse proxy/SSL planned (if needed)

---

## 🚀 Deployment Steps

### Step 1: Push to GitHub

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
git status                                    # Check what will be committed
git add deploy/ *.md                         # Add deployment files
git commit -m "Deployment package for CredoBank"
git push origin client/credo-bank            # Push to GitHub
```

**Verification:**
- [ ] Push successful
- [ ] GitHub Actions build completed (if configured)
- [ ] Docker images available in registry

---

### Step 2: Connect to Client Server

```bash
# Replace with your actual values
ssh -J JUMPUSER@JUMPHOST CLIENTUSER@CLIENTHOST
```

**Verification:**
- [ ] Connected successfully
- [ ] Have sudo/root access: `sudo -v`

---

### Step 3: Install Prerequisites (if needed)

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# NOTE: Log out and back in after this

# Git
sudo apt-get update && sudo apt-get install -y git

# Python cryptography
sudo apt-get install -y python3 python3-pip
sudo pip3 install cryptography
```

**Verification:**
- [ ] `docker --version` works
- [ ] `docker compose version` works
- [ ] `git --version` works
- [ ] `python3 -c "from cryptography.fernet import Fernet; print('OK')"` works

---

### Step 4: Deploy from GitHub

**Set environment variables (if needed):**
```bash
export GITHUB_REPO=https://github.com/YOUR-ORG/YOUR-REPO.git
export GITHUB_BRANCH=client/credo-bank

# For private repo with SSH key:
export GIT_SSH_COMMAND="ssh -i ~/.ssh/deploy_key"

# For private repo with token:
export GITHUB_REPO=https://TOKEN@github.com/YOUR-ORG/YOUR-REPO.git
```

**Run deployment:**
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR-ORG/YOUR-REPO/client/credo-bank/deploy/deploy-from-github.sh | sudo -E bash
```

**During deployment, script will prompt:**
- [ ] Admin password entered (NOT default!)
- [ ] Auto-start enabled: y

**Verification:**
- [ ] Script completed without errors
- [ ] No red error messages in output
- [ ] Services started successfully

---

### Step 5: Verify Deployment

```bash
cd /opt/wardops
./verify.sh
```

**Expected results:**
- [ ] All services showing "Up" or "Up (healthy)"
- [ ] Database check passed
- [ ] Redis check passed
- [ ] API health check passed
- [ ] No failed checks

**Manual verification:**
```bash
# Check services
docker compose ps

# Test API
curl http://localhost:5001/api/v1/health

# View logs
docker compose logs --tail=50
```

**Verification:**
- [ ] All containers running
- [ ] No error messages in logs
- [ ] API returns healthy status
- [ ] Can access web UI from browser

---

## ✅ Post-Deployment

### Immediate Tasks

- [ ] Access web UI: `http://SERVER-IP:5001`
- [ ] Login with admin credentials
- [ ] **CHANGE ADMIN PASSWORD** immediately
- [ ] Verify dashboard loads
- [ ] Check that devices are listed (if pre-seeded)
- [ ] Test one alert rule
- [ ] Review logs for any warnings

### Backup & Security

- [ ] Backup `/opt/wardops/.env.prod`:
  ```bash
  sudo cp /opt/wardops/.env.prod ~/wardops-env-backup.txt
  chmod 600 ~/wardops-env-backup.txt
  ```
- [ ] Store backup securely offline
- [ ] Document admin credentials in secure location
- [ ] Update CORS_ORIGINS in `.env.prod` (if needed):
  ```bash
  cd /opt/wardops
  sudo nano .env.prod  # Update CORS_ORIGINS
  docker compose restart api
  ```

### Optional Setup

- [ ] Configure firewall rules:
  ```bash
  sudo ufw allow 22/tcp      # SSH
  sudo ufw allow 5001/tcp    # API
  sudo ufw enable
  ```
- [ ] Set up reverse proxy with SSL (Nginx/Caddy)
- [ ] Configure database backups:
  ```bash
  # Add to crontab
  0 2 * * * cd /opt/wardops && docker compose exec -T db pg_dump -U fluxdb -Fc ward_ops > backups/backup-$(date +\%Y\%m\%d).dump
  ```
- [ ] Set up monitoring/alerts for WARD OPS itself

### Documentation

- [ ] Document deployment date
- [ ] Record server IP and access details
- [ ] Note any customizations made
- [ ] Share access credentials with team (securely)
- [ ] Create runbook for common operations

---

## 📊 Deployment Sign-Off

**Deployed By:** _____________
**Date:** _____________
**Time:** _____________

**Services Status:**
- [ ] API: Running
- [ ] Database: Running
- [ ] Redis: Running
- [ ] Celery Worker: Running
- [ ] Celery Beat: Running

**Access Information:**
- Server IP: _____________
- API URL: http://_____________:5001
- Admin Username: admin
- Admin Password: _____ (Stored securely: ______)

**Issues Encountered:**
_____________________________________________________________
_____________________________________________________________

**Notes:**
_____________________________________________________________
_____________________________________________________________

**Verified By:** _____________
**Date:** _____________

---

## 📞 Support & Resources

**Documentation:**
- Jump Server Guide: [deploy/JUMP_SERVER_GUIDE.md](deploy/JUMP_SERVER_GUIDE.md)
- GitHub Deployment: [deploy/DEPLOY_VIA_GITHUB.md](deploy/DEPLOY_VIA_GITHUB.md)
- Complete Handbook: [deploy/README.md](deploy/README.md)
- Quick Reference: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

**Common Commands:**
```bash
# View logs
cd /opt/wardops && docker compose logs -f

# Restart services
cd /opt/wardops && docker compose restart

# Update services
cd /opt/wardops && docker compose pull && docker compose up -d

# Health check
cd /opt/wardops && ./verify.sh

# Backup database
cd /opt/wardops && docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backups/backup.dump
```

**Issues?**
1. Check logs: `cd /opt/wardops && docker compose logs -f`
2. Run verification: `cd /opt/wardops && ./verify.sh`
3. Review documentation: See links above
4. Contact support: [Your support contact]

---

**Status:** ☐ In Progress ☐ Completed ☐ Issues Found

---

*This checklist ensures a smooth, complete deployment of CredoBank WARD OPS monitoring platform.*
