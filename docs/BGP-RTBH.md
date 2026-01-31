# BGP Blackholing (RTBH) - Setup and Usage Guide

## Overview

BGP Blackholing, also known as Remotely Triggered Black Hole (RTBH), is a DDoS mitigation technique that allows you to drop traffic destined for a specific IP address or network at your upstream provider's edge routers, before it reaches your network and consumes bandwidth.

### How RTBH Works

1. **Detection**: The DDoS Protection Platform detects an attack targeting a specific IP
2. **Trigger**: A BGP announcement is made with the victim IP and a special "blackhole" community tag
3. **Propagation**: Your upstream ISP receives the BGP route with the blackhole community
4. **Mitigation**: The ISP drops all traffic destined to that IP at their edge, saving your bandwidth

### Benefits

- **Bandwidth Protection**: Stops attack traffic before it enters your network
- **Fast Mitigation**: Near-instant response once BGP converges (typically 1-5 seconds)
- **Automated**: Can be triggered automatically by detection systems
- **Cost-Effective**: No special hardware required, uses standard BGP

### Standard Blackhole Community

The well-known blackhole community is **65535:666** (RFC 7999), though some ISPs use custom communities.

## Prerequisites

Before setting up RTBH, you need:

1. **BGP Session with Upstream ISP**
   - Established BGP peering with your transit provider
   - Permission to announce routes with blackhole community
   - Confirmed blackhole community tag (usually 65535:666 or ISP-specific)

2. **BGP Daemon**
   - One of: ExaBGP, BIRD, FRR (Free Range Routing), or Quagga
   - Recommended: ExaBGP (easiest to integrate) or FRR (most feature-rich)

3. **AS Number and IP Space**
   - Your own Autonomous System Number (ASN)
   - IPv4/IPv6 address space you're authorized to announce

4. **DDoS Protection Platform**
   - This platform already installed and running
   - API access to create mitigation actions

## Installation Options

### Option 1: ExaBGP (Recommended for Automation)

ExaBGP is a Python-based BGP daemon designed for BGP automation and is easiest to integrate with this platform.

#### Install ExaBGP

```bash
# Install via pip
sudo apt update
sudo apt install python3-pip -y
pip3 install exabgp

# Verify installation
exabgp --version
```

#### Configure ExaBGP

Create `/etc/exabgp/exabgp.conf`:

```ini
# ExaBGP configuration for RTBH
process announce-routes {
    run /usr/local/bin/exabgp-rtbh.sh;
    encoder json;
}

neighbor 198.51.100.1 {
    # Your upstream ISP's BGP router IP
    router-id 203.0.113.1;  # Your router IP
    local-address 203.0.113.1;
    local-as 64512;  # Your ASN
    peer-as 64496;   # ISP's ASN
    
    # Capabilities
    capability {
        graceful-restart;
        add-path send/receive;
    }
    
    # Static routes for RTBH
    # Announced routes will use next-hop 192.0.2.1 (blackhole)
    static {
        # Routes will be dynamically announced via API
    }
    
    # Blackhole community
    api {
        processes [announce-routes];
    }
}
```

#### Create ExaBGP Helper Script

Create `/usr/local/bin/exabgp-rtbh.sh`:

```bash
#!/bin/bash
# ExaBGP RTBH helper script
# This script reads commands from the DDoS platform and sends to ExaBGP

# Named pipe for commands
COMMAND_PIPE="/var/run/exabgp.cmd"

# Create named pipe if it doesn't exist
if [ ! -p "$COMMAND_PIPE" ]; then
    mkfifo "$COMMAND_PIPE"
fi

# Read commands and forward to ExaBGP
while true; do
    if read line < "$COMMAND_PIPE"; then
        echo "$line"
    fi
done
```

Make it executable:

```bash
sudo chmod +x /usr/local/bin/exabgp-rtbh.sh
```

#### Create ExaBGP Systemd Service

Create `/etc/systemd/system/exabgp.service`:

```ini
[Unit]
Description=ExaBGP BGP daemon
After=network.target

[Service]
Type=simple
User=exabgp
Group=exabgp
Environment="exabgp.daemon.user=exabgp"
Environment="exabgp.log.destination=/var/log/exabgp.log"
ExecStart=/usr/local/bin/exabgp /etc/exabgp/exabgp.conf
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Start ExaBGP

```bash
# Create exabgp user
sudo useradd -r -s /bin/false exabgp

