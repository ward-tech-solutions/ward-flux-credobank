# CredoBank WARD OPS - Deployment Package Information

**Version:** 2.0 - CredoBank Production Release
**Date:** October 2025
**Client:** CredoBank
**Vendor:** WARD Tech Solutions

---

## 📦 Package Contents

This deployment package contains everything needed for a production-ready WARD OPS deployment:

### Core Files

| File | Purpose | Required |
|------|---------|----------|
| `deploy.sh` | Automated deployment script | ✅ Yes |
| `docker-compose.yml` | Service orchestration configuration | ✅ Yes |
| `.env.prod.example` | Environment configuration template | ✅ Yes |
| `verify.sh` | Post-deployment verification | ⭐ Recommended |

### Documentation

| File | Purpose | Audience |
|------|---------|----------|
| `QUICKSTART.md` | 5-minute quick start guide | Operators |
| `README.md` | Comprehensive deployment guide | All |
| `DEPLOYMENT.md` | Detailed technical documentation | Engineers |
| `PACKAGE_INFO.md` | This file - package overview | All |

---

## 🎯 Deployment Methods

### Method 1: Automated (Recommended)

**Command:**
```bash
sudo ./deploy.sh
```

**Time:** ~5 minutes
**Difficulty:** Easy
**Best for:** Quick deployments, non-technical staff

**What it does:**
- ✅ Checks prerequisites
- ✅ Generates secure secrets automatically
- ✅ Configures environment
- ✅ Pulls Docker images
- ✅ Starts all services
- ✅ Sets up auto-start

### Method 2: Manual

**Time:** ~15 minutes
**Difficulty:** Medium
**Best for:** Custom configurations, troubleshooting

**Steps:**
1. Install Docker manually
2. Copy files to `/opt/wardops`
3. Create `.env.prod` from template
4. Generate secrets
5. Pull images
6. Start services with `docker compose up -d`

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed steps.

---

## 🏗️ Architecture

### Docker Images

**Application Image:**
```
ward_flux/wardops-app:credobank-latest
```
- Multi-stage build
- Frontend (React) + Backend (FastAPI)
- Python 3.11 slim base
- Size: ~800MB
- Built via GitHub Actions CI/CD

**Database Image:**
```
ward_flux/wardops-postgres-seeded:credobank-latest
```
- PostgreSQL 15 Alpine
- Pre-seeded with CredoBank data
- Includes users, devices, branches, alert rules
- Size: ~50MB
- Built via GitHub Actions CI/CD

### Services

```
┌─────────────────────────────────────┐
│         Docker Compose Stack         │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌────────────────┐   │
│  │   API   │  │  Celery Worker │   │
│  │ :5001   │  │ (SNMP Polling) │   │
│  └────┬────┘  └────────┬───────┘   │
│       │                │            │
│  ┌────┴──────┬────────┴───────┐    │
│  │PostgreSQL │     Redis      │    │
│  │  (Seeded) │  (Task Queue)  │    │
│  └───────────┴────────────────┘    │
│       │                             │
│  ┌────┴──────────────────────┐     │
│  │     Celery Beat           │     │
│  │     (Scheduler)           │     │
│  └───────────────────────────┘     │
└─────────────────────────────────────┘
```

**Ports Exposed:**
- `5001` - API/Backend
- `5432` - PostgreSQL (optional, for external tools)

**Networks:**
- `wardops-network` (172.28.0.0/16)

**Volumes:**
- `db-data` - PostgreSQL persistent data
- `redis-data` - Redis persistence
- `api-data`, `worker-data`, `beat-data` - Application data
- `./logs` - Mounted logs directory
- `./backups` - Mounted backups directory

---

## ⚙️ Configuration

### Environment Variables

All configuration is stored in `.env.prod`:

**Critical Settings:**
- `SECRET_KEY` - JWT signing secret (auto-generated)
- `ENCRYPTION_KEY` - Credential encryption (auto-generated)
- `REDIS_PASSWORD` - Redis authentication (auto-generated)
- `DEFAULT_ADMIN_PASSWORD` - Initial admin password

**Database:**
- `DATABASE_URL` - PostgreSQL connection string

**Application:**
- `LOG_LEVEL` - Logging verbosity (INFO default)
- `MONITORING_MODE` - hybrid/snmp_only/zabbix_only
- `CORS_ORIGINS` - Allowed origins for API

**Optional:**
- `ZABBIX_URL`, `ZABBIX_USER`, `ZABBIX_PASSWORD` - Zabbix integration
- `VICTORIA_URL` - VictoriaMetrics integration

### Pre-seeded Data

The database includes:

**Users:**
- `admin` - Administrator (password: from env)
- Additional users as configured

**Devices:**
- CredoBank-specific network devices
- Branches and locations
- SNMP credentials (encrypted)

