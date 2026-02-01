# Custom Rule Engine - Advanced Traffic Filtering

## Overview

The Custom Rule Engine provides a flexible, policy-based approach to DDoS protection. It allows you to define sophisticated rules that automatically evaluate incoming traffic and take appropriate actions based on:

- **Rate Limits**: Detect and mitigate traffic that exceeds defined thresholds
- **IP Blocks**: Block or allow specific IP addresses or ranges
- **Protocol Filters**: Control traffic based on protocol (TCP, UDP, ICMP, etc.)
- **Geo-Blocking**: Filter traffic based on geographic origin
- **Port Filters**: Restrict traffic to/from specific ports

## Features

### 1. Rate Limiting

Automatically detect when traffic exceeds defined thresholds and take action.

**Capabilities:**
- Packets per second (PPS) thresholds
- Bytes per second (BPS) thresholds
- Protocol-specific rate limits
- IP-specific or network-wide limits
- Configurable time windows

### 2. IP Blocking

Block traffic from specific IP addresses or ranges.

**Capabilities:**
- Single IP blocking
- CIDR range blocking
- IPv4 and IPv6 support
- Whitelist and blacklist modes

### 3. Protocol Filtering

Control traffic based on network protocols.

**Capabilities:**
- Block specific protocols (TCP, UDP, ICMP, etc.)
- Allow-only mode (whitelist protocols)
- Protocol-specific rules

### 4. Geo-Blocking

Filter traffic based on geographic origin.

**Capabilities:**
- Block traffic from specific countries
- Allow-only mode (whitelist countries)
- Automatic IP geolocation lookup
- Support for GeoIP2 database

### 5. Port Filtering

Restrict traffic based on port numbers.

**Capabilities:**
- Source and destination port filtering
- Port range support
- Block or allow modes
- Protocol-aware filtering

## Configuration

### GeoIP Setup (Optional)

For geo-blocking, install GeoIP2 database:

```bash
# Install GeoIP2 library
pip install geoip2

# Download GeoLite2 database (free)
wget https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb
sudo mkdir -p /usr/share/GeoIP
sudo mv GeoLite2-Country.mmdb /usr/share/GeoIP/

# Configure path in .env
echo "GEOIP_DATABASE_PATH=/usr/share/GeoIP/GeoLite2-Country.mmdb" >> backend/.env
```

## Usage

### Creating Rules

#### Via API

**1. Block Specific IP**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block malicious IP",
    "rule_type": "ip_block",
    "condition": {
      "ip": "192.0.2.100"
    },
    "action": "block",
    "priority": 100
  }'
```

**2. Block IP Range (CIDR)**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block malicious network",
    "rule_type": "ip_block",
    "condition": {
      "ip": "192.0.2.0/24"
    },
    "action": "block",
    "priority": 100
  }'
```

**3. Rate Limit Rule**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rate limit suspicious traffic",
    "rule_type": "rate_limit",
    "condition": {
      "ip": "198.51.100.0/24",
      "protocol": "tcp",
      "threshold": 10000,
      "window": 60
    },
    "action": "rate_limit",
    "priority": 50
  }'
```

**4. Protocol Filter (Block)**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block ICMP floods",
    "rule_type": "protocol_filter",
    "condition": {
      "protocols": ["icmp"],
      "mode": "block"
    },
    "action": "block",
    "priority": 75
  }'
```

**5. Protocol Filter (Allow-Only)**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Allow only HTTP/HTTPS",
    "rule_type": "protocol_filter",
    "condition": {
      "protocols": ["tcp", "udp"],
      "mode": "allow"
    },
    "action": "block",
    "priority": 90
  }'
```

**6. Geo-Blocking**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block traffic from high-risk countries",
    "rule_type": "geo_block",
    "condition": {
      "countries": ["CN", "RU", "KP"],
      "mode": "block"
    },
    "action": "block",
    "priority": 60
  }'
```

**7. Geo-Allow (Whitelist)**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Allow only US/CA traffic",
    "rule_type": "geo_block",
    "condition": {
      "countries": ["US", "CA", "GB"],
      "mode": "allow"
    },
    "action": "block",
    "priority": 70
  }'
```

**8. Port Blocking**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Block SSH brute force attempts",
    "rule_type": "port_filter",
    "condition": {
      "ports": [22, 23, 3389],
      "port_type": "dest",
      "mode": "block"
    },
    "action": "block",
    "priority": 80
  }'
```

**9. Temporary Rule with Expiration**

```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Temporary block",
    "rule_type": "ip_block",
    "condition": {
      "ip": "192.0.2.100",
      "expires_at": "2027-12-31T23:59:59"
    },
    "action": "block",
    "priority": 100
  }'
```

### Via Python

