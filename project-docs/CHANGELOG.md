# Changelog

All notable changes to the DDoS Protection Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-03-25

### Security
- **HIGH**: Updated `python-jose[cryptography]` from 3.3.0 to 3.4.0 to fix algorithm confusion
  vulnerability with OpenSSH ECDSA keys (affected versions < 3.4.0)
- **HIGH**: Updated `axios` from ^1.6.5 to ^1.13.5 (resolved 1.13.6) to fix Denial of Service
  vulnerability via `__proto__` key in `mergeConfig` (affected versions >= 1.0.0, <= 1.13.4)

## [1.0.1] - 2024-01-31

### Security
- **CRITICAL**: Updated `fastapi` from 0.109.0 to 0.109.1 to fix Content-Type Header ReDoS vulnerability
- **CRITICAL**: Updated `python-multipart` from 0.0.6 to 0.0.22 to fix:
  - Arbitrary File Write vulnerability
  - Denial of Service via malformed multipart/form-data boundary
  - Content-Type Header ReDoS vulnerability

## [1.0.0] - 2024-01-31

### Added

#### Backend
- FastAPI-based REST API with comprehensive endpoints
- PostgreSQL database models for ISPs, users, rules, alerts, and traffic logs
- JWT-based authentication and authorization system
- Role-based access control (admin, operator, viewer)
- Multi-tenant architecture with ISP isolation
- Traffic collector service supporting NetFlow/sFlow/IPFIX
- Anomaly detection engine with:
  - SYN flood detection
  - UDP flood detection
  - Entropy-based anomaly detection
- Automated mitigation service with:
  - iptables/nftables integration
  - MikroTik API support
  - BGP blackholing (RTBH) capability
  - FlowSpec announcement support
- Custom rule engine for rate limits, IP blocks, and protocol filters
- Report generation system (monthly/weekly/daily)
- Redis integration for real-time counters
- Prometheus metrics exporters

#### Frontend
- React-based web dashboard
- Real-time traffic monitoring interface
- Alert management dashboard
- Firewall rule management UI
- ISP settings and configuration panel
- Report generation and download interface
- Responsive design with modern CSS
- JWT token-based authentication

#### Infrastructure
- Docker and Docker Compose configuration
- Multi-container architecture
- PostgreSQL database container
- Redis cache container
- Prometheus monitoring container
- Grafana visualization container
- Automated health checks

#### Documentation
- Comprehensive README with features and architecture
- Quick Start Guide for rapid deployment
- Deployment Guide for production setup
- Development Guide for contributors
- Router integration scripts for:
  - MikroTik routers (Python script)
  - Cisco routers (shell script)
  - Juniper routers (shell script)

#### Testing
- Backend API test suite
- Authentication and authorization tests
- Rule management tests
- Traffic monitoring tests

### Security
- TLS/SSL support configuration
- Password hashing with bcrypt
- JWT token authentication
- Input validation with Pydantic
- CORS configuration
- API rate limiting support
- Secure secrets management

### Features
- Real-time traffic statistics
- Protocol distribution analysis
- Active alert monitoring
- Automated mitigation actions
- Multi-ISP tenant support
- Custom rule creation and management
- Report generation and export
- API key management for routers
- Email and Telegram alert notifications
- Grafana dashboard integration
- Prometheus metrics collection

## [Unreleased]

### Planned Features
- Machine learning-based anomaly detection
- Advanced geo-blocking capabilities
- Elasticsearch integration for log indexing
- Payment gateway integration (Stripe/PayPal)
- Subscription management system
- Advanced attack visualization maps
- Mobile application
- Kubernetes deployment manifests
- Helm charts
- Advanced reporting with PDF generation
- Two-factor authentication (2FA)
- Webhook support for alerts
- API versioning
- GraphQL API
- Real-time WebSocket updates
- Advanced traffic analysis
- DDoS attack playbooks
- Automated response workflows
- Integration with external threat intelligence
- Custom dashboard widgets

### Known Issues
- Payment integration needs implementation
- PDF report generation needs enhancement
- Some router integrations require testing
- Machine learning features not yet implemented
- WebSocket real-time updates not implemented

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Support

For questions and support:
- GitHub Issues: https://github.com/i4edubd/ddos-potection/issues
- Documentation: See docs/ folder
- Email: support@ispbills.com
