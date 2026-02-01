"""
Hostgroup management for per-subnet threshold configuration
Supports hierarchical subnet groups with custom thresholds
"""
import os
import ipaddress
import json
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import redis

from config import settings
from database import SessionLocal
from models.models import Alert


class HostGroup:
    """Represents a group of hosts (subnet) with custom thresholds"""
    
    def __init__(self, name: str, subnet: str, thresholds: Dict[str, int], 
                 scripts: Optional[Dict[str, str]] = None):
        """
        Initialize hostgroup
        
        Args:
            name: Group name
            subnet: CIDR subnet (e.g., '192.168.1.0/24')
            thresholds: Threshold values (pps, bps, fps)
            scripts: Optional notification/block scripts
        """
        self.name = name
        self.subnet = ipaddress.ip_network(subnet)
        self.thresholds = thresholds
        self.scripts = scripts or {}
    
    def contains_ip(self, ip: str) -> bool:
        """Check if IP is in this hostgroup"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return ip_addr in self.subnet
        except ValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'subnet': str(self.subnet),
            'thresholds': self.thresholds,
            'scripts': self.scripts
        }


class HostGroupManager:
    """Manages hostgroups and threshold-based monitoring"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        self.hostgroups = {}
        self.load_hostgroups()
        
        # Default thresholds
        self.default_thresholds = {
            'packets_per_second': getattr(settings, 'DEFAULT_PPS_THRESHOLD', 10000),
            'bytes_per_second': getattr(settings, 'DEFAULT_BPS_THRESHOLD', 100000000),  # 100 Mbps
            'flows_per_second': getattr(settings, 'DEFAULT_FPS_THRESHOLD', 1000)
        }
    
    def load_hostgroups(self):
        """Load hostgroups from Redis"""
        try:
            keys = self.redis_client.keys('hostgroup:*')
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    config = json.loads(data)
                    hostgroup = HostGroup(
                        name=config['name'],
                        subnet=config['subnet'],
                        thresholds=config['thresholds'],
                        scripts=config.get('scripts', {})
                    )
                    self.hostgroups[config['name']] = hostgroup
            
            print(f"Loaded {len(self.hostgroups)} hostgroups from Redis")
        except Exception as e:
            print(f"Error loading hostgroups: {e}")
    
    def add_hostgroup(self, name: str, subnet: str, thresholds: Dict[str, int],
                     scripts: Optional[Dict[str, str]] = None) -> bool:
        """
        Add a new hostgroup
        
        Args:
            name: Group name
            subnet: CIDR subnet
            thresholds: Threshold configuration
            scripts: Optional scripts for block/notify actions
            
        Returns:
            True if added successfully
        """
        try:
            # Validate subnet
            ipaddress.ip_network(subnet)
            
            hostgroup = HostGroup(name, subnet, thresholds, scripts)
            self.hostgroups[name] = hostgroup
            
            # Persist to Redis
            self.redis_client.set(
                f'hostgroup:{name}',
                json.dumps(hostgroup.to_dict())
            )
            
            print(f"Added hostgroup: {name} ({subnet})")
            return True
            
        except Exception as e:
            print(f"Error adding hostgroup: {e}")
            return False
    
    def remove_hostgroup(self, name: str) -> bool:
        """Remove a hostgroup"""
        if name in self.hostgroups:
            del self.hostgroups[name]
            self.redis_client.delete(f'hostgroup:{name}')
            print(f"Removed hostgroup: {name}")
            return True
        return False
    
    def get_hostgroup_for_ip(self, ip: str) -> Optional[HostGroup]:
        """
        Find the most specific hostgroup for an IP
        Uses longest prefix match
        
        Args:
            ip: IP address
            
        Returns:
            HostGroup or None
        """
        matching_groups = []
        
        for hostgroup in self.hostgroups.values():
            if hostgroup.contains_ip(ip):
                matching_groups.append(hostgroup)
        
        # Return most specific (largest prefix length)
        if matching_groups:
            return max(matching_groups, key=lambda g: g.subnet.prefixlen)
        
        return None
    
    def get_thresholds_for_ip(self, ip: str) -> Dict[str, int]:
        """
        Get thresholds for a specific IP
        Uses hostgroup if available, otherwise defaults
        
        Args:
            ip: IP address
            
        Returns:
            Threshold dictionary
        """
        hostgroup = self.get_hostgroup_for_ip(ip)
        if hostgroup:
            return hostgroup.thresholds
        return self.default_thresholds
    
    def check_thresholds(self, ip: str, metrics: Dict[str, int], isp_id: int = 1) -> bool:
        """
        Check if IP exceeds configured thresholds
        
        Args:
            ip: IP address to check
            metrics: Current metrics (packets_per_second, bytes_per_second, flows_per_second)
            isp_id: ISP ID
            
        Returns:
            True if threshold exceeded
        """
        thresholds = self.get_thresholds_for_ip(ip)
        hostgroup = self.get_hostgroup_for_ip(ip)
        
        exceeded = []
        
        # Check each threshold
        for metric, value in metrics.items():
            threshold_key = metric
            if threshold_key in thresholds:
                if value > thresholds[threshold_key]:
                    exceeded.append({
                        'metric': metric,
                        'value': value,
                        'threshold': thresholds[threshold_key]
                    })
        
        # If any threshold exceeded, trigger actions
        if exceeded:
            self.handle_threshold_exceeded(ip, exceeded, hostgroup, isp_id)
            return True
        
        return False
    
    def handle_threshold_exceeded(self, ip: str, exceeded: List[Dict], 
                                  hostgroup: Optional[HostGroup], isp_id: int):
        """
        Handle threshold exceeded event
        Creates alert and executes scripts if configured
        
        Args:
            ip: IP address
            exceeded: List of exceeded thresholds
            hostgroup: Hostgroup configuration
            isp_id: ISP ID
        """
        # Create alert
        db = SessionLocal()
        try:
            description = f"Threshold exceeded for {ip}:\n"
            for item in exceeded:
                description += f"  - {item['metric']}: {item['value']} > {item['threshold']}\n"
            
            alert = Alert(
                isp_id=isp_id,
                alert_type='threshold_exceeded',
                severity='high',
                target_ip=ip,
                source_ip='multiple',
                description=description,
                status='active'
            )
            db.add(alert)
            db.commit()
            
            alert_id = alert.id
            
            # Execute scripts if configured
            if hostgroup and hostgroup.scripts:
                self.execute_scripts(hostgroup.scripts, ip, exceeded, alert_id)
            
        except Exception as e:
            print(f"Error handling threshold exceeded: {e}")
        finally:
            db.close()
    
    def execute_scripts(self, scripts: Dict[str, str], ip: str, 
                       exceeded: List[Dict], alert_id: int):
        """
        Execute configured scripts for block/notify actions
        
        Args:
            scripts: Script configuration
            ip: Target IP
            exceeded: Exceeded thresholds
            alert_id: Alert ID
        """
        # Prepare environment variables for scripts
        env = {
            'TARGET_IP': ip,
            'ALERT_ID': str(alert_id),
            'EXCEEDED_METRICS': json.dumps(exceeded),
            'TIMESTAMP': datetime.now(timezone.utc).isoformat()
        }
        
        # Execute block script
        if 'block' in scripts and scripts['block']:
            try:
                print(f"Executing block script for {ip}")
                result = subprocess.run(
                    [scripts['block'], ip],
                    env={**env, **dict(os.environ)},
                    capture_output=True,
                    timeout=30,
                    text=True
                )
                print(f"Block script output: {result.stdout}")
                if result.returncode != 0:
                    print(f"Block script error: {result.stderr}")
            except Exception as e:
                print(f"Error executing block script: {e}")
        
        # Execute notify script
        if 'notify' in scripts and scripts['notify']:
            try:
                print(f"Executing notify script for {ip}")
                result = subprocess.run(
                    [scripts['notify'], ip, str(alert_id)],
                    env={**env, **dict(os.environ)},
                    capture_output=True,
                    timeout=30,
                    text=True
                )
                print(f"Notify script output: {result.stdout}")
                if result.returncode != 0:
                    print(f"Notify script error: {result.stderr}")
            except Exception as e:
                print(f"Error executing notify script: {e}")
    
    def monitor_traffic(self, isp_id: int = 1):
        """
        Monitor traffic and check thresholds
        Should be called periodically (e.g., every second)
        
        Args:
            isp_id: ISP ID to monitor
        """
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            
            # Aggregate traffic by destination IP
            dst_metrics = {}
            
            # Scan Redis for current second traffic
            for key in self.redis_client.scan_iter(match=f"traffic:dst:{isp_id}:*:{current_second}"):
                parts = key.split(':')
                if len(parts) >= 5:
                    dst_ip = ':'.join(parts[3:-1])
                    packets = int(self.redis_client.get(key) or 0)
                    
                    if dst_ip not in dst_metrics:
                        dst_metrics[dst_ip] = {
                            'packets_per_second': 0,
                            'bytes_per_second': 0,
                            'flows_per_second': 0
                        }
                    
                    dst_metrics[dst_ip]['packets_per_second'] += packets
            
            # Check thresholds for each IP
            for ip, metrics in dst_metrics.items():
                self.check_thresholds(ip, metrics, isp_id)
                
        except Exception as e:
            print(f"Error monitoring traffic: {e}")
    
    def list_hostgroups(self) -> List[Dict[str, Any]]:
        """List all hostgroups"""
        return [hg.to_dict() for hg in self.hostgroups.values()]


# Module-level singleton
_hostgroup_manager = None

def get_hostgroup_manager() -> HostGroupManager:
    """Get or create hostgroup manager singleton"""
    global _hostgroup_manager
    if _hostgroup_manager is None:
        _hostgroup_manager = HostGroupManager()
    return _hostgroup_manager
