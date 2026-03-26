# Changelog

All notable changes to the DDoS Protection Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 2026-03-26

### Added

#### Security & Reliability
- **`/health/live`** and **`/health/ready`** Kubernetes probe endpoints in `main.py`.
  `live` always returns 200; `ready` checks PostgreSQL + Redis connectivity (returns 503 if either is down).
- **Audit logging middleware** (`backend/middleware/audit_middleware.py`): automatically records every
  `POST`, `PUT`, `PATCH`, `DELETE` request to the `audit_logs` table (user, path, IP, redacted body).
- **`AuditLog` model** added to `models/models.py`.

#### Attack Detection
- **NTP amplification detection** (`detect_ntp_amplification`): triggers when UDP per-packet byte size
  ≥ `NTP_AMPLIFICATION_THRESHOLD` (default 468 B) with > 1 000 packets/min.
- **Memcached amplification detection** (`detect_memcached_amplification`): triggers at ≥ 1 400 B/pkt.
- **SSDP amplification detection** (`detect_ssdp_amplification`): triggers at ≥ 400 B/pkt.
- **TCP RST flood detection** (`detect_tcp_rst_flood`): uses Redis `rst:{isp_id}:{dst_ip}:{ts}` counters.
- **TCP ACK flood detection** (`detect_tcp_ack_flood`): uses Redis `ack:{isp_id}:{dst_ip}:{ts}` counters.
- All five new detectors are wired into `run_detection_loop`.
- New config keys: `NTP_AMPLIFICATION_THRESHOLD`, `MEMCACHED_AMPLIFICATION_THRESHOLD`,
  `SSDP_AMPLIFICATION_THRESHOLD`, `TCP_RST_FLOOD_THRESHOLD`, `TCP_ACK_FLOOD_THRESHOLD`.

#### Notifications
- **Slack** incoming webhook support (`send_slack`, `format_alert_slack`) in `notification_service.py`.
- **Microsoft Teams** incoming webhook support (`send_teams`, `format_alert_teams`).
- New config keys: `SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`.
- `notify_alert` automatically reads Slack/Teams URLs from settings when not provided inline.

#### SLA Tracking
- **`SLARecord` model** in `models/models.py` — stores `attack_started_at`, `detected_at`,
  `mitigated_at`, `resolved_at`, computed `ttd_seconds`, `ttm_seconds`, and `sla_met` flag.
- **`/api/v1/sla/` router** (`backend/routers/sla_router.py`) with `POST`, `GET`, `PATCH` endpoints.
- Tier-based SLA targets: Basic (TTD ≤ 5 min, TTM ≤ 15 min) / Pro / Enterprise.

#### Webhook System
- **`Webhook` model** in `models/models.py` — stores URL, HMAC-SHA256 signing secret, event list.
- **`webhook_service.py`** — signed delivery with exponential back-off retry.
- **`/api/v1/webhooks/` router** (`backend/routers/webhook_router.py`) — CRUD for webhook endpoints.
- New config keys: `WEBHOOK_MAX_RETRIES`, `WEBHOOK_RETRY_BACKOFF`, `WEBHOOK_TIMEOUT`.
- Supported events: `alert.created`, `alert.resolved`, `mitigation.started`, `mitigation.stopped`, `mitigation.failed`.

### Fixed
- **`main.py` syntax error** — missing comma in router import list caused `SyntaxError`.
- **`Payment.metadata` reserved attribute** — renamed column to `payment_metadata` (SQLAlchemy 2.0
  reserves `metadata` as a class attribute). Updated `payment_router.py` accordingly.
- **`apply_iptables_rule`** — added `ipaddress` validation + protocol allow-list before building subprocess args.
- **`apply_nftables_rule`** — added `ipaddress` validation before building subprocess args.
- **`apply_rate_limit`** — added `ipaddress` validation + rate-format regex before building subprocess args.
- **NetFlow v5 parsing** (`traffic_collector.py`) — fixed struct format from 46-byte `IIIHHIIIIHHBBBBHHH`
  to RFC-3954-compliant 48-byte `IIIHHIIIIHHxBBBHHBBxx` and updated all field-index mappings.
- **`from fpdf2 import FPDF`** in `reports_router.py` — the `fpdf2` package installs as `fpdf`; fixed import.
- **Anomaly detector tests** — mock setup for `existing alert` check now sets
  `mock_db.query().filter().first.return_value = None` so alerts are correctly created.
- **Test keys with stale timestamps** — UDP/ICMP/RST/ACK test keys now use `int(time.time())` so
  the 60-second window check in the detector passes.

### Security
- `get_current_user_from_token(token)` helper added to `auth_router.py` — used by `AuditMiddleware`
  to resolve caller identity from Bearer token without a FastAPI `Depends` injection.

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
