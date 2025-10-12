# CredoBank WARD OPS - Jump Server Deployment Guide

> **For IT teams accessing servers through jump hosts/bastion servers**

---

## 🎯 Your Scenario

You need to deploy WARD OPS on a client server, but:
- ❌ No direct SSH/SCP access to client server
- ❌ Must go through jump server first
- ❌ Cannot easily transfer files
- ✅ Client server has internet access
- ✅ You can SSH through jump host

**Solution:** Deploy directly from GitHub! 🚀

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Push Code to GitHub

**On your local machine:**

```bash
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"

# Add and commit deployment package
git add deploy/
git commit -m "Add GitHub deployment capability for CredoBank"
git push origin client/credo-bank
```

### Step 2: SSH Through Jump Server

```bash
# Replace with your actual jump server and client server details
ssh -J jumpuser@jump.server.com clientuser@client.server.com
```

### Step 3: Run One-Line Deployment

**On client server (connected via jump host):**

```bash
# Download and run deployment script
curl -fsSL https://raw.githubusercontent.com/YOUR-ORG/YOUR-REPO/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**That's it!** ✅

The script will:
1. Check prerequisites (Docker, Git, Python)
2. Clone your GitHub repository
3. Generate secure secrets
4. Pull Docker images
5. Start all services

⏱️ **Total time: ~5 minutes**

---

## 📋 Prerequisites on Client Server

The client server needs:

### 1. Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Verify
docker --version
docker compose version
```

### 2. Git

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y git

# RHEL/CentOS
sudo yum install -y git

# Verify
git --version
```

### 3. Python 3 with cryptography

```bash
# Ubuntu/Debian
sudo apt-get install -y python3 python3-pip
sudo pip3 install cryptography

# RHEL/CentOS
sudo yum install -y python3 python3-pip
sudo pip3 install cryptography

# Verify
python3 -c "from cryptography.fernet import Fernet; print('OK')"
```

---

## 🔧 Detailed Step-by-Step

### Complete Deployment Example

```bash
# ============================================================
# STEP 1: On Your Local Machine - Push to GitHub
# ============================================================
cd "/Users/g.jalabadze/Desktop/WARD OPS/CredoBranches"
git add deploy/
git commit -m "Add GitHub deployment for CredoBank"
git push origin client/credo-bank

# ============================================================
# STEP 2: Connect to Client Server via Jump Host
# ============================================================
# Basic method
ssh -J jumpuser@jump.example.com clientuser@client.example.com

# Or with specific jump port
ssh -J jumpuser@jump.example.com:2222 clientuser@client.example.com

# Or multiple jump hosts
ssh -J jump1@host1.com,jump2@host2.com clientuser@client.example.com

# Or using ProxyJump in SSH config (add to ~/.ssh/config):
# Host client-server
#   HostName client.example.com
#   User clientuser
#   ProxyJump jumpuser@jump.example.com
# Then just: ssh client-server

# ============================================================
# STEP 3: Install Prerequisites (if needed)
# ============================================================

# Check what's installed
docker --version        # Check Docker
git --version          # Check Git
python3 --version      # Check Python

# Install Docker if missing
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    # Note: Log out and back in for group changes
fi

# Install Git if missing
if ! command -v git &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y git
fi

# Install Python and cryptography if missing
if ! python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
    sudo apt-get install -y python3 python3-pip
    sudo pip3 install cryptography
fi

# ============================================================
# STEP 4: Download Deployment Script
# ============================================================

# Download script
curl -fsSL https://raw.githubusercontent.com/YOUR-ORG/YOUR-REPO/client/credo-bank/deploy/deploy-from-github.sh -o deploy.sh

# Make executable
chmod +x deploy.sh

# Optional: Review script before running
less deploy.sh

# ============================================================
# STEP 5: Run Deployment
# ============================================================

