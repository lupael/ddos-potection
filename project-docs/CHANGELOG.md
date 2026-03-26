# Changelog

All notable changes to the DDoS Protection Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 2026-03-26

### Added

#### Tasks 1–10: Foundation, Detection, ML Baselines
- **Task 1 — Alembic Migrations**: `backend/alembic.ini`, `backend/alembic/env.py`,
  `backend/alembic/script.py.mako`, `backend/alembic/versions/001_initial_schema.py`.
  Creates all 13 production tables with indexes; supports offline SQL generation.
- **Task 2 — Config Sub-models**: `backend/config.py` now exposes `DatabaseSettings`,
  `RedisSettings`, `DetectionSettings`, `NotificationSettings`, `BGPSettings`, `CaptureSettings`
  sub-model instances on `settings.*`. All flat fields preserved for backward compatibility.
- **Task 3 — Mitigation State Machine**: `MitigationStateMachine` class with `MITIGATION_STATES`,
  `VALID_TRANSITIONS` constants, `transition(alert_id, new_state, db)` with legality checks,
  and `verify_mitigation()` that resolves or escalates based on pps vs threshold.
- **Task 4 — Event-driven Anomaly Detector**: `run_detection_loop` now subscribes to
  `ddos:flow_events` Redis pub/sub channel; `publish_flow_event()` helper added.
  Falls back to polling every `DETECTOR_POLL_INTERVAL` (default 30s) seconds.
- **Task 5 — SO_REUSEPORT Collector**: `create_reuseport_socket(port, host)` and
  `MultiProcessCollector(num_workers, port)` added to `services/traffic_collector.py`.
- **Task 6 — HTTP Flood / Slowloris Detection**: `detect_http_flood()` and
  `detect_slowloris()` added to `AnomalyDetector`. Config: `HTTP_FLOOD_THRESHOLD`,
  `SLOWLORIS_THRESHOLD`.
- **Task 7 — DNS Water-Torture Detection**: `detect_dns_water_torture()` added to
  `AnomalyDetector`. Config: `DNS_NXDOMAIN_THRESHOLD`.
- **Task 8 — BGP Hijack Indicator**: `detect_bgp_hijack(prefix, expected_asn, observed_asn)`
  added to `AnomalyDetector`.
- **Task 9 — IP Spoofing Detection**: `detect_ip_spoofing(source_ip, ingress_prefix, registered)`
  added to `AnomalyDetector` using `ipaddress` module for uRPF-style check.
- **Task 10 — ML Adaptive Baselines**: `services/baseline_service.py` with `BaselineService`
  using `sklearn.ensemble.IsolationForest`; per-prefix rolling buffers in Redis;
  shadow-mode when < `BASELINE_MIN_SAMPLES` samples. Config: `BASELINE_WINDOW_SIZE`,
  `BASELINE_MIN_SAMPLES`.

#### Tasks 11–30: Customer Portal, GDPR, Audit Export, Branding, Campaigns, Redis HA, K8s HPA/Network-Policies, Helm, Forecasting, RPKI
- **Task 21 — Customer Self-Service Portal**: `routers/customer_router.py` with `/my-protection`,
  `/my-alerts`, `/my-reports`, `/my-settings` (GET/PUT). `CustomerSettings` model added.
  All endpoints scoped to `isp_id` from the authenticated user.
- **Task 22 — GDPR Data Governance**: `routers/gdpr_router.py` with retention policy CRUD,
  right-to-erasure purge, subject-access-request JSON export. `GDPRRetentionPolicy` model added.
  `services/retention_service.py` for background cleanup of expired data.
- **Task 23 — Audit Log Export**: `routers/audit_router.py` with paginated listing and CSV
  `StreamingResponse` export (admin only, filterable by user/path/method/date range).
- **Task 24 — Whitelabel Branding**: Five branding columns added to `ISP` model
  (`brand_logo_url`, `brand_primary_color`, `brand_company_name`, `brand_portal_domain`,
  `brand_support_email`). `GET/PUT /{isp_id}/branding` endpoints added to `isp_router.py`.
- **Task 25 — Attack Campaign Tracking**: `AttackCampaign` model; `services/campaign_tracker.py`
  groups related alerts by ASN within 4-hour windows; `routers/campaign_router.py` with
  list/get/update endpoints (isp_id scoped).
- **Task 26 — Redis Sentinel HA**: `docker-compose.yml` refactored to `redis-master`,
  `redis-replica`, `redis-sentinel` services; `docker/redis-sentinel.conf` created.
  Config: `REDIS_SENTINEL_ENABLED`, `REDIS_SENTINEL_HOSTS`.
