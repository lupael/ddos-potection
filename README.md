<div align="center">

# 🛡️ DDoS Protection Platform for ISPs

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.0+-61DAFB.svg?logo=react)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)

**A comprehensive, enterprise-grade DDoS protection platform designed for Internet Service Providers (ISPs)**

Real-time traffic monitoring • Anomaly detection • Automated mitigation • Beautiful web dashboard

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Screenshots](#-screenshots)

</div>

---

## 📑 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Requirements](#-requirements)
- [Quick Start](#-quick-start)
- [Router Integration](#-router-integration)
- [API Documentation](#-api-documentation)
- [Architecture](#️-architecture)
- [Technology Stack](#-technology-stack)
- [Security](#-security)
- [Monitoring](#-monitoring)
- [Testing](#-testing)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

## 🚀 Features

### 🎯 Performance & Detection
- **Detects DoS/DDoS in 1-2 seconds**: Ultra-fast attack detection using real-time analysis
- **Scales to terabits on single server**: NetFlow/sFlow/IPFIX with sampling handles massive traffic
- **40G+ in mirror mode**: Direct packet capture with AF_PACKET and AF_XDP

### 📡 Supported Packet Capture Engines
- **NetFlow v5, v9, v9 Lite**: Industry-standard flow export from Cisco and compatible routers
- **IPFIX**: IETF standard for IP Flow Information Export (NetFlow v10)
- **sFlow v5**: Real-time traffic sampling for switches and routers
- **PCAP**: Full packet capture for forensic analysis
- **AF_PACKET (Recommended)**: High-performance Linux native capture (10-40 Gbps)
- **AF_XDP**: Ultra-high-speed XDP-based capture (40-100+ Gbps)
- **Netmap**: FreeBSD support (deprecated for Linux)
- **PF_RING / PF_RING ZC**: Legacy support (deprecated, CentOS 6 only in v1.2.0)

[See comparison table for all packet capture engines →](docs/PACKET_CAPTURE.md)

### Traffic Collection & Detection
- **Multi-vendor Router Support**: Collect traffic data from MikroTik, Cisco, Juniper, and other routers
- **Real-time Anomaly Detection**: Detect SYN floods, UDP floods, and other attack patterns
- **Entropy Analysis**: Identify distributed attacks using statistical analysis
- **Complete IPv6 Support**: Full support for IPv6 traffic collection, detection, and mitigation
- **Per-Subnet Thresholds**: Configure different thresholds per subnet with hostgroups feature
- **VLAN Untagging**: Automatic VLAN tag removal in mirror and sFlow modes
- **Redis Integration**: Fast real-time counters and event streaming

### Mitigation & Automation
- **Automated Firewall Rules**: Support for iptables/nftables
- **MikroTik API Integration**: Direct router control for rule deployment
- **BGP Blackholing (RTBH)**: Announce blackhole routes for attack traffic (supports ExaBGP, GoBGP, FRR, BIRD)
- **FlowSpec Support**: Send FlowSpec announcements to BGP routers (RFC 5575)
- **Custom Rule Engine**: Define rate limits, IP blocks, protocol filters, geo-blocking, and port filters
- **Trigger Scripts**: Execute custom block/notify scripts on attack detection
- **Attack Fingerprints**: Capture attack traffic in PCAP format for forensic analysis

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

### Data Export & Integration
- **Kafka Export**: Stream flows and packets in JSON and Protobuf format
- **ClickHouse Integration**: High-performance analytics database
- **InfluxDB Integration**: Time-series metrics and monitoring
- **Graphite Integration**: Metrics aggregation and visualization
- **MongoDB Protocol Support**: Compatible with native MongoDB and FerretDB

### Monitoring & Alerts
- **Prometheus Support**: System metrics and total traffic counters
- **Grafana Dashboards**: Advanced visualization
- **Multi-channel Alerts**: Email, SMS, Telegram, Slack, and PagerDuty notifications
- **Live Attack Maps**: Visualize attacks in real-time
- **Mitigation Status**: Track active and historical mitigations

### API & Automation
- **RESTful API**: Complete API for programmatic access and automation
- **Redis Integration**: Real-time data processing and pub/sub messaging
- **Webhook Support**: Integrate with external systems

## 📸 Screenshots

### Dashboard Overview
<div align="center">

![Dashboard](https://github.com/user-attachments/assets/477edd08-aee4-4c7a-9b7a-b07452e2252e)

*Real-time monitoring dashboard showing traffic statistics, active alerts, and system health*

</div>

### Traffic Monitor
<div align="center">

![Traffic Monitor](https://github.com/user-attachments/assets/3b9173ed-128a-4c9f-98ef-6e81a4b6148c)

*Live traffic visualization with protocol distribution and attack pattern detection*

</div>

### Alert Management
<div align="center">

![Alerts](https://github.com/user-attachments/assets/e3646f08-32fe-4d81-8f07-612535751de1)

*Comprehensive alert dashboard with severity levels and real-time notifications*

</div>

### Rule Management
<div align="center">

![Rules](https://github.com/user-attachments/assets/42a87a3f-4bb7-48df-a71c-792f62c5935d)

*Intuitive interface for creating and managing DDoS mitigation rules*

</div>

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

## 💻 Technology Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL 15** - Primary data storage
- **Redis 7** - Real-time caching and pub/sub
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation and settings
- **Celery** - Distributed task queue (optional)

### Frontend
- **React 18** - Modern UI framework
- **Chart.js** - Beautiful data visualization
- **Axios** - HTTP client
- **React Router** - Navigation
- **CSS3** - Responsive styling

### DevOps & Monitoring
- **Docker & Docker Compose** - Containerization
- **Prometheus** - Metrics collection
- **Grafana** - Monitoring dashboards
- **Kubernetes** - Production orchestration (optional)
- **GitHub Actions** - CI/CD pipeline

### Network Protocols
- **NetFlow v9/v10** - Cisco traffic export
- **sFlow v5** - Real-time traffic sampling
- **IPFIX** - IP Flow Information Export (NetFlow v10)
- **BGP** - Route advertisements for mitigation (ExaBGP, GoBGP, FRR, BIRD)
- **PCAP/AF_PACKET/AF_XDP** - Direct packet capture engines

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
- [Complete Feature Guide](docs/FEATURES.md) - **Comprehensive overview of all features**
- [Packet Capture Engine Guide](docs/PACKET_CAPTURE.md) - **Compare all 8 packet capture engines**
- [Traffic Collection Guide](docs/TRAFFIC_COLLECTION.md) - NetFlow, sFlow, and IPFIX setup
- [BGP Blackholing (RTBH) Guide](docs/BGP-RTBH.md) - Setup ExaBGP, GoBGP, FRR, and BIRD
- [FlowSpec Guide](docs/FLOWSPEC.md) - RFC 5575 traffic filtering
- [Custom Rules Engine](docs/CUSTOM-RULES.md) - Rate limits, geo-blocking, and more
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Security Documentation](SECURITY.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

Need help? We're here for you!

- 📖 [Documentation](docs/)
- 🐛 [GitHub Issues](https://github.com/i4edubd/ddos-potection/issues)
- 💬 [Discussions](https://github.com/i4edubd/ddos-potection/discussions)
- 📧 Email: support@example.com

## 🙏 Acknowledgments

Special thanks to these amazing open-source projects:

- [FastAPI](https://fastapi.tiangolo.com/) - Excellent Python web framework
- [React](https://reactjs.org/) - Modern UI framework
- [PostgreSQL](https://www.postgresql.org/) - Robust database
- [Redis](https://redis.io/) - Fast in-memory data store
- [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/) - Monitoring stack

---

<div align="center">

**⭐ Star this project if you find it useful! ⭐**

**Made with ❤️ for ISPs worldwide**

![GitHub stars](https://img.shields.io/github/stars/i4edubd/ddos-potection?style=social)
![GitHub forks](https://img.shields.io/github/forks/i4edubd/ddos-potection?style=social)

</div>