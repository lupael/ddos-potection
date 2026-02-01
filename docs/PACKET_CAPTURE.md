# Packet Capture Engine Guide

## Overview

The DDoS Protection Platform supports multiple packet capture engines to accommodate different hardware, operating systems, and performance requirements. This guide covers all supported engines, their configuration, and a comprehensive comparison table to help you choose the right engine for your deployment.

## Supported Packet Capture Engines

### 1. NetFlow (v5, v9, v9 Lite)

**Status**: ✅ Fully Supported | **Recommended For**: Cisco routers, scalability to terabits

NetFlow is Cisco's proprietary protocol for collecting IP traffic information. It's one of the most widely deployed flow export protocols.

#### NetFlow v5
- **Features**: Basic flow export with fixed format
- **Fields**: Source/dest IP, ports, protocol, packets, bytes, TCP flags
- **Max Flow Rate**: ~50,000 flows/second
- **Use Case**: Legacy Cisco routers, simple deployments

#### NetFlow v9
- **Features**: Template-based flexible format
- **Fields**: Customizable templates with variable field definitions
- **Max Flow Rate**: ~30,000 flows/second (with template caching)
- **Use Case**: Modern Cisco routers, custom flow data

#### NetFlow v9 Lite
- **Features**: Simplified NetFlow v9 with reduced overhead
- **Fields**: Essential fields only for faster processing
- **Max Flow Rate**: ~40,000 flows/second
- **Use Case**: High-volume environments with bandwidth constraints

**Configuration**:
```bash
# Environment Variables
NETFLOW_PORT=2055
NETFLOW_V5_ENABLED=true
NETFLOW_V9_ENABLED=true

# Router Configuration (Cisco)
flow exporter DDOS-COLLECTOR
  destination <collector-ip>
  transport udp 2055
  
flow monitor DDOS-MONITOR
  record netflow ipv4 original-input
  exporter DDOS-COLLECTOR
```

**Performance**: Scales to **terabits per second** on single server with proper hardware

### 2. IPFIX (IP Flow Information Export)

**Status**: ✅ Fully Supported | **Recommended For**: Multi-vendor environments, standards compliance

IPFIX is the IETF standard for flow export (RFC 5101), often called "NetFlow v10".

#### Features
- Template-based like NetFlow v9
- Enterprise field support for vendor extensions
- Compatible with Cisco, Juniper, Huawei, and other vendors
- RFC 5101, 5102, 5103 compliant

#### Configuration
```bash
# Environment Variables
IPFIX_PORT=4739
IPFIX_ENABLED=true

# Router Configuration (Juniper)
services {
    flow-monitoring {
        version-ipfix {
            template ipv4 {
                flow-active-timeout 60;
                flow-inactive-timeout 30;
            }
        }
    }
}
```

**Max Flow Rate**: ~30,000 records/second
**Performance**: Excellent for multi-vendor deployments

### 3. sFlow v5

**Status**: ✅ Fully Supported | **Recommended For**: Switches, real-time sampling

sFlow provides statistical packet sampling for network monitoring.

#### Features
- Packet header sampling (not full flows)
- Agent address tracking
- Multi-vendor support (HP, Arista, Juniper)
- Real-time traffic visibility

#### Configuration
```bash
# Environment Variables
SFLOW_PORT=6343
SFLOW_ENABLED=true

# Router Configuration (Juniper)
protocols {
    sflow {
        collector <collector-ip> udp-port 6343;
        interfaces all;
        sample-rate 1000;
    }
}
```

**Max Sample Rate**: ~20,000 samples/second
**Performance**: Lower overhead than NetFlow

### 4. PCAP (Packet Capture)

**Status**: ⚠️ Supported (High overhead) | **Recommended For**: Small networks, forensics

PCAP provides full packet capture using libpcap/tcpdump.

#### Features
- Complete packet visibility (Layer 2-7)
- Attack fingerprint capture
- Compatible with Wireshark for analysis
- Supports BPF filtering

