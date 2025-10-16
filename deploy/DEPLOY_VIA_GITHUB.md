# Deploy CredoBank WARD OPS via GitHub

> **Perfect for jump server scenarios** - No need for direct file transfer!

---

## 🎯 Why This Method?

When you access the client server through jump hosts and don't have direct SCP/SFTP access, deploying from GitHub is the simplest solution.

**Benefits:**
- ✅ No file transfers needed
- ✅ One command deployment
- ✅ Always deploys latest code from branch
- ✅ Works through jump servers
- ✅ Easy to repeat/rollback

---

## 📋 Prerequisites

### On Client Server

The server needs:
- Docker & Docker Compose
- Git
- Python 3 with cryptography module
- Internet access to GitHub and Docker registry

---

## 🚀 Deployment Methods

### Method 1: One-Line Deployment (Easiest)

**From client server (via jump host):**

```bash
# SSH through jump host to client server
ssh -J jumpuser@jumpserver user@client-server

# Run this ONE command
curl -fsSL https://raw.githubusercontent.com/your-org/wardops/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**Done!** The script will:
- Clone the repo
- Generate secrets
- Pull Docker images
- Start services

---

### Method 2: Download Script First (Recommended)

**Step 1: SSH to client server**
```bash
ssh -J jumpuser@jumpserver user@client-server
```

**Step 2: Download the deployment script**
```bash
# Download script
curl -fsSL https://raw.githubusercontent.com/your-org/wardops/client/credo-bank/deploy/deploy-from-github.sh -o deploy-from-github.sh

# Make executable
chmod +x deploy-from-github.sh

# Review the script (optional but recommended)
less deploy-from-github.sh
```

**Step 3: Run deployment**
```bash
sudo ./deploy-from-github.sh
```

**Step 4: Follow prompts**
- Enter admin password (or press Enter for default)
- Choose whether to enable auto-start on boot

---

### Method 3: Clone and Deploy (Most Control)

**Step 1: SSH to client server**
```bash
ssh -J jumpuser@jumpserver user@client-server
```

**Step 2: Clone the repository**
```bash
git clone --branch client/credo-bank --single-branch --depth 1 \
  https://github.com/your-org/wardops.git /tmp/wardops
```

**Step 3: Run deployment**
```bash
cd /tmp/wardops/deploy
sudo ./deploy-from-github.sh
```

---

## 🔐 For Private Repositories

If your GitHub repository is private, you have two options:

### Option A: Use SSH Keys (Recommended)

**On client server:**

```bash
# Generate SSH key (if not exists)
ssh-keygen -t ed25519 -C "client-server@credobank"

# Show public key
cat ~/.ssh/id_ed25519.pub
```

**On GitHub:**
1. Go to repository Settings > Deploy Keys
2. Add the public key
3. Give it read access

**Deploy:**
```bash
# Use SSH URL
export GITHUB_REPO=git@github.com:your-org/wardops.git
sudo -E ./deploy-from-github.sh
```

### Option B: Use Personal Access Token

**Create token on GitHub:**
1. Settings > Developer settings > Personal access tokens
2. Generate new token with `repo` scope
3. Copy the token

**Deploy:**
```bash
# Use HTTPS with token
export GITHUB_REPO=https://YOUR_TOKEN@github.com/your-org/wardops.git
sudo -E ./deploy-from-github.sh
```

---

## 🛠️ Customization

You can customize deployment with environment variables:

```bash
# Custom repository and branch
export GITHUB_REPO=https://github.com/your-org/wardops.git
export GITHUB_BRANCH=client/credo-bank

# Custom Docker images (if using different registry)
export REGISTRY_URL=registry.example.com
export APP_IMAGE=custom/wardops-app:latest
export DB_IMAGE=custom/wardops-db:latest

# For private registry
export REGISTRY_USERNAME=your-username
export REGISTRY_PASSWORD=your-password

# Run deployment with custom settings
sudo -E ./deploy-from-github.sh
```

---

## 📝 Complete Example: Through Jump Server

Here's a complete example of deploying through a jump server:

```bash
# Step 1: SSH to client server through jump host
ssh -J youruser@jump.server.com clientuser@client.server.com

# Step 2: Install prerequisites (if needed)
# Docker
curl -fsSL https://get.docker.com | sudo sh

# Git
sudo apt-get update && sudo apt-get install -y git

# Python cryptography
sudo apt-get install -y python3 python3-pip
sudo pip3 install cryptography

# Step 3: Download deployment script
curl -fsSL https://raw.githubusercontent.com/your-org/wardops/client/credo-bank/deploy/deploy-from-github.sh -o deploy.sh
chmod +x deploy.sh

# Step 4: Run deployment
sudo ./deploy.sh