```python
import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000/api/v1"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def create_rate_limit_rule(ip_range: str, threshold: int, window: int = 60):
    """Create a rate limit rule"""
    rule = {
        "name": f"Rate limit {ip_range}",
        "rule_type": "rate_limit",
        "condition": {
            "ip": ip_range,
            "threshold": threshold,
            "window": window
        },
        "action": "rate_limit",
        "priority": 50
    }
    
    response = requests.post(
        f"{API_URL}/rules/",
        headers=headers,
        json=rule
    )
    
    return response.json()

def create_geo_block_rule(countries: list, mode: str = "block"):
    """Create geo-blocking rule"""
    rule = {
        "name": f"Geo-{mode} {', '.join(countries)}",
        "rule_type": "geo_block",
        "condition": {
            "countries": countries,
            "mode": mode
        },
        "action": "block",
        "priority": 60
    }
    
    response = requests.post(
        f"{API_URL}/rules/",
        headers=headers,
        json=rule
    )
    
    return response.json()

def create_temporary_block(ip: str, duration_hours: int = 24):
    """Create temporary IP block"""
    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    
    rule = {
        "name": f"Temporary block {ip}",
        "rule_type": "ip_block",
        "condition": {
            "ip": ip,
            "expires_at": expires_at.isoformat()
        },
        "action": "block",
        "priority": 100
    }
    
    response = requests.post(
        f"{API_URL}/rules/",
        headers=headers,
        json=rule
    )
    
    return response.json()

# Example usage
rate_limit_rule = create_rate_limit_rule("192.0.2.0/24", threshold=10000)
geo_block_rule = create_geo_block_rule(["CN", "RU"], mode="block")
temp_block_rule = create_temporary_block("192.0.2.100", duration_hours=48)
```

## Rule Types and Parameters

### IP Block

Block traffic from specific IP addresses or ranges.

**Required Parameters:**
- `ip`: IP address or CIDR range

**Example:**
```json
{
  "rule_type": "ip_block",
  "condition": {
    "ip": "192.0.2.100"  // or "192.0.2.0/24"
  },
  "action": "block"
}
```

### Rate Limit

Detect when traffic exceeds thresholds.

**Required Parameters:**
- `threshold`: Packets per second threshold

**Optional Parameters:**
- `ip`: IP address or CIDR range to monitor
- `protocol`: Protocol to monitor (tcp, udp, icmp)
- `window`: Time window in seconds (default: 60)

**Example:**
```json
{
  "rule_type": "rate_limit",
  "condition": {
    "ip": "192.0.2.0/24",
    "protocol": "tcp",
    "threshold": 10000,
    "window": 60
  },
  "action": "rate_limit"
}
```

### Protocol Filter

Control traffic based on protocols.

**Required Parameters:**
- `protocols`: List of protocols (tcp, udp, icmp, etc.)
- `mode`: "block" or "allow"

**Example:**
```json
{
  "rule_type": "protocol_filter",
  "condition": {
    "protocols": ["icmp", "gre"],
    "mode": "block"
  },
  "action": "block"
}
```

### Geo Block

Filter traffic based on country of origin.

**Required Parameters:**
- `countries`: List of ISO country codes
- `mode`: "block" or "allow"

**Example:**
```json
{
  "rule_type": "geo_block",
  "condition": {
    "countries": ["CN", "RU", "KP"],
    "mode": "block"
  },
  "action": "block"
}
```

### Port Filter

Filter based on port numbers.

**Required Parameters:**
- `ports`: List of port numbers
- `port_type`: "dest" or "source"
- `mode`: "block" or "allow"

**Example:**
```json
{
  "rule_type": "port_filter",
  "condition": {
    "ports": [22, 23, 3389],
    "port_type": "dest",
    "mode": "block"
  },
  "action": "block"
}
```

## Rule Priority

Rules are evaluated in priority order (lower number = higher priority).

**Priority Ranges:**
- 1-25: Emergency rules (immediate threats)
- 26-50: High priority (rate limits, geo-blocks)
- 51-75: Medium priority (protocol filters)
- 76-100: Low priority (general blocks)

**Example:**
```python
# Critical IP block
priority = 10

# Standard rate limit
priority = 50

# Protocol filter
priority = 75

# General block
priority = 100
```

## Rule Actions

### block

Drop all matching traffic using iptables/nftables.

```json
{
  "action": "block"
}
```

### rate_limit

Apply rate limiting using Linux tc (traffic control).

```json
{
  "action": "rate_limit",
  "condition": {
    "rate": "1000/s"  // Optional rate specification
  }
}
```

### alert

Log an alert without blocking traffic.

```json
{
  "action": "alert"
}
```

## Rule Management

### List Rules

```bash
curl -X GET http://localhost:8000/api/v1/rules/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Specific Rule

```bash
curl -X GET http://localhost:8000/api/v1/rules/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Rule

```bash
curl -X PUT http://localhost:8000/api/v1/rules/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'
```

### Delete Rule

```bash
curl -X DELETE http://localhost:8000/api/v1/rules/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Programmatic Usage

### Using the Rule Engine Directly

```python
from services.rule_engine import RuleEngine

# Create engine instance
engine = RuleEngine()

# Evaluate traffic
traffic_data = {
    'source_ip': '192.0.2.100',
    'dest_ip': '198.51.100.50',
    'protocol': 'tcp',
    'source_port': 54321,
    'dest_port': 80,
    'packets': 5000,
    'bytes': 250000,
    'country': 'CN'
}

