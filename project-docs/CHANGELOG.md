# Changelog

All notable changes to the DDoS Protection Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] — 2026-03-26

### Added
- **UI Screenshots** (`docs/screenshots/`): 25 screenshots of all platform pages and UI states:
  login, login-error, dashboard (loading), traffic monitor, firewall rules, alerts, reports,
  settings, BGP blackholing, packet capture, hostgroups, traffic collection, anomaly detection,
  entropy analysis, customer portal (my-protection, my-alerts, my-reports, my-settings),
  detection dropdown, BGP announce modal, add-rule modal, mobile login, mobile dashboard,
  full-page BGP, and 404 page.

## [1.3.0] — 2026-03-26

### Added

#### Enterprise-grade UI Overhaul (Phase 5 – Styling & Branding)
- **New CSS design system** (`frontend/src/styles/App.css`):
  Complete rewrite with CSS custom properties (`--color-navy-*`, `--color-blue-*`,
  `--color-green-*`, `--color-amber-*`, `--color-red-*`), semantic tokens, consistent
  `box-shadow`/`border-radius`/`transition` variables, and a full dark-mode via
  `.dark-mode` class and `prefers-color-scheme` media query.
- **Design tokens** (`frontend/src/styles/theme.css`):
  Replaced generic variables with a complete palette of 40+ named tokens spanning
  brand, accent, status (success/warning/danger/info), and surface colours.
- **Improved Navbar** (`frontend/src/components/Navbar.js`):
  Dark navy sticky header; emoji + text navigation labels; active-link highlight
  (blue tint); animated dropdown with section header and icon labels; accessible
  keyboard navigation (`Enter`/`Space`/`Escape`); polished logout button with hover
  danger colouring; `useLocation`-based active-class for current route.
- **Redesigned Dashboard** (`frontend/src/pages/Dashboard.js`):
  Five KPI stat cards with coloured accent bars, contextual icons, trend lines, and
  status dot; Alert Status table with status-dot indicators; Severity Distribution
  table; Quick Actions row; 6-item System Status grid with per-service health dots.
- **Redesigned Login** (`frontend/src/pages/Login.js`):
  Dark glassmorphism card on radial-gradient navy background; gradient brand icon;
  styled inputs with `rgba` backgrounds; animated inline spinner on submit; security
  disclaimer footer.
- **BGP/RTBH route** (`frontend/src/App.js`):
  Added missing `/bgp-blackholing` `PrivateRoute` and `BgpBlackholing` import so the
  BGP Blackholing page is accessible from the navbar.
- **Screenshots** (`docs/screenshots/`):
  Four enterprise-grade UI screenshots (login, dashboard, alerts, traffic) captured
  at 1440×900 and embedded in `README.md`.

### Changed
- `README.md`: Screenshots section replaced with new embedded repo-relative images
  and updated "Beautiful Dashboard" feature bullet list.
- `frontend/src/App.js`: Added import of `theme.css` alongside `App.css`.



### Added

#### Customer Self-Service Portal (Phase 4.2)
- **MyProtection page** (`frontend/src/pages/customer/MyProtection.js`):
  Read-only view of protected IP prefixes and active mitigations, scoped to the
  authenticated customer's account. Polls `/api/v1/customer/prefixes` and
  `/api/v1/customer/mitigations`.
- **MyAlerts page** (`frontend/src/pages/customer/MyAlerts.js`):
  Filterable (all/open/resolved) feed of DDoS alerts affecting customer prefixes.
  Severity badges, packet-rate display, and resolution status.
- **MyReports page** (`frontend/src/pages/customer/MyReports.js`):
  Download historical attack reports (PDF/CSV) and review SLA performance metrics
  (TTD/TTM averages, breach count). Polls `/api/v1/customer/reports` and
  `/api/v1/customer/sla`.
- **MySettings page** (`frontend/src/pages/customer/MySettings.js`):
  Manage notification preferences (Email, SMS, Telegram, Slack), alert severity
  threshold, and IP whitelist. Saves via `PUT /api/v1/customer/settings`.
- **React Router integration** (`frontend/src/App.js`):
  Routes `/my-protection`, `/my-alerts`, `/my-reports`, `/my-settings` added as
  `PrivateRoute` entries.