# Step 5: Follow interactive prompts
# - Enter admin password (or use default: admin123)
# - Enable auto-start? (recommended: y)

# Step 6: Wait ~5 minutes for images to download and services to start

# Step 7: Verify deployment
cd /opt/wardops
sudo ./verify.sh

# Step 8: Access the application
# http://client-server-ip:5001 (API)
# Login: admin / [your-password]

# Done! 🎉
```

---

## ✅ Post-Deployment

After deployment completes:

### Verify Installation

```bash
cd /opt/wardops
./verify.sh
```

### Check Service Status

```bash
cd /opt/wardops
docker compose ps
```

Expected output:
```
NAME              STATUS
wardops-api       Up (healthy)
wardops-beat      Up
wardops-db        Up (healthy)
wardops-redis     Up
wardops-worker    Up
```

### View Logs

```bash
cd /opt/wardops
docker compose logs -f
```

### Test API

```bash
curl http://localhost:5001/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

## 🔄 Updating to New Version

When you push updates to GitHub:

```bash
# SSH to client server
ssh -J jumpuser@jumpserver user@client-server

# Re-run the deployment script
cd /tmp
curl -fsSL https://raw.githubusercontent.com/your-org/wardops/client/credo-bank/deploy/deploy-from-github.sh -o deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh

# It will:
# - Pull latest code from GitHub
# - Keep existing .env.prod (or regenerate if you choose)
# - Pull new Docker images
# - Restart services with new version
```

Or manually:

```bash
cd /opt/wardops

# Pull new images
docker compose pull

# Restart with new images
docker compose up -d

# Verify
./verify.sh
```

---

## 🐛 Troubleshooting

### Issue: "Permission denied" when cloning

**Solution:**
```bash
# Make sure you have GitHub access
ssh -T git@github.com

# Or use HTTPS with credentials
export GITHUB_REPO=https://USERNAME:TOKEN@github.com/your-org/wardops.git
```

### Issue: "Cannot connect to Docker daemon"

**Solution:**
```bash
# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Issue: Script fails during image pull

**Solution:**
```bash
# Check Docker Hub rate limits
docker login

# Or use authenticated pulls
export REGISTRY_USERNAME=your-username
export REGISTRY_PASSWORD=your-password
```

### Issue: Git clone is slow

**Solution:**
```bash
# Use shallow clone (script does this by default)
git clone --depth 1 --single-branch ...

# Or increase Git buffer size
git config --global http.postBuffer 524288000
```

---

## 🔐 Security Best Practices

### 1. Use Deploy Keys

For production, use deploy keys instead of personal credentials:

```bash
# On client server
ssh-keygen -t ed25519 -f ~/.ssh/wardops_deploy_key -C "wardops-deploy"

# Add to GitHub as deploy key (read-only)
# Then use:
git clone git@github.com:your-org/wardops.git -c core.sshCommand="ssh -i ~/.ssh/wardops_deploy_key"
```

### 2. Protect .env.prod

```bash
# After deployment, backup securely
sudo cp /opt/wardops/.env.prod ~/wardops.env.backup
chmod 600 ~/wardops.env.backup

# Never commit .env.prod to Git!
```

### 3. Limit Repository Access

- Use branch protection on `client/credo-bank`
- Require pull request reviews
- Enable signed commits

---

## 📞 Common Workflow

**Initial Deployment:**
```bash
ssh -J jump@jump.server client@target.server
curl -fsSL https://raw.githubusercontent.com/org/repo/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**Regular Updates:**
```bash
ssh -J jump@jump.server client@target.server
cd /opt/wardops
docker compose pull && docker compose up -d
```

**Check Status:**
```bash
ssh -J jump@jump.server client@target.server
cd /opt/wardops && ./verify.sh
```

**View Logs:**
```bash
ssh -J jump@jump.server client@target.server
cd /opt/wardops && docker compose logs -f api
```

---

## 🎯 Quick Reference

**Deploy:**
```bash
curl -fsSL https://raw.githubusercontent.com/org/repo/client/credo-bank/deploy/deploy-from-github.sh | sudo bash
```

**Verify:**
```bash
cd /opt/wardops && ./verify.sh
```

**Update:**
```bash
cd /opt/wardops && docker compose pull && docker compose up -d
```

**Logs:**
```bash
cd /opt/wardops && docker compose logs -f
```

---

## 📚 Additional Resources

- **Full Documentation**: See `/opt/wardops/README.md` after deployment
- **Verification**: Run `/opt/wardops/verify.sh`
- **API Docs**: `http://server-ip:5001/docs`

---

**Ready to deploy via GitHub!** 🚀

Just push your code to GitHub, then run the deployment script on the client server.
