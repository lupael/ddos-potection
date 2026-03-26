# TODO — DDoS Protection Platform

> **AI agents:** Read [`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md) before making any changes to this repository.

This file tracks concrete, actionable work items. Each item references the relevant
source file(s) and the phase in [`ROADMAP.md`](ROADMAP.md) it belongs to.

Legend: `[ ]` open · `[x]` done · `[~]` in-progress · `[!]` blocked

---

## 🔴 Critical — Must fix before next production release

- [x] **[Security] Sanitise `subprocess` calls in `mitigation_service.py`**
  - File: `backend/services/mitigation_service.py`
  - Fixed: `apply_iptables_rule`, `apply_nftables_rule`, `apply_rate_limit` now validate IP/CIDR
    with the `ipaddress` module before passing to subprocess; protocol names are allow-listed.

- [x] **[Security] PCAP download path traversal**
  - File: `backend/routers/capture_router.py` — `GET /api/v1/capture/download/{file}`
  - Already fixed: path resolved and checked against capture directory.

- [ ] **[Infra] Add Alembic for database migrations**
  - Without migrations, schema changes require manual SQL or full DB recreation
  - Steps: `pip install alembic`, `alembic init`, create initial migration from current models, add to CI

- [x] **[Health] Add `/health/live` and `/health/ready` endpoints**
  - File: `backend/main.py`
  - Added: `live` → always 200; `ready` → checks DB + Redis, returns 503 if unhealthy.

---

## 🟠 High Priority

- [x] **[Detection] NTP amplification detection**
  - File: `backend/services/anomaly_detector.py`
  - Added: `detect_ntp_amplification` — high UDP response rate > `NTP_AMPLIFICATION_THRESHOLD` (468 B/pkt).

- [x] **[Detection] Memcached amplification detection**
  - File: `backend/services/anomaly_detector.py`
  - Added: `detect_memcached_amplification` — UDP responses > `MEMCACHED_AMPLIFICATION_THRESHOLD` (1400 B/pkt).

- [x] **[Detection] SSDP amplification detection**
  - File: `backend/services/anomaly_detector.py`
  - Added: `detect_ssdp_amplification` — UDP large responses > `SSDP_AMPLIFICATION_THRESHOLD` (400 B/pkt).

- [x] **[Detection] TCP RST flood and TCP ACK flood**
  - File: `backend/services/anomaly_detector.py`
  - Added: `detect_tcp_rst_flood` and `detect_tcp_ack_flood` using Redis counters.

- [ ] **[GeoIP] Replace placeholder coordinates in attack map**
  - File: `backend/routers/attack_map_router.py`
  - Current implementation returns hardcoded/random coordinates
  - Fix: integrate MaxMind GeoLite2 (`geoip2` Python library, free DB download on startup)

- [ ] **[Scale] Wire Kafka for flow pipeline**
  - `aiokafka` is already in `requirements.txt` but not used
  - Files: `backend/services/traffic_collector.py`, new `backend/services/kafka_consumer.py`
  - Provide `KAFKA_ENABLED=false` env flag to keep Redis Streams fallback

- [ ] **[Config] Refactor `config.py` into sub-models**
  - File: `backend/config.py`
  - 111 flat env variables; group into: `DatabaseSettings`, `RedisSettings`, `DetectionSettings`, `NotificationSettings`, `BGPSettings`, `CaptureSettings`

- [ ] **[Mitigation] Implement mitigation lifecycle state machine**
  - Files: `backend/services/mitigation_service.py`, `backend/routers/mitigation_router.py`
  - States: `Detected → Mitigating → Verifying → Resolved` (+ `Escalating`)
  - Add post-mitigation traffic verification and cooldown-based de-mitigation

- [ ] **[Detector] Make anomaly detector event-driven**
  - File: `backend/services/anomaly_detector.py`
  - Currently polls Redis with `asyncio.sleep(10)` — replace with event-driven consumer

- [x] **[Alerts] Add Slack and Microsoft Teams notification channels**
  - File: `backend/services/notification_service.py`
  - Added `send_slack`, `send_teams`, `format_alert_slack`, `format_alert_teams`.
  - Config: `SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`.

- [x] **[Observability] Add SLA tracking**
  - Record TTD (time-to-detect) and TTM (time-to-mitigate) for every incident
  - New model: `SLARecord`; new router: `backend/routers/sla_router.py`

---

## 🟡 Medium Priority

- [ ] **[Frontend] TypeScript migration for API service layer**
  - File: `frontend/src/services/api.js` → `api.ts`
  - Start with service layer to catch API contract mismatches at build time

- [ ] **[Infra] Redis Sentinel in docker-compose.yml**
  - Replace single Redis container with Sentinel configuration for HA

- [ ] **[Scale] SO_REUSEPORT for collector workers**
  - File: `backend/services/traffic_collector.py`
  - Spread UDP receive across N CPU cores using `SO_REUSEPORT`

- [ ] **[Threat intel] Threat intelligence feed ingestion**
  - New file: `backend/services/threat_intel.py`
  - Sources: Spamhaus DROP/EDROP, Emerging Threats, CINS Army, Feodo Tracker
  - Refresh hourly via Celery beat; store in Redis SET for O(1) lookup

- [x] **[Auth] Webhook system with HMAC-SHA256 signatures**
  - New files: `backend/services/webhook_service.py`, `backend/routers/webhook_router.py`
  - Register URLs for alert/mitigation events; exponential-backoff retry on failure.

- [ ] **[RBAC] Customer self-service portal**
  - Add `customer` role to RBAC (read-only, scoped to their IP prefixes)
  - New frontend pages: MyProtection, MyAlerts, MyReports, MySettings

- [x] **[Compliance] Audit logging middleware**
  - New files: `backend/models/models.py` (AuditLog model), `backend/middleware/audit_middleware.py`
  - Auto-logs all POST/PUT/PATCH/DELETE API calls: who, what, old value, new value, IP.

- [ ] **[HA] Horizontal Pod Autoscaler for Kubernetes**
  - File: `kubernetes/`
  - Add HPA for collector and API deployments based on CPU and custom flow-rate metric

---

## 🟢 Low Priority / Nice to Have

- [ ] **[Frontend] Dark mode / theming**
- [ ] **[API] GraphQL endpoint** alongside REST
- [ ] **[Reporting] Two-Factor Authentication (TOTP)**
- [ ] **[Mobile] React Native companion app**
- [ ] **[Integration] Netbox IPAM sync** (`backend/services/netbox_sync.py`)
- [ ] **[Integration] SNMP trap sender** for Zabbix/Nagios
- [ ] **[Analytics] Attack campaign tracking** across ISP tenants
- [ ] **[Analytics] Traffic forecasting** (ARIMA/Prophet) for capacity planning
- [ ] **[DevOps] Helm chart** for Kubernetes deployment
- [ ] **[DevOps] HashiCorp Vault** integration for secrets management

---

## ✅ Completed

- [x] FastAPI backend, PostgreSQL, Redis, JWT auth
- [x] React 18 dashboard with Chart.js
- [x] NetFlow v5/v9, sFlow v5, IPFIX collection
- [x] SYN / UDP / ICMP / DNS-amp / entropy detection
- [x] NTP / Memcached / SSDP amplification detection
- [x] TCP RST flood and TCP ACK flood detection
- [x] iptables, nftables, MikroTik API, BGP RTBH, FlowSpec mitigation
- [x] Subprocess input validation in mitigation_service.py (iptables, nftables, tc)
- [x] Multi-tenant ISP accounts with RBAC
- [x] Stripe, PayPal, bKash billing
- [x] 33 Prometheus metrics + 3 Grafana dashboards
- [x] Email, Twilio SMS, Telegram notifications
- [x] Slack and Microsoft Teams notifications
- [x] AF_PACKET packet capture; AF_XDP with fallback
- [x] VLAN untagging (802.1Q, 802.1ad, QinQ)
- [x] Per-subnet hostgroups with longest-prefix-match
- [x] WebSocket live attack map
- [x] PDF/CSV/TXT report generation
- [x] Docker Compose + Kubernetes YAML
- [x] 9+ pytest test modules (184+ tests)
- [x] Prometheus / Grafana monitoring stack
- [x] FastAPI security patch (CVE - python-multipart ≤0.0.6)
- [x] PCAP download path traversal fix
- [x] /health/live and /health/ready Kubernetes probe endpoints
- [x] SLA tracking (SLARecord model + /api/v1/sla/ router)
- [x] Audit logging middleware (AuditLog model + AuditMiddleware)
- [x] Webhook system with HMAC-SHA256 signatures (/api/v1/webhooks/ router)

---

*Last updated: 2026-03-25*