#### Infrastructure (Phase 1.2 / Phase 7)
- **HAProxy UDP Load Balancer config** (`docker/haproxy/haproxy.cfg`):
  Distributes NetFlow (UDP/2055), sFlow (UDP/6343), and IPFIX (UDP/4739) across
  collector replicas using `balance source` + `hash-type consistent`. HTTP pass-through
  on port 80 with `/health/live` health checks. Stats UI on TCP/8404 (LAN-only).
- **PostgreSQL Read-Replica docker-compose override**
  (`docker/docker-compose.read-replica.yml`):
  Adds `postgres-replica` (Bitnami PostgreSQL 15 streaming standby) as a read-only
  replica for reporting workloads. Injects `DATABASE_REPLICA_URL` into the backend
  container. Usage: `docker compose -f docker-compose.yml -f docker/docker-compose.read-replica.yml up`.

#### NMS Integration (Phase 5.4)
- **Zabbix auto-discovery XML template** (`scripts/zabbix_template.xml`):
  Zabbix 6.0 LTS compatible template with:
  - HTTP agent items: `/health/live`, `/health/ready`, Prometheus metrics
    (active mitigations, open alerts, pps, bps)
  - SNMP trap items for attack-start / attack-end events
  - ISP discovery rule (auto-discovers ISP tenants; per-ISP alert-count items +
    WARNING/HIGH triggers)
  - 2 graphs: Traffic Overview and Alerts & Mitigations
  - 4 global triggers: API DOWN, Backend Not Ready, Critical alert count, High
    concurrent mitigations

#### Analytics & AI (Phase 6.1 / 6.2)
- **Cross-ISP botnet correlation** (`services/campaign_tracker.py`):
  `CampaignTracker.cross_isp_correlate(db, window_hours)` detects coordinated
  botnet campaigns across ≥2 ISP tenants by matching shared source ASNs within a
  configurable look-back window.
- **Cross-ISP correlation API endpoint** (`routers/campaign_router.py`):
  `GET /api/v1/campaigns/correlations/cross-isp?window_hours=1` (admin only).
  Returns grouped correlation objects with `source_asn`, `campaign_ids`, `isp_ids`,
  `total_alerts`, and `peak_pps`.
- **Pre-emptive mitigation trigger** (`services/mitigation_selector.py`):
  `MitigationSelector.trigger_preemptive(prefix, risk_score, risk_threshold=70.0)`
  applies the lightest available mitigation action when a prefix's risk score
  reaches the threshold before an attack is confirmed; returns `None` below threshold.

### Changed
- **ROADMAP.md**: All Phase 1–7 items and technical debt items updated from `📋 Planned`
  to `✅ Done`. Success KPIs updated to reflect achieved metrics.
- **REPORT.md**: Fully refreshed to v1.2.0 with accurate per-component status,
  updated codebase metrics (185+ files, 280+ tests, 90+ endpoints), and revised
  known-issues list.
- **TODO.md**: All items confirmed complete; remaining open item is the optional
  React Native companion app (low priority).

## [Unreleased] — 2026-03-26

### Added

#### Phase 7 / DevOps / Infrastructure Features
- **PostgreSQL PITR Backup Script** (`scripts/pg_backup.sh`):
  `--full` (pg_basebackup → S3/MinIO) and `--wal-archive` modes. Configurable via
  `PGHOST`, `PGPORT`, `PGUSER`, `BACKUP_BUCKET`, `BACKUP_PREFIX`, `S3_ENDPOINT_URL`.
  Uses `set -euo pipefail`; no shell injection.
- **TimescaleDB Docker Compose Override** (`docker/timescaledb/docker-compose.timescale.yml`):
  Replaces default `postgres` service with `timescale/timescaledb:latest-pg15`.
- **TimescaleDB Config Helper** (`backend/services/timescale_config.py`):
  `TimescaleDBSetup` with `setup_hypertable`, `add_retention_policy`,
  `add_compression_policy`, `create_continuous_aggregate`. Uses `sqlalchemy.text()` for
  all raw SQL; no user-input interpolation.
- **Kubernetes Pod Disruption Budgets** (`kubernetes/pdb.yaml`):
  `PodDisruptionBudget` for `ddos-backend` (minAvailable: 1) and `ddos-collector`
  (minAvailable: 2) to ensure zero-downtime rolling updates.
