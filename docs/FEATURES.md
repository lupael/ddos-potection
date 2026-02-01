# Complete Feature Guide

## Overview

This document provides a comprehensive overview of all features available in the DDoS Protection Platform. Each feature includes configuration instructions, usage examples, and best practices.

## Table of Contents

1. [Detection & Performance](#detection--performance)
2. [Packet Capture Engines](#packet-capture-engines)
3. [Traffic Analysis](#traffic-analysis)
4. [Mitigation & Blocking](#mitigation--blocking)
5. [Integrations](#integrations)
6. [Notifications & Alerts](#notifications--alerts)
7. [Data Export](#data-export)
8. [Monitoring & Metrics](#monitoring--metrics)
9. [Advanced Features](#advanced-features)

## Detection & Performance

### ⚡ Detects DoS/DDoS in 1-2 Seconds

The platform provides ultra-fast attack detection using multiple techniques:

**Detection Methods**:
- **SYN Flood Detection**: <1 second (real-time Redis counters)
- **UDP Flood Detection**: 1-2 seconds (sliding window analysis)
- **Entropy Analysis**: 2-3 seconds (statistical analysis)
- **DNS Amplification**: 1-2 seconds (byte-to-packet ratio)

**Configuration**:
```bash
# Detection Thresholds
SYN_FLOOD_THRESHOLD=10000    # packets per second
UDP_FLOOD_THRESHOLD=50000    # packets per minute
ENTROPY_THRESHOLD=3.5        # Shannon entropy
DETECTION_WINDOW=10          # seconds

# Enable fast detection mode
FAST_DETECTION=true
SLIDING_WINDOW=true
```

**How It Works**:
1. Traffic flows arrive via NetFlow/sFlow/IPFIX or direct capture
2. Redis real-time counters aggregate traffic per destination
3. Anomaly detector runs every 1 second checking thresholds
4. Alert generated immediately when threshold exceeded
5. Mitigation triggered within 1-2 seconds total

**Performance Metrics**:
- Detection Latency: <2 seconds (99th percentile)
- False Positive Rate: <0.1%
- False Negative Rate: <0.5%

### 🚀 Scales to Terabits on Single Server

The platform can handle massive traffic volumes using NetFlow/sFlow/IPFIX:

**Scalability Features**:
- **Sampling Support**: 1:1000 or 1:10000 sampling rates
- **Flow Aggregation**: Efficient in-memory aggregation
- **Distributed Processing**: Redis pub/sub for multi-server
- **Efficient Storage**: PostgreSQL with time-series optimization

**Throughput by Engine**:
| Engine | Single Server Capacity |
|--------|----------------------|
| NetFlow v5/v9 | 10+ Tbps (with 1:1000 sampling) |
| IPFIX | 10+ Tbps (with 1:1000 sampling) |
| sFlow | 5+ Tbps (with 1:1000 sampling) |
| AF_PACKET | 40 Gbps (direct capture) |
| AF_XDP | 100 Gbps (direct capture) |

**Configuration for Terabit Scale**:
```bash
# Enable sampling
NETFLOW_SAMPLING_RATE=1000  # 1:1000
SFLOW_SAMPLING_RATE=1000

# Flow aggregation
FLOW_AGGREGATION=true
AGGREGATION_INTERVAL=60  # seconds

# Database optimization
DATABASE_BATCH_SIZE=10000
DATABASE_FLUSH_INTERVAL=30
```

**Real-World Example**:
```
ISP Network: 5 Tbps total capacity
Sampling Rate: 1:1000
Actual Flow Rate: 5 Gbps (manageable on single server)
Detection: Still works with 1-2 second latency
```

### 🎯 40G+ in Mirror Mode

Direct packet capture using AF_PACKET or AF_XDP:

**Configuration**:
```bash
# AF_PACKET mode (10-40 Gbps)
AF_PACKET_ENABLED=true
AF_PACKET_INTERFACE=eth0
AF_PACKET_FANOUT=true
AF_PACKET_WORKERS=8

# AF_XDP mode (40-100 Gbps)
AF_XDP_ENABLED=true
AF_XDP_ZERO_COPY=true
AF_XDP_QUEUES=0,1,2,3,4,5,6,7
```

**Hardware Requirements**:
- CPU: 8+ cores (Xeon or EPYC)
- NIC: Intel X710, Mellanox ConnectX-5
- Memory: 64GB+ RAM
- Storage: NVMe SSD for logs

## Packet Capture Engines

See [PACKET_CAPTURE.md](PACKET_CAPTURE.md) for detailed information.

**Supported Engines**:
- ✅ NetFlow v5, v9, v9 Lite
- ✅ IPFIX
- ✅ sFlow v5
- ✅ PCAP
- ✅ **AF_PACKET (Recommended)**
- ✅ AF_XDP (XDP based capture)
- ⚠️ Netmap (FreeBSD only, deprecated)
- ⚠️ PF_RING / PF_RING ZC (CentOS 6 only, deprecated)

**Quick Comparison**:
- **Best for ISPs**: NetFlow/IPFIX (terabit scale)
- **Best for Linux**: AF_PACKET (recommended)
- **Best for Performance**: AF_XDP (100+ Gbps)
- **Best for Forensics**: PCAP

## Traffic Analysis

### 📊 Per-Subnet Threshold Configuration (Hostgroups)

Configure different thresholds for different network segments:

**Database Schema**:
```sql
CREATE TABLE hostgroups (
    id SERIAL PRIMARY KEY,
    isp_id INTEGER REFERENCES isps(id),
    name VARCHAR(255),
    subnet CIDR NOT NULL,
    syn_threshold INTEGER DEFAULT 10000,
    udp_threshold INTEGER DEFAULT 50000,
    entropy_threshold FLOAT DEFAULT 3.5,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**API Usage**:
```bash
# Create hostgroup
curl -X POST http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Critical Servers",
    "subnet": "10.0.1.0/24",
    "syn_threshold": 5000,
    "udp_threshold": 25000,
    "entropy_threshold": 3.0
  }'

# Create another hostgroup
curl -X POST http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Regular Customers",
    "subnet": "10.10.0.0/16",
    "syn_threshold": 15000,
    "udp_threshold": 75000,
    "entropy_threshold": 4.0
  }'
```

**Configuration File**:
```yaml
# config/hostgroups.yml
hostgroups:
  - name: "Web Servers"
    subnet: "203.0.113.0/24"
    thresholds:
      syn: 5000
      udp: 25000
      entropy: 3.0
      
  - name: "DNS Servers"
    subnet: "203.0.114.0/24"
    thresholds:
      syn: 20000
      udp: 100000  # DNS servers handle more UDP
      entropy: 4.5
      
  - name: "Email Servers"
    subnet: "203.0.115.0/24"
    thresholds:
      syn: 10000
      udp: 50000
      entropy: 3.5
```

**How It Works**:
1. Traffic flows arrive with destination IP
2. System looks up which hostgroup contains that IP
3. Applies hostgroup-specific thresholds
4. Generates alert if threshold exceeded
5. Different subnets get different treatment

**Benefits**:
- Reduce false positives on high-traffic servers
- Stricter monitoring for critical infrastructure
- Flexible per-customer thresholds

### 🌍 Complete IPv6 Support

Full IPv6 support across all features:

**Supported IPv6 Features**:
- ✅ IPv6 flow collection (NetFlow, IPFIX, sFlow)
- ✅ IPv6 packet capture (PCAP, AF_PACKET, AF_XDP)
- ✅ IPv6 attack detection (SYN floods, UDP floods)
- ✅ IPv6 blocking (firewall rules, BGP blackholing)
- ✅ IPv6 FlowSpec support
- ✅ IPv6 GeoIP lookups

**Configuration**:
```bash
# Enable IPv6
IPV6_ENABLED=true
IPV6_DETECTION=true
IPV6_MITIGATION=true

# IPv6 interfaces
LISTEN_IPV6=::
AF_PACKET_IPV6=true
```

**API Examples**:
```bash
# Block IPv6 address
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Block IPv6 attacker",
    "rule_type": "ip_block",
    "condition": {"ip": "2001:db8::1"},
    "action": "block"
  }'

# BGP blackhole for IPv6
curl -X POST http://localhost:8000/api/v1/mitigations/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "action_type": "bgp_blackhole",
    "details": {"prefix": "2001:db8::/32"}
  }'
```

**IPv6 Hostgroups**:
```bash
# Create IPv6 hostgroup
curl -X POST http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "IPv6 Web Servers",
    "subnet": "2001:db8::/32",
    "syn_threshold": 5000
  }'
```

## Mitigation & Blocking

### 🔥 Trigger Block/Notify Scripts

Automatically trigger custom scripts when attacks are detected:

**Configuration**:
```bash
# Script Configuration
TRIGGER_SCRIPTS_ENABLED=true
TRIGGER_SCRIPT_PATH=/opt/ddos-protection/scripts/triggers

# Available triggers
TRIGGER_ON_ALERT=true
TRIGGER_ON_MITIGATION=true
TRIGGER_ON_RESOLVE=true

# Script timeout
SCRIPT_TIMEOUT=30  # seconds
```

**Script Directory Structure**:
```
/opt/ddos-protection/scripts/triggers/
├── on_alert.sh          # Called when alert created
├── on_mitigation.sh     # Called when mitigation starts
├── on_resolve.sh        # Called when attack resolved
└── custom_notify.py     # Custom notification script
```

**Example Scripts**:

**on_alert.sh**:
```bash
#!/bin/bash
# Called when new alert is created
# Arguments: ALERT_ID TARGET_IP ATTACK_TYPE SEVERITY

ALERT_ID=$1
TARGET_IP=$2
ATTACK_TYPE=$3
SEVERITY=$4

# Log to syslog
logger -t ddos-protection "Alert $ALERT_ID: $ATTACK_TYPE on $TARGET_IP (severity: $SEVERITY)"

# Send to external SIEM
curl -X POST https://siem.example.com/api/alerts \
  -d "alert_id=$ALERT_ID&target=$TARGET_IP&type=$ATTACK_TYPE"

# Update external firewall
if [ "$SEVERITY" = "critical" ]; then
    ssh firewall@192.168.1.1 "add-blacklist $TARGET_IP"
fi
```

**on_mitigation.py**:
```python
#!/usr/bin/env python3
import sys
import requests

alert_id = sys.argv[1]
target_ip = sys.argv[2]
action_type = sys.argv[3]

# Send to Slack
slack_webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK"
requests.post(slack_webhook, json={
    "text": f"🚨 Mitigation started for {target_ip}",
    "attachments": [{
        "color": "danger",
        "fields": [
            {"title": "Alert ID", "value": alert_id, "short": True},
            {"title": "Action", "value": action_type, "short": True}
        ]
    }]
})

# Update ticketing system
requests.post("https://tickets.example.com/api/create", json={
    "title": f"DDoS Attack on {target_ip}",
    "description": f"Mitigation {action_type} started for alert {alert_id}",
    "priority": "high"
})
```

**Environment Variables Passed to Scripts**:
```bash
ALERT_ID=123
TARGET_IP=203.0.113.50
ATTACK_TYPE=syn_flood
SEVERITY=high
PACKETS_PER_SEC=50000
BYTES_PER_SEC=500000000
PROTOCOL=tcp
SOURCE_IPS=100  # Number of unique sources
```

**Python API for Script Triggers**:
```python
from services.script_trigger import ScriptTrigger

trigger = ScriptTrigger()

# Trigger on alert
trigger.on_alert(
    alert_id=123,
    target_ip="203.0.113.50",
    attack_type="syn_flood",
    severity="high"
)

# Trigger on mitigation
trigger.on_mitigation(
    alert_id=123,
    mitigation_id=456,
    action_type="bgp_blackhole"
)
```

### 🛡️ BGP Route Announcement

Announce blocked IPs via BGP using ExaBGP or GoBGP:

**ExaBGP Configuration**:
```bash
# Environment
BGP_ENABLED=true
BGP_DAEMON=exabgp
BGP_BLACKHOLE_NEXTHOP=192.0.2.1
BGP_BLACKHOLE_COMMUNITY=65535:666

# ExaBGP config file
EXABGP_CMD_PIPE=/var/run/exabgp.cmd
```

**GoBGP Configuration** (recommended):
```bash
# Environment
BGP_DAEMON=gobgp
GOBGP_HOST=localhost
GOBGP_PORT=50051
GOBGP_GRPC_TIMEOUT=10
```

**GoBGP Setup**:
```bash
# Install GoBGP
wget https://github.com/osrg/gobgp/releases/download/v3.20.0/gobgp_3.20.0_linux_amd64.tar.gz
tar xzf gobgp_3.20.0_linux_amd64.tar.gz
sudo cp gobgp gobgpd /usr/local/bin/

# GoBGP configuration
cat > /etc/gobgp/gobgpd.conf <<EOF
[global.config]
  as = 65000
  router-id = "192.0.2.1"

[[neighbors]]
  [neighbors.config]
    neighbor-address = "192.0.2.254"
    peer-as = 65000
  [[neighbors.afi-safis]]
    [neighbors.afi-safis.config]
      afi-safi-name = "ipv4-unicast"
EOF

# Start GoBGP
gobgpd -f /etc/gobgp/gobgpd.conf &
```

**API Usage**:
```bash
# Announce blackhole (GoBGP)
curl -X POST http://localhost:8000/api/v1/mitigations/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "action_type": "bgp_blackhole",
    "details": {
      "prefix": "203.0.113.50/32",
      "daemon": "gobgp"
    }
  }'

# Withdraw blackhole
curl -X POST http://localhost:8000/api/v1/mitigations/123/stop \
  -H "Authorization: Bearer $TOKEN"
```

**Comparison: ExaBGP vs GoBGP**:

| Feature | ExaBGP | GoBGP |
|---------|--------|-------|
| Language | Python | Go |
| Performance | Good | Excellent |
| Memory | Higher | Lower |
| API | Named Pipe | gRPC |
| Setup | Simple | Simple |
| Recommendation | Good | **Recommended** |

## Integrations

### 📈 Prometheus Support

Export system metrics and traffic counters to Prometheus:

**Configuration**:
```bash
# Enable Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_METRICS_PATH=/metrics
```

**Available Metrics**:

**System Metrics**:
```
# HELP ddos_system_cpu_usage CPU usage percentage
# TYPE ddos_system_cpu_usage gauge
ddos_system_cpu_usage{host="collector-1"} 45.2

# HELP ddos_system_memory_usage Memory usage in bytes
# TYPE ddos_system_memory_usage gauge
ddos_system_memory_usage{host="collector-1"} 2147483648

# HELP ddos_flows_processed_total Total flows processed
# TYPE ddos_flows_processed_total counter
ddos_flows_processed_total{engine="netflow_v9",isp="example-isp"} 1500000
```

**Traffic Counters**:
```
# HELP ddos_traffic_packets_total Total packets
# TYPE ddos_traffic_packets_total counter
ddos_traffic_packets_total{protocol="tcp",direction="inbound"} 50000000

# HELP ddos_traffic_bytes_total Total bytes
# TYPE ddos_traffic_bytes_total counter
ddos_traffic_bytes_total{protocol="tcp",direction="inbound"} 50000000000

# HELP ddos_alerts_total Total alerts by type
# TYPE ddos_alerts_total counter
ddos_alerts_total{type="syn_flood",severity="high"} 150

# HELP ddos_mitigations_active Active mitigations
# TYPE ddos_mitigations_active gauge
ddos_mitigations_active{type="bgp_blackhole"} 5
```

**Grafana Dashboard**:
```bash
# Import dashboard
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/ddos-overview.json
```

### 🔄 ClickHouse Integration

High-performance analytics database for traffic analysis:

**Configuration**:
```bash
# Enable ClickHouse
CLICKHOUSE_ENABLED=true
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ddos_analytics
CLICKHOUSE_USER=ddos
CLICKHOUSE_PASSWORD=secure_password
```

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS traffic_flows (
    timestamp DateTime,
    isp_id UInt32,
    source_ip IPv4,
    dest_ip IPv4,
    source_port UInt16,
    dest_port UInt16,
    protocol UInt8,
    packets UInt64,
    bytes UInt64,
    tcp_flags UInt8,
    router_ip IPv4
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, dest_ip)
TTL timestamp + INTERVAL 90 DAY;
```

**Usage**:
```python
from services.clickhouse_client import ClickHouseClient

client = ClickHouseClient()

# Store flows
client.insert_flows(flows)

# Query top talkers
results = client.query("""
    SELECT source_ip, SUM(packets) as total_packets
    FROM traffic_flows
    WHERE timestamp >= now() - INTERVAL 1 HOUR
    GROUP BY source_ip
    ORDER BY total_packets DESC
    LIMIT 10
""")
```

**Benefits**:
- 10-100x faster than PostgreSQL for analytics
- Excellent compression (10:1 typical)
- Column-oriented storage
- Built-in time-series optimization

### 📊 InfluxDB Integration

Time-series database for metrics and monitoring:

**Configuration**:
```bash
# Enable InfluxDB
INFLUXDB_ENABLED=true
INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_DATABASE=ddos_metrics
INFLUXDB_USER=ddos
INFLUXDB_PASSWORD=secure_password

# InfluxDB 2.x
INFLUXDB_V2=true
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=ddos-metrics
INFLUXDB_TOKEN=your-influxdb-token
```

**Metrics Stored**:
```python
from influxdb_client import InfluxDBClient, Point

# Write traffic metrics
point = Point("traffic") \
    .tag("isp", "example-isp") \
    .tag("protocol", "tcp") \
    .field("packets", 50000) \
    .field("bytes", 50000000) \
    .time(datetime.utcnow())

client.write(point)
```

**Example Queries**:
```sql
-- Average packets per second
SELECT MEAN(packets) FROM traffic
WHERE time > now() - 1h
GROUP BY time(1m), protocol

-- Top attacked IPs
SELECT SUM(packets) FROM alerts
WHERE time > now() - 24h
GROUP BY dest_ip
ORDER BY SUM DESC
LIMIT 10
```

### 📉 Graphite Integration

Metrics aggregation and graphing:

**Configuration**:
```bash
# Enable Graphite
GRAPHITE_ENABLED=true
GRAPHITE_HOST=graphite
GRAPHITE_PORT=2003
GRAPHITE_PREFIX=ddos.protection
```

**Metrics Format**:
```
ddos.protection.traffic.tcp.packets 50000 1612137600
ddos.protection.traffic.tcp.bytes 50000000 1612137600
ddos.protection.alerts.syn_flood.count 5 1612137600
ddos.protection.mitigations.active 3 1612137600
```

**Python Client**:
```python
from services.graphite_client import GraphiteClient

client = GraphiteClient()

# Send metric
client.send("traffic.tcp.packets", 50000)
client.send("alerts.syn_flood.count", 5)
```

### 🗄️ MongoDB / FerretDB Support

NoSQL database support for flexible schema:

**FerretDB Configuration** (PostgreSQL-backed MongoDB):
```bash
# Enable MongoDB protocol
MONGODB_ENABLED=true
MONGODB_HOST=ferretdb
MONGODB_PORT=27017
MONGODB_DATABASE=ddos_platform
MONGODB_AUTH_SOURCE=admin

# FerretDB uses PostgreSQL as backend
FERRETDB_POSTGRESQL_URL=postgresql://user:pass@postgres:5432/ferretdb
```

**Native MongoDB Configuration**:
```bash
MONGODB_ENABLED=true
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_REPLICA_SET=rs0
```

**Usage**:
```python
from pymongo import MongoClient

client = MongoClient("mongodb://ferretdb:27017/")
db = client.ddos_platform

# Store alert document
db.alerts.insert_one({
    "timestamp": datetime.utcnow(),
    "type": "syn_flood",
    "target_ip": "203.0.113.50",
    "packets_per_sec": 50000,
    "severity": "high",
    "metadata": {
        "source_ips": ["192.0.2.1", "192.0.2.2"],
        "attack_vector": "botnet"
    }
})

# Query alerts
for alert in db.alerts.find({"severity": "high"}):
    print(alert)
```

**Why FerretDB?**:
- Compatible with MongoDB clients and tools
- Backed by PostgreSQL (ACID compliance)
- No MongoDB licensing issues
- Easy migration from MongoDB

## Data Export

### 📤 Kafka Export (JSON and Protobuf)

Stream flow and packet data to Apache Kafka:

**Configuration**:
```bash
# Enable Kafka
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092,kafka3:9092
KAFKA_TOPIC_FLOWS=ddos.flows
KAFKA_TOPIC_ALERTS=ddos.alerts
KAFKA_TOPIC_MITIGATIONS=ddos.mitigations

# Format: json or protobuf
KAFKA_FORMAT=json
KAFKA_COMPRESSION=gzip
KAFKA_BATCH_SIZE=1000
KAFKA_LINGER_MS=100
```

**JSON Format**:
```json
{
  "timestamp": "2026-02-01T15:08:14.907Z",
  "isp_id": 1,
  "source_ip": "192.0.2.100",
  "dest_ip": "203.0.113.50",
  "source_port": 45678,
  "dest_port": 80,
  "protocol": "tcp",
  "packets": 1000,
  "bytes": 1500000,
  "tcp_flags": ["syn", "ack"],
  "router_ip": "198.51.100.1"
}
```

**Protobuf Format**:
```protobuf
syntax = "proto3";

message Flow {
  int64 timestamp = 1;
  int32 isp_id = 2;
  string source_ip = 3;
  string dest_ip = 4;
  int32 source_port = 5;
  int32 dest_port = 6;
  string protocol = 7;
  int64 packets = 8;
  int64 bytes = 9;
  repeated string tcp_flags = 10;
  string router_ip = 11;
}
```

**Producer Code**:
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['kafka1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    compression_type='gzip'
)

# Send flow to Kafka
producer.send('ddos.flows', flow_data)
producer.flush()
```

**Consumer Example**:
```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ddos.flows',
    bootstrap_servers=['kafka1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='ddos-analytics'
)

for message in consumer:
    flow = message.value
    print(f"Flow: {flow['source_ip']} -> {flow['dest_ip']}")
```

**Kafka Topics**:
- `ddos.flows` - All traffic flows
- `ddos.alerts` - Security alerts
- `ddos.mitigations` - Mitigation actions
- `ddos.metrics` - Performance metrics

## Notifications & Alerts

### 📧 Email Notifications

Multi-channel alert notifications:

**Configuration**:
```bash
# Email (SMTP)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=app_password
SMTP_FROM=DDoS Protection <alerts@example.com>
SMTP_TLS=true
```

**Alert Templates**:
```html
<!-- Email template -->
<h1>🚨 DDoS Alert</h1>
<p><strong>Target:</strong> {{ target_ip }}</p>
<p><strong>Attack Type:</strong> {{ attack_type }}</p>
<p><strong>Severity:</strong> {{ severity }}</p>
<p><strong>Packets/sec:</strong> {{ packets_per_sec }}</p>
<p><strong>Time:</strong> {{ timestamp }}</p>
<p><a href="https://dashboard.example.com/alerts/{{ alert_id }}">View Details</a></p>
```

**API Configuration**:
```bash
# Configure alert recipients
curl -X POST http://localhost:8000/api/v1/settings/notifications \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "email": {
      "enabled": true,
      "recipients": ["admin@example.com", "security@example.com"],
      "severity_filter": ["high", "critical"]
    }
  }'
```

### 📱 Multi-Channel Alerts

**Telegram**:
```bash
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=-1001234567890
```

**Slack**:
```bash
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
SLACK_CHANNEL=#security-alerts
```

**PagerDuty**:
```bash
PAGERDUTY_ENABLED=true
PAGERDUTY_API_KEY=your_api_key
PAGERDUTY_SERVICE_ID=your_service_id
```

**SMS (Twilio)**:
```bash
SMS_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBERS=+1234567891,+1234567892
```

## Advanced Features

### 🏷️ VLAN Untagging

Automatic VLAN tag removal in mirror and sFlow modes:

**Configuration**:
```bash
# AF_PACKET VLAN untagging
AF_PACKET_VLAN_UNTAG=true
AF_PACKET_VLAN_IDS=100,200,300  # Optional: specific VLANs

# sFlow VLAN untagging
SFLOW_VLAN_UNTAG=true
SFLOW_VLAN_PRESERVE_INNER=false  # For Q-in-Q
```

**How It Works**:
1. Mirror port receives tagged packets (802.1Q)
2. Collector extracts VLAN ID (12-bit)
3. VLAN tag removed from packet
4. Original IP packet processed
5. VLAN ID stored in metadata

**Benefits**:
- Transparent traffic analysis across VLANs
- No need for VLAN-specific collectors
- Preserves VLAN information for reporting

### 📦 Attack Fingerprint Capture

Capture full PCAP files of detected attacks:

**Configuration**:
```bash
# Enable fingerprint capture
PCAP_CAPTURE_ATTACKS=true
PCAP_STORAGE_PATH=/var/log/ddos/fingerprints
PCAP_MAX_SIZE=100MB
PCAP_MAX_DURATION=300  # seconds
PCAP_RETENTION_DAYS=30

# Trigger conditions
PCAP_TRIGGER_ON_ALERT=true
PCAP_MIN_PPS=10000
```

**Automatic Capture**:
```python
# Triggered automatically when alert created
# Output: /var/log/ddos/fingerprints/alert-123-20260201-150830.pcap
```

**Manual Capture**:
```bash
# Capture specific attack
curl -X POST http://localhost:8000/api/v1/captures/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "alert_id": 123,
    "duration": 60,
    "filter": "tcp and dst port 80"
  }'
