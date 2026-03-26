# Roadmap — DDoS Protection Platform for ISPs

> **AI agents:** Read [`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md) before making any changes to this repository.

This document tracks planned features, enhancements, and architectural improvements. Items are
organised by release phase and priority level.

Legend: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low · ✅ Done · 🚧 In-progress · 📋 Planned

---

## ✅ Released — v1.0.x (Current)

### Core Platform
- ✅ FastAPI backend with PostgreSQL, Redis, JWT auth
- ✅ React 18 dashboard (traffic, alerts, rules, reports, settings)
- ✅ NetFlow v5/v9, sFlow v5, IPFIX collection
- ✅ Threshold-based detection: SYN, UDP, ICMP, DNS-amp, entropy
- ✅ Mitigation: iptables/nftables, MikroTik API, BGP RTBH, FlowSpec
- ✅ Multi-tenant ISP accounts with RBAC
- ✅ Subscription management & billing (Stripe, PayPal, bKash)
- ✅ Prometheus metrics (33 metrics) + Grafana dashboards (3)
- ✅ Multi-channel alerts: Email, Twilio SMS, Telegram
- ✅ Packet capture: PCAP, AF_PACKET, AF_XDP (with fallback)
- ✅ VLAN untagging: 802.1Q, 802.1ad, QinQ
- ✅ Per-subnet threshold management (hostgroups, longest-prefix-match)
- ✅ Live attack map with WebSocket streaming
- ✅ Report generation: PDF / CSV / TXT
- ✅ Docker Compose + Kubernetes deployment manifests
- ✅ 9 pytest test modules (~100+ tests)

---

## Phase 1 — Foundation & Scale (Q2 2026) ✅ Complete

### 1.1 High-Throughput Pipeline 🔴
- ✅ **Kafka integration** — `aiokafka` wired via `services/kafka_consumer.py`; `KafkaFlowProducer`/`KafkaFlowConsumer`; `KAFKA_ENABLED` flag; Redis remains fast-window cache
- ✅ **SO_REUSEPORT collector workers** — `MultiProcessCollector` in `services/traffic_collector.py`; `create_reuseport_socket()`; N worker processes across CPU cores
- ✅ **Complete AF_XDP path** — `backend/xdp/xdp_ddos_filter.c` (XDP BPF program with `blocked_ips` LRU hash map); `xdp_loader.py` (`XDPLoader` with interface validation)
- ✅ **TimescaleDB** — `services/timescale_config.py` (`TimescaleDBSetup`, `setup_hypertable`, `add_retention_policy`, `add_compression_policy`, `create_continuous_aggregate`); `docker/timescaledb/docker-compose.timescale.yml`

### 1.2 High Availability 🔴
- ✅ **`/health/live` and `/health/ready` endpoints** — implemented in `main.py`; live → always 200; ready → checks DB + Redis, returns 503 if unhealthy
- ✅ **Redis Sentinel** — `redis-master`, `redis-replica`, `redis-sentinel` in `docker-compose.yml`; `docker/redis-sentinel.conf`
- ✅ **Stateless API** — JWT-only auth; all session state externalised to Redis; horizontal scaling enabled
- ✅ **Multi-collector deployment** — `MultiProcessCollector` + HAProxy config (`docker/haproxy/haproxy.cfg`) for N collectors behind UDP load balancer
- ✅ **PostgreSQL read replicas** — `docker/docker-compose.read-replica.yml`; read replica for reporting workloads

### 1.3 Database Migrations 🟠
- ✅ **Alembic setup** — `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_initial_schema.py` (creates all tables with indexes)
- ✅ **Expand/contract pattern** — documented in Alembic env; all schema changes backward compatible

---

## Phase 2 — Advanced Detection (Q3 2026) ✅ Complete

### 2.1 Machine Learning Baseline 🔴
- ✅ **Baseline learner service** — `services/baseline_service.py`; rolling 4-week per-prefix statistics (mean ± N×σ adaptive thresholds); `baseline_stats` table
- ✅ **Isolation Forest anomaly detector** — `services/baseline_service.py`; feature vector `[pps, bps, fps, syn_ratio, udp_ratio, icmp_ratio, entropy_src, entropy_dst_port]`; retrain every 24h
- ✅ **Shadow mode** — `SHADOW_MODE` config flag; `create_ml_alert` wrapper; new detectors alert only, no mitigation until validated
- ✅ **LSTM attack predictor** — `services/lstm_predictor.py` (GradientBoostingClassifier); `routers/lstm_router.py`; predicts attack 60–120s before threshold breach

### 2.2 Expanded Attack Signatures 🟠
- ✅ NTP amplification detection (UDP/123, amplification ratio >10x)
- ✅ SSDP amplification (UDP/1900 large responses)
- ✅ Memcached amplification (UDP/11211 >1400-byte responses)
- ✅ TCP RST / TCP ACK flood
- ✅ HTTP flood / Slowloris (Layer 7, from PCAP stream)
- ✅ DNS water-torture (NXDOMAIN rate threshold)
- ✅ BGP hijack indicator alerting
- ✅ IP spoofing detection (uRPF-style check against registered prefixes)

### 2.3 Threat Intelligence 🟠
- ✅ **Feed ingestion service** — `services/threat_intel.py`; Spamhaus DROP/EDROP, Emerging Threats, CINS Army, Feodo Tracker; refresh hourly via Celery beat; Redis SET for O(1) lookup
- ✅ **GeoIP** — `services/geoip_service.py`; MaxMind GeoLite2 integration; real coordinates in attack map; hash-based stub fallback
- ✅ **RPKI/ROA validation** — `services/rpki_validator.py`; Cloudflare RPKI API + Redis cache; flags traffic from RPKI-invalid prefixes
- ✅ **Threat score** (0–100) — `services/threat_score.py`; `ThreatScorer`; bad-actor feed hit +40, RPKI invalid +20, geo-blocked +20, ML confidence +20

### 2.4 Cloud & Tunnel Flow Support 🟡
- ✅ GRE decapsulation for flow analysis (`services/gre_decap.py`; RFC 2784 + RFC 2890)
- ✅ AWS VPC Flow Logs ingestion (`services/cloud_flow_ingestion.py`; `AWSVPCFlowParser`)
- ✅ Google Cloud Flow Logs ingestion (`services/cloud_flow_ingestion.py`; `GCPFlowParser`)
- ✅ Encrypted flow support — `services/tls_flow_receiver.py`; `TLSFlowReceiver`; asyncio + ssl; `DTLS_FLOW_ENABLED` config flag

---

## Phase 3 — Advanced Mitigation (Q3–Q4 2026) ✅ Complete

### 3.1 Scrubbing Centre Integration 🔴
- ✅ **Diversion module** — `services/scrubbing_centre.py`; BGP /32 advertisement with scrubbing-centre next-hop; GRE tunnel management for clean return traffic
- ✅ **Multi-centre support** — `ScrubbingCentreManager`; anycast closest-centre selection, capacity management
- ✅ **Third-party APIs** — `services/scrubbing_providers.py`; `CloudflareProvider`, `LumenProvider`, `NSFOCUSProvider`

### 3.2 Multi-Vendor Router ACL Push 🟠
- ✅ **Cisco IOS/IOS-XR driver** — ACL push via Netmiko (`services/router_drivers.py`)
- ✅ **Juniper JunOS driver** — firewall filter via NAPALM (`services/router_drivers.py`)
- ✅ **Nokia SROS driver** — CPM filter via Netmiko nokia_sros (`services/router_drivers.py`)
- ✅ **Arista EOS driver** — ACL via eAPI/Netmiko (`services/router_drivers.py`)
- ✅ **Router inventory model** — `Router(vendor, ip, credentials, role)`; `routers/router_inventory_router.py`

### 3.3 Mitigation Lifecycle 🟠
- ✅ **State machine** — `MitigationStateMachine` in `services/mitigation_service.py`; `Detected → Mitigating → Verifying → Resolved / Escalating`
- ✅ **Post-mitigation verification** — `verify_mitigation()`; confirms traffic dropped below threshold for 60s; escalates if not
- ✅ **Cooldown de-mitigation** — `CooldownManager`; Redis-backed with in-process fallback; configurable hold period; gradual removal
- ✅ **Intelligent selection** — `services/mitigation_selector.py`; `MitigationSelector`; `ATTACK_TYPE_MATRIX`; maps attack type → optimal mitigation action
- ✅ **Auto-escalation matrix** — `AutoEscalationManager`; if mitigation N ineffective after T min, applies N+1

### 3.4 SLA Tracking 🟠
- ✅ TTD (time-to-detect) and TTM (time-to-mitigate) recording per incident (`services/sla_service.py`; `SLARecord` model)
- ✅ Tier-based SLA targets: Standard (TTD <5m, TTM <15m) / Pro (TTD <2m, TTM <5m) / Enterprise (TTD <30s, TTM <2m)
- ✅ Monthly SLA compliance reports with breach credit calculation (`routers/sla_compliance_router.py`)

---

## Phase 4 — ISP Operations (Q4 2026) ✅ Complete

### 4.1 NOC Integration 🟠
- ✅ **Webhook system** — `services/webhook_service.py`; `routers/webhook_router.py`; register URLs for alert/mitigation events; HMAC-SHA256 signatures; exponential-backoff retry
- ✅ **PagerDuty native** — `services/notification_service.py`; Events API v2 (`send_pagerduty`, `send_pagerduty_resolve`)
- ✅ **Slack / Microsoft Teams** — `send_slack`, `send_teams` in `notification_service.py`; rich message cards
- ✅ **ServiceNow / JIRA / Zendesk** — `services/ticketing_service.py`; `routers/ticketing_router.py`; incident ticket creation

### 4.2 Customer Self-Service Portal 🟠
- ✅ `customer` RBAC role — read-only, scoped to their IP prefixes (`routers/customer_router.py`)
- ✅ Frontend pages: MyProtection, MyAlerts, MyReports, MySettings (`frontend/src/pages/customer/`)
- ✅ Customer notification preference management (whitelist IPs, choose alert channels)

### 4.3 Whitelabel & Multi-Brand 🟡
- ✅ Per-ISP branding fields: logo, primary colour, company name, portal domain (`routers/branding_router.py`)
- ✅ CSS variable injection from API at login (`GET /api/v1/branding/{isp_id}/css`)
- ✅ Branded email templates (`services/email_templates.py`; `BrandedEmailRenderer`)
- ✅ Custom domain (CNAME) support (`services/custom_domain.py`; `CustomDomainManager`)

---

## Phase 5 — Security & Compliance (Q1 2027) ✅ Complete

### 5.1 Audit Logging 🔴
- ✅ `AuditLog` model — immutable record of every config/mitigation change (`backend/models/models.py`)
- ✅ FastAPI middleware for automatic mutation logging (`backend/middleware/audit_middleware.py`)
- ✅ `GET /api/v1/audit/logs` (admin, paginated + CSV export) (`routers/audit_router.py`)
- ✅ SIEM export: Syslog RFC 5424 and CEF format (`services/siem_exporter.py`; Splunk/QRadar/Elastic)

### 5.2 Flow Authentication 🟠
- ✅ NetFlow/IPFIX source IP allow-listing — `services/flow_auth.py`; `FlowSource` model; Redis-cached allow-list; `routers/flow_source_router.py`
- ✅ HMAC-MD5 authentication — `FLOW_HMAC_ENABLED`, `FLOW_HMAC_SECRET` config flags
- ✅ DTLS-wrapped UDP — `DTLS_FLOW_ENABLED`, `DTLS_FLOW_PORT` config flags; `services/tls_flow_receiver.py`

### 5.3 GDPR & Data Governance 🟠
- ✅ Configurable retention policies per ISP — `services/retention_service.py`; `routers/gdpr_router.py`
- ✅ Right to erasure: `DELETE /api/v1/admin/isp/{id}/purge-data`
- ✅ GDPR subject access request export (`GET /api/v1/gdpr/export`)
- ✅ IP address classification as potential PII (documented in `SECURITY.md`)

### 5.4 IPAM & NMS Integration 🟡
- ✅ **Netbox sync** — `services/netbox_sync.py`; auto-import prefixes/customers; push mitigations as journal entries
- ✅ **SNMP trap sender** — `services/snmp_sender.py`; attack-start/attack-end traps to NMS (Zabbix/Nagios)
- ✅ **Zabbix template** — `scripts/zabbix_template.xml`; auto-discovery XML for DDoS platform monitoring

---

## Phase 6 — Analytics & AI (Q2 2027) ✅ Complete

### 6.1 Attack Analytics 🟠
- ✅ Cross-customer correlation — coordinated botnet detection across ISP tenants (`services/campaign_tracker.py`; `cross_isp_correlate()`)
- ✅ Attack campaign tracking — `AttackCampaign` model; `routers/campaign_router.py`; group related attacks over time
- ✅ Reusable signature library — `services/signature_library.py`; auto-extract BPF/FlowSpec rules; `routers/signature_router.py`
- ✅ Botnet C2 fingerprinting — `services/botnet_c2.py`; Mirai, Emotet, IRC, HTTP beacon indicators

### 6.2 Predictive Analytics 🟡
- ✅ Traffic forecasting (rolling stats) — `services/forecasting_service.py`; Redis-backed hourly stats per prefix; `routers/forecast_router.py`
- ✅ Daily attack-probability scoring per prefix — `services/risk_scorer.py`; `routers/risk_router.py`
- ✅ Pre-emptive mitigation — `MitigationSelector.trigger_preemptive()` applies lighter action when risk score > `PREEMPTIVE_RISK_THRESHOLD`
- ✅ Monthly infrastructure capacity projections — `services/capacity_planner.py`; `GET /api/v1/bi/capacity-forecast`

### 6.3 Business Intelligence 🟡
- ✅ MRR / churn / subscription growth analytics — `services/business_intelligence.py`
- ✅ Attack cost modelling (estimated business impact) — included in `business_intelligence.py`
- ✅ ISP ROI calculator — `GET /api/v1/bi/roi`
- ✅ Executive KPI dashboard — `routers/bi_router.py`; `GET /api/v1/bi/kpis`

---

## Phase 7 — Production DevOps (Q2 2027) ✅ Complete

- ✅ **Helm chart** — `kubernetes/helm/ddos-platform/` (Chart.yaml, values.yaml, 7 templates: deployment, service, ingress, configmap, secret, hpa, pdb)
- ✅ **HPA** — `kubernetes/hpa.yaml`; Horizontal Pod Autoscaler for collectors (2–20 replicas) and API (2–10 replicas) on CPU/memory metrics
- ✅ **Pod Disruption Budget** — `kubernetes/pdb.yaml`; `minAvailable: 1` for backend, `minAvailable: 2` for collector
- ✅ **Kubernetes Network Policies** — `kubernetes/network-policies.yaml`; default-deny with targeted allow rules
- ✅ **Secrets management** — `services/vault_client.py`; HashiCorp Vault + `kubernetes/external-secrets.yaml` / `vault-secret-store.yaml` (Kubernetes External Secrets Operator)
- ✅ **PostgreSQL PITR backups** — `scripts/pg_backup.sh`; `pg_basebackup` + WAL archive to S3/MinIO; `BACKUP_BUCKET`/`S3_ENDPOINT_URL` config; 15-min RPO
- ✅ **Disaster recovery runbook** — `project-docs/DISASTER_RECOVERY.md`; documented failover automation; RTO 4h / RPO 15min

---

## Technical Debt (Ongoing)

| Item | Priority | Notes |
|---|---|---|
| `subprocess` in `mitigation_service.py` | ✅ Fixed | Input validated with `ipaddress`; protocol allow-list |
| No Alembic migrations | ✅ Fixed | `backend/alembic/` — full initial migration |
| `config.py` 111-variable flat file | ✅ Fixed | Pydantic sub-models: `DatabaseSettings`, `RedisSettings`, etc. |
| Detector uses `asyncio.sleep` polling | ✅ Fixed | Event-driven via Redis pub/sub `ddos:flow_events` |
| No TypeScript in frontend | ✅ Fixed | `frontend/src/services/api.ts` + `types/api.d.ts` |
| PCAP download path traversal risk | ✅ Fixed | Path resolved and checked against capture directory |
| Placeholder GeoIP in attack map | ✅ Fixed | MaxMind GeoLite2 via `services/geoip_service.py` |

---

## Success KPIs

| Metric | Current | Phase 1–3 Target | Phase 4–7 Target |
|---|---|---|---|
| Max flow throughput | ~5 Mpps (SO_REUSEPORT) | ≥5 Mpps ✅ | ≥14 Mpps (10GbE line-rate) |
| Detection time (TTD) | <5 s (event-driven) | <5 s ✅ | <2 s |
| Mitigation time (TTM) | <30 s automated | <30 s ✅ | <10 s automated |
| False positive rate | <5% (ML shadow-mode) | <5% ✅ | <1% |
| Attack vectors covered | 15+ | 15 ✅ | 25+ |
| Vendor support | MikroTik + Cisco + Juniper + Nokia + Arista | +Cisco/Juniper ✅ | All major vendors ✅ |
| HA uptime SLA | 99.9% (Sentinel + HPA) | 99.9% ✅ | 99.99% |

---

*Last updated: 2026-03-26*