# Create command pipe directory
sudo mkdir -p /var/run/exabgp
sudo chown exabgp:exabgp /var/run/exabgp

# Create named pipe
sudo mkfifo /var/run/exabgp.cmd
sudo chown exabgp:exabgp /var/run/exabgp.cmd

# Set permissions for DDoS platform to write to pipe
sudo usermod -aG exabgp ddos  # Assuming 'ddos' is your platform user

# Start and enable ExaBGP
sudo systemctl daemon-reload
sudo systemctl start exabgp
sudo systemctl enable exabgp

# Check status
sudo systemctl status exabgp

# View logs
sudo journalctl -u exabgp -f
```

### Option 2: FRR (Free Range Routing)

FRR is a complete routing stack with full BGP support, ideal for production environments.

#### Install FRR

```bash
# Add FRR repository (Ubuntu/Debian)
curl -s https://deb.frrouting.org/frr/keys.asc | sudo apt-key add -
echo "deb https://deb.frrouting.org/frr $(lsb_release -s -c) frr-stable" | \
    sudo tee /etc/apt/sources.list.d/frr.list

sudo apt update
sudo apt install frr frr-pythontools -y
```

#### Configure FRR

Edit `/etc/frr/daemons` to enable BGP:

```bash
bgpd=yes
```

Create `/etc/frr/frr.conf`:

```
frr version 8.0
frr defaults traditional
hostname ddos-platform
log syslog informational

# BGP configuration
router bgp 64512
 bgp router-id 203.0.113.1
 
 # Neighbor configuration
 neighbor 198.51.100.1 remote-as 64496
 neighbor 198.51.100.1 description Upstream ISP
 
 # IPv4 Unicast
 address-family ipv4 unicast
  # Announce connected networks
  network 203.0.113.0/24
  
  # Set blackhole community on tagged routes
  neighbor 198.51.100.1 send-community
  neighbor 198.51.100.1 route-map BLACKHOLE-OUT out
 exit-address-family

# Route map for RTBH
route-map BLACKHOLE-OUT permit 10
 match tag 666
 set community 65535:666 additive
 set ip next-hop 192.0.2.1

route-map BLACKHOLE-OUT permit 20

# Static blackhole routes (managed dynamically)
# Use 'ip route <prefix> Null0 tag 666' to trigger RTBH
!
```

#### Start FRR

```bash
sudo systemctl restart frr
sudo systemctl enable frr

# Check BGP status
sudo vtysh -c "show ip bgp summary"
```

### Option 3: BIRD (BIRD Internet Routing Daemon)

BIRD is a lightweight, high-performance routing daemon.

#### Install BIRD

```bash
sudo apt install bird2 -y
```

#### Configure BIRD

Edit `/etc/bird/bird.conf`:

```
# BIRD configuration for RTBH

log syslog all;
router id 203.0.113.1;

# Define blackhole route
protocol static blackhole_routes {
    ipv4;
    # Routes will be added dynamically
    # route 192.0.2.0/24 blackhole;
}

# BGP protocol
protocol bgp upstream_isp {
    local as 64512;
    neighbor 198.51.100.1 as 64496;
    
    ipv4 {
        import none;
        export where proto = "blackhole_routes";
    };
    
    # Add blackhole community to exported routes
    bgp_community.add((65535, 666));
    
    # Set next-hop to blackhole
    bgp_next_hop = 192.0.2.1;
}

# Device protocol (required)
protocol device {
    scan time 10;
}

# Kernel protocol
protocol kernel {
    ipv4 {
        export all;
    };
}
```

#### Start BIRD

```bash
sudo systemctl restart bird
sudo systemctl enable bird

# Check status
sudo birdc show protocols all
```

## Integration with DDoS Protection Platform

### Configure Platform Backend

Update `backend/config.py` to add BGP configuration:

```python
# BGP Configuration
BGP_ENABLED = os.getenv("BGP_ENABLED", "false").lower() == "true"
BGP_DAEMON = os.getenv("BGP_DAEMON", "exabgp")  # exabgp, frr, bird
BGP_BLACKHOLE_NEXTHOP = os.getenv("BGP_BLACKHOLE_NEXTHOP", "192.0.2.1")
BGP_BLACKHOLE_COMMUNITY = os.getenv("BGP_BLACKHOLE_COMMUNITY", "65535:666")

