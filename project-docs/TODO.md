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

- [x] **[Bug] `campaign_router.py` / `campaign_tracker.py` prevents server startup**
  - File: `backend/services/campaign_tracker.py`
  - Fixed: `_infer_campaign_type` function body was stranded as bare module-level code (missing `def` statement); caused `NameError` on import → server crashed on startup.

- [x] **[Deps] pytest / pytest-asyncio version conflict**
  - File: `backend/requirements.txt`
  - Fixed: upgraded `pytest==7.4.3` → `pytest==8.3.5`; `pytest-asyncio==0.24.0` requires pytest ≥8.0.

- [x] **[Deps] bcrypt >=4.1 incompatibility with passlib 1.7.4 ("72 character limit" error)**
  - File: `backend/requirements.txt`
  - Fixed: added explicit `bcrypt==4.0.1` pin; without it, `pip` installs bcrypt ≥4.1 on fresh setups, which breaks passlib's version detection and 72-char pre-check, causing a spurious error even for short passwords.


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

- [x] **[Docs] Add 25 UI screenshots to `docs/screenshots/`**
  - Captured all 17 pages + 8 extra states (error, modals, mobile, full-page, 404)
  - Files: `docs/screenshots/01-login.png` through `docs/screenshots/25-404-not-found.png`

---

## 🟡 Medium Priority

- [x] **[Frontend] TypeScript migration for API service layer**
  - File: `frontend/src/services/api.ts` + `frontend/src/types/api.d.ts`
  - Full typed API service with `AxiosInstance` and typed generics for all endpoints

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

- [x] **[Frontend] Customer self-service portal — frontend pages**
  - Files: `frontend/src/pages/customer/MyProtection.js`, `MyAlerts.js`, `MyReports.js`, `MySettings.js`
  - Routes: `/my-protection`, `/my-alerts`, `/my-reports`, `/my-settings` added to `App.js`
  - MyProtection: protected prefixes + active mitigations (read-only)
  - MyAlerts: filterable alert feed with severity badges
  - MyReports: PDF/CSV download + SLA performance table with TTD/TTM averages
  - MySettings: notification channel toggles, alert threshold, IP whitelist

- [x] **[NMS] Zabbix auto-discovery XML template**
  - File: `scripts/zabbix_template.xml`
  - Zabbix 6.0 LTS compatible; health probe items; Prometheus metrics items; SNMP trap items;
    ISP auto-discovery rule with per-ISP alert-count items; triggers; graphs

- [x] **[Infra] PostgreSQL read-replica docker-compose override**
  - File: `docker/docker-compose.read-replica.yml`
  - Bitnami PostgreSQL 15 streaming standby; injects `DATABASE_REPLICA_URL` into backend

- [x] **[Infra] HAProxy UDP load balancer config**
  - File: `docker/haproxy/haproxy.cfg`
  - NetFlow/sFlow/IPFIX UDP distribution; `balance source` + consistent hashing;
    stats UI on TCP/8404; HTTP API pass-through with health check

- [x] **[Analytics] Cross-ISP botnet correlation**
  - File: `backend/services/campaign_tracker.py` — `CampaignTracker.cross_isp_correlate()`
  - Router: `GET /api/v1/campaigns/correlations/cross-isp` (admin only)

- [x] **[Mitigation] Pre-emptive mitigation trigger**
  - File: `backend/services/mitigation_selector.py` — `MitigationSelector.trigger_preemptive()`
  - Applies lightest action when prefix risk score ≥ `PREEMPTIVE_RISK_THRESHOLD` (default 70)



- [x] **[Frontend] Dark mode / theming**
  - `frontend/src/styles/theme.css` — CSS custom properties; `prefers-color-scheme` + `.dark-mode` class
  - `frontend/src/hooks/useDarkMode.js` — `[isDarkMode, toggleDarkMode]` hook with localStorage
- [x] **[API] GraphQL endpoint** alongside REST
  - `backend/routers/graphql_router.py` — Strawberry schema with `alerts` + `traffic_logs` queries; stub if not installed; mounted at `/api/v1/graphql`
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
- [x] **[DevOps] HashiCorp Vault** integration for secrets management
  - `backend/services/vault_client.py` — `VaultClient` with aiohttp/urllib fallback; `VAULT_ADDR/TOKEN/ROLE` config
  - `kubernetes/vault-secret-store.yaml` — Kubernetes SecretStore CRD pointing to Vault
  - `kubernetes/external-secrets.yaml` — ExternalSecret manifests for DB, Redis, app secrets
- [x] **[Integration] ServiceNow / JIRA / Zendesk ticketing**
  - `backend/services/ticketing_service.py`; `backend/routers/ticketing_router.py`
  - Config: `SERVICENOW_*`, `JIRA_*`, `ZENDESK_*` settings.
- [x] **[Branding] CSS variable injection (per-ISP)**
  - `backend/routers/branding_router.py` — public CSS endpoint + CRUD + custom domain.
  - `backend/services/custom_domain.py` — `CustomDomainManager`.
- [x] **[Branding] Branded email templates**
  - `backend/services/email_templates.py` — `BrandedEmailRenderer` (alert, report, welcome).
- [x] **[Security] Botnet C2 fingerprinting**
  - `backend/services/botnet_c2.py` — Mirai, Emotet, IRC, HTTP beacon indicators.
- [x] **[Signatures] BPF / FlowSpec signature library**
  - `backend/services/signature_library.py`; `backend/routers/signature_router.py`.
  - `Signature` model added to `backend/models/models.py`.