# Set GitHub repository (optional, defaults are usually fine)
export GITHUB_REPO=https://github.com/YOUR-ORG/YOUR-REPO.git
export GITHUB_BRANCH=client/credo-bank

# Run deployment
sudo -E ./deploy.sh

# ============================================================
# STEP 6: Follow Interactive Prompts
# ============================================================

# The script will ask:
# 1. "Enter admin password (default: admin123):"
#    - Press Enter for default, or type your custom password

# 2. "Enable auto-start on boot? (y/N):"
#    - Type 'y' for production servers (recommended)

# 3. "Run health verification now? (Y/n):"
#    - Press Enter to verify deployment

# ============================================================
# STEP 7: Verify Deployment
# ============================================================

cd /opt/wardops
./verify.sh

# Check services
docker compose ps

# View logs
docker compose logs -f

# Test API
curl http://localhost:5001/api/v1/health

# ============================================================
# STEP 8: Access Application
# ============================================================

# Get server IP
hostname -I | awk '{print $1}'

# Access from browser:
# http://SERVER-IP:5001  (API)

# Login credentials:
# Username: admin
# Password: [what you set during deployment]

# Done! 🎉
```

---

## 🔐 For Private GitHub Repositories

If your repository is private, use one of these methods:

### Method A: SSH Deploy Key (Recommended)

**On client server:**

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "wardops-deploy-key" -f ~/.ssh/wardops_deploy
cat ~/.ssh/wardops_deploy.pub
```

**On GitHub:**
1. Go to: Repository → Settings → Deploy keys → Add deploy key
2. Paste the public key
3. Give it a descriptive name: "CredoBank Production Server"
4. ✅ Allow read access only

**Deploy:**
```bash
# Configure Git to use the deploy key
export GIT_SSH_COMMAND="ssh -i ~/.ssh/wardops_deploy"

# Set repository URL (SSH format)
export GITHUB_REPO=git@github.com:YOUR-ORG/YOUR-REPO.git
export GITHUB_BRANCH=client/credo-bank

# Run deployment
sudo -E ./deploy-from-github.sh
```

### Method B: Personal Access Token

**On GitHub:**
1. Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Select scope: `repo` (Full control of private repositories)
4. Copy the token (shown only once!)

**Deploy:**
```bash
# Use HTTPS URL with token embedded
export GITHUB_REPO=https://YOUR_TOKEN@github.com/YOUR-ORG/YOUR-REPO.git
export GITHUB_BRANCH=client/credo-bank

# Run deployment
sudo -E ./deploy-from-github.sh
```

---

## 🔄 SSH Config for Easy Access

Make jump server access easier with SSH config:

**On your local machine, edit `~/.ssh/config`:**

```
# Jump server configuration
Host jump
    HostName jump.example.com
    User jumpuser
    Port 22

# Client server via jump host
Host client-prod
    HostName client.example.com
    User clientuser
    Port 22
    ProxyJump jump

# Now you can simply run:
# ssh client-prod
```

**Then deployment becomes:**

```bash
# Connect
ssh client-prod

# Deploy
curl -fsSL https://raw.githubusercontent.com/.../deploy-from-github.sh | sudo bash
```

---

## 📊 SSH Tunneling for Web Access

If you can't access the client server's web ports directly, use SSH tunneling:

### Forward API Port

```bash
# From your local machine
ssh -J jumpuser@jump.server.com -L 5001:localhost:5001 clientuser@client.server.com

# Now access locally:
# http://localhost:5001 → goes to client server
```

### Forward Multiple Ports

```bash
# Forward API and Frontend
ssh -J jumpuser@jump.server.com \
    -L 5001:localhost:5001 \
    clientuser@client.server.com

# Access:
# http://localhost:5001 → API on client server
```

---

## 🛠️ Common Operations

### View Logs

```bash
ssh -J jump@jump.server client@client.server
cd /opt/wardops
docker compose logs -f
```

### Restart Services

