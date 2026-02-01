# Packet Capture and Threshold Management Guide

This guide covers the advanced packet capture features and per-subnet threshold configuration capabilities of the DDoS Protection Platform.

## Table of Contents

- [Packet Capture Overview](#packet-capture-overview)
- [Capture Modes](#capture-modes)
- [VLAN Untagging](#vlan-untagging)
- [Attack Fingerprinting](#attack-fingerprinting)
- [Hostgroups and Thresholds](#hostgroups-and-thresholds)
- [Script Execution](#script-execution)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Best Practices](#best-practices)

## Packet Capture Overview

The platform supports multiple packet capture methods for recording network traffic and capturing attack fingerprints. All captures are saved in standard PCAP format for analysis with tools like Wireshark.

### Features

- **Multiple capture modes**: PCAP, AF_PACKET, AF_XDP
- **VLAN untagging**: Automatic removal of 802.1Q and 802.1ad tags
- **Attack fingerprinting**: Automatic capture of attack traffic patterns
- **BPF filtering**: Fine-grained packet filtering
- **Configurable limits**: Control file size and duration
- **Automatic cleanup**: Remove old capture files

## Capture Modes

### PCAP Capture

Standard packet capture using Scapy. Best for general purpose captures with filtering.

**Use case**: Manual traffic analysis, debugging, development

**Advantages**:
- Easy to use and configure
- Supports complex BPF filters
- Works on all platforms

**Limitations**:
- Lower performance than AF_PACKET
- Higher CPU overhead

**Example**:
```python
from services.packet_capture import get_packet_capture_service

service = get_packet_capture_service()
capture_id = service.start_pcap_capture(
    interface="eth0",
    filter_bpf="tcp and port 80",
    duration=60,
    target_ip="192.168.1.100"
)
```

### AF_PACKET Capture

High-performance packet capture using Linux raw sockets (AF_PACKET).

**Use case**: High-traffic environments, production monitoring

**Advantages**:
- Bypasses kernel networking stack
- Lower latency and CPU usage
- Better performance than standard PCAP

**Requirements**:
- Linux kernel 2.4+
- CAP_NET_RAW capability or root access

**Example**:
```python
capture_id = service.start_af_packet_capture(
    interface="eth0",
    duration=60
)
```

### AF_XDP Capture

Ultra-high-performance packet capture using Express Data Path (XDP) with eBPF.

**Use case**: Very high-traffic environments (10Gbps+), DDoS mitigation

**Advantages**:
- Highest performance available
- Kernel bypass with eBPF
- Minimal CPU overhead

**Requirements**:
- Linux kernel 4.18+
- libxdp and BPF support
- XDP-capable network driver

**Note**: Currently falls back to AF_PACKET. Full AF_XDP support requires additional configuration.

**Example**:
```python
capture_id = service.start_af_xdp_capture(
    interface="eth0",
    duration=60
)
```

## VLAN Untagging

The platform automatically removes VLAN tags from captured packets when enabled, making analysis easier and reducing file size.

### Supported VLAN Types

**802.1Q (Single VLAN Tag)**
- EtherType: 0x8100
- Tag size: 4 bytes (TCI + EtherType)
- VLAN ID: 12 bits (0-4095)

**802.1ad (QinQ / Double VLAN Tag)**
- Outer EtherType: 0x88a8 or 0x9100
- Inner EtherType: 0x8100
- Tag size: 8 bytes total
- Supports service provider and customer VLAN separation

### How It Works

1. Packet is captured from network interface
2. VLAN tags are detected by EtherType
3. Tag bytes are removed from Ethernet frame
4. Original MAC addresses preserved
5. Packet written to PCAP file

### Configuration

```python
# In config.py or .env
VLAN_UNTAGGING_ENABLED=True  # Default: True
```

Enable/disable at runtime:
```python
service = get_packet_capture_service()
service.vlan_untagging_enabled = False  # Disable untagging
```

## Attack Fingerprinting

Automatically capture packets during detected attacks for forensic analysis.

### How It Works

1. Anomaly detector identifies attack (SYN flood, UDP flood, etc.)
2. Attack fingerprint capture is triggered automatically
3. Packets matching the attack are captured for 30 seconds
4. PCAP file saved with attack metadata
5. Metadata stored in Redis for retrieval

### Captured Attacks

- **SYN Flood**: TCP packets with SYN flag to target IP
- **UDP Flood**: UDP packets to target IP
- **ICMP Flood**: ICMP packets to target IP
- **Other attacks**: All packets to target IP

### Metadata

Each fingerprint capture includes:
- Alert ID
- Target IP address
- Attack type
- Timestamp
- Packet count
- PCAP file path

### Example

Fingerprints are captured automatically, but can be triggered manually:

```python
from services.packet_capture import get_packet_capture_service

service = get_packet_capture_service()
pcap_file = service.capture_attack_fingerprint(
    alert_id=123,
    target_ip="192.168.1.100",
    attack_type="syn_flood",
    duration=30
)
```

## Hostgroups and Thresholds

Configure per-subnet thresholds with the hostgroups feature. Different subnets can have different rate limits and actions.

### Hostgroup Structure

```python
{
    "name": "customer_network_1",
    "subnet": "192.168.1.0/24",
    "thresholds": {
        "packets_per_second": 10000,
        "bytes_per_second": 100000000,  # 100 Mbps
        "flows_per_second": 1000
    },
    "scripts": {
        "block": "/etc/ddos-protection/scripts/block.sh",
        "notify": "/etc/ddos-protection/scripts/notify.sh"
    }
}
```

### Creating Hostgroups

**Via API**:
```bash
curl -X POST http://localhost:8000/api/v1/hostgroups/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_network_1",
    "subnet": "192.168.1.0/24",
    "thresholds": {
      "packets_per_second": 10000,
      "bytes_per_second": 100000000,
      "flows_per_second": 1000
    }
  }'
```

**Via Python**:
```python
from services.hostgroup_manager import get_hostgroup_manager

manager = get_hostgroup_manager()
manager.add_hostgroup(
    name="customer_network_1",
    subnet="192.168.1.0/24",
    thresholds={
        "packets_per_second": 10000,
        "bytes_per_second": 100000000,
        "flows_per_second": 1000
    }
)
```

### Longest Prefix Match

When an IP belongs to multiple hostgroups, the most specific (longest prefix) match is used:

```
192.168.0.0/16  → 10,000 pps (general)
192.168.1.0/24  → 5,000 pps (specific)

192.168.1.50 → Uses 5,000 pps (more specific)
192.168.2.50 → Uses 10,000 pps (only matches /16)
```

### Default Thresholds

If an IP doesn't match any hostgroup, system defaults are used:

```python
# Default thresholds (can be configured)
DEFAULT_PPS_THRESHOLD: int = 10000
DEFAULT_BPS_THRESHOLD: int = 100000000  # 100 Mbps
DEFAULT_FPS_THRESHOLD: int = 1000
```

## Script Execution

Execute custom scripts when thresholds are exceeded for automated mitigation and notifications.

### Script Types

**Block Script**:
- Executed when threshold exceeded
- Should implement blocking (firewall rules, BGP announcements, etc.)
- Receives target IP as argument

**Notify Script**:
- Executed when threshold exceeded
- Should send notifications (SMS, Slack, PagerDuty, etc.)
- Receives target IP and alert ID as arguments

### Script Environment Variables

Scripts receive these environment variables:

- `TARGET_IP`: IP address that exceeded threshold
- `ALERT_ID`: Alert ID in database
- `EXCEEDED_METRICS`: JSON array of exceeded thresholds
- `TIMESTAMP`: ISO 8601 timestamp

### Example Block Script

```bash
#!/bin/bash
# /etc/ddos-protection/scripts/block.sh

TARGET_IP=$1

# Add iptables rule to block IP
iptables -A INPUT -s $TARGET_IP -j DROP

# Log the action
echo "$(date): Blocked $TARGET_IP due to threshold exceeded" >> /var/log/ddos-blocks.log

# Optional: Announce BGP blackhole route
if [ -n "$BGP_ENABLED" ]; then
    echo "announce route $TARGET_IP/32 next-hop $BGP_BLACKHOLE_NEXTHOP" \
        > /var/run/exabgp.cmd
fi

exit 0
```

### Example Notify Script

```bash
#!/bin/bash
# /etc/ddos-protection/scripts/notify.sh

TARGET_IP=$1
ALERT_ID=$2

# Send Slack notification
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d "{
    \"text\": \"🚨 DDoS Alert: IP $TARGET_IP exceeded threshold\",
    \"attachments\": [{
      \"color\": \"danger\",
      \"fields\": [
        {\"title\": \"Target IP\", \"value\": \"$TARGET_IP\", \"short\": true},
        {\"title\": \"Alert ID\", \"value\": \"$ALERT_ID\", \"short\": true},
        {\"title\": \"Exceeded Metrics\", \"value\": \"$EXCEEDED_METRICS\"}
      ]
    }]
  }"

exit 0
```

### Script Security

**Important security considerations**:

1. **Validate scripts**: Test scripts thoroughly before deployment
2. **Use absolute paths**: Avoid PATH-based script execution
3. **Set proper permissions**: Scripts should be owned by root and not world-writable
4. **Timeout protection**: Scripts are killed after 30 seconds
5. **Error handling**: Scripts should handle errors gracefully
6. **Audit logging**: Log all script executions

```bash
# Recommended script permissions
chmod 750 /etc/ddos-protection/scripts/block.sh
chown root:ddos /etc/ddos-protection/scripts/block.sh
```

## API Reference

### Packet Capture Endpoints

#### Start Capture
```
POST /api/v1/capture/start
```

Request body:
```json
{
  "interface": "eth0",
  "capture_mode": "af_packet",
  "filter_bpf": "tcp and port 80",
  "duration": 60,
  "target_ip": "192.168.1.100"
}
```

#### Stop Capture
```
POST /api/v1/capture/stop/{capture_id}
```

#### Get Capture Status
```
GET /api/v1/capture/status/{capture_id}
```

#### List Captures
```
GET /api/v1/capture/list
```

#### Download PCAP
```
GET /api/v1/capture/download/{filename}
```

### Hostgroup Endpoints

#### Create Hostgroup
```
POST /api/v1/hostgroups/
```

#### List Hostgroups
```
GET /api/v1/hostgroups/
```

#### Get Hostgroup
```
GET /api/v1/hostgroups/{name}
```

#### Delete Hostgroup
```
DELETE /api/v1/hostgroups/{name}
```

#### Check IP Thresholds
```
POST /api/v1/hostgroups/check-ip
```

Request body:
```json
{
  "ip": "192.168.1.50"
}
```

## Configuration

### Environment Variables

```bash
# Packet Capture
PCAP_ENABLED=true
PCAP_DIR=/var/lib/ddos-protection/pcaps
PCAP_MAX_PACKETS=10000
VLAN_UNTAGGING_ENABLED=true
AF_PACKET_ENABLED=true
AF_XDP_ENABLED=false

# Thresholds
DEFAULT_PPS_THRESHOLD=10000
DEFAULT_BPS_THRESHOLD=100000000
DEFAULT_FPS_THRESHOLD=1000
THRESHOLD_CHECK_INTERVAL=1

# Scripts
SCRIPTS_ENABLED=true
SCRIPTS_DIR=/etc/ddos-protection/scripts
SCRIPT_TIMEOUT=30
```

### File Locations

- **PCAP files**: `/var/lib/ddos-protection/pcaps/`
- **Scripts**: `/etc/ddos-protection/scripts/`
- **Logs**: `/var/log/ddos-protection/`
- **Configuration**: `/etc/ddos-protection/config.yaml`

## Best Practices

### Packet Capture

1. **Use appropriate capture mode**:
   - PCAP for debugging and analysis
   - AF_PACKET for production monitoring
   - AF_XDP for very high-traffic environments

2. **Apply BPF filters**: Reduce capture size and CPU usage
   ```python
   filter_bpf="tcp and (port 80 or port 443)"
   ```

3. **Limit capture duration**: Avoid filling disk with long captures
   ```python
   duration=60  # 1 minute is usually sufficient
   ```

4. **Cleanup old captures**: Run periodic cleanup
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/capture/cleanup?max_age_days=7
   ```

### Hostgroups

1. **Start with defaults**: Use system defaults for most networks
2. **Create specific groups**: Only create hostgroups for networks that need different thresholds
3. **Use hierarchical subnets**: Take advantage of longest prefix matching
4. **Monitor and adjust**: Review alerts and adjust thresholds based on actual traffic
5. **Document groups**: Keep track of which customers/networks use which hostgroups

### Script Execution

1. **Test scripts thoroughly**: Test in non-production environment first
2. **Handle errors gracefully**: Scripts should never crash
3. **Use idempotent operations**: Scripts may be called multiple times
4. **Log all actions**: Keep audit trail of all script executions
5. **Monitor script performance**: Ensure scripts complete within timeout

### Performance

1. **VLAN untagging overhead**: Minimal (<1% CPU), safe to leave enabled
2. **Capture impact**: PCAP capture can use 10-20% CPU for high traffic
3. **AF_PACKET optimization**: Use for captures >1Gbps
4. **Threshold checking**: Runs every second, negligible overhead
5. **Script execution**: Async, doesn't block detection

## Troubleshooting

### PCAP Capture Issues

**Problem**: "Scapy not available"
```bash
# Solution: Install scapy
pip install scapy
```

**Problem**: "Permission denied" when capturing
```bash
# Solution: Run with CAP_NET_RAW or as root
setcap cap_net_raw=eip /usr/bin/python3.11
```

### AF_PACKET Issues

**Problem**: "AF_PACKET not supported"
```bash
# Solution: AF_PACKET is Linux-only
# Use PCAP mode on other platforms
```

### Script Execution Issues

**Problem**: Scripts not executing
```bash
# Check if scripts are enabled
echo $SCRIPTS_ENABLED  # Should be "true"

# Check script permissions
ls -l /etc/ddos-protection/scripts/

# Check script logs
tail -f /var/log/ddos-protection/scripts.log
```

**Problem**: Scripts timing out
```bash
# Increase timeout in config.py
SCRIPT_TIMEOUT=60  # Increase from 30 to 60 seconds
```

### Hostgroup Issues

**Problem**: Wrong thresholds applied
```bash
# Check which hostgroup matches
curl -X POST http://localhost:8000/api/v1/hostgroups/check-ip \
  -d '{"ip": "192.168.1.50"}'
```

**Problem**: Hostgroups not persisting
```bash
# Check Redis connection
redis-cli ping

# List hostgroups in Redis
redis-cli KEYS "hostgroup:*"
```

## Examples

### Complete Capture Workflow

```python
from services.packet_capture import get_packet_capture_service
import time

# Initialize service
service = get_packet_capture_service()

# Start capture
print("Starting capture...")
capture_id = service.start_af_packet_capture(
    interface="eth0",
    duration=60
)
print(f"Capture ID: {capture_id}")

# Check status
while True:
    status = service.get_capture_status(capture_id)
    if not status['active']:
        break
    print(f"Capturing... File size: {status['file_size']} bytes")
    time.sleep(5)

print(f"Capture complete: {status['pcap_file']}")

# List all captures
captures = service.list_captures()
print(f"Total captures: {len(captures)}")
```

### Complete Hostgroup Workflow

```python
from services.hostgroup_manager import get_hostgroup_manager

# Initialize manager
manager = get_hostgroup_manager()

# Create hostgroups
manager.add_hostgroup(
    name="critical_servers",
    subnet="10.0.1.0/24",
    thresholds={
        "packets_per_second": 5000,  # Lower threshold
        "bytes_per_second": 50000000
    },
    scripts={
        "block": "/etc/ddos-protection/scripts/block.sh",
        "notify": "/etc/ddos-protection/scripts/notify-critical.sh"
    }
)

manager.add_hostgroup(
    name="general_users",
    subnet="10.0.0.0/16",
    thresholds={
        "packets_per_second": 20000,  # Higher threshold
        "bytes_per_second": 200000000
    }
)

# Check which group applies to specific IPs
for ip in ["10.0.1.5", "10.0.2.5", "192.168.1.1"]:
    group = manager.get_hostgroup_for_ip(ip)
    thresholds = manager.get_thresholds_for_ip(ip)
    print(f"\nIP: {ip}")
    print(f"  Group: {group.name if group else 'default'}")
    print(f"  PPS Threshold: {thresholds['packets_per_second']}")
```

## See Also

- [Traffic Collection Guide](TRAFFIC_COLLECTION.md)
- [DDoS Detection Guide](DETECTION.md)
- [Mitigation Guide](MITIGATION.md)
- [API Documentation](API.md)