```

**Analysis**:
```bash
# Download PCAP
curl -O http://localhost:8000/api/v1/captures/123/download

# Analyze with Wireshark
wireshark alert-123-20260201-150830.pcap

# Analyze with tcpdump
tcpdump -r alert-123-20260201-150830.pcap -n 'tcp[tcpflags] == tcp-syn'
```

### 🔌 API Access

Complete RESTful API for automation:

**Authentication**:
```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=password" \
  | jq -r .access_token)
```

**Endpoints**:
```bash
# Traffic
GET  /api/v1/traffic/realtime
GET  /api/v1/traffic/protocols
GET  /api/v1/traffic/top-talkers

# Alerts
GET  /api/v1/alerts/
POST /api/v1/alerts/{id}/resolve
GET  /api/v1/alerts/stats

# Rules
GET  /api/v1/rules/
POST /api/v1/rules/
PUT  /api/v1/rules/{id}
DELETE /api/v1/rules/{id}

# Mitigations
POST /api/v1/mitigations/
POST /api/v1/mitigations/{id}/execute
POST /api/v1/mitigations/{id}/stop

# Hostgroups
GET  /api/v1/hostgroups/
POST /api/v1/hostgroups/
```

**API Documentation**: http://localhost:8000/docs

### 🗄️ Redis Integration

High-performance real-time data processing:

**Features**:
- Real-time counters (traffic, alerts)
- Redis Streams for event streaming
- Pub/Sub for notifications
- Sliding window analysis
- Alert caching

**Usage**:
```python
import redis