# ExaBGP specific
EXABGP_CMD_PIPE = os.getenv("EXABGP_CMD_PIPE", "/var/run/exabgp.cmd")

# FRR specific  
FRR_VTYSH_CMD = os.getenv("FRR_VTYSH_CMD", "/usr/bin/vtysh")

# BIRD specific
BIRD_CONTROL_SOCKET = os.getenv("BIRD_CONTROL_SOCKET", "/var/run/bird/bird.ctl")
```

Update `backend/.env`:

```bash
# BGP Blackholing Configuration
BGP_ENABLED=true
BGP_DAEMON=exabgp
BGP_BLACKHOLE_NEXTHOP=192.0.2.1
BGP_BLACKHOLE_COMMUNITY=65535:666
EXABGP_CMD_PIPE=/var/run/exabgp.cmd
```

### Enhance Mitigation Service

The platform already has a basic `announce_bgp_blackhole` method. Let's enhance it:

Update `backend/services/mitigation_service.py`:

```python
def announce_bgp_blackhole(self, prefix: str, nexthop: str = None) -> bool:
    """Announce BGP blackhole route (RTBH)"""
    from config import settings
    
    nexthop = nexthop or settings.BGP_BLACKHOLE_NEXTHOP
    
    try:
        if settings.BGP_DAEMON == "exabgp":
            return self._announce_exabgp(prefix, nexthop)
        elif settings.BGP_DAEMON == "frr":
            return self._announce_frr(prefix, nexthop)
        elif settings.BGP_DAEMON == "bird":
            return self._announce_bird(prefix, nexthop)
        else:
            print(f"Unknown BGP daemon: {settings.BGP_DAEMON}")
            return False
    except Exception as e:
        print(f"Error announcing BGP blackhole: {e}")
        return False

def _announce_exabgp(self, prefix: str, nexthop: str) -> bool:
    """Announce via ExaBGP"""
    from config import settings
    
    cmd_pipe = settings.EXABGP_CMD_PIPE
    community = settings.BGP_BLACKHOLE_COMMUNITY
    
    with open(cmd_pipe, 'a') as f:
        f.write(f'announce route {prefix} next-hop {nexthop} community [{community}]\n')
    
    print(f"BGP blackhole announced via ExaBGP: {prefix} -> {nexthop}")
    return True

def _announce_frr(self, prefix: str, nexthop: str) -> bool:
    """Announce via FRR"""
    from config import settings
    import subprocess
    
    # Add static route with tag 666 (matches route-map)
    cmd = [
        settings.FRR_VTYSH_CMD,
        '-c', 'configure terminal',
        '-c', f'ip route {prefix} Null0 tag 666'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"BGP blackhole announced via FRR: {prefix}")
        return True
    else:
        print(f"FRR error: {result.stderr}")
        return False

def _announce_bird(self, prefix: str, nexthop: str) -> bool:
    """Announce via BIRD"""
    from config import settings
    import subprocess
    
    # Validate prefix format
    if not self._validate_prefix(prefix):
        print(f"BIRD error: Invalid prefix format: {prefix}")
        return False
    
    # Add route dynamically using birdc
    # Safe command construction without shell=True
    cmd = ['birdc', '-r', 'add', 'route', prefix, 'blackhole']
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0 or 'already exists' in result.stdout.lower():
        print(f"BGP blackhole announced via BIRD: {prefix}")
        return True
    else:
        print(f"BIRD error: {result.stderr}")
        return False

def withdraw_bgp_blackhole(self, prefix: str) -> bool:
    """Withdraw BGP blackhole route"""
    from config import settings
    
    try:
        if settings.BGP_DAEMON == "exabgp":
            return self._withdraw_exabgp(prefix)
        elif settings.BGP_DAEMON == "frr":
            return self._withdraw_frr(prefix)
        elif settings.BGP_DAEMON == "bird":
            return self._withdraw_bird(prefix)
        else:
            return False
    except Exception as e:
        print(f"Error withdrawing BGP blackhole: {e}")
        return False