# Get matching rules
actions = engine.evaluate_traffic(traffic_data)

# Apply actions
for action in actions:
    print(f"Rule matched: {action['rule_name']}")
    print(f"Action: {action['action']}")
    
    # Apply the action
    success = engine.apply_rule_action(action)
    if success:
        print("Action applied successfully")
```

## Best Practices

### 1. Use Appropriate Priorities

```python
# Critical threats - highest priority
critical_block = {"priority": 10}

# Rate limits - high priority
rate_limit = {"priority": 50}

# General rules - lower priority
general_filter = {"priority": 100}
```

### 2. Start with Alert Mode

Test rules before blocking:

```python
# Step 1: Alert only
rule = {
    "action": "alert",
    "priority": 50
}

# Step 2: Monitor alerts
# ...

# Step 3: Change to block if confirmed threat
rule = {
    "action": "block",
    "priority": 50
}
```

### 3. Use Temporary Rules

Add expiration for temporary blocks:

```python
from datetime import datetime, timedelta

expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

rule = {
    "condition": {
        "ip": "192.0.2.100",
        "expires_at": expires_at
    }
}
```

### 4. Combine Multiple Rule Types

Layer defenses with multiple rules:

```python
# 1. Geo-block high-risk countries
geo_rule = {"rule_type": "geo_block", "priority": 60}

# 2. Rate limit remaining traffic
rate_rule = {"rule_type": "rate_limit", "priority": 50}

# 3. Protocol filter
protocol_rule = {"rule_type": "protocol_filter", "priority": 75}

# 4. IP block confirmed threats
ip_rule = {"rule_type": "ip_block", "priority": 10}
```

### 5. Monitor and Adjust

Regularly review rules and adjust:

```python
# Get all active rules
rules = get_all_rules()

# Check effectiveness
for rule in rules:
    matches = get_rule_matches(rule['id'])
    if matches == 0:
        # Consider removing ineffective rule
        deactivate_rule(rule['id'])
```

## Troubleshooting

### Rules Not Matching

**Check rule priority:**
- Lower number = higher priority
- High-priority "block" stops evaluation

**Verify rule conditions:**
```bash
# Test rule manually
curl -X GET http://localhost:8000/api/v1/rules/123
```

**Check traffic data format:**
```python
# Ensure traffic data has required fields
traffic = {
    'source_ip': '...',  # Required
    'dest_ip': '...',    # Required
    'protocol': '...',   # Lowercase
    'packets': 0,        # Integer
}
```

### Geo-Blocking Not Working

**Install GeoIP2:**
```bash
pip install geoip2
```

**Download database:**
```bash
wget https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb
sudo mv GeoLite2-Country.mmdb /usr/share/GeoIP/
```

**Configure path:**
```bash
echo "GEOIP_DATABASE_PATH=/usr/share/GeoIP/GeoLite2-Country.mmdb" >> .env
```

### Rate Limiting Not Applied

**Check Linux tc availability:**
```bash
which tc
# Should return /sbin/tc or similar
```

**Verify permissions:**
```bash
# May need sudo for tc commands
sudo usermod -aG sudo ddos
```

**Check system limits:**
```bash
# Increase if needed
sudo sysctl -w net.core.netdev_max_backlog=5000
```

## Performance Considerations

### Rule Evaluation Order

Rules are evaluated in priority order and stop at first "block" action:

```python
# Fast: High-priority blocks evaluated first
rule1 = {"priority": 10, "action": "block"}  # Checked first
rule2 = {"priority": 50, "action": "block"}  # Checked second
rule3 = {"priority": 100, "action": "alert"} # Checked last
```

### Database Queries

Rule engine caches active rules:

```python
# Efficient: Single query for all rules
rules = db.query(Rule).filter(Rule.is_active == True).all()
```

### Geo Lookup Performance

GeoIP lookups are fast but consider caching:

```python
# Cache country lookups for 5 minutes
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=10000)
def lookup_country_cached(ip: str) -> str:
    return lookup_country(ip)
```

## Security Considerations

### Input Validation

All rule parameters are validated:
- IP addresses using `ipaddress` module
- CIDR notation validation
- Protocol name validation

### Access Control

Only admins and operators can create rules:

```python
if current_user.role not in ["admin", "operator"]:
    raise HTTPException(status_code=403)
```

### Audit Logging

All rule changes are logged:

```python
audit_log = {
    "action": "rule_created",
    "user": current_user.username,
    "rule_id": rule.id,
    "timestamp": datetime.utcnow()
}
```

## References

- **GeoIP2**: https://dev.maxmind.com/geoip/geoip2/
- **iptables**: https://www.netfilter.org/
- **Linux Traffic Control**: https://tldp.org/HOWTO/Traffic-Control-HOWTO/

## Support

For rule engine issues:
- Check logs: `docker-compose logs -f backend`
- Test rules: Use API endpoint `/api/v1/rules/`
- GitHub Issues: https://github.com/i4edubd/ddos-protection/issues