**Monitoring:**
- Alert rules and templates
- Monitoring profiles
- SNMP configurations

**System:**
- Default settings and configurations
- Pre-configured alert thresholds

---

## 🔒 Security Features

### Built-in Security

- ✅ JWT-based authentication
- ✅ Bcrypt password hashing
- ✅ AES-256 credential encryption
- ✅ Secure secret generation
- ✅ Role-based access control
- ✅ CORS protection
- ✅ Health check endpoints

### Production Hardening

**Recommended post-deployment:**

1. **Change Default Passwords**
   - Admin UI password
   - Database passwords (if exposed)

2. **Network Security**
   - Configure firewall rules
   - Set up reverse proxy (Nginx)
   - Enable SSL/TLS certificates
   - Restrict PostgreSQL port (5432) access

3. **Backup Strategy**
   - Schedule regular database backups
   - Backup `.env.prod` securely
   - Test restore procedures

4. **Monitoring**
   - Set up external monitoring for the platform itself
   - Configure log rotation
   - Monitor disk usage

---

## 📊 Resource Requirements

### Minimum (Development/Testing)

- **CPU:** 2 cores
- **RAM:** 4 GB
- **Disk:** 20 GB
- **Devices:** Up to 100

### Recommended (Production)

- **CPU:** 4+ cores
- **RAM:** 8 GB
- **Disk:** 50 GB (SSD recommended)
- **Devices:** 100-500

### High-Scale (Enterprise)

- **CPU:** 8+ cores
- **RAM:** 16 GB
- **Disk:** 100 GB SSD
- **Devices:** 500-2000+
- **Note:** Scale Celery workers horizontally

---

## 🚀 Deployment Workflow

### Pre-Deployment

1. Review server specifications
2. Ensure Docker is installed
3. Review network/firewall requirements
4. Obtain Docker registry credentials (if private)
5. Read [QUICKSTART.md](QUICKSTART.md) or [README.md](README.md)

### Deployment

1. Transfer package to server
2. Run `sudo ./deploy.sh`
3. Follow interactive prompts
4. Wait for image pulls (~3-5 minutes)
5. Services start automatically

### Post-Deployment

1. Run `./verify.sh` to check health
2. Access web UI and change admin password
3. Configure monitoring settings
4. Add devices and alert rules
5. Set up backups and monitoring

### Verification Checklist

- [ ] All services show "Up" status
- [ ] API health check returns 200 OK
- [ ] Can log into web UI
- [ ] Database contains seeded data
- [ ] Celery worker is processing tasks
- [ ] Logs show no critical errors

---

## 🛠️ Maintenance

### Regular Tasks

**Daily:**
- Monitor service health
- Review alert dashboard
- Check for critical errors in logs

**Weekly:**
- Review disk space usage
- Check database performance
- Verify backup completion

**Monthly:**
- Apply security updates
- Review and optimize alert rules
- Analyze monitoring coverage

**Quarterly:**
- Update to latest version
- Review resource utilization
- Audit user access and permissions

### Update Procedure

```bash
cd /opt/wardops

# Backup database first
docker compose exec db pg_dump -U fluxdb -Fc ward_ops > backups/pre-update.backup

# Pull new images
docker compose pull

# Restart with new images
docker compose up -d

# Verify
./verify.sh
```

---

## 📞 Support

### Self-Service

1. **Logs:** `docker compose logs -f`
2. **Status:** `docker compose ps`
3. **Health:** `./verify.sh`
4. **Documentation:** [README.md](README.md), [DEPLOYMENT.md](DEPLOYMENT.md)

### Contact

- **Technical Issues:** Ward Tech Solutions support
- **Deployment Help:** See documentation or contact support
- **Feature Requests:** Via support channel

---

## 📝 Version History

### v2.0 - October 2025
- ✨ Production release for CredoBank
- ✨ Pre-seeded PostgreSQL database
- ✨ Automated deployment script
- ✨ Alert rules management system
- ✨ SNMP standalone monitoring
- ✨ Hybrid Zabbix integration
- ✨ Comprehensive documentation

---

## 📄 License & Copyright

**Copyright:** © 2025 WARD Tech Solutions
**Client:** CredoBank
**License:** Proprietary - For CredoBank internal use only

---

## 🎯 Quick Reference

**Deploy:**
```bash
sudo ./deploy.sh
```

**Verify:**
```bash
./verify.sh
```

**Access:**
```
http://your-server-ip:3000
```

**Login:**
```
Username: admin
Password: admin123 (or custom)
```

**Logs:**
```bash
cd /opt/wardops && docker compose logs -f
```

**Restart:**
```bash
cd /opt/wardops && docker compose restart
```

---

**Questions?** See [README.md](README.md) for comprehensive documentation.
