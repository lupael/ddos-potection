# DDoS Protection Platform for ISPs

A comprehensive, full-stack DDoS protection platform designed for Internet Service Providers (ISPs). This platform provides real-time traffic monitoring, anomaly detection, automated mitigation, and a beautiful web dashboard for managing DDoS attacks.

## 🚀 Features

### Traffic Collection & Detection
- **NetFlow/sFlow/IPFIX Support**: Collect traffic data from MikroTik, Cisco, and Juniper routers
- **Real-time Anomaly Detection**: Detect SYN floods, UDP floods, and other attack patterns
- **Entropy Analysis**: Identify distributed attacks using statistical analysis
- **Redis Integration**: Fast real-time counters and event streaming

### Mitigation & Automation
- **Automated Firewall Rules**: Support for iptables/nftables
- **MikroTik API Integration**: Direct router control for rule deployment
- **BGP Blackholing (RTBH)**: Announce blackhole routes for attack traffic (supports ExaBGP, FRR, BIRD)
- **FlowSpec Support**: Send FlowSpec announcements to BGP routers
- **Custom Rule Engine**: Define rate limits, IP blocks, protocol filters, and geo-blocking

### Beautiful Dashboard
- **React-based UI**: Modern, responsive web interface
- **Real-time Charts**: Live traffic visualization and attack patterns
- **Rule Management**: Easy-to-use interface for adding/removing rules
- **Alert Dashboard**: Monitor and respond to security events
- **Settings Panel**: Configure thresholds, notifications, and API keys

### Multi-ISP Support
- **Multi-tenant Architecture**: Isolated dashboards and rule sets per ISP
- **Role-based Access Control**: Admin, operator, and viewer roles
- **Subscription Management**: Support for paid service tiers
- **Payment Integration**: Stripe, PayPal, and other payment gateways
- **Monthly Reports**: Generate PDF/CSV reports for customers

### Monitoring & Alerts
- **Prometheus Integration**: Comprehensive metrics collection
- **Grafana Dashboards**: Advanced visualization
- **Multi-channel Alerts**: Email, SMS, and Telegram notifications
- **Live Attack Maps**: Visualize attacks in real-time
- **Mitigation Status**: Track active and historical mitigations

## 📋 Requirements

- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+
- Python 3.11+
- Node.js 18+

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/i4edubd/ddos-potection.git
cd ddos-potection
```

### 2. Configure Environment

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://ddos_user:ddos_pass@postgres:5432/ddos_platform

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Detection Thresholds
SYN_FLOOD_THRESHOLD=10000
UDP_FLOOD_THRESHOLD=50000
ENTROPY_THRESHOLD=3.5

# Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
TELEGRAM_BOT_TOKEN=your-bot-token
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Traffic Collector (ports 2055/UDP, 6343/UDP, 4739/UDP)
- Anomaly Detector
- Frontend Dashboard (port 3000)
- Prometheus (port 9090)
- Grafana (port 3001)

### 4. Access the Platform

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

### 5. Create Your First Account

Use the API to register:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@yourisp.com",
    "password": "YourSecurePassword123!",
    "isp_name": "Your ISP Name",
    "role": "admin"
  }'
```

Then login at http://localhost:3000 with your credentials.

## 🔧 Router Integration

### MikroTik

```bash
# Using the provided script
python scripts/mikrotik_integration.py 192.168.1.1 admin password <collector-ip> 2055
```

Or configure manually:
```
/ip traffic-flow
set enabled=yes interfaces=all
/ip traffic-flow target
add address=<collector-ip>:2055 version=9
```

### Cisco

```bash
# Generate configuration
bash scripts/cisco_netflow.sh 192.168.1.1 <collector-ip> 2055
```

### Juniper

```bash
# Generate configuration
bash scripts/juniper_sflow.sh 192.168.1.1 <collector-ip> 6343
```

## 📚 API Documentation

The platform provides a RESTful API for programmatic access:

### Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=password"

# Get current user
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

### Traffic Monitoring
```bash
# Get real-time traffic stats
curl -X GET http://localhost:8000/api/v1/traffic/realtime \
  -H "Authorization: Bearer <token>"

# Get protocol distribution
curl -X GET http://localhost:8000/api/v1/traffic/protocols \
  -H "Authorization: Bearer <token>"
```

### Rule Management
```bash
# Create a rule
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block malicious IP",
    "rule_type": "ip_block",
    "condition": {"ip": "1.2.3.4"},
    "action": "block",
    "priority": 100
  }'

# List rules
curl -X GET http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer <token>"
```

### Alerts
```bash
# List active alerts
curl -X GET http://localhost:8000/api/v1/alerts/?status=active \
  -H "Authorization: Bearer <token>"

# Resolve an alert
curl -X POST http://localhost:8000/api/v1/alerts/1/resolve \
  -H "Authorization: Bearer <token>"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                     http://localhost:3000                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Backend API (FastAPI)                     │
│                     http://localhost:8000                    │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
    ┌──────▼─────┐  ┌────▼─────┐  ┌────▼──────┐
    │ PostgreSQL │  │  Redis   │  │ Services  │
    │  Database  │  │  Cache   │  │ (Workers) │
    └────────────┘  └──────────┘  └───────────┘
                                        │
                          ┌─────────────┼─────────────┐
                          │             │             │
                   ┌──────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
                   │   Traffic   │ │Anomaly │ │ Mitigation │
                   │  Collector  │ │Detector│ │  Service   │
                   └──────┬──────┘ └────────┘ └─────┬──────┘
                          │                          │
            ┌─────────────┼──────────────┐          │
            │             │              │          │
      ┌─────▼─────┐ ┌────▼─────┐ ┌─────▼────┐ ┌───▼────┐
      │ MikroTik  │ │  Cisco   │ │ Juniper  │ │ BGP    │
      │  Router   │ │  Router  │ │  Router  │ │ Peers  │
      └───────────┘ └──────────┘ └──────────┘ └────────┘
```

## 🔒 Security

- **TLS/SSL**: All communications encrypted
- **JWT Authentication**: Secure token-based auth
- **Role-based Access**: Fine-grained permissions
- **API Key Management**: Secure router integration
- **Password Hashing**: bcrypt for password storage
- **Input Validation**: Pydantic models for data validation

## 📊 Monitoring

The platform includes Prometheus and Grafana for comprehensive monitoring:

- Traffic metrics (packets/sec, bytes/sec)
- Alert statistics
- API performance
- Database queries
- System resources

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📖 Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [BGP Blackholing (RTBH) Guide](docs/BGP-RTBH.md) - Setup and use BGP-based DDoS mitigation
- [Security Documentation](SECURITY.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- GitHub Issues: https://github.com/i4edubd/ddos-potection/issues
- Email: support@example.com

## 🙏 Acknowledgments

- FastAPI for the excellent Python web framework
- React for the frontend framework
- PostgreSQL and Redis for data storage
- Prometheus and Grafana for monitoring

---

**Made with ❤️ for ISPs worldwide**