#### Configuration
```bash
# Environment Variables
PCAP_ENABLED=true
PCAP_INTERFACE=eth0
PCAP_SNAPLEN=1500
PCAP_PROMISC=true
PCAP_FILTER="tcp or udp"

# Optional: Save attack fingerprints
PCAP_CAPTURE_ATTACKS=true
PCAP_STORAGE_PATH=/var/log/ddos/pcaps
```

#### Python Example
```python
from services.pcap_collector import PcapCollector

collector = PcapCollector(
    interface="eth0",
    filter="tcp port 80 or udp port 53",
    snaplen=1500
)
collector.start()
```

**Max Rate**: ~1-10 Gbps depending on hardware
**Performance**: High CPU and storage overhead
**Use Case**: 
- Capture attack fingerprints for analysis
- Forensic investigation
- Small networks (<1 Gbps)

### 5. AF_PACKET (Linux Native Socket)

**Status**: ✅ Recommended | **Recommended For**: Linux servers, 10-40 Gbps

AF_PACKET is the recommended high-performance packet capture method for Linux systems.

#### Features
- Kernel-level packet capture without libpcap
- Zero-copy ring buffers (PACKET_RX_RING)
- VLAN untagging support
- Fanout mode for multi-core scaling

#### Configuration
```bash
# Environment Variables
AF_PACKET_ENABLED=true
AF_PACKET_INTERFACE=eth0
AF_PACKET_FANOUT=true
AF_PACKET_FANOUT_TYPE=hash  # hash, lb, cpu, rollover
AF_PACKET_RING_SIZE=2048
AF_PACKET_BLOCK_SIZE=4096

# VLAN Support
AF_PACKET_VLAN_UNTAG=true
```

#### Python Example
```python
from services.af_packet_collector import AFPacketCollector

collector = AFPacketCollector(
    interface="eth0",
    fanout=True,
    fanout_type="hash",
    ring_size=2048,
    vlan_untag=True
)
collector.start()
```

**Max Rate**: 10-40 Gbps (depends on CPU cores)
**Performance**: 
- Very low CPU overhead with ring buffers
- Multi-core scaling with fanout mode
- Hardware offload support (GRO, LRO)

**Advantages**:
- Native Linux support (no additional drivers)
- Excellent performance on commodity hardware
- VLAN untagging in mirror mode
- Multi-core packet distribution

**Requirements**:
- Linux kernel 3.x or higher
- root/CAP_NET_RAW privileges

### 6. AF_XDP (eXpress Data Path)

**Status**: ✅ Supported | **Recommended For**: 40+ Gbps, ultra-low latency

AF_XDP is the newest Linux packet capture technology using XDP (eXpress Data Path).

#### Features
- Kernel bypass for ultimate performance
- Zero-copy mode (ZC) with compatible NICs
- XDP programs for in-kernel filtering
- Sub-microsecond latency

#### Configuration
```bash
# Environment Variables
AF_XDP_ENABLED=true
AF_XDP_INTERFACE=eth0
AF_XDP_ZERO_COPY=true
AF_XDP_QUEUE_SIZE=4096
AF_XDP_BATCH_SIZE=64

# XDP Mode
AF_XDP_MODE=native  # native, skb, or offload
```

#### Python Example (requires xdp-tools)
```python
from services.af_xdp_collector import AFXDPCollector

collector = AFXDPCollector(
    interface="eth0",
    zero_copy=True,
    queue_size=4096,
    mode="native"
)
collector.start()
```

**Max Rate**: 40-100 Gbps (with zero-copy)
**Performance**: 
- Lowest latency (<1 μs)
- Highest throughput with supported NICs
- Minimal CPU overhead

**Advantages**:
- Best performance for high-speed networks
- Programmable packet filtering at NIC level
- Future-proof technology

**Requirements**:
- Linux kernel 4.18+ (5.x recommended)
- Compatible NIC with XDP support (Intel i40e, ixgbe, mlx5)
- root/CAP_NET_RAW and CAP_BPF privileges

