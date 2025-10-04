# 🚀 WARD OPS Network Monitor - Deployment Guide

## Overview

WARD OPS is a production-ready network monitoring platform that integrates with Zabbix to provide comprehensive visibility into your network infrastructure. Each deployment runs independently with its own isolated database.

## 📋 Prerequisites

- Docker installed (version 20.10 or higher)
- Zabbix server accessible from your deployment environment
- Internet access to pull Docker images from GitHub Container Registry

## 🐳 Docker Deployment (Recommended)

### Option 1: Pull from GitHub Container Registry

```bash
# Pull the latest image
docker pull ghcr.io/ward-tech-solutions/ward-tech-solutions:latest

# Run the container
docker run -d \
  --name ward-ops \
  -p 5001:5001 \
  -v ward-ops-data:/app/data \
  -v ward-ops-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/ward-tech-solutions/ward-tech-solutions:latest
```

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/ward-tech-solutions/ward-tech-solutions.git
cd ward-tech-solutions

# Build the Docker image
docker build -t ward-ops:latest .

# Run the container
docker run -d \
  --name ward-ops \
  -p 5001:5001 \
  -v ward-ops-data:/app/data \
  -v ward-ops-logs:/app/logs \
  --restart unless-stopped \
  ward-ops:latest
```

## 🔧 Configuration

### Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change the default password immediately after first login!

### Environment Variables

You can customize the deployment using environment variables:

```bash
docker run -d \
  --name ward-ops \
  -p 5001:5001 \
  -e PORT=5001 \
  -e SETUP_MODE=enabled \
  -v ward-ops-data:/app/data \
  -v ward-ops-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/ward-tech-solutions/ward-tech-solutions:latest
```

Available environment variables:
- `PORT`: Application port (default: 5001)
- `SETUP_MODE`: Enable/disable setup mode (default: enabled)

## 🌐 Accessing the Platform

After deployment, access the platform at:

```
http://localhost:5001
```

Or replace `localhost` with your server IP/domain:

```
http://your-server-ip:5001
```

## 🔍 Health Check

Monitor the health of your deployment:

```bash
# Simple health check
curl http://localhost:5001/health

# Detailed health check with component status
curl http://localhost:5001/api/v1/health
```

Response includes:
- Database status
- Zabbix connection status
- API health
- Version information

## 📊 Data Persistence

The deployment uses Docker volumes for data persistence:

- `ward-ops-data`: SQLite database and application data
- `ward-ops-logs`: Application logs

### Backup Data

```bash
# Backup database
docker run --rm \
  -v ward-ops-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/ward-ops-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore Data

```bash
# Restore database
docker run --rm \
  -v ward-ops-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/ward-ops-backup-YYYYMMDD.tar.gz -C /"
```

## 🔄 Updating

### Update to Latest Version

```bash
# Stop and remove current container
docker stop ward-ops
docker rm ward-ops

# Pull latest image
docker pull ghcr.io/ward-tech-solutions/ward-tech-solutions:latest

# Run new container (data persists in volumes)
docker run -d \
  --name ward-ops \
  -p 5001:5001 \
  -v ward-ops-data:/app/data \
  -v ward-ops-logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/ward-tech-solutions/ward-tech-solutions:latest
```

## 🐛 Troubleshooting

### Container Not Starting

```bash
# Check container logs
docker logs ward-ops

# Check container status
docker ps -a | grep ward-ops
```

### Database Issues

```bash
# Reset database (WARNING: This deletes all data!)
docker volume rm ward-ops-data
```

### Port Already in Use

```bash
# Find process using port 5001
lsof -ti:5001

# Kill the process
lsof -ti:5001 | xargs kill -9

# Or use a different port
docker run -d --name ward-ops -p 5002:5001 ...
```

### Zabbix Connection Issues

1. Verify Zabbix server is accessible from Docker container
2. Check Zabbix API URL in Settings page
3. Verify Zabbix credentials are correct
4. Check firewall rules between containers

## 🔒 Security Recommendations

1. **Change default password** immediately after first login
2. **Use HTTPS** with a reverse proxy (nginx/traefik)
3. **Regular backups** of the data volume
4. **Firewall rules** to restrict access to port 5001
5. **Keep updated** to latest version for security patches

## 📝 Production Deployment with Nginx (Optional)

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Generate SSL certificate
certbot --nginx -d your-domain.com
```

## 📞 Support

For issues, questions, or feature requests:
- Email: support@wardops.tech
- GitHub Issues: https://github.com/ward-tech-solutions/ward-tech-solutions/issues

## 📄 License

Copyright © 2025 WARD Tech Solutions. All rights reserved.
