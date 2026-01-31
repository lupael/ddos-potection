"""
Mitigation automation service
"""
import subprocess
from typing import Dict, Any
import requests
from datetime import datetime

from database import SessionLocal
from models.models import MitigationAction, Alert, Rule
from config import settings

class MitigationService:
    def __init__(self):
        pass
    
    def apply_iptables_rule(self, action: str, ip: str, protocol: str = None) -> bool:
        """Apply iptables firewall rule"""
        try:
            if action == "block":
                cmd = ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
                if protocol:
                    cmd.insert(4, "-p")
                    cmd.insert(5, protocol.lower())
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            
            elif action == "unblock":
                cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
                
        except Exception as e:
            print(f"Error applying iptables rule: {e}")
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
    
    def announce_bgp_blackhole(self, prefix: str, nexthop: str = "192.0.2.1") -> bool:
        """Announce BGP blackhole route (RTBH)"""
        try:
            # This would integrate with BGP daemon (BIRD, FRR, Quagga)
            # Example using ExaBGP or direct BGP API
            
            # Simplified: write to ExaBGP command file
            with open('/var/run/exabgp.cmd', 'a') as f:
                f.write(f'announce route {prefix} next-hop {nexthop} community [65535:666]\n')
            
            return True
            
        except Exception as e:
            print(f"Error announcing BGP blackhole: {e}")
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
    service = MitigationService()
    print("Mitigation service initialized")

if __name__ == "__main__":
    main()
