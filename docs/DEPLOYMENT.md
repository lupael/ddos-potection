# Deployment Guide

This guide provides detailed instructions for deploying the DDoS Protection Platform in production environments.

## Prerequisites

- Linux server (Ubuntu 22.04 LTS recommended)
- Docker and Docker Compose installed
- Domain name with DNS configured
- SSL certificate (Let's Encrypt recommended)
- Minimum 4GB RAM, 2 CPU cores
- 50GB disk space

## Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Create application user
sudo useradd -m -s /bin/bash ddos
sudo usermod -aG docker ddos
```

### 2. Clone and Configure

```bash
# Switch to ddos user
sudo su - ddos

# Clone repository
git clone https://github.com/i4edubd/ddos-potection.git
cd ddos-potection

# Create production environment file
cat > backend/.env << EOF
# Database
DATABASE_URL=postgresql://ddos_user:CHANGE_THIS_PASSWORD@postgres:5432/ddos_platform

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security (CHANGE THESE!)
SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Settings
HOST=0.0.0.0
PORT=8000
DEBUG=False

# CORS (add your domain)
ALLOWED_ORIGINS=["https://yourdomain.com"]

# Detection Thresholds
SYN_FLOOD_THRESHOLD=10000
UDP_FLOOD_THRESHOLD=50000
ENTROPY_THRESHOLD=3.5
AUTO_MITIGATION=True

# Alerts (configure your settings)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=alerts@yourdomain.com

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Payment (Stripe)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
EOF
```

### 3. Configure Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow NetFlow/sFlow/IPFIX
sudo ufw allow 2055/udp
sudo ufw allow 6343/udp
sudo ufw allow 4739/udp

# Enable firewall
sudo ufw enable
```

### 4. SSL/TLS Configuration

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificate will be saved at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### 5. Nginx Reverse Proxy

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo cat > /etc/nginx/sites-available/ddos-platform << 'EOF'
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/ddos-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Start Services

```bash
# Build and start containers
docker-compose -f docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 7. Database Initialization

```bash
# Run database migrations (if using Alembic)
docker-compose exec backend alembic upgrade head

# Create first admin user via API
# IMPORTANT: Use a strong, unique password - NOT the example shown here!
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@yourdomain.com",
    "password": "USE-A-STRONG-UNIQUE-PASSWORD-HERE",
    "isp_name": "Admin ISP",
    "role": "admin"
  }'

# Alternative: Create via Python script with environment variable
docker-compose exec backend python -c "
import os
from database import SessionLocal
from models.models import User, ISP
from routers.auth_router import get_password_hash
import secrets

# Get password from environment variable (set this before running!)
admin_password = os.environ.get('ADMIN_PASSWORD')
if not admin_password:
    raise ValueError('ADMIN_PASSWORD environment variable must be set')

db = SessionLocal()
isp = ISP(name='Admin ISP', email='admin@yourdomain.com', api_key=secrets.token_urlsafe(32))
db.add(isp)
db.commit()

user = User(
    username='admin',
    email='admin@yourdomain.com',
    hashed_password=get_password_hash(admin_password),
    role='admin',
    isp_id=isp.id
)
db.add(user)
db.commit()
print('Admin user created successfully')
"
```

## Monitoring Setup

### Configure Prometheus

Edit `docker/prometheus.yml` to add additional targets:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ddos-backend'
    static_configs:
      - targets: ['backend:8000']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### Configure Grafana

1. Access Grafana at https://yourdomain.com:3001
2. Login with admin/admin (change password)
3. Add Prometheus as a data source
4. Import pre-built dashboards from docs/grafana/

## Backup Strategy

### Database Backup

```bash
# Create backup script
cat > /home/ddos/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ddos/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec ddos-postgres pg_dump -U ddos_user ddos_platform > \
  $BACKUP_DIR/db_backup_$DATE.sql

# Backup Redis
docker exec ddos-redis redis-cli --rdb /data/dump.rdb
docker cp ddos-redis:/data/dump.rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# Compress backups
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
  $BACKUP_DIR/db_backup_$DATE.sql \
  $BACKUP_DIR/redis_backup_$DATE.rdb

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/backup_$DATE.tar.gz"
EOF

chmod +x /home/ddos/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ddos/backup.sh") | crontab -
```

## Scaling Considerations

### Horizontal Scaling

For high-traffic ISPs, consider:

1. **Load Balancer**: Use HAProxy or AWS ELB
2. **Multiple Backend Instances**: Scale API servers
3. **PostgreSQL Replication**: Master-slave setup
4. **Redis Cluster**: For distributed caching
5. **Separate Worker Nodes**: Run collectors/detectors on dedicated servers

### Kubernetes Deployment

See `docs/kubernetes/` for K8s manifests and Helm charts.

## Maintenance

### Update Application

```bash
cd /home/ddos/ddos-potection
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Monitor Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100
```

### Health Checks

```bash
# API health
curl https://yourdomain.com/api/v1/health

# Database connectivity
docker exec ddos-postgres pg_isready -U ddos_user

# Redis connectivity
docker exec ddos-redis redis-cli ping
```

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs backend

# Restart service
docker-compose restart backend

# Rebuild if needed
docker-compose up -d --build backend
```

### Database connection issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check database exists
docker exec ddos-postgres psql -U ddos_user -l

# Recreate database
docker-compose exec postgres psql -U ddos_user -c "DROP DATABASE IF EXISTS ddos_platform;"
docker-compose exec postgres psql -U ddos_user -c "CREATE DATABASE ddos_platform;"
```

### High memory usage

```bash
# Check resource usage
docker stats

# Limit container resources
# Edit docker-compose.yml and add:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

## Security Hardening

1. **Change default passwords**
2. **Enable firewall (ufw)**
3. **Use strong SECRET_KEY**
4. **Enable SSL/TLS**
5. **Regular security updates**
6. **Limit SSH access**
7. **Enable fail2ban**
8. **Regular backups**
9. **Monitor logs for suspicious activity**
10. **Keep Docker images updated**

## Support

For production deployment support:
- Email: support@example.com
- Documentation: https://docs.yourdomain.com
- Community: https://community.yourdomain.com