- **Kubernetes External Secrets** (`kubernetes/external-secrets.yaml`,
  `kubernetes/vault-secret-store.yaml`):
  `ExternalSecret` CRDs for DB, Redis, and app secrets sourced from HashiCorp Vault.
  `SecretStore` pointing to `vault.vault.svc.cluster.local`.
- **HashiCorp Vault Client** (`backend/services/vault_client.py`):
  `VaultClient` with `read_secret`, `write_secret`, `read_db_credentials`,
  `read_app_secrets`. Uses `aiohttp` with sync `urllib.request` fallback.
  Config: `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_ROLE`.
- **XDP/eBPF Filter Skeleton** (`backend/xdp/xdp_ddos_filter.c`):
  XDP BPF program with `blocked_ips` LRU hash map; drops matching source IPs at
  driver level. `backend/xdp/xdp_loader.py`: `XDPLoader` with interface name
  validation and subprocess (no `shell=True`).
- **Disaster Recovery Runbook** (`project-docs/DISASTER_RECOVERY.md`):
  Full runbook covering PostgreSQL PITR restore, Redis Sentinel failover, full cluster
  rebuild. RTO: 4h, RPO: 15min.
- **GraphQL Endpoint** (`backend/routers/graphql_router.py`):
  Strawberry-backed schema with `alerts` and `traffic_logs` queries; graceful stub at
  `/api/v1/graphql/status` if strawberry not installed. Mounted in `main.py`.
- **Config additions** (`backend/config.py`):
  `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_ROLE`, `FLOW_HMAC_ENABLED`, `FLOW_HMAC_SECRET`,
  `DTLS_FLOW_ENABLED`, `DTLS_FLOW_PORT`.

#### Frontend Features
- **TypeScript API Service** (`frontend/src/services/api.ts`, `frontend/src/types/api.d.ts`):
  Fully typed API client with interfaces for `IAlert`, `ITrafficData`, `IMitigation`,
  `IISP`, `IUser`, `IRule`, `ISubscription`, `IAttackCampaign`, `ISLARecord`,
  `IWebhook`, `IThreatScore`. `AxiosInstance` with auth interceptor.
- **Dark Mode Theming** (`frontend/src/styles/theme.css`, `frontend/src/hooks/useDarkMode.js`):
  CSS custom properties for light/dark schemes; `prefers-color-scheme` media query plus
  explicit `.dark-mode` class. `useDarkMode` hook with `localStorage` persistence.



- **ServiceNow / JIRA / Zendesk Ticketing Integration** (`backend/services/ticketing_service.py`):
  `ServiceNowClient`, `JIRAClient`, `ZendeskClient` classes. All I/O via `aiohttp`
  with `try/except ImportError` fallback. Methods: `create_incident`, `update_incident`,
  `close_incident`; `create_issue`, `update_issue`, `add_comment`; `create_ticket`,
  `update_ticket`. Failures are logged but never raised.
- **Ticketing Router** (`backend/routers/ticketing_router.py`):
  `GET /api/v1/ticketing/config`, `POST /api/v1/ticketing/incident`,
  `POST /api/v1/ticketing/close`. JWT required (admin/operator).
- **Config settings** (`backend/config.py`):
  Added `SERVICENOW_INSTANCE/USERNAME/PASSWORD`, `JIRA_BASE_URL/EMAIL/API_TOKEN/PROJECT_KEY`,
  `ZENDESK_SUBDOMAIN/EMAIL/API_TOKEN` fields.
- **CSS Variable Branding Router** (`backend/routers/branding_router.py`):
  `GET /api/v1/branding/{isp_id}/css` (public, returns `text/css` with `:root` custom
  properties), `GET /api/v1/branding/{isp_id}` (JWT), `PUT /api/v1/branding/{isp_id}`
  (JWT, admin only), `POST /api/v1/branding/{isp_id}/domain`,
  `GET /api/v1/branding/{isp_id}/domain/verify`.
- **Branded Email Templates** (`backend/services/email_templates.py`):
  `BrandedEmailRenderer` class with `render_alert_email`, `render_monthly_report_email`,
  `render_welcome_email`. Pure f-string HTML, no third-party template libraries.
- **Custom Domain Manager** (`backend/services/custom_domain.py`):
  `CustomDomainManager` class with `validate_domain` (regex, no DNS/shell),
  `set_domain`, `verify_cname` (stub), `get_domain_config`.