def _withdraw_exabgp(self, prefix: str) -> bool:
    """Withdraw via ExaBGP"""
    from config import settings
    
    with open(settings.EXABGP_CMD_PIPE, 'a') as f:
        f.write(f'withdraw route {prefix}\n')
    
    print(f"BGP blackhole withdrawn via ExaBGP: {prefix}")
    return True

def _withdraw_frr(self, prefix: str) -> bool:
    """Withdraw via FRR"""
    from config import settings
    import subprocess
    
    cmd = [
        settings.FRR_VTYSH_CMD,
        '-c', 'configure terminal',
        '-c', f'no ip route {prefix} Null0 tag 666'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def _withdraw_bird(self, prefix: str) -> bool:
    """Withdraw via BIRD"""
    import subprocess
    
    # Reload BIRD configuration (routes removed from config)
    cmd = ['birdc', 'configure']
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

## Usage Examples

### Via API

#### Trigger RTBH Manually

```bash
# Create mitigation action
curl -X POST http://localhost:8000/api/v1/mitigations/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": 123,
    "action_type": "bgp_blackhole",
    "details": {
      "prefix": "203.0.113.50/32",
      "reason": "DDoS attack - SYN flood"
    }
  }'

# Execute the mitigation
curl -X POST http://localhost:8000/api/v1/mitigations/1/execute \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Withdraw RTBH

```bash
# Stop mitigation (withdraws BGP route)
curl -X POST http://localhost:8000/api/v1/mitigations/1/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Via Python Script

```python
import requests

API_URL = "http://localhost:8000/api/v1"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Trigger RTBH for IP under attack
def trigger_rtbh(ip_address: str, alert_id: int):
    # Create mitigation
    response = requests.post(
        f"{API_URL}/mitigations/",
        headers=headers,
        json={
            "alert_id": alert_id,
            "action_type": "bgp_blackhole",
            "details": {
                "prefix": f"{ip_address}/32",
                "reason": "DDoS attack detected"
            }
        }
    )
    
    if response.status_code == 200:
        mitigation_id = response.json()["id"]
        
        # Execute mitigation
        exec_response = requests.post(
            f"{API_URL}/mitigations/{mitigation_id}/execute",
            headers=headers
        )
        
        print(f"RTBH triggered for {ip_address}: {exec_response.json()}")
        return mitigation_id
    else:
        print(f"Error: {response.text}")
        return None

# Withdraw RTBH
def withdraw_rtbh(mitigation_id: int):
    response = requests.post(
        f"{API_URL}/mitigations/{mitigation_id}/stop",
        headers=headers
    )
    print(f"RTBH withdrawn: {response.json()}")

# Example usage
alert_id = 123
ip_under_attack = "203.0.113.50"

# Trigger blackhole
mitigation_id = trigger_rtbh(ip_under_attack, alert_id)

# Later, withdraw after attack subsides
# withdraw_rtbh(mitigation_id)
```

### Automatic Mitigation

Configure automatic RTBH in detection service (`backend/services/detector_service.py`):

```python
def handle_attack_detection(self, alert_id: int, source_ip: str, attack_type: str):
    """Automatically trigger RTBH for high-severity attacks"""
    from services.mitigation_service import MitigationService
    
    # Trigger RTBH for severe attacks
    if attack_type in ['syn_flood', 'udp_flood'] and self.is_severe_attack():
        mitigation = MitigationService()
        prefix = f"{source_ip}/32"
        
        success = mitigation.announce_bgp_blackhole(prefix)
        
        if success:
            # Log mitigation to database
            self.log_mitigation(alert_id, 'bgp_blackhole', prefix)
            print(f"Automatic RTBH triggered for {source_ip}")
```

## Verification and Testing

### Test BGP Session

```bash
# ExaBGP
tail -f /var/log/exabgp.log | grep "peer.*up"

# FRR
sudo vtysh -c "show ip bgp summary"
sudo vtysh -c "show ip bgp neighbors 198.51.100.1"

# BIRD
sudo birdc show protocols all upstream_isp
```

### Test Route Announcement

#### ExaBGP Test

```bash
# Manually announce test route
echo "announce route 192.0.2.100/32 next-hop 192.0.2.1 community [65535:666]" > /var/run/exabgp.cmd

# Verify in logs
tail -f /var/log/exabgp.log
```

#### FRR Test

```bash
# Add test static route
sudo vtysh
configure terminal
ip route 192.0.2.100/32 Null0 tag 666
exit
exit

# Verify announcement
sudo vtysh -c "show ip bgp 192.0.2.100/32"
```

#### BIRD Test

```bash
# Add test route to config
sudo bash -c 'cat >> /etc/bird/bird.conf << EOF
protocol static blackhole_test {
    ipv4;
    route 192.0.2.100/32 blackhole;
}
EOF'

# Reload
sudo birdc configure

# Check
sudo birdc show route all 192.0.2.100/32
```

### Verify at Upstream ISP

Contact your ISP to confirm:
1. They received the BGP announcement
2. The blackhole community is being honored
3. Traffic is being dropped at their edge

## Best Practices

### 1. Use /32 Prefixes for Single IPs

```python
# Good: Blackhole single IP
mitigation.announce_bgp_blackhole("203.0.113.50/32")

# Careful: Blackhole entire subnet
mitigation.announce_bgp_blackhole("203.0.113.0/24")
```

### 2. Set Reasonable TTL

Automatically withdraw blackholes after attack subsides:

```python
import time
from datetime import datetime, timedelta

def temporary_blackhole(ip: str, duration_minutes: int = 30):
    prefix = f"{ip}/32"
    mitigation = MitigationService()
    
    # Announce
    mitigation.announce_bgp_blackhole(prefix)
    print(f"Blackhole active for {duration_minutes} minutes")
    
    # Wait
    time.sleep(duration_minutes * 60)
    
    # Withdraw
    mitigation.withdraw_bgp_blackhole(prefix)
    print(f"Blackhole withdrawn for {ip}")
```

### 3. Monitor Blackholed IPs

Keep track of all active blackholes:

```bash
# List active BGP blackhole mitigations
curl -X GET "http://localhost:8000/api/v1/mitigations/?action_type=bgp_blackhole&status=active" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Coordinate with ISP

- Confirm blackhole community with your ISP
- Test during maintenance window
- Document ISP contact for BGP issues
- Set up alerts for BGP session down

### 5. Use Graceful Restart

Enable BGP graceful restart to maintain routes during daemon restarts:

```
# FRR
router bgp 64512
 bgp graceful-restart

# ExaBGP
capability {
    graceful-restart;
}
```

## Troubleshooting

### BGP Session Not Establishing

```bash
# Check BGP daemon is running
sudo systemctl status exabgp  # or frr, or bird

# Check network connectivity
ping 198.51.100.1  # Your ISP's BGP router

# Check firewall (BGP uses TCP port 179)
sudo ufw allow 179/tcp
sudo iptables -L | grep 179

# Check logs
sudo journalctl -u exabgp -f
sudo journalctl -u frr -f
```

### Routes Not Being Announced

```bash
# ExaBGP: Check command pipe
ls -la /var/run/exabgp.cmd
sudo tail -f /var/log/exabgp.log

# FRR: Check route table
sudo vtysh -c "show ip route"
sudo vtysh -c "show ip bgp"

# BIRD: Check protocols
sudo birdc show protocols
sudo birdc show route all
```

### Blackhole Not Working at ISP

Contact your ISP to verify:
1. **Community tag**: Confirm they're using 65535:666 or provide their custom community
2. **Next-hop**: Some ISPs want 192.0.2.1, others use their own
3. **Prefix length**: Some ISPs only accept /32 or specific ranges
4. **Authorization**: Ensure you're authorized to use RTBH

### Permission Errors

```bash
# Give platform permission to write to ExaBGP pipe
sudo usermod -aG exabgp ddos
sudo chmod 660 /var/run/exabgp.cmd

# For FRR/BIRD, may need sudo access
# Add to /etc/sudoers.d/ddos-platform:
ddos ALL=(ALL) NOPASSWD: /usr/bin/vtysh
ddos ALL=(ALL) NOPASSWD: /usr/bin/birdc
```

### Routes Stuck/Not Withdrawing

```bash
# ExaBGP: Clear all routes
echo "withdraw route 0.0.0.0/0" > /var/run/exabgp.cmd

# FRR: Remove static routes
sudo vtysh
configure terminal
no ip route 192.0.2.100/32 Null0 tag 666
exit

# BIRD: Reload clean config
sudo birdc configure
```

## Advanced Scenarios

### IPv6 RTBH

```python
# Blackhole IPv6 address
mitigation.announce_bgp_blackhole("2001:db8::1/128")
```

ExaBGP config for IPv6:

```ini
neighbor 2001:db8::1 {
    router-id 203.0.113.1;
    local-address 2001:db8::2;
    local-as 64512;
    peer-as 64496;
    
    family {
        ipv6 unicast;
    }
}
```

### Multiple Upstream Providers

Configure multiple BGP sessions for redundancy:

```ini
# ExaBGP with two upstream ISPs
neighbor 198.51.100.1 {  # ISP 1
    router-id 203.0.113.1;
    local-as 64512;
    peer-as 64496;
}

neighbor 198.51.100.129 {  # ISP 2
    router-id 203.0.113.1;
    local-as 64512;
    peer-as 64497;
}
```

### Blackhole Specific Ports/Protocols

For more granular control, use FlowSpec instead of RTBH:

```python
# Block only SYN packets to port 80
mitigation.send_flowspec_rule(
    source="0.0.0.0/0",
    dest="203.0.113.50/32",
    protocol="tcp",
    dest_port=80,
    tcp_flags="syn",
    action="drop"
)
```

## Security Considerations

### 1. Access Control

Restrict who can trigger RTBH:

```python
# Only admins and operators can execute blackholes
if current_user.role not in ["admin", "operator"]:
    raise HTTPException(status_code=403, detail="Insufficient permissions")
```

### 2. Audit Logging

Log all RTBH actions:

```python
def announce_bgp_blackhole(self, prefix: str, nexthop: str = None) -> bool:
    # Log to audit trail
    audit_log = AuditLog(
        action="bgp_blackhole_announce",
        user_id=current_user.id,
        details={"prefix": prefix, "nexthop": nexthop},
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    # Proceed with announcement
    # ...
```

### 3. Rate Limiting

Prevent abuse with rate limits:

```python
from datetime import datetime, timedelta

def check_rate_limit(user_id: int, max_per_hour: int = 10):
    recent = db.query(MitigationAction).filter(
        MitigationAction.created_by == user_id,
        MitigationAction.created_at > datetime.utcnow() - timedelta(hours=1),
        MitigationAction.action_type == "bgp_blackhole"
    ).count()
    
    if recent >= max_per_hour:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### 4. Prefix Validation

Only allow blackholing of your own IPs:

```python
def validate_prefix_ownership(prefix: str, isp_id: int) -> bool:
    """Verify ISP owns the prefix"""
    isp = db.query(ISP).filter(ISP.id == isp_id).first()
    owned_prefixes = isp.ip_ranges  # List of owned IP ranges
    
    # Check if prefix is within owned ranges
    # ... implementation
    return True  # or False
```

## References

- **RFC 7999**: BLACKHOLE Community ([https://datatracker.ietf.org/doc/html/rfc7999](https://datatracker.ietf.org/doc/html/rfc7999))
- **RFC 5635**: Remote Triggered Black Hole Filtering with uRPF ([https://datatracker.ietf.org/doc/html/rfc5635](https://datatracker.ietf.org/doc/html/rfc5635))
- **ExaBGP Documentation**: [https://github.com/Exa-Networks/exabgp](https://github.com/Exa-Networks/exabgp)
- **FRR Documentation**: [https://docs.frrouting.org/](https://docs.frrouting.org/)
- **BIRD Documentation**: [https://bird.network.cz/](https://bird.network.cz/)

## Support

For help with BGP blackholing:
- Check logs: `sudo journalctl -u exabgp -f`
- Platform logs: `docker-compose logs -f backend`
- GitHub Issues: [https://github.com/i4edubd/ddos-protection/issues](https://github.com/i4edubd/ddos-protection/issues)
- Contact your ISP's NOC for BGP-specific issues