### 7. Netmap

**Status**: ⚠️ Deprecated | **Supported For**: FreeBSD only

Netmap is a high-performance packet I/O framework for BSD systems.

#### Features
- Direct NIC access without kernel stack
- Zero-copy buffer sharing
- Cross-platform (originally for FreeBSD)

#### Configuration (FreeBSD only)
```bash
# Load Netmap kernel module
kldload netmap

# Environment Variables
NETMAP_ENABLED=true
NETMAP_INTERFACE=ix0
NETMAP_RING_SIZE=2048
```

**Max Rate**: 10-40 Gbps
**Performance**: Similar to AF_PACKET on FreeBSD

**Status**: 
- ⚠️ Deprecated for Linux (use AF_PACKET or AF_XDP instead)
- Still supported for FreeBSD deployments
- No active development for this platform

**Note**: We recommend migrating to AF_PACKET or AF_XDP on Linux for better support and performance.

### 8. PF_RING / PF_RING ZC

**Status**: ⚠️ Deprecated | **Supported For**: CentOS 6 (version 1.2.0 only)

PF_RING is ntop's packet capture acceleration technology.

#### Features
- Kernel module for accelerated capture
- Zero-copy mode (ZC) with special NICs
- DNA (Direct NIC Access) support

#### Configuration (CentOS 6 only)
```bash
# Install PF_RING module
yum install pfring-dkms

# Environment Variables
PFRING_ENABLED=true
PFRING_INTERFACE=eth0
PFRING_CLUSTER_ID=99
PFRING_ZC_ENABLED=false
```

**Max Rate**: 
- PF_RING: 10 Gbps
- PF_RING ZC: 40+ Gbps

**Status**: 
- ⚠️ Deprecated - only available in version 1.2.0 for CentOS 6
- Not supported in current versions (2.x+)
- CentOS 6 reached EOL in 2020
- Requires proprietary drivers

**Recommendation**: 
- Migrate to AF_PACKET (Linux 7+) or AF_XDP (Linux 8+)
- Use NetFlow/IPFIX for scalability to terabits

## Packet Capture Engine Comparison Table

| Feature | NetFlow | IPFIX | sFlow | PCAP | AF_PACKET | AF_XDP | Netmap | PF_RING |
|---------|---------|-------|-------|------|-----------|--------|--------|---------|
| **Status** | ✅ Stable | ✅ Stable | ✅ Stable | ⚠️ High Overhead | ✅ Recommended | ✅ Advanced | ⚠️ Deprecated | ⚠️ Deprecated |
| **Max Throughput** | Terabits | Terabits | Terabits | 10 Gbps | 40 Gbps | 100+ Gbps | 40 Gbps | 40 Gbps |
| **CPU Overhead** | Very Low | Very Low | Very Low | High | Low | Very Low | Low | Low |
| **Memory Usage** | Low | Low | Low | Very High | Medium | Low | Medium | Medium |
| **Latency** | 1-5 sec | 1-5 sec | <1 sec | <1 ms | <10 ms | <1 μs | <10 ms | <10 ms |
| **Platform** | Any | Any | Any | Any | Linux | Linux 4.18+ | FreeBSD | CentOS 6 |
| **Zero-Copy** | N/A | N/A | N/A | No | Yes | Yes | Yes | Yes |
| **VLAN Untag** | Yes | Yes | Yes | Manual | Yes | Yes | Yes | Yes |
| **Multi-Core** | N/A | N/A | N/A | No | Yes (Fanout) | Yes | Yes | Yes |
| **Layer 7** | No | No | No | Yes | Yes | Yes | Yes | Yes |
| **Setup Difficulty** | Easy | Easy | Easy | Easy | Medium | Hard | Medium | Hard |
| **NIC Requirements** | Standard | Standard | Standard | Standard | Standard | XDP-capable | Standard | PF_RING |
| **Kernel Module** | No | No | No | No | No | Optional | Yes | Yes |
| **Best Use Case** | Scale to terabits | Multi-vendor | Switches | Forensics | **General purpose** | **Ultra high-speed** | FreeBSD | Legacy only |