```bash
ssh -J jump@jump.server client@client.server
cd /opt/wardops
docker compose restart
```

### Update to New Version

**After pushing new code to GitHub:**

```bash
ssh -J jump@jump.server client@client.server
cd /opt/wardops

# Pull new images
docker compose pull

# Restart with new images
docker compose up -d

# Verify
./verify.sh
```

### Backup Database

```bash
ssh -J jump@jump.server client@client.server
cd /opt/wardops

# Create backup
docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backups/backup-$(date +%Y%m%d).dump

# Download backup to your local machine (via jump)
scp -J jump@jump.server client@client.server:/opt/wardops/backups/backup-*.dump ./
```

---

## 🐛 Troubleshooting

### Issue: SSH connection times out

**Solutions:**

```bash
# Increase timeout
ssh -o ConnectTimeout=30 -J jump@jump.server client@client.server

# Use keep-alive
ssh -o ServerAliveInterval=60 -J jump@jump.server client@client.server

# Add to ~/.ssh/config:
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### Issue: Git clone fails through jump server

**Solutions:**

```bash
# Check internet access from client server
ssh -J jump@jump.server client@client.server
curl -I https://github.com

# If blocked, use proxy
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080

# Or use corporate Git mirror
export GITHUB_REPO=https://git.corporate.com/mirror/wardops.git
```

### Issue: Docker pull is very slow

**Solutions:**

```bash
# Use Docker Hub mirror (if available)
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://mirror.example.com"]
}
EOF
sudo systemctl restart docker

# Or download images on jump server and transfer
# (if jump server has better internet)
```

### Issue: Permission denied after sudo

**Solution:**

```bash
# Preserve environment variables with sudo
sudo -E ./deploy-from-github.sh

# Or set them for sudo
sudo GITHUB_REPO=$GITHUB_REPO GITHUB_BRANCH=$GITHUB_BRANCH ./deploy-from-github.sh
```

---

## 📝 Deployment Checklist

**Before deployment:**

- [ ] Code pushed to GitHub (`client/credo-bank` branch)
- [ ] SSH access to jump server configured
- [ ] Jump server can reach client server
- [ ] Client server has internet access
- [ ] Docker installed on client server (or will install)
- [ ] Git installed on client server (or will install)
- [ ] For private repo: Deploy key or PAT configured

**During deployment:**

- [ ] Connected to client server via jump host
- [ ] Downloaded deployment script
- [ ] Ran deployment with appropriate GitHub repo URL
- [ ] Set admin password
- [ ] Enabled auto-start on boot

**After deployment:**

- [ ] Ran verification script (`./verify.sh`)
- [ ] All services showing "Up" status
- [ ] API health check returns 200 OK
- [ ] Logged into web UI successfully
- [ ] Changed admin password from default
- [ ] Documented credentials securely
- [ ] Backed up `/opt/wardops/.env.prod`

---

## 🎯 Quick Reference Card

**Connect:**
```bash
ssh -J jump@jump.server client@client.server
```

**Deploy:**
```bash
curl -fsSL https://raw.githubusercontent.com/org/repo/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**Verify:**
```bash
cd /opt/wardops && ./verify.sh
```

**Logs:**
```bash
cd /opt/wardops && docker compose logs -f
```

**Update:**
```bash
cd /opt/wardops && docker compose pull && docker compose up -d
```

**Backup:**
```bash
cd /opt/wardops && docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backups/backup.dump
```

---

## 📞 Support

**Documentation:**
- GitHub deployment: [DEPLOY_VIA_GITHUB.md](DEPLOY_VIA_GITHUB.md)
- Full guide: [README.md](README.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)

**After deployment:**
- Logs: `/opt/wardops/logs/`
- Verification: `/opt/wardops/verify.sh`
- API docs: `http://server-ip:5001/docs`

---

**You're ready to deploy via jump server!** 🚀

Push your code to GitHub, SSH through the jump host, and run the deployment script!
