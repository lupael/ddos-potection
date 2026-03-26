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

- [AI Agents — Read This First](#-ai-agents--read-this-first)
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
- [Comparison with FastNetMon](#-comparison-with-fastnetmon)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

## 🚀 Features

### Traffic Collection & Detection
- **NetFlow/sFlow/IPFIX Support**: Collect traffic data from MikroTik, Cisco, and Juniper routers
- **PCAP Capture**: Record packets with standard PCAP format for analysis
- **AF_PACKET/AF_XDP**: High-performance packet capture for Linux systems
- **VLAN Untagging**: Automatic removal of 802.1Q and 802.1ad VLAN tags
- **Real-time Anomaly Detection**: Detect SYN floods, UDP floods, and other attack patterns
- **Attack Fingerprinting**: Automatically capture attack traffic in PCAP format
- **Entropy Analysis**: Identify distributed attacks using statistical analysis
- **Redis Integration**: Fast real-time counters and event streaming

### Threshold Management
- **Hostgroups**: Configure per-subnet thresholds for packets/bytes/flows per second
- **Longest Prefix Match**: Hierarchical subnet configuration with most specific match
- **Default Thresholds**: System-wide defaults for networks without specific configuration
- **Script Execution**: Trigger custom block/notify scripts when thresholds exceeded
- **Dynamic Configuration**: Update thresholds without service restart

### Mitigation & Automation
- **Automated Firewall Rules**: Support for iptables/nftables
- **MikroTik API Integration**: Direct router control for rule deployment
- **BGP Blackholing (RTBH)**: Announce blackhole routes for attack traffic (supports ExaBGP, FRR, BIRD)
- **FlowSpec Support**: Send FlowSpec announcements to BGP routers
- **Custom Rule Engine**: Define rate limits, IP blocks, protocol filters, and geo-blocking

### Beautiful Dashboard
- **React 18 UI**: Modern, responsive enterprise-grade web interface
- **Dark Navbar**: Sticky dark navy navigation with active-link highlighting and emoji icons
- **KPI Stat Cards**: Colour-coded metric cards with trend indicators and contextual icons
- **Real-time Charts**: Live traffic visualization and attack patterns
- **Rule Management**: Easy-to-use interface for adding/removing rules
- **Alert Dashboard**: Severity-coded (critical/high/medium/low) alert feed with one-click mitigate/resolve
- **System Status Panel**: Per-service health indicators on the dashboard
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

## 📸 Screenshots

The screenshots below show the redesigned enterprise-grade UI (dark navbar, colour-coded severity badges, KPI stat cards, and real-time status indicators).

### 🔐 Login Page
<div align="center">

![Login Page](docs/screenshots/login.png)

*Dark glassmorphism login screen with gradient branding and enterprise security messaging*

</div>

### 📊 Operations Dashboard
<div align="center">

![Dashboard](docs/screenshots/dashboard.png)

*Real-time KPI cards with colour-coded status indicators, alert severity breakdown, quick-action shortcuts, and live system health panel*

</div>

### 🚨 Alert Management
<div align="center">

![Alert Management](docs/screenshots/alerts.png)

*Colour-coded severity badges (critical/high/medium/low), per-alert mitigation and resolve actions, live feed of active threats*

</div>

### 📡 Traffic Monitor
<div align="center">

![Traffic Monitor](docs/screenshots/traffic.png)

*Protocol distribution bar-chart, live traffic log with anomaly flags, and per-flow bytes/packet counters*

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

### Packet Capture
```bash
# Start PCAP capture
curl -X POST http://localhost:8000/api/v1/capture/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "eth0",
    "capture_mode": "af_packet",
    "duration": 60,
    "filter_bpf": "tcp and port 80"
  }'

# List captures
curl -X GET http://localhost:8000/api/v1/capture/list \
  -H "Authorization: Bearer <token>"

# Download PCAP file
curl -X GET http://localhost:8000/api/v1/capture/download/capture_20260201_123456.pcap \
  -H "Authorization: Bearer <token>" \
  -o capture.pcap
```

### Hostgroups (Per-Subnet Thresholds)
```bash
# Create hostgroup
curl -X POST http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_network_1",
    "subnet": "192.168.1.0/24",
    "thresholds": {
      "packets_per_second": 10000,
      "bytes_per_second": 100000000,
      "flows_per_second": 1000
    },
    "scripts": {
      "block": "/etc/ddos-protection/scripts/block.sh",
      "notify": "/etc/ddos-protection/scripts/notify.sh"
    }
  }'

# List hostgroups
curl -X GET http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer <token>"

# Check IP thresholds
curl -X POST http://localhost:8000/api/v1/hostgroups/check-ip \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.50"}'
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
- **sFlow** - Real-time traffic sampling
- **IPFIX** - IP Flow Information Export
- **BGP/ExaBGP** - Route advertisements for mitigation

## 🔒 Security

- **TLS/SSL**: All communications encrypted
- **JWT Authentication**: Secure token-based auth
- **Role-based Access**: Fine-grained permissions
- **API Key Management**: Secure router integration
- **Password Hashing**: bcrypt for password storage
- **Input Validation**: Pydantic models for data validation

## 📊 Monitoring

The platform includes comprehensive monitoring and alerting capabilities:

### Prometheus Metrics
- **Traffic metrics**: packets/sec, bytes/sec, flow counts by protocol
- **Alert metrics**: active alerts, severity distribution, resolution rates
- **Mitigation metrics**: active mitigations, success rates, duration histograms
- **Attack detection**: attack types, volumes, targets
- **System health**: database, Redis, API status

### Grafana Dashboards
- **DDoS Overview**: Real-time operational dashboard with traffic stats and alerts
- **Attack Analysis**: Detailed attack visualization with geographic data
- **Mitigation Status**: Track active and historical mitigations with success metrics
- **System Health**: Monitor database connections, API performance, and resource usage

### Multi-channel Alerts
- **Email notifications**: HTML-formatted alerts with severity color coding
- **SMS alerts**: Twilio-based SMS for critical incidents (concise format)
- **Telegram notifications**: Rich formatted messages with emoji indicators
- Configurable per ISP with channel preferences

### Live Attack Maps
- **Real-time visualization**: WebSocket-based attack streaming
- **Geographic mapping**: Source and target IP geolocation
- **Attack heatmaps**: Aggregate attack data by region and time
- **Statistics dashboard**: Attack counts, types, and targets

### API Endpoints
```bash
# Prometheus metrics
GET /metrics

# Live attack data
GET /api/v1/attack-map/live-attacks
GET /api/v1/attack-map/attack-heatmap
GET /api/v1/attack-map/attack-statistics
WS  /api/v1/attack-map/ws/live-attacks

# Mitigation status
GET /api/v1/mitigation/status/active
GET /api/v1/mitigation/status/history
GET /api/v1/mitigation/status/analytics
```

For detailed monitoring setup and configuration, see [Monitoring Guide](project-docs/MONITORING.md).

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🔄 Comparison with FastNetMon

Wondering how we compare to commercial solutions like FastNetMon Advanced? We've got you covered!

Our platform offers a **modern, open-source alternative** to commercial DDoS protection solutions. Here's a quick comparison:

| Feature | Our Platform | FastNetMon Advanced |
|---------|--------------|---------------------|
| **License** | ✓ Open Source (MIT) | ❌ Commercial |
| **Cost** | ✓ Free | ❌ Paid License |
| **Multi-tenancy** | ✓ Full ISP support | ❌ Limited |
| **Modern UI** | ✓ React Dashboard | ✓ Web UI |
| **Customization** | ✓ Unlimited | ❌ Limited |
| **Scale** | Up to 100Gbps+ | Up to 5Tbps |

**Key Advantages:**
- 🆓 **Zero licensing costs** - No expensive commercial licenses
- 🔓 **Full source code access** - Customize anything you need
- 🏢 **Built-in multi-tenancy** - Perfect for ISP service offerings
- 🚀 **Modern tech stack** - React, FastAPI, PostgreSQL, Redis
- 🐳 **Docker-first** - Deploy in minutes with Docker Compose
- 💳 **Payment integration** - Stripe/PayPal for subscription billing

**When to choose us:**
- You want an open-source solution with no licensing fees
- You need full customization capabilities
- You're building a multi-tenant ISP DDoS protection service
- Your network is under 100Gbps
- You prefer modern web technologies and DevOps practices

For a detailed feature-by-feature comparison, migration guide, and use case recommendations, see our **[FastNetMon Comparison Guide](project-docs/COMPARISON_FASTNETMON.md)**.

## 🤖 AI Agents — Read This First

> **If you are an AI coding agent** (GitHub Copilot, Claude, GPT-4o, Cursor, Aider, or any
> other AI tool): you **must** read
> [`project-docs/AI_INSTRUCTIONS.md`](project-docs/AI_INSTRUCTIONS.md) before making any
> changes to this repository. It contains mandatory rules, style guides, architecture
> constraints, and the correct technical reference for every area of the codebase.
>
> Instruction files are also present at:
> - [`AGENTS.md`](AGENTS.md) — OpenAI Codex / general agents
> - [`CLAUDE.md`](CLAUDE.md) — Claude (Anthropic)
> - [`.github/copilot-instructions.md`](.github/copilot-instructions.md) — GitHub Copilot

---

## 📖 Documentation

All documentation lives in the **[`project-docs/`](project-docs/)** folder.
See **[`project-docs/INDEX.md`](project-docs/INDEX.md)** for the full table of contents.

### Planning & Status
- [Project Overview](project-docs/OVERVIEW.md) — architecture, tech stack, service ports
- [Status Report](project-docs/REPORT.md) — current implementation status & known issues
- [Roadmap](project-docs/ROADMAP.md) — planned features by phase (Q2 2026 – Q2 2027)
- [TODO](project-docs/TODO.md) — open tasks with file references and priorities
- [Changelog](project-docs/CHANGELOG.md) — version history

### Getting Started
- [Quick Start Guide](project-docs/QUICKSTART.md) — running in under 10 minutes
- [Deployment Guide](project-docs/DEPLOYMENT.md) — production deployment
- [Development Guide](project-docs/DEVELOPMENT.md) — local dev setup & standards
- [Contributing Guidelines](project-docs/CONTRIBUTING.md)

### Feature Guides
- [Traffic Collection Guide](project-docs/TRAFFIC_COLLECTION.md) — NetFlow/sFlow/IPFIX
- [Packet Capture & Thresholds Guide](project-docs/PACKET_CAPTURE.md) — PCAP, AF_PACKET, AF_XDP, VLAN, hostgroups
- [BGP Blackholing (RTBH) Guide](project-docs/BGP-RTBH.md) — BGP-based mitigation
- [FlowSpec Guide](project-docs/FLOWSPEC.md) — FlowSpec announcements
- [Custom Rules Guide](project-docs/CUSTOM-RULES.md) — rule engine
- [Monitoring & Alerting Guide](project-docs/MONITORING.md) — Prometheus, Grafana, notifications
- [Multi-ISP Setup Guide](project-docs/MULTI_ISP_SETUP.md) — multi-tenant configuration

### Security
- [Security Documentation](project-docs/SECURITY.md)
- [Security Summary](project-docs/SECURITY_SUMMARY.md) — CodeQL analysis results

### Comparison
- [FastNetMon Comparison](project-docs/COMPARISON_FASTNETMON.md) — vs FastNetMon Advanced Edition

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](project-docs/CONTRIBUTING.md) before submitting PRs.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

Need help? We're here for you!

- 📖 [Documentation](project-docs/INDEX.md)
- 🐛 [GitHub Issues](https://github.com/i4edubd/ddos-potection/issues)
- 💬 [Discussions](https://github.com/i4edubd/ddos-potection/discussions)
- 📧 Email: support@ispbills.com

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
