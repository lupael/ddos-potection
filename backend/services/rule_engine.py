"""
Custom Rule Engine for DDoS Protection
Evaluates and applies rules for rate limits, IP blocks, protocol filters, and geo-blocking
"""
import ipaddress
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from database import SessionLocal
from models.models import Rule
from config import settings


class RuleEngine:
    """Custom rule engine for evaluating and applying DDoS protection rules"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def evaluate_traffic(self, traffic_data: Dict) -> List[Dict]:
        """Evaluate traffic against all active rules
        
        Args:
            traffic_data: Dictionary containing traffic information
                {
                    'source_ip': str,
                    'dest_ip': str,
                    'protocol': str,
                    'source_port': int,
                    'dest_port': int,
                    'packets': int,
                    'bytes': int,
                    'country': str (optional)
                }
        
        Returns:
            List of actions to take based on matching rules
        """
        actions = []
        
        # Get all active rules ordered by priority (lower number = higher priority)
        rules = self.db.query(Rule).filter(
            Rule.is_active == True
        ).order_by(Rule.priority.asc()).all()
        
        for rule in rules:
            if self.rule_matches(rule, traffic_data):
                action = {
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'rule_type': rule.rule_type,
                    'action': rule.action,
                    'condition': rule.condition
                }
                actions.append(action)
                
                # If action is 'block', stop processing (highest priority action)
                if rule.action == 'block':
                    break
        
        return actions
    
    def rule_matches(self, rule: Rule, traffic_data: Dict) -> bool:
        """Check if a rule matches the given traffic data
        
        Args:
            rule: Rule object from database
            traffic_data: Traffic information dictionary
        
        Returns:
            True if rule matches, False otherwise
        """
        condition = rule.condition
        
        if rule.rule_type == 'ip_block':
            return self._match_ip_block(condition, traffic_data)
        
        elif rule.rule_type == 'rate_limit':
            return self._match_rate_limit(condition, traffic_data)
        
        elif rule.rule_type == 'protocol_filter':
            return self._match_protocol_filter(condition, traffic_data)
        
        elif rule.rule_type == 'geo_block':
            return self._match_geo_block(condition, traffic_data)
        
        elif rule.rule_type == 'port_filter':
            return self._match_port_filter(condition, traffic_data)
        
        return False
    
    def _match_ip_block(self, condition: Dict, traffic: Dict) -> bool:
        """Match IP block rule"""
        try:
            target_ip = condition.get('ip')
            source_ip = traffic.get('source_ip')
            
            if not target_ip or not source_ip:
                return False
            
            # Check if it's a CIDR notation
            if '/' in target_ip:
                network = ipaddress.ip_network(target_ip, strict=False)
                ip = ipaddress.ip_address(source_ip)
                return ip in network
            else:
                return target_ip == source_ip
            
        except (ValueError, KeyError):
            return False
    
    def _match_rate_limit(self, condition: Dict, traffic: Dict) -> bool:
        """Match rate limit rule
        
        Condition format:
        {
            'ip': '192.0.2.0/24' or specific IP (optional),
            'protocol': 'tcp' or 'udp' (optional),
            'threshold': 1000,  # packets per second
            'window': 60  # time window in seconds (default: 60)
        }
        """
        try:
            # Check if IP matches (if specified)
            if 'ip' in condition:
                target_ip = condition['ip']
                source_ip = traffic.get('source_ip')
                
                if '/' in target_ip:
                    network = ipaddress.ip_network(target_ip, strict=False)
                    ip = ipaddress.ip_address(source_ip)
                    if ip not in network:
                        return False
                elif target_ip != source_ip:
                    return False
            
            # Check if protocol matches (if specified)
            if 'protocol' in condition:
                if condition['protocol'].lower() != traffic.get('protocol', '').lower():
                    return False
            
            # Check if rate exceeds threshold
            threshold = condition.get('threshold', 1000)
            packets = traffic.get('packets', 0)
            window = condition.get('window', 60)
            
            # Calculate packets per second
            pps = packets / window if window > 0 else packets
            
            return pps > threshold
            
        except (ValueError, KeyError):
            return False
    
    def _match_protocol_filter(self, condition: Dict, traffic: Dict) -> bool:
        """Match protocol filter rule
        
        Condition format:
        {
            'protocols': ['tcp', 'udp', 'icmp'],  # allowed or blocked protocols
            'mode': 'allow' or 'block'
        }
        """
        try:
            protocols = condition.get('protocols', [])
            mode = condition.get('mode', 'block')
            traffic_protocol = traffic.get('protocol', '').lower()
            
            if mode == 'block':
                # Block if protocol is in the list
                return traffic_protocol in [p.lower() for p in protocols]
            else:  # allow mode
                # Block if protocol is NOT in the list
                return traffic_protocol not in [p.lower() for p in protocols]
            
        except (KeyError, AttributeError):
            return False
    
    def _match_geo_block(self, condition: Dict, traffic: Dict) -> bool:
        """Match geo-blocking rule
        
        Condition format:
        {
            'countries': ['CN', 'RU', 'KP'],  # ISO country codes
            'mode': 'block' or 'allow'
        }
        """
        try:
            countries = condition.get('countries', [])
            mode = condition.get('mode', 'block')
            
            # Get country from traffic data
            traffic_country = traffic.get('country', '')
            
            # If no country data, try to look it up
            if not traffic_country:
                source_ip = traffic.get('source_ip')
                if source_ip:
                    traffic_country = self._lookup_country(source_ip)
            
            if not traffic_country:
                # If we can't determine country, default to not matching
                return False
            
            if mode == 'block':
                # Block if country is in the list
                return traffic_country.upper() in [c.upper() for c in countries]
            else:  # allow mode
                # Block if country is NOT in the list
                return traffic_country.upper() not in [c.upper() for c in countries]
            
        except (KeyError, AttributeError):
            return False
    
    def _match_port_filter(self, condition: Dict, traffic: Dict) -> bool:
        """Match port filter rule
        
        Condition format:
        {
            'ports': [80, 443, 22],  # list of ports
            'port_type': 'dest' or 'source',
            'mode': 'block' or 'allow'
        }
        """
        try:
            ports = condition.get('ports', [])
            port_type = condition.get('port_type', 'dest')
            mode = condition.get('mode', 'block')
            
            # Get the relevant port from traffic
            if port_type == 'dest':
                traffic_port = traffic.get('dest_port')
            else:
                traffic_port = traffic.get('source_port')
            
            if traffic_port is None:
                return False
            
            if mode == 'block':
                # Block if port is in the list
                return traffic_port in ports
            else:  # allow mode
                # Block if port is NOT in the list
                return traffic_port not in ports
            
        except (KeyError, AttributeError):
            return False
    
    def _lookup_country(self, ip_address: str) -> Optional[str]:
        """Lookup country code for IP address using GeoIP database
        
        Args:
            ip_address: IP address to lookup
        
        Returns:
            ISO country code (e.g., 'US', 'CN') or None if not found
        """
        try:
            # Try to use GeoIP2 if available
            import geoip2.database
            
            geoip_db_path = getattr(settings, 'GEOIP_DATABASE_PATH', 
                                   '/usr/share/GeoIP/GeoLite2-Country.mmdb')
            
            try:
                reader = geoip2.database.Reader(geoip_db_path)
                response = reader.country(ip_address)
                return response.country.iso_code
            except (geoip2.errors.AddressNotFoundError, FileNotFoundError):
                return None
            
        except ImportError:
            # GeoIP2 not available, try alternative methods
            pass
        
        # Fallback: use external API (not recommended for production)
        # This is just a placeholder - production should use local GeoIP database
        return None
    
    def apply_rule_action(self, action: Dict) -> bool:
        """Apply the action specified by a rule
        
        Args:
            action: Action dictionary from evaluate_traffic
        
        Returns:
            True if action was applied successfully, False otherwise
        """
        try:
            from services.mitigation_service import MitigationService
            mitigation = MitigationService()
            
            action_type = action['action']
            condition = action['condition']
            
            if action_type == 'block':
                # Apply IP block using iptables
                ip = condition.get('ip')
                protocol = condition.get('protocol')
                if ip:
                    return mitigation.apply_iptables_rule('block', ip, protocol)
            
            elif action_type == 'rate_limit':
                # Apply rate limiting
                ip = condition.get('ip')
                rate = condition.get('rate', '1000/s')
                if ip:
                    return mitigation.apply_rate_limit(ip, rate)
            
            elif action_type == 'alert':
                # Just log an alert (don't block traffic)
                print(f"Alert triggered: {action['rule_name']}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error applying rule action: {e}")
            return False
    
    def cleanup_expired_rules(self):
        """Remove or deactivate rules that have expired"""
        try:
            # Find rules with expiration dates
            expired_rules = self.db.query(Rule).filter(
                Rule.is_active == True,
                Rule.condition.contains({'expires_at': ''})
            ).all()
            
            for rule in expired_rules:
                expires_at_str = rule.condition.get('expires_at')
                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if datetime.utcnow() > expires_at:
                            rule.is_active = False
                            print(f"Deactivated expired rule: {rule.name}")
                    except ValueError:
                        pass
            
            self.db.commit()
            
        except Exception as e:
            print(f"Error cleaning up expired rules: {e}")
            self.db.rollback()
    
    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'db'):
            self.db.close()


def main():
    """Example usage of the rule engine"""
    engine = RuleEngine()
    
    # Example traffic data
    traffic = {
        'source_ip': '192.0.2.100',
        'dest_ip': '198.51.100.50',
        'protocol': 'tcp',
        'source_port': 54321,
        'dest_port': 80,
        'packets': 5000,
        'bytes': 250000,
        'country': 'CN'
    }
    
    # Evaluate traffic
    actions = engine.evaluate_traffic(traffic)
    
    print(f"Matched {len(actions)} rules:")
    for action in actions:
        print(f"  - {action['rule_name']}: {action['action']}")
        
        # Apply the action
        # engine.apply_rule_action(action)


if __name__ == "__main__":
    main()