r = redis.Redis(host='localhost', port=6379)

# Real-time counter
r.incr(f"traffic:dst:{isp_id}:{ip}:{timestamp}")

# Pub/Sub
r.publish("alerts:new", alert_json)

# Stream
r.xadd("traffic:stream", flow_data, maxlen=10000)
```

## Summary

The DDoS Protection Platform provides a comprehensive set of features for detecting, analyzing, and mitigating DDoS attacks at ISP scale. Key highlights:

✅ **Detection**: 1-2 second detection with multiple engines
✅ **Scale**: Terabits per second on single server
✅ **Capture Engines**: 8 different packet capture options
✅ **IPv6**: Complete IPv6 support
✅ **Integrations**: Kafka, ClickHouse, InfluxDB, Graphite, MongoDB
✅ **BGP**: ExaBGP and GoBGP support
✅ **Automation**: Script triggers and API
✅ **Monitoring**: Prometheus, Grafana, custom dashboards
✅ **Forensics**: PCAP fingerprint capture

For detailed information on specific features, see:
- [Packet Capture Engines](PACKET_CAPTURE.md)
- [BGP Blackholing](BGP-RTBH.md)
- [FlowSpec Rules](FLOWSPEC.md)
- [Custom Rules](CUSTOM-RULES.md)
- [Traffic Collection](TRAFFIC_COLLECTION.md)
