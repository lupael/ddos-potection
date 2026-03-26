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

- [x] **[Infra] Add Alembic for database migrations**
  - `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
  - `backend/alembic/versions/001_initial_schema.py` creates all 13 tables with indexes

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

- [x] **[GeoIP] Replace placeholder coordinates in attack map**
  - File: `backend/routers/attack_map_router.py`
  - Fixed: `services/geoip_service.py` with MaxMind GeoLite2 integration and hash-based stub fallback.

- [x] **[Scale] Wire Kafka for flow pipeline**
  - `aiokafka` is already in `requirements.txt` but not used
  - Fixed: `services/kafka_consumer.py` with `KafkaFlowProducer`/`KafkaFlowConsumer`; `TrafficCollector.publish_to_kafka()` added; `KAFKA_ENABLED=false` fallback.

- [x] **[Config] Refactor `config.py` into sub-models**
  - File: `backend/config.py`
  - Added: `DatabaseSettings`, `RedisSettings`, `DetectionSettings`, `NotificationSettings`, `BGPSettings`, `CaptureSettings` sub-models; all flat fields preserved for backward compatibility.

- [x] **[Mitigation] Implement mitigation lifecycle state machine**
  - Files: `backend/services/mitigation_service.py`
  - Added: `MitigationStateMachine` with states `detected→mitigating→verifying→resolved/escalating`; `verify_mitigation()` function.

- [x] **[Detector] Make anomaly detector event-driven**
  - File: `backend/services/anomaly_detector.py`
  - Changed: `run_detection_loop` subscribes to `ddos:flow_events` Redis pub/sub channel; `DETECTOR_POLL_INTERVAL` fallback (default 30s).

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

- [x] **[Infra] Redis Sentinel in docker-compose.yml**
  - Updated `docker-compose.yml`: `redis-master`, `redis-replica`, `redis-sentinel` services; `docker/redis-sentinel.conf` added.

- [x] **[Scale] SO_REUSEPORT for collector workers**
  - File: `backend/services/traffic_collector.py`
  - Added: `create_reuseport_socket()` and `MultiProcessCollector` class (N worker processes with `SO_REUSEPORT`).

- [x] **[Threat intel] Threat intelligence feed ingestion**
  - New file: `backend/services/threat_intel.py`
  - Sources: Spamhaus DROP/EDROP, Emerging Threats, CINS Army, Feodo Tracker
  - Refresh hourly via Celery beat; store in Redis SET for O(1) lookup
  - Router: `backend/routers/threat_intel_router.py`

- [x] **[Auth] Webhook system with HMAC-SHA256 signatures**
  - New files: `backend/services/webhook_service.py`, `backend/routers/webhook_router.py`
  - Register URLs for alert/mitigation events; exponential-backoff retry on failure.

- [x] **[RBAC] Customer self-service portal**
  - Add `customer` role to RBAC (read-only, scoped to their IP prefixes)
  - New router: `backend/routers/customer_router.py`; `CustomerSettings` model added.

- [x] **[Compliance] Audit logging middleware**
  - New files: `backend/models/models.py` (AuditLog model), `backend/middleware/audit_middleware.py`
  - Auto-logs all POST/PUT/PATCH/DELETE API calls: who, what, old value, new value, IP.

- [x] **[HA] Horizontal Pod Autoscaler for Kubernetes**
  - File: `kubernetes/hpa.yaml`
  - HPA for backend (2-10 replicas) and collector (2-20 replicas) on CPU/memory metrics.

---

## 🟢 Low Priority / Nice to Have

- [ ] **[Frontend] Dark mode / theming**
- [ ] **[API] GraphQL endpoint** alongside REST
- [x] **[Reporting] Two-Factor Authentication (TOTP)**
  - `routers/totp_router.py`: setup/verify/disable/validate; `User.totp_secret` + `totp_enabled`
- [ ] **[Mobile] React Native companion app**
- [x] **[Integration] Netbox IPAM sync** (`backend/services/netbox_sync.py`)
- [x] **[Integration] SNMP trap sender** for Zabbix/Nagios (`backend/services/snmp_sender.py`)
- [x] **[Analytics] Attack campaign tracking** across ISP tenants
  - `AttackCampaign` model; `services/campaign_tracker.py`; `routers/campaign_router.py`
- [x] **[Analytics] Traffic forecasting** (rolling stats) for capacity planning
  - `services/forecasting_service.py` with Redis-backed hourly stats; `routers/forecast_router.py`
- [x] **[DevOps] Helm chart** for Kubernetes deployment
  - Full chart in `kubernetes/helm/ddos-platform/` with HPA, ingress, configmap, secret templates.
- [ ] **[DevOps] HashiCorp Vault** integration for secrets management

---

## ✅ Completed

- [x] FastAPI backend, PostgreSQL, Redis, JWT auth
- [x] React 18 dashboard with Chart.js
- [x] NetFlow v5/v9, sFlow v5, IPFIX collection
- [x] SYN / UDP / ICMP / DNS-amp / entropy detection
- [x] NTP / Memcached / SSDP amplification detection
- [x] TCP RST flood and TCP ACK flood detection
- [x] HTTP flood and Slowloris detection
- [x] DNS water-torture (NXDOMAIN rate) detection
- [x] BGP hijack indicator alerting
- [x] IP spoofing detection (uRPF-style)
- [x] ML adaptive baselines (Isolation Forest via `services/baseline_service.py`)
- [x] iptables, nftables, MikroTik API, BGP RTBH, FlowSpec mitigation
- [x] Mitigation lifecycle state machine (Detected→Mitigating→Verifying→Resolved/Escalating)
- [x] Cisco IOS/IOS-XR ACL push (Netmiko); Juniper JunOS filter (NAPALM); Arista EOS (Netmiko)
- [x] Subprocess input validation in mitigation_service.py (iptables, nftables, tc)
- [x] Multi-tenant ISP accounts with RBAC (admin / operator / viewer / customer)
- [x] Customer self-service portal (/api/v1/customer/ router; CustomerSettings model)
- [x] Stripe, PayPal, bKash billing
- [x] 33 Prometheus metrics + 3 Grafana dashboards
- [x] Email, Twilio SMS, Telegram notifications
- [x] Slack and Microsoft Teams notifications
- [x] PagerDuty Events API v2 integration
- [x] SIEM export: Syslog RFC-5424 + CEF (services/siem_exporter.py)
- [x] AF_PACKET packet capture; AF_XDP with fallback
- [x] VLAN untagging (802.1Q, 802.1ad, QinQ)
- [x] Per-subnet hostgroups with longest-prefix-match
- [x] WebSocket live attack map
- [x] GeoIP MaxMind GeoLite2 integration (with hash-based stub fallback)
- [x] PDF/CSV/TXT report generation
- [x] Audit log export endpoint (GET /api/v1/audit/logs — paginated + CSV export)
- [x] GDPR data governance (retention policies, right-to-erasure, SAR export)
- [x] Whitelabel/branding fields per ISP
- [x] Attack campaign tracking (AttackCampaign model + campaign_tracker.py)
- [x] Traffic forecasting (rolling stats per prefix/hour-of-week)
- [x] RPKI/ROA validation (Cloudflare RPKI API + Redis cache)
- [x] Threat intelligence feeds (Spamhaus DROP/EDROP, CINS Army, Feodo Tracker)
- [x] Two-Factor Authentication / TOTP (pyotp; /api/v1/auth/totp/ endpoints)
- [x] Flow source authentication (FlowSource model + Redis-cached allow-list)
- [x] Netbox IPAM sync (services/netbox_sync.py)
- [x] SNMP trap sender for Zabbix/Nagios (services/snmp_sender.py)
- [x] Kafka flow pipeline (services/kafka_consumer.py; KAFKA_ENABLED flag)
- [x] SO_REUSEPORT multi-process collector (MultiProcessCollector class)
- [x] Event-driven anomaly detector (Redis pub/sub; ddos:flow_events channel)
- [x] Config sub-models (DatabaseSettings, RedisSettings, DetectionSettings, etc.)
- [x] Alembic database migrations (alembic.ini + env.py + initial migration)
- [x] Docker Compose + Kubernetes YAML
- [x] Redis Sentinel HA (redis-master + redis-replica + redis-sentinel in docker-compose)
- [x] Kubernetes HPA (api: 2-10 replicas; collector: 2-20 replicas)
- [x] Kubernetes NetworkPolicies (default-deny; targeted allow rules)
- [x] Helm chart (kubernetes/helm/ddos-platform/ — Chart.yaml, values.yaml, 7 templates)
- [x] 9+ pytest test modules (184+ tests)
- [x] Prometheus / Grafana monitoring stack
- [x] FastAPI security patch (CVE - python-multipart ≤0.0.6)
- [x] PCAP download path traversal fix
- [x] /health/live and /health/ready Kubernetes probe endpoints
- [x] SLA tracking (SLARecord model + /api/v1/sla/ router)
- [x] Audit logging middleware (AuditLog model + AuditMiddleware)
- [x] Webhook system with HMAC-SHA256 signatures (/api/v1/webhooks/ router)

---

*Last updated: 2026-03-26*