### Recommendation Matrix

| Network Speed | Recommended Engine | Alternative |
|---------------|-------------------|-------------|
| < 1 Gbps | PCAP, NetFlow | AF_PACKET |
| 1-10 Gbps | NetFlow, IPFIX, sFlow | AF_PACKET |
| 10-40 Gbps | **AF_PACKET (Recommended)** | NetFlow/IPFIX |
| 40-100 Gbps | **AF_XDP**, NetFlow/IPFIX | - |
| 100+ Gbps (Terabits) | **NetFlow/IPFIX** (with sampling) | - |

### Platform-Specific Recommendations

| Platform | Primary Choice | Secondary Choice |
|----------|---------------|------------------|
| Linux (Modern) | AF_PACKET | AF_XDP |
| Linux (High-Speed) | AF_XDP | NetFlow/IPFIX |
| FreeBSD | Netmap | NetFlow/IPFIX |
| Any OS (ISP Scale) | NetFlow/IPFIX | sFlow |
| Small Networks | PCAP | AF_PACKET |
| Legacy CentOS 6 | PF_RING (1.2.0 only) | Upgrade OS! |

## Detection Performance by Engine

All engines support detection in **1-2 seconds**:

| Engine | Detection Latency | Notes |
|--------|------------------|-------|
| NetFlow v5/v9 | 1-5 seconds | Depends on active timeout |
| IPFIX | 1-5 seconds | Depends on template export rate |
| sFlow | <1 second | Real-time sampling |
| PCAP | <100 ms | Immediate packet analysis |
| AF_PACKET | <500 ms | Near real-time |
| AF_XDP | <100 ms | Ultra-low latency |
| Netmap | <500 ms | Near real-time |
| PF_RING | <500 ms | Near real-time |

**All engines meet the requirement of detecting DoS/DDoS in 1-2 seconds.**

## Advanced Features

### VLAN Untagging

VLAN untagging is supported in mirror and sFlow modes with these engines:

- ✅ AF_PACKET (native support)
- ✅ AF_XDP (via XDP programs)
- ✅ sFlow (automatic in collector)
- ✅ PCAP (manual/BPF filters)

**Configuration**:
```bash
# AF_PACKET VLAN Untagging
AF_PACKET_VLAN_UNTAG=true
AF_PACKET_VLAN_IDS=100,200,300  # Optional: specific VLANs

# sFlow VLAN Untagging
SFLOW_VLAN_UNTAG=true
```

### Attack Fingerprint Capture

Capture full packet captures of detected attacks for forensic analysis:

**Engines**: PCAP, AF_PACKET, AF_XDP

**Configuration**:
```bash
# Enable attack fingerprint capture
PCAP_CAPTURE_ATTACKS=true
PCAP_STORAGE_PATH=/var/log/ddos/fingerprints
PCAP_MAX_SIZE=100MB  # Per attack
PCAP_MAX_DURATION=300  # Seconds
PCAP_RETENTION_DAYS=30

# Trigger conditions
PCAP_TRIGGER_ON_ALERT=true
PCAP_MIN_PPS=10000  # Minimum packets/sec to trigger
```

**Example**:
```python
from services.pcap_fingerprint import PCAPFingerprint

# Automatically triggered on alerts
fingerprint = PCAPFingerprint()
fingerprint.capture_attack(
    alert_id=123,
    target_ip="203.0.113.50",
    duration=60
)

# Output: /var/log/ddos/fingerprints/alert-123-20260201-150830.pcap
```

### Multi-Queue and Multi-Core Scaling

For high-performance deployments:

**AF_PACKET Fanout Mode**:
```bash
AF_PACKET_FANOUT=true
AF_PACKET_FANOUT_TYPE=hash  # Distribute by flow hash
AF_PACKET_WORKERS=4  # Number of worker threads
```