- **Task 27 — Kubernetes HPA + NetworkPolicy**: `kubernetes/hpa.yaml` (backend 2-10 replicas,
  collector 2-20 replicas); `kubernetes/network-policies.yaml` with default-deny-all plus
  targeted allow policies for frontend→backend, backend→postgres/redis, collector UDP.
- **Task 28 — Helm Chart**: Full chart in `kubernetes/helm/ddos-platform/` including
  `Chart.yaml`, `values.yaml`, `_helpers.tpl`, configmap, secret, deployments (api+collector),
  service, ingress, and HPA templates.
- **Task 29 — Traffic Forecasting**: `services/forecasting_service.py` with per-prefix
  per-hour-of-week rolling statistics in Redis; mean/std predictions, anomaly detection.
  `routers/forecast_router.py` with `/capacity-risk` and `/{prefix:path}` endpoints.
  Config: `FORECAST_HISTORY_WEEKS`.
- **Task 30 — RPKI/ROA Validation**: `services/rpki_validator.py` validates BGP routes via
  Cloudflare RPKI API; Redis-cached (1h TTL); bulk concurrent validation.
  `routers/rpki_router.py` with `/validate/{asn}/{prefix:path}` and `/bulk-validate`.
  Config: `RPKI_VALIDATION_ENABLED`, `RPKI_API_URL`.

#### Tasks 11–20: Integration Services & Platform Features
- **Task 11 — GeoIP MaxMind GeoLite2 Integration**: `services/geoip_service.py` with `GeoIPService`
  class; falls back to deterministic hash-based stub coordinates when DB unavailable.
  `attack_map_router.py` updated to use `GeoIPService`. Added `GEOIP_CITY_DB_PATH` to config.
- **Task 12 — Threat Intelligence Feed Ingestion**: `services/threat_intel.py` with `ThreatIntelService`
  (Spamhaus DROP/EDROP, CINS Army, Feodo Tracker); Redis SET storage, O(1) lookup, feed stats.
  `routers/threat_intel_router.py` with GET stats, GET check/{ip}, POST refresh (admin).
  Config: `THREAT_INTEL_ENABLED`, `THREAT_INTEL_REFRESH_INTERVAL`.
- **Task 13 — PagerDuty Integration**: `send_pagerduty()` and `send_pagerduty_resolve()` added to
  `NotificationService`. Config: `PAGERDUTY_INTEGRATION_KEY`, `PAGERDUTY_ENABLED`.
- **Task 14 — SIEM Export (Syslog RFC-5424 + CEF)**: `services/siem_exporter.py` with `SIEMExporter`;
  UDP delivery, RFC 5424 and CEF formatting. Config: `SIEM_ENABLED`, `SIEM_HOST`, `SIEM_PORT`,
  `SIEM_FORMAT`, `SIEM_FACILITY`.
- **Task 15 — Cisco/Juniper/Arista Router ACL Push**: `services/router_drivers.py` with
  `CiscoIOSDriver` (Netmiko), `JuniperDriver` (NAPALM), `AristaEOSDriver` (Netmiko), and
  `RouterACLService` factory; graceful fallback when libraries are not installed.
- **Task 16 — NetBox IPAM Sync**: `services/netbox_sync.py` with `NetboxSyncService`; prefix fetch,
  DB upsert, journal entry push, IP info lookup. Config: `NETBOX_URL`, `NETBOX_TOKEN`, `NETBOX_ENABLED`.
- **Task 17 — SNMP Trap Sender**: `services/snmp_sender.py` with `SNMPTrapSender`; SNMPv2c traps via
  pysnmp (preferred) or minimal BER/UDP socket encoder. Config: `SNMP_ENABLED`, `SNMP_MANAGER_HOST`,
  `SNMP_MANAGER_PORT`, `SNMP_COMMUNITY`, `SNMP_ENTERPRISE_OID`.
- **Task 18 — Kafka Flow Pipeline**: `services/kafka_consumer.py` with `KafkaFlowProducer` and
  `KafkaFlowConsumer` (aiokafka). `TrafficCollector.publish_to_kafka()` added. Config: `KAFKA_ENABLED`,
  `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_FLOW_TOPIC`, `KAFKA_CONSUMER_GROUP`.
- **Task 19 — TOTP 2FA**: `totp_secret` and `totp_enabled` fields on `User` model.
  `routers/totp_router.py` with setup/verify/disable/validate endpoints (pyotp).
- **Task 20 — Flow Source Authentication**: `FlowSource` model in `models/models.py`.
  `services/flow_auth.py` with `FlowAuthenticator` (Redis-cached DB lookup). 
  `routers/flow_source_router.py` with CRUD endpoints.

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
