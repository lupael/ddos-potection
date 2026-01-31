"""
Mitigation automation service
"""
import subprocess
import re
from datetime import datetime

from database import SessionLocal
from models.models import MitigationAction, Alert
from config import settings

def validate_prefix(prefix: str) -> bool:
    """Validate that prefix is a valid IPv4 or IPv6 CIDR notation
    
    Args:
        prefix: IP prefix in CIDR notation (e.g., "192.0.2.1/32")
    
    Returns:
        True if valid, False otherwise
    """
    # IPv4 CIDR pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
    # IPv6 CIDR pattern
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}/\d{1,3}$'
    
    if re.match(ipv4_pattern, prefix):
        # Validate IPv4 octets and prefix length
        parts = prefix.split('/')
        octets = parts[0].split('.')
        prefix_len = int(parts[1])
        
        if all(0 <= int(octet) <= 255 for octet in octets) and 0 <= prefix_len <= 32:
            return True
    elif re.match(ipv6_pattern, prefix):
        # Basic IPv6 validation (prefix length)
        parts = prefix.split('/')
        prefix_len = int(parts[1])
        return 0 <= prefix_len <= 128
    
    return False

class MitigationService:
    def __init__(self):
        pass
    
    def apply_iptables_rule(self, action: str, ip: str, protocol: str = None) -> bool:
        """Apply iptables firewall rule"""
        try:
            if action == "block":
                cmd = ["iptables", "-A", "INPUT"]
                if protocol:
                    cmd.extend(["-p", protocol.lower()])
                cmd.extend(["-s", ip, "-j", "DROP"])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            
            elif action == "unblock":
                cmd = ["iptables", "-D", "INPUT"]
                if protocol:
                    cmd.extend(["-p", protocol.lower()])
                cmd.extend(["-s", ip, "-j", "DROP"])
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
                
        except Exception as e:
            print(f"Error applying iptables rule: {e}")
            return False
            return False
    
    def apply_nftables_rule(self, action: str, ip: str) -> bool:
        """Apply nftables firewall rule"""
        try:
            if action == "block":
                cmd = ["nft", "add", "rule", "inet", "filter", "input", "ip", "saddr", ip, "drop"]
            else:
                cmd = ["nft", "delete", "rule", "inet", "filter", "input", "ip", "saddr", ip, "drop"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error applying nftables rule: {e}")
            return False
    
    def mikrotik_block_ip(self, router_ip: str, username: str, password: str, 
                          target_ip: str, comment: str = "") -> bool:
        """Block IP via MikroTik RouterOS API"""
        try:
            # Using MikroTik REST API or RouterOS API
            # This is a simplified example
            from routeros_api import RouterOsApiPool
            
            connection = RouterOsApiPool(
                router_ip,
                username=username,
                password=password,
                plaintext_login=True
            )
            
            api = connection.get_api()
            
            # Add firewall rule
            firewall = api.get_resource('/ip/firewall/filter')
            firewall.add(
                chain='input',
                action='drop',
                src_address=target_ip,
                comment=comment or f'DDoS mitigation - {datetime.now()}'
            )
            
            connection.disconnect()
            return True
            
        except Exception as e:
            print(f"Error blocking IP on MikroTik: {e}")
            return False
    
    def announce_bgp_blackhole(self, prefix: str, nexthop: str = None) -> bool:
        """Announce BGP blackhole route (RTBH)
        
        Supports multiple BGP daemons: ExaBGP, FRR, BIRD
        See docs/BGP-RTBH.md for setup instructions
        """
        try:
            # Use configured BGP daemon or default to ExaBGP
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            nexthop = nexthop or getattr(settings, 'BGP_BLACKHOLE_NEXTHOP', '192.0.2.1')
            
            if bgp_daemon == 'exabgp':
                return self._announce_exabgp(prefix, nexthop)
            elif bgp_daemon == 'frr':
                return self._announce_frr(prefix, nexthop)
            elif bgp_daemon == 'bird':
                return self._announce_bird(prefix, nexthop)
            else:
                print(f"Unknown BGP daemon: {bgp_daemon}")
                return False
                
        except Exception as e:
            print(f"Error announcing BGP blackhole: {e}")
            return False
    
    def _announce_exabgp(self, prefix: str, nexthop: str) -> bool:
        """Announce via ExaBGP"""
        try:
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            community = getattr(settings, 'BGP_BLACKHOLE_COMMUNITY', '65535:666')
            
            with open(cmd_pipe, 'a') as f:
                f.write(f'announce route {prefix} next-hop {nexthop} community [{community}]\n')
            
            print(f"BGP blackhole announced via ExaBGP: {prefix} -> {nexthop}")
            return True
        except Exception as e:
            print(f"ExaBGP error: {e}")
            return False
    
    def _announce_frr(self, prefix: str, nexthop: str) -> bool:
        """Announce via FRR (Free Range Routing)"""
        try:
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            # Add static route with tag 666 (matches route-map for RTBH)
            cmd = [
                vtysh_cmd,
                '-c', 'configure terminal',
                '-c', f'ip route {prefix} Null0 tag 666'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"BGP blackhole announced via FRR: {prefix}")
                return True
            else:
                print(f"FRR error: {result.stderr}")
                return False
        except Exception as e:
            print(f"FRR error: {e}")
            return False
    
    def _announce_bird(self, prefix: str, nexthop: str) -> bool:
        """Announce via BIRD"""
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"BIRD error: Invalid prefix format: {prefix}")
                return False
            
            # For BIRD, we need to add route dynamically using birdc
            # Note: This requires BIRD configuration to allow dynamic routes
            # via the blackhole_routes protocol
            # Using list form prevents shell injection
            cmd = ['birdc', '-r', 'add', 'route', prefix, 'blackhole']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'already exists' in result.stdout.lower():
                print(f"BGP blackhole announced via BIRD: {prefix}")
                return True
            else:
                print(f"BIRD error: {result.stderr}")
                return False
        except Exception as e:
            print(f"BIRD error: {e}")
            return False
    
    def withdraw_bgp_blackhole(self, prefix: str) -> bool:
        """Withdraw BGP blackhole route
        
        Removes previously announced blackhole route
        See docs/BGP-RTBH.md for details
        """
        try:
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            
            if bgp_daemon == 'exabgp':
                return self._withdraw_exabgp(prefix)
            elif bgp_daemon == 'frr':
                return self._withdraw_frr(prefix)
            elif bgp_daemon == 'bird':
                return self._withdraw_bird(prefix)
            else:
                return False
                
        except Exception as e:
            print(f"Error withdrawing BGP blackhole: {e}")
            return False
    
    def _withdraw_exabgp(self, prefix: str) -> bool:
        """Withdraw via ExaBGP"""
        try:
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            
            with open(cmd_pipe, 'a') as f:
                f.write(f'withdraw route {prefix}\n')
            
            print(f"BGP blackhole withdrawn via ExaBGP: {prefix}")
            return True
        except Exception as e:
            print(f"ExaBGP withdrawal error: {e}")
            return False
    
    def _withdraw_frr(self, prefix: str) -> bool:
        """Withdraw via FRR"""
        try:
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            cmd = [
                vtysh_cmd,
                '-c', 'configure terminal',
                '-c', f'no ip route {prefix} Null0 tag 666'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"BGP blackhole withdrawn via FRR: {prefix}")
                return True
            else:
                print(f"FRR withdrawal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"FRR withdrawal error: {e}")
            return False
    
    def _withdraw_bird(self, prefix: str) -> bool:
        """Withdraw via BIRD"""
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"BIRD error: Invalid prefix format: {prefix}")
                return False
            
            # Remove the route dynamically using birdc
            # Using list form prevents shell injection
            cmd = ['birdc', '-r', 'delete', 'route', prefix]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'not found' in result.stdout.lower():
                print(f"BGP blackhole withdrawn via BIRD: {prefix}")
                return True
            else:
                print(f"BIRD withdrawal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"BIRD withdrawal error: {e}")
            return False
    
    def send_flowspec_rule(self, source: str = None, dest: str = None, 
                          protocol: str = None, action: str = "drop") -> bool:
        """Send FlowSpec announcement"""
        try:
            # FlowSpec requires BGP FlowSpec capable router
            # This would integrate with BGP daemon
            
            flowspec_rule = {
                'source': source,
                'destination': dest,
                'protocol': protocol,
                'action': action
            }
            
            # Example: send to ExaBGP
            with open('/var/run/exabgp.cmd', 'a') as f:
                f.write(f'announce flow route {flowspec_rule}\n')
            
            return True
            
        except Exception as e:
            print(f"Error sending FlowSpec rule: {e}")
            return False
    
    def apply_rate_limit(self, ip: str, rate: str = "1000/s") -> bool:
        """Apply rate limiting using tc (traffic control)"""
        try:
            # Using Linux tc for rate limiting
            cmd = [
                "tc", "filter", "add", "dev", "eth0", "protocol", "ip",
                "parent", "1:0", "prio", "1", "u32",
                "match", "ip", "src", ip,
                "police", "rate", rate, "burst", "100k", "drop"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error applying rate limit: {e}")
            return False
    
    def auto_mitigate_alert(self, alert_id: int) -> bool:
        """Automatically mitigate an alert"""
        db = SessionLocal()
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            # Determine mitigation strategy based on alert type
            if alert.alert_type in ['syn_flood', 'udp_flood']:
                # Block source IP
                success = self.apply_iptables_rule('block', alert.source_ip)
                
                if success:
                    mitigation = MitigationAction(
                        alert_id=alert.id,
                        action_type='firewall',
                        details={'rule': 'iptables', 'ip': alert.source_ip, 'action': 'block'},
                        status='active'
                    )
                    db.add(mitigation)
                    alert.status = 'mitigated'
                    db.commit()
                    return True
            
            elif alert.alert_type == 'dns_amplification':
                # Rate limit UDP/53
                success = self.apply_rate_limit(alert.source_ip, '100/s')
                
                if success:
                    mitigation = MitigationAction(
                        alert_id=alert.id,
                        action_type='rate_limit',
                        details={'ip': alert.source_ip, 'rate': '100/s'},
                        status='active'
                    )
                    db.add(mitigation)
                    alert.status = 'mitigated'
                    db.commit()
                    return True
            
            return False
            
        finally:
            db.close()

def main():
    MitigationService()
    print("Mitigation service initialized")

if __name__ == "__main__":
    main()