- [x] **[Risk] Daily attack-probability scoring per prefix**
  - `backend/services/risk_scorer.py`; `backend/routers/risk_router.py`.
- [x] **[BI] Business intelligence service (MRR, ROI, attack cost, KPIs)**
  - `backend/services/business_intelligence.py`; partial of `backend/routers/bi_router.py`.
- [x] **[Capacity] Monthly capacity projections**
  - `backend/services/capacity_planner.py`; `GET /api/v1/bi/capacity-forecast`.

- [x] **[Frontend] Enterprise UI overhaul — styles, colours, widgets, all pages**
  - `frontend/src/styles/App.css` — complete design-system rewrite (40+ CSS tokens, dark navy palette, enterprise cards, buttons, badges, forms, tables, login, stats, empty states)
  - `frontend/src/styles/theme.css` — full token palette with dark-mode support
  - `frontend/src/components/Navbar.js` — dark sticky navbar, emoji icons, active-link highlight, accessible dropdown, polished logout
  - `frontend/src/pages/Dashboard.js` — 5 KPI stat cards, colour-coded badges, quick-actions, 6-item system-status panel
  - `frontend/src/pages/Login.js` — glassmorphism dark login card, gradient branding, inline loading spinner
  - `frontend/src/App.js` — added `/bgp-blackholing` route; imported `theme.css`
  - `docs/screenshots/` — 4 UI screenshots (login, dashboard, alerts, traffic)
  - `README.md` — updated Screenshots section with new images; updated feature list



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
- [x] Shadow Mode for ML detectors (SHADOW_MODE config flag; create_ml_alert wrapper)
- [x] Threat Score service (ThreatScorer; get_threat_score with Redis bad-actor feed check)
- [x] LSTM Attack Predictor (GradientBoostingClassifier approximation; lstm_router)
- [x] GRE Decapsulation service (RFC 2784 + RFC 2890; GREDecapsulator)
- [x] AWS VPC Flow Log ingestion (AWSVPCFlowParser; cloud_flow_router)
- [x] GCP VPC Flow Log ingestion (GCPFlowParser; cloud_flow_router)
- [x] TLS-wrapped NetFlow receiver (TLSFlowReceiver; asyncio + ssl; config flags)
- [x] Phase 2 test suite (31 unit tests in test_phase2_detection.py)
- [x] Nokia SROS router driver (NokiaSROSDriver; netmiko nokia_sros; push_acl, withdraw_acl)
- [x] Router Inventory model + API (Router model; /api/v1/routers/ CRUD + test-connection)
- [x] Scrubbing Centre diversion (ScrubbingCentre + ScrubbingCentreManager; BGP /32 anycast)
- [x] Scrubbing Centre API (/api/v1/scrubbing/ divert + return + centres)
- [x] Third-party scrubbing providers (CloudflareProvider, LumenProvider, NSFOCUSProvider)
- [x] Cooldown de-mitigation (CooldownManager; Redis-backed with in-process fallback)
- [x] Intelligent mitigation selection (MitigationSelector; ATTACK_TYPE_MATRIX; AutoEscalationManager)
- [x] Tier-based SLA targets (SLA_TIERS; SLAComplianceChecker; monthly report + breach credits)
- [x] SLA Compliance API (/api/v1/sla/compliance/ tiers + monthly)
- [x] Phase 3 test suite (63 unit tests in test_phase3_mitigation.py)
- [x] ServiceNow / JIRA / Zendesk ticketing (services/ticketing_service.py + ticketing_router.py)
- [x] CSS variable injection (branding_router.py; public /css endpoint per-ISP)
- [x] Branded email templates (services/email_templates.py; alert, report, welcome)
- [x] Custom domain / CNAME support (services/custom_domain.py; /domain endpoints)
- [x] Botnet C2 fingerprinting (services/botnet_c2.py; Mirai/Emotet/IRC/HTTP indicators)
- [x] BPF / FlowSpec signature library (services/signature_library.py; signature_router.py)
- [x] Daily attack-probability risk scoring (services/risk_scorer.py; risk_router.py)
- [x] Business Intelligence dashboard (services/business_intelligence.py; bi_router.py)
- [x] Monthly capacity projections (services/capacity_planner.py; /bi/capacity-forecast)
- [x] Phase 4–6 test suite (47 unit tests in test_phase4_6_analytics.py)
- [x] TypeScript API service layer (frontend/src/services/api.ts + types/api.d.ts)
- [x] Dark mode theming (frontend/src/styles/theme.css + hooks/useDarkMode.js)
- [x] GraphQL endpoint (routers/graphql_router.py; strawberry schema with fallback stub)
- [x] Kubernetes Pod Disruption Budgets (kubernetes/pdb.yaml)
- [x] Kubernetes External Secrets (kubernetes/external-secrets.yaml + vault-secret-store.yaml)
- [x] HashiCorp Vault client (services/vault_client.py; VAULT_ADDR/TOKEN/ROLE config)
- [x] XDP/eBPF filter skeleton (backend/xdp/xdp_ddos_filter.c + xdp_loader.py)
- [x] TimescaleDB configuration helper (services/timescale_config.py + docker-compose.timescale.yml)
- [x] PostgreSQL PITR backup script (scripts/pg_backup.sh; base backup + WAL archive to S3)
- [x] Disaster recovery runbook (project-docs/DISASTER_RECOVERY.md; RTO 4h / RPO 15min)
- [x] HMAC-MD5 flow auth + DTLS config flags (FLOW_HMAC_ENABLED, DTLS_FLOW_ENABLED in config.py)

---

*Last updated: 2026-03-26*