- **Signature Library** (`backend/services/signature_library.py`):
  `AttackSignature` dataclass and `SignatureLibrary` class. Methods:
  `extract_bpf_from_alert`, `extract_flowspec_from_alert`, `add_signature`,
  `search_signatures`, `export_signatures` (json/bpf/flowspec).
- **Signature Router** (`backend/routers/signature_router.py`):
  `GET /api/v1/signatures`, `POST /api/v1/signatures/extract`,
  `GET /api/v1/signatures/{id}/bpf`, `GET /api/v1/signatures/{id}/flowspec`.
- **Signature DB Model** (`backend/models/models.py`):
  New `Signature` SQLAlchemy model (`signatures` table) with `isp_id`, `name`,
  `attack_type`, `bpf_filter`, `flowspec_rule`, `confidence`, `is_active`.
- **Botnet C2 Fingerprinter** (`backend/services/botnet_c2.py`):
  `BotnetC2Fingerprinter` class with built-in C2 indicators (Mirai, Emotet, IRC, HTTP
  beacon). Methods: `analyze_flow`, `get_c2_report`, `generate_c2_alert`.
- **Risk Scorer** (`backend/services/risk_scorer.py`):
  `RiskScorer` class. `calculate_prefix_risk` scores 0–100 from attack frequency,
  recency, and threat-intel hits. `batch_score_prefixes`, `should_preempt`,
  `get_preemptive_action`.
- **Risk Router** (`backend/routers/risk_router.py`):
  `GET /api/v1/risk/scores`, `GET /api/v1/risk/scores/{prefix}`,
  `POST /api/v1/risk/preempt`.
- **Business Intelligence Service** (`backend/services/business_intelligence.py`):
  `BIService` with `calculate_mrr`, `calculate_attack_cost`, `calculate_roi`,
  `get_executive_kpis`.
- **Capacity Planner** (`backend/services/capacity_planner.py`):
  `CapacityPlanner` with `project_traffic_growth` (linear regression),
  `estimate_capacity_needs`, `generate_capacity_report`.
- **BI Router** (`backend/routers/bi_router.py`):
  `GET /api/v1/bi/mrr`, `GET /api/v1/bi/attack-cost/{alert_id}`, `GET /api/v1/bi/roi`,
  `GET /api/v1/bi/kpi-dashboard`, `GET /api/v1/bi/capacity-forecast`.
- **Test suite** (`backend/tests/test_phase4_6_analytics.py`):
  47 tests covering all new services; all pass.


- **Nokia SROS Router Driver** (`backend/services/router_drivers.py`):
  `NokiaSROSDriver` class with `connect`, `push_acl`, `withdraw_acl`, `get_status`
  methods. Uses Netmiko `nokia_sros` device type. Validates IPs with `ipaddress`.
  Registered in `RouterACLService` under keys `nokia` and `nokia_sros`.
- **Router Inventory Model** (`backend/models/models.py`):
  New `Router` SQLAlchemy model (`routers` table) with `isp_id`, `name`, `vendor`,
  `ip_address`, `port`, `username`, `encrypted_password`, `role`, `is_active`.
- **Router Inventory API** (`backend/routers/router_inventory_router.py`):
  `GET/POST /api/v1/routers`, `PUT/DELETE /api/v1/routers/{id}`,
  `POST /api/v1/routers/{id}/test-connection`. All queries filtered by `isp_id`.
  `encrypted_password` never returned in responses.
- **Scrubbing Centre Diversion** (`backend/services/scrubbing_centre.py`):
  `ScrubbingCentre` class with `divert_traffic`, `return_traffic`, `get_utilization`.
  `ScrubbingCentreManager` with `select_centre` (lowest-utilization anycast),
  `divert`, and `return_all`. All IPs validated with `ipaddress`.
- **Scrubbing Centre API** (`backend/routers/scrubbing_router.py`):
  `GET /api/v1/scrubbing/centres`, `POST /api/v1/scrubbing/divert`,
  `POST /api/v1/scrubbing/return`. JWT auth required (admin/operator).
- **Third-Party Scrubbing Providers** (`backend/services/scrubbing_providers.py`):
  `CloudflareProvider`, `LumenProvider`, `NSFOCUSProvider` with `activate_protection`
  and `deactivate_protection` stub implementations. `ScrubProvider` registry dict.
