# Integration Setup Guide

This guide provides step-by-step instructions for setting up all external integrations supported by the DDoS Protection Platform.

## Table of Contents

1. [Kafka](#kafka-integration)
2. [ClickHouse](#clickhouse-integration)
3. [InfluxDB](#influxdb-integration)
4. [Graphite](#graphite-integration)
5. [MongoDB/FerretDB](#mongodbferretdb-integration)
6. [Testing Integrations](#testing-integrations)

## Kafka Integration

Apache Kafka provides real-time data streaming for flows and alerts.

### Installation (Docker)

```yaml
# Add to docker-compose.yml
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

### Configuration

```bash
# Enable Kafka in .env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_FLOWS=ddos.flows
KAFKA_TOPIC_ALERTS=ddos.alerts
KAFKA_FORMAT=json
KAFKA_COMPRESSION=gzip
```

### Create Topics

```bash
# Create topics
docker exec kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic ddos.flows \
  --partitions 3 \
  --replication-factor 1

docker exec kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic ddos.alerts \
  --partitions 1 \
  --replication-factor 1
```

### Test Consumer

```bash
# Consume messages from flows topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ddos.flows \
  --from-beginning
```

### Python Consumer Example

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'ddos.flows',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='ddos-analytics'
)

for message in consumer:
    flow = message.value
    print(f"Flow: {flow['source_ip']} -> {flow['dest_ip']}")
```

## ClickHouse Integration

ClickHouse provides high-performance analytics for traffic data.

### Installation (Docker)

```yaml
# Add to docker-compose.yml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
      - "8123:8123"
    environment:
      CLICKHOUSE_DB: ddos_analytics
      CLICKHOUSE_USER: ddos
      CLICKHOUSE_PASSWORD: secure_password
    volumes:
      - clickhouse_data:/var/lib/clickhouse
```

### Configuration

```bash
# Enable ClickHouse in .env
CLICKHOUSE_ENABLED=true
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=ddos_analytics
CLICKHOUSE_USER=ddos
CLICKHOUSE_PASSWORD=secure_password
```

### Create Tables

```sql
-- Connect to ClickHouse
clickhouse-client --host localhost --port 9000

-- Create traffic flows table
CREATE TABLE IF NOT EXISTS ddos_analytics.traffic_flows (
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

-- Create index for faster queries
CREATE INDEX idx_dest_ip ON traffic_flows (dest_ip) TYPE minmax GRANULARITY 4;
```

### Example Queries

```sql
-- Top talkers in last hour
SELECT source_ip, SUM(packets) as total_packets, SUM(bytes) as total_bytes
FROM traffic_flows
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY source_ip
ORDER BY total_packets DESC
LIMIT 10;

-- Traffic by protocol
SELECT protocol, COUNT(*) as flow_count, SUM(packets) as total_packets
FROM traffic_flows
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY protocol;

-- Top attacked destinations
SELECT dest_ip, COUNT(DISTINCT source_ip) as unique_sources, SUM(packets) as total_packets
FROM traffic_flows
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY dest_ip
HAVING unique_sources > 100
ORDER BY total_packets DESC;
```

### Install Python Client

```bash
pip install clickhouse-driver
```

## InfluxDB Integration

InfluxDB stores time-series metrics for monitoring and alerting.

### Installation (Docker) - InfluxDB 2.x

```yaml
# Add to docker-compose.yml
services:
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: adminpassword
      DOCKER_INFLUXDB_INIT_ORG: my-org
      DOCKER_INFLUXDB_INIT_BUCKET: ddos-metrics
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: my-super-secret-auth-token
    volumes:
      - influxdb_data:/var/lib/influxdb2
```

### Configuration (InfluxDB 2.x)

```bash
# Enable InfluxDB in .env
INFLUXDB_ENABLED=true
INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_V2=true
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=ddos-metrics
INFLUXDB_TOKEN=my-super-secret-auth-token
```

### Example Queries (Flux)

```flux
// Average packets per second
from(bucket: "ddos-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "traffic")
  |> filter(fn: (r) => r._field == "packets")
  |> aggregateWindow(every: 1m, fn: mean)

// Top protocols
from(bucket: "ddos-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "traffic")
  |> group(columns: ["protocol"])
  |> sum()
  |> sort(desc: true)
  |> limit(n: 10)
```

### Install Python Client

```bash
pip install influxdb-client
```

## Graphite Integration

Graphite provides metrics aggregation and graphing.

### Installation (Docker)

```yaml
# Add to docker-compose.yml
services:
  graphite:
    image: graphiteapp/graphite-statsd:latest
    ports:
      - "2003:2003"  # Carbon plaintext
      - "2004:2004"  # Carbon pickle
      - "8080:8080"  # Graphite web UI
    volumes:
      - graphite_data:/opt/graphite/storage
```

### Configuration

```bash
# Enable Graphite in .env
GRAPHITE_ENABLED=true
GRAPHITE_HOST=graphite
GRAPHITE_PORT=2003
GRAPHITE_PREFIX=ddos.protection
```

### Access Web UI

Open http://localhost:8080 to view Graphite web interface.

### Example Metrics

Metrics are automatically sent in this format:
```
ddos.protection.traffic.tcp.packets 50000 1612137600
ddos.protection.traffic.tcp.bytes 50000000 1612137600
ddos.protection.alerts.syn_flood.count 5 1612137600
ddos.protection.mitigations.active 3 1612137600
```

### Query Example

```
# In Graphite UI, use these targets:
sumSeries(ddos.protection.traffic.*.packets)
averageSeries(ddos.protection.traffic.tcp.packets)
derivative(ddos.protection.alerts.*.count)
```

## MongoDB/FerretDB Integration

MongoDB provides flexible document storage. FerretDB offers MongoDB compatibility backed by PostgreSQL.

### Option 1: Native MongoDB

```yaml
# Add to docker-compose.yml
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password
      MONGO_INITDB_DATABASE: ddos_platform
    volumes:
      - mongodb_data:/data/db
```

### Option 2: FerretDB (Recommended)

FerretDB provides MongoDB compatibility without MongoDB licensing issues.

```yaml
# Add to docker-compose.yml
services:
  ferretdb:
    image: ghcr.io/ferretdb/ferretdb:latest
    ports:
      - "27017:27017"
    environment:
      FERRETDB_POSTGRESQL_URL: postgresql://ddos_user:ddos_pass@postgres:5432/ferretdb
    depends_on:
      - postgres
```

### Configuration

```bash
# Enable MongoDB in .env
MONGODB_ENABLED=true
MONGODB_HOST=ferretdb  # or mongodb
MONGODB_PORT=27017
MONGODB_DATABASE=ddos_platform

# For FerretDB
FERRETDB_POSTGRESQL_URL=postgresql://ddos_user:ddos_pass@postgres:5432/ferretdb
```

### Python Usage

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.ddos_platform

# Store alert
db.alerts.insert_one({
    "timestamp": "2026-02-01T15:08:14Z",
    "type": "syn_flood",
    "target_ip": "203.0.113.50",
    "severity": "high",
    "packets_per_sec": 50000
})

# Query alerts
for alert in db.alerts.find({"severity": "high"}):
    print(alert)
```

### Install Python Client

```bash
pip install pymongo
```

## Testing Integrations

### Test Script

Create a test script to verify all integrations:

```python
#!/usr/bin/env python3
"""Test all integrations."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.integrations import (
    kafka_integration,
    clickhouse_integration,
    influxdb_integration,
    graphite_integration,
    mongodb_integration
)

async def test_kafka():
    """Test Kafka integration."""
    if not kafka_integration.enabled:
        print("❌ Kafka: Disabled")
        return
    
    flow_data = {
        'source_ip': '192.0.2.100',
        'dest_ip': '203.0.113.50',
        'packets': 1000,
        'bytes': 1500000
    }
    
    result = await kafka_integration.send_flow(flow_data)
    print(f"{'✅' if result else '❌'} Kafka: {'OK' if result else 'Failed'}")

def test_clickhouse():
    """Test ClickHouse integration."""
    if not clickhouse_integration.enabled:
        print("❌ ClickHouse: Disabled")
        return
    
    flows = [{
        'timestamp': '2026-02-01 15:08:14',
        'source_ip': '192.0.2.100',
        'dest_ip': '203.0.113.50',
        'packets': 1000,
        'bytes': 1500000
    }]
    
    result = clickhouse_integration.insert_flows(flows)
    print(f"{'✅' if result else '❌'} ClickHouse: {'OK' if result else 'Failed'}")

def test_influxdb():
    """Test InfluxDB integration."""
    if not influxdb_integration.enabled:
        print("❌ InfluxDB: Disabled")
        return
    
    result = influxdb_integration.write_metric(
        'traffic',
        {'protocol': 'tcp'},
        {'packets': 1000, 'bytes': 1500000}
    )
    print(f"{'✅' if result else '❌'} InfluxDB: {'OK' if result else 'Failed'}")

def test_graphite():
    """Test Graphite integration."""
    if not graphite_integration.enabled:
        print("❌ Graphite: Disabled")
        return
    
    result = graphite_integration.send_metric('traffic.test.packets', 1000)
    print(f"{'✅' if result else '❌'} Graphite: {'OK' if result else 'Failed'}")

def test_mongodb():
    """Test MongoDB integration."""
    if not mongodb_integration.enabled:
        print("❌ MongoDB: Disabled")
        return
    
    alert_data = {
        'type': 'test',
        'severity': 'low',
        'target_ip': '203.0.113.50'
    }
    
    result = mongodb_integration.insert_alert(alert_data)
    print(f"{'✅' if result else '❌'} MongoDB: {'OK' if result else 'Failed'}")

async def main():
    """Run all tests."""
    print("Testing integrations...\n")
    
    await test_kafka()
    test_clickhouse()
    test_influxdb()
    test_graphite()
    test_mongodb()
    
    print("\nIntegration tests complete!")

if __name__ == '__main__':
    asyncio.run(main())
```

Save as `backend/scripts/test_integrations.py` and run:

```bash
cd backend
python scripts/test_integrations.py
```

### Expected Output

```
Testing integrations...

❌ Kafka: Disabled
❌ ClickHouse: Disabled
❌ InfluxDB: Disabled
❌ Graphite: Disabled
❌ MongoDB: Disabled

Integration tests complete!
```

Enable integrations in `.env` and run again to see successful connections.

## Complete Docker Compose Example

Here's a complete `docker-compose.yml` with all integrations:

```yaml
version: '3.8'

services:
  # ... existing services ...

  # Kafka Stack
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  # ClickHouse
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
      - "8123:8123"
    environment:
      CLICKHOUSE_DB: ddos_analytics
      CLICKHOUSE_USER: ddos
      CLICKHOUSE_PASSWORD: secure_password
    volumes:
      - clickhouse_data:/var/lib/clickhouse

  # InfluxDB
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: adminpassword
      DOCKER_INFLUXDB_INIT_ORG: my-org
      DOCKER_INFLUXDB_INIT_BUCKET: ddos-metrics
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: my-token
    volumes:
      - influxdb_data:/var/lib/influxdb2

  # Graphite
  graphite:
    image: graphiteapp/graphite-statsd:latest
    ports:
      - "2003:2003"
      - "8080:8080"
    volumes:
      - graphite_data:/opt/graphite/storage

  # FerretDB (MongoDB-compatible)
  ferretdb:
    image: ghcr.io/ferretdb/ferretdb:latest
    ports:
      - "27017:27017"
    environment:
      FERRETDB_POSTGRESQL_URL: postgresql://ddos_user:ddos_pass@postgres:5432/ferretdb

volumes:
  clickhouse_data:
  influxdb_data:
  graphite_data:
```

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka logs
docker logs kafka

# Test connection
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### ClickHouse Connection Issues

```bash
# Check ClickHouse logs
docker logs clickhouse

# Test connection
clickhouse-client --host localhost --port 9000 --query "SELECT 1"
```

### InfluxDB Connection Issues

```bash
# Check InfluxDB logs
docker logs influxdb

# Test connection (InfluxDB 2.x)
curl -I http://localhost:8086/health
```

### Graphite Connection Issues

```bash
# Check Graphite logs
docker logs graphite

# Test connection
echo "test.metric 1 $(date +%s)" | nc localhost 2003
```

### MongoDB/FerretDB Connection Issues

```bash
# Check FerretDB logs
docker logs ferretdb

# Test connection
mongosh mongodb://localhost:27017/
```

## Next Steps

- Review [FEATURES.md](FEATURES.md) for complete feature documentation
- See [PACKET_CAPTURE.md](PACKET_CAPTURE.md) for packet capture engines
- Check [BGP-RTBH.md](BGP-RTBH.md) for BGP blackholing setup
- Read [FLOWSPEC.md](FLOWSPEC.md) for FlowSpec configuration

## Support

For issues with integrations:
- GitHub Issues: https://github.com/i4edubd/ddos-potection/issues
- Documentation: https://github.com/i4edubd/ddos-potection/tree/main/docs
