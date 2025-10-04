# 🛡️ WARD TECH SOLUTIONS - Network Monitoring Platform

**Enterprise Network Monitoring Made Simple**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://hub.docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)

Transform your Zabbix infrastructure into a modern platform with maps, dashboards, and one-click reports.

---

## 🚀 Quick Start (2 Commands, 15 Minutes)

```bash
# Pull and run
docker run -d -p 5001:5001 --name ward-monitor \
  -v ward-data:/app/data \
  ghcr.io/YOUR_GITHUB_USERNAME/ward-tech-solutions:latest

# Access setup wizard
http://your-server:5001/setup
```

**That's it!** The setup wizard guides you through the rest.

---

## ✨ What You Get

- 📊 **Modern Dashboards** - Real-time device status with WebSocket updates
- 🗺️ **Geographic Maps** - See all devices on interactive maps
- 📑 **One-Click Reports** - Generate Excel reports instantly
- 🎨 **Beautiful UI** - Dark/light modes, mobile-responsive
- 🔒 **Secure** - JWT auth, rate limiting, security headers
- ⚡ **Fast Setup** - 5-step wizard, no technical knowledge needed

---

## 📋 Requirements

- Zabbix Server 5.0+
- Docker 20.10+
- 4GB RAM, 10GB disk
- Zabbix API access (read-only)

---

## 🎬 Setup Wizard (5 Steps)

1. **Welcome** - Review features
2. **Zabbix** - Enter URL + credentials
3. **Groups** - Select host groups to monitor
4. **Admin** - Create admin account
5. **Done!** - Start monitoring

---

## 📖 Full Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete technical docs
- [Customer Onboarding](CUSTOMER_ONBOARDING.md) - Sales workflow
- [Business Guide](SAAS_TRANSFORMATION_COMPLETE.md) - SaaS strategy
- [API Docs](http://localhost:5001/docs) - Interactive API documentation

---

## 🐳 Docker Deployment Options

### Option 1: Docker Run
```bash
docker run -d -p 5001:5001 --name ward \
  -v ward-data:/app/data \
  -v ward-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/YOUR_GITHUB_USERNAME/ward-tech-solutions:latest
```

### Option 2: Docker Compose
```bash
curl -O https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/ward-tech-solutions/main/docker-compose.yml
docker-compose up -d
```

### Option 3: From Source
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/ward-tech-solutions.git
cd ward-tech-solutions
docker-compose up -d
```

---

## 🔧 Configuration

All configuration happens via the **Setup Wizard** on first access. No manual file editing needed!

Optional `.env` file (wizard creates this automatically):
```env
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_USER=monitoring
ZABBIX_PASSWORD=your_password
```

---

## 📊 Features

### Dashboard
- Total device count
- Online/offline status
- Device type breakdown
- Real-time updates

### Device Management
- Complete device list
- Search and filter
- Bulk import/export
- Geographic locations

### Reporting
- Excel export
- Custom templates
- Scheduled reports

### Security
- Role-based access (4 levels)
- Rate limiting
- 6 security headers
- JWT authentication

---

## 🔄 Updates

```bash
docker-compose pull
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Setup wizard not showing
```bash
# Reset setup state
docker exec -it ward sqlite3 /app/data/ward_ops.db \
  "UPDATE setup_wizard_state SET is_complete = 0;"
docker restart ward
```

### Can't connect to Zabbix
- Verify URL is accessible from container
- Check Zabbix user has API access
- Test: `docker exec -it ward curl YOUR_ZABBIX_URL`

### Logs
```bash
docker logs ward --tail 100
```

---

## 📈 Use Cases

✅ Retail chains (multiple stores)
✅ Manufacturing (plants/factories)
✅ Healthcare (hospitals)
✅ Education (universities)
✅ MSPs (multi-client management)

---

## 🎯 Why WARD?

| Feature | WARD | Raw Zabbix | Other Tools |
|---------|------|------------|-------------|
| Setup Time | 15 min | Days | Hours |
| Geographic Maps | ✅ | ❌ | Some |
| One-Click Reports | ✅ | ❌ | Some |
| Uses Existing Zabbix | ✅ | N/A | ❌ |
| Modern UI | ✅ | ❌ | ✅ |
| Mobile Responsive | ✅ | ❌ | Some |

---

## 📞 Support

- **Docs**: See documentation files
- **API**: http://your-server:5001/docs
- **Email**: support@wardops.tech

---

## 📜 License

Proprietary - WARD TECH SOLUTIONS
Contact: sales@wardops.tech

---

## ⚡ Get Started

```bash
# 1. Run container
docker run -d -p 5001:5001 --name ward \
  ghcr.io/YOUR_GITHUB_USERNAME/ward-tech-solutions:latest

# 2. Open browser
http://localhost:5001/setup

# 3. Follow 5-step wizard

# 4. Start monitoring!
```

---

*WARD TECH SOLUTIONS - Network Monitoring Made Simple*

*Copyright © 2025. All rights reserved.*