**AF_XDP Multi-Queue**:
```bash
AF_XDP_QUEUES=0,1,2,3  # Bind to specific RX queues
AF_XDP_WORKERS=4
```

## Integration with Other Components

### Redis Integration
All packet capture engines publish flow data to Redis streams:
- Stream: `traffic:stream`
- Pub/Sub: `traffic:events`
- Real-time counters for attack detection

### Database Storage
Flow records stored in PostgreSQL:
- Table: `traffic_flows`
- Retention: Configurable (default 30 days)
- Indexes: source_ip, dest_ip, timestamp

### Attack Detection
All engines feed into the same anomaly detection system:
- SYN flood detection
- UDP flood detection
- Entropy analysis
- DNS amplification detection

## Troubleshooting

### Common Issues

#### No packets captured
```bash
# Check interface is up
ip link show eth0

# Check permissions
sudo setcap cap_net_raw+ep /path/to/python

# Test with tcpdump
sudo tcpdump -i eth0 -c 10
```

#### High CPU usage
```bash
# Enable hardware offload
ethtool -K eth0 gro on lro on

# Increase ring buffer
ethtool -G eth0 rx 4096 tx 4096

# Use AF_PACKET fanout mode
AF_PACKET_FANOUT=true
```

#### Dropped packets
```bash
# Check statistics
netstat -i
cat /proc/net/dev

# Increase ring buffer sizes
AF_PACKET_RING_SIZE=4096
AF_XDP_QUEUE_SIZE=8192
```

## Migration Guide

### From PF_RING to AF_PACKET

**Step 1**: Update configuration
```bash
# Old (PF_RING)
PFRING_ENABLED=true
PFRING_INTERFACE=eth0

# New (AF_PACKET)
AF_PACKET_ENABLED=true
AF_PACKET_INTERFACE=eth0
AF_PACKET_FANOUT=true
```

**Step 2**: Install dependencies
```bash
# Remove PF_RING
yum remove pfring-dkms

# No additional packages needed for AF_PACKET
# Native Linux kernel support
```

**Step 3**: Test and verify
```bash
# Start collector
python backend/services/af_packet_collector.py

# Monitor performance
watch -n 1 'cat /proc/net/dev'
```

### From PCAP to AF_PACKET

Straightforward migration with better performance:
```bash
# Update environment variables
PCAP_ENABLED=false
AF_PACKET_ENABLED=true
```

## Performance Tuning

### Network Interface Configuration

```bash
# Increase ring buffer sizes
ethtool -G eth0 rx 4096 tx 4096

# Enable hardware offload
ethtool -K eth0 gro on lro on tso on

# Disable interrupt coalescing for low latency
ethtool -C eth0 rx-usecs 0 tx-usecs 0

# Enable multi-queue
ethtool -L eth0 combined 4
```

### System Tuning

```bash
# Increase socket buffer sizes
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# Increase netdev backlog
sysctl -w net.core.netdev_max_backlog=50000

# Enable RPS (Receive Packet Steering)
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus
```

## Security Considerations

1. **Permissions**: Packet capture requires root or CAP_NET_RAW
2. **Network Isolation**: Deploy collectors in isolated networks
3. **Storage**: Encrypt captured PCAPs at rest
4. **Retention**: Configure appropriate data retention policies
5. **Access Control**: Restrict access to PCAP files

## References

- [NetFlow v9 RFC 3954](https://www.rfc-editor.org/rfc/rfc3954)
- [IPFIX RFC 5101](https://www.rfc-editor.org/rfc/rfc5101)
- [sFlow v5 Specification](https://sflow.org/sflow_version_5.txt)
- [AF_PACKET Documentation](https://man7.org/linux/man-pages/man7/packet.7.html)
- [AF_XDP Documentation](https://www.kernel.org/doc/html/latest/networking/af_xdp.html)
- [Netmap Paper](https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo)

## Support

For questions or issues with packet capture engines:
- GitHub Issues: https://github.com/i4edubd/ddos-potection/issues
- Documentation: https://github.com/i4edubd/ddos-potection/tree/main/docs
