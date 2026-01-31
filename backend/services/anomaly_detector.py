"""
Anomaly detection engine for DDoS attacks
"""
import redis
import time
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import defaultdict
import math

from database import SessionLocal
from models.models import Alert, TrafficLog
from config import settings

class AnomalyDetector:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        # Subscribe to Redis pub/sub for real-time events
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe('traffic:events')
    
    def detect_syn_flood(self, isp_id: int = 1) -> bool:
        """
        Detect SYN flood attacks using Redis counters
        Checks for high rate of SYN packets to specific destinations
        """
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            detected = False
            
            # Check last 10 seconds of SYN counters
            for i in range(10):
                second = current_second - i
                pattern = f"syn:{isp_id}:*:{second}"
                
                for key in self.redis_client.scan_iter(match=pattern):
                    count = int(self.redis_client.get(key) or 0)
                    
                    if count > settings.SYN_FLOOD_THRESHOLD:
                        # Extract destination IP from key
                        parts = key.split(':')
                        if len(parts) >= 3:
                            dst_ip = parts[2]
                            
                            self.create_alert(
                                isp_id=isp_id,
                                alert_type='syn_flood',
                                severity='critical',
                                target_ip=dst_ip,
                                description=f'SYN flood detected: {count} SYN packets/sec to {dst_ip}'
                            )
                            detected = True
            
            return detected
            
        except Exception as e:
            print(f"Error in SYN flood detection: {e}")
            return False
    
    def detect_udp_flood(self, isp_id: int = 1) -> bool:
        """Detect UDP flood attacks using Redis counters"""
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            detected = False
            
            # Check UDP traffic (protocol 17) in last 60 seconds
            total_udp_packets = 0
            dst_ip_packets = defaultdict(int)
            
            for i in range(60):
                second = current_second - i
                key = f"traffic:proto:{isp_id}:17:{second}"
                packets = int(self.redis_client.get(key) or 0)
                total_udp_packets += packets
                
                # Also check per-destination
                pattern = f"traffic:dst:{isp_id}:*:{second}"
                for dst_key in self.redis_client.scan_iter(match=pattern):
                    dst_ip = dst_key.split(':')[3]
                    dst_packets = int(self.redis_client.get(dst_key) or 0)
                    dst_ip_packets[dst_ip] += dst_packets
            
            # Check if any destination exceeds threshold
            for dst_ip, packets in dst_ip_packets.items():
                if packets > settings.UDP_FLOOD_THRESHOLD:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='udp_flood',
                        severity='high',
                        target_ip=dst_ip,
                        description=f'UDP flood detected: {packets} packets/min to {dst_ip}'
                    )
                    detected = True
            
            return detected
            
        except Exception as e:
            print(f"Error in UDP flood detection: {e}")
            return False
    
    def calculate_entropy(self, data: List[str]) -> float:
        """Calculate Shannon entropy"""
        if not data:
            return 0.0
        
        frequencies = defaultdict(int)
        for item in data:
            frequencies[item] += 1
        
        total = len(data)
        entropy = 0.0
        
        for count in frequencies.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def detect_entropy_anomaly(self, isp_id: int = 1) -> bool:
        """Detect anomalies using multi-dimensional entropy analysis"""
        db = SessionLocal()
        try:
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
            
            logs = db.query(TrafficLog).filter(
                TrafficLog.isp_id == isp_id,
                TrafficLog.timestamp >= one_min_ago
            ).limit(10000).all()
            
            if not logs or len(logs) < 100:
                return False
            
            # Analyze multiple dimensions
            source_ips = [log.source_ip for log in logs]
            dest_ips = [log.dest_ip for log in logs]
            protocols = [log.protocol for log in logs]
            
            src_entropy = self.calculate_entropy(source_ips)
            dst_entropy = self.calculate_entropy(dest_ips)
            proto_entropy = self.calculate_entropy(protocols)
            
            # Low source entropy + low destination entropy = distributed DDoS to single target
            if src_entropy < settings.ENTROPY_THRESHOLD and dst_entropy < 1.0:
                top_sources = defaultdict(int)
                for ip in source_ips:
                    top_sources[ip] += 1
                
                top_attacker = max(top_sources.items(), key=lambda x: x[1])[0] if top_sources else 'unknown'
                top_target = max(defaultdict(int, [(ip, source_ips.count(ip)) for ip in set(dest_ips)]).items(), 
                               key=lambda x: x[1])[0]
                
                self.create_alert(
                    isp_id=isp_id,
                    alert_type='distributed_ddos',
                    severity='critical',
                    source_ip=top_attacker,
                    target_ip=top_target,
                    description=f'Distributed DDoS detected (src_entropy={src_entropy:.2f}, dst_entropy={dst_entropy:.2f})'
                )
                return True
            
            # High source entropy + low destination entropy = volumetric attack
            elif src_entropy > 5.0 and dst_entropy < 2.0:
                top_target = max(defaultdict(int, [(ip, dest_ips.count(ip)) for ip in set(dest_ips)]).items(), 
                               key=lambda x: x[1])[0]
                
                self.create_alert(
                    isp_id=isp_id,
                    alert_type='volumetric_attack',
                    severity='high',
                    source_ip='multiple',
                    target_ip=top_target,
                    description=f'Volumetric attack detected (src_entropy={src_entropy:.2f}): many sources to few targets'
                )
                return True
            
            return False
        except Exception as e:
            print(f"Error in entropy analysis: {e}")
            return False
        finally:
            db.close()
    
    def detect_icmp_flood(self, isp_id: int = 1) -> bool:
        """Detect ICMP flood attacks"""
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            detected = False
            
            # Check ICMP traffic (protocol 1) in last 60 seconds
            dst_ip_packets = defaultdict(int)
            
            for i in range(60):
                second = current_second - i
                key = f"traffic:proto:{isp_id}:1:{second}"
                
                # Get destination IPs receiving ICMP
                pattern = f"traffic:dst:{isp_id}:*:{second}"
                for dst_key in self.redis_client.scan_iter(match=pattern):
                    # Would need to filter by protocol, but for simplicity check total
                    dst_ip = dst_key.split(':')[3]
                    packets = int(self.redis_client.get(dst_key) or 0)
                    dst_ip_packets[dst_ip] += packets
            
            # Check threshold (10000 ICMP packets/min)
            for dst_ip, packets in dst_ip_packets.items():
                if packets > 10000:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='icmp_flood',
                        severity='medium',
                        target_ip=dst_ip,
                        description=f'ICMP flood detected: {packets} packets/min to {dst_ip}'
                    )
                    detected = True
            
            return detected
            
        except Exception as e:
            print(f"Error in ICMP flood detection: {e}")
            return False
    
    def detect_dns_amplification(self, isp_id: int = 1) -> bool:
        """Detect DNS amplification attacks (high UDP port 53 traffic)"""
        db = SessionLocal()
        try:
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
            
            from sqlalchemy import func
            # Look for high volume UDP traffic to port 53
            # Note: This would require storing port info in TrafficLog
            # For now, check for UDP spikes which could indicate DNS amplification
            
            udp_stats = db.query(
                TrafficLog.dest_ip,
                func.sum(TrafficLog.packets).label('total_packets'),
                func.sum(TrafficLog.bytes).label('total_bytes')
            ).filter(
                TrafficLog.isp_id == isp_id,
                TrafficLog.protocol == 'UDP',
                TrafficLog.timestamp >= one_min_ago
            ).group_by(TrafficLog.dest_ip).all()
            
            detected = False
            for stat in udp_stats:
                # DNS amplification has high byte-to-packet ratio
                if stat.total_packets > 0:
                    bytes_per_packet = stat.total_bytes / stat.total_packets
                    # DNS responses are typically large (500+ bytes)
                    if bytes_per_packet > 500 and stat.total_packets > 1000:
                        self.create_alert(
                            isp_id=isp_id,
                            alert_type='dns_amplification',
                            severity='high',
                            target_ip=stat.dest_ip,
                            description=f'Possible DNS amplification: {stat.total_packets} packets, {bytes_per_packet:.0f} bytes/packet to {stat.dest_ip}'
                        )
                        detected = True
            
            return detected
            
        except Exception as e:
            print(f"Error in DNS amplification detection: {e}")
            return False
        finally:
            db.close()
    
    def create_alert(self, isp_id: int, alert_type: str, severity: str, 
                     target_ip: str, description: str, source_ip: str = 'unknown'):
        """Create an alert in the database and publish to Redis"""
        db = SessionLocal()
        try:
            # Check if similar alert exists recently
            recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            existing_alert = db.query(Alert).filter(
                Alert.isp_id == isp_id,
                Alert.alert_type == alert_type,
                Alert.target_ip == target_ip,
                Alert.status == 'active',
                Alert.created_at >= recent_time
            ).first()
            
            if existing_alert:
                # Don't create duplicate alert
                return
            
            alert = Alert(
                isp_id=isp_id,
                alert_type=alert_type,
                severity=severity,
                source_ip=source_ip,
                target_ip=target_ip,
                description=description,
                status='active'
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Store in Redis for real-time dashboard
            alert_key = f"alert:{alert.id}"
            alert_data = {
                'id': alert.id,
                'type': alert_type,
                'severity': severity,
                'target_ip': target_ip,
                'source_ip': source_ip,
                'description': description,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.redis_client.setex(
                alert_key,
                3600,  # 1 hour TTL
                json.dumps(alert_data)
            )
            
            # Publish alert to pub/sub channel
            self.redis_client.publish('alerts:new', json.dumps(alert_data))
            
            # Add to alerts stream
            self.redis_client.xadd('alerts:stream', alert_data, maxlen=1000)
            
            print(f"Alert created: {alert_type} [{severity}] - {description}")
            
        except Exception as e:
            print(f"Error creating alert: {e}")
        finally:
            db.close()
    
    def process_realtime_stream(self):
        """Process real-time traffic events from Redis pub/sub"""
        print("Starting real-time stream processor...")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    event = json.loads(message['data'])
                    # Process event for immediate threat detection
                    # This could trigger instant alerts for critical threats
                    
                except Exception as e:
                    print(f"Error processing stream message: {e}")
    
    def run_detection_loop(self):
        """Main detection loop"""
        print("Starting anomaly detection engine...")
        print("Detection methods:")
        print("  - SYN Flood Detection")
        print("  - UDP Flood Detection")
        print("  - ICMP Flood Detection")
        print("  - DNS Amplification Detection")
        print("  - Multi-dimensional Entropy Analysis")
        
        while True:
            try:
                # Run all detections
                self.detect_syn_flood()
                self.detect_udp_flood()
                self.detect_icmp_flood()
                self.detect_dns_amplification()
                self.detect_entropy_anomaly()
                
                # Sleep for a bit before next check
                time.sleep(10)
                
            except Exception as e:
                print(f"Error in detection loop: {e}")
                time.sleep(5)

def main():
    detector = AnomalyDetector()
    detector.run_detection_loop()

if __name__ == "__main__":
    main()