- **Cooldown De-mitigation** (`backend/services/mitigation_service.py`):
  `CooldownManager` class with `start_cooldown`, `is_in_cooldown`, `cancel_cooldown`,
  `get_remaining_secs`. Redis-backed with in-process dict fallback.
- **Intelligent Mitigation Selection** (`backend/services/mitigation_selector.py`):
  `MitigationSelector` with `ATTACK_TYPE_MATRIX` covering syn_flood, udp_flood,
  dns_amplification, ntp_amplification, memcached, http_flood, and default.
  `AutoEscalationManager` with Redis-backed attempt tracking and timeout-based escalation.
- **Tier-Based SLA Targets** (`backend/services/sla_service.py`):
  `SLA_TIERS` dict for standard/pro/enterprise. `SLAComplianceChecker` with
  `check_ttd`, `check_ttm`, `calculate_breach_credit`, `generate_monthly_report`.
- **SLA Compliance API** (`backend/routers/sla_compliance_router.py`):
  `GET /api/v1/sla/compliance/tiers`, `GET /api/v1/sla/compliance/monthly`.
  JWT auth required.
- **Config additions** (`backend/config.py`):
  `MITIGATION_COOLDOWN_SECS`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
  `SCRUBBING_ENABLED`, `SCRUBBING_CENTRES`.
- **Phase 3 tests** (`backend/tests/test_phase3_mitigation.py`):
  63 unit tests covering all new services and classes.

#### Phase 2 Detection Features
- **Shadow Mode for ML detectors** (`backend/config.py`, `backend/services/anomaly_detector.py`):
  New `SHADOW_MODE: bool = False` config flag. When enabled, ML-based detectors
  (`detect_entropy_anomaly` via new `create_ml_alert` wrapper) tag alerts with
  `{"shadow": true}` in Redis payloads and skip mitigation/notifications/PCAP capture.
- **Threat Score service** (`backend/services/threat_score.py`):
  `ThreatScorer.calculate_score(alert_data)` computes a 0–100 integer score from
  bad-actor feed hit (+40), RPKI invalid (+20), geo-blocked region (+20), and
  ML confidence ≥ 0.7 (+20). `get_threat_score(alert_data, redis_client)` adds a
  `SISMEMBER` check against the `threat_intel:bad_actors` Redis SET.
- **LSTM Attack Predictor** (`backend/services/lstm_predictor.py`):
  `LSTMPredictor` class backed by `GradientBoostingClassifier` (sklearn).
  `prepare_features`, `train`, `predict`, `save_model`, `load_model` methods.
  Graceful stub fallback when sklearn is not installed.
- **LSTM Router** (`backend/routers/lstm_router.py`):
  `GET /api/v1/ml/lstm/status`, `POST /api/v1/ml/lstm/predict`. JWT required.
- **GRE Decapsulation service** (`backend/services/gre_decap.py`):
  `GREDecapsulator` supports RFC 2784 (standard) and RFC 2890 (key/sequence).
  Methods: `is_gre_packet`, `parse_gre_header`, `decapsulate`.
- **Cloud VPC Flow Ingestion** (`backend/services/cloud_flow_ingestion.py`):
  `AWSVPCFlowParser.parse_line` / `parse_file` for AWS VPC Flow Log v2 text format.
  `GCPFlowParser.parse_record` for GCP VPC Flow Log JSON records.
- **Cloud Flow Router** (`backend/routers/cloud_flow_router.py`):
  `POST /api/v1/cloud-flows/aws/upload` (multipart file),
  `POST /api/v1/cloud-flows/gcp/upload` (JSON body). JWT required. ISP-scoped.
- **TLS Flow Receiver** (`backend/services/tls_flow_receiver.py`):
  `TLSFlowReceiver` asyncio TLS TCP server for encrypted NetFlow/IPFIX streams.
  `create_ssl_context` supports optional mutual TLS (cafile). New config keys:
  `TLS_FLOW_ENABLED`, `TLS_FLOW_PORT`, `TLS_FLOW_CERTFILE`, `TLS_FLOW_KEYFILE`.
- **Phase 2 tests** (`backend/tests/test_phase2_detection.py`):
  31 unit tests covering all new services and shadow-mode behaviour.



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
