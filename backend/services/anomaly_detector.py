"""
Anomaly detection engine for DDoS attacks
"""
import redis
import time
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from collections import defaultdict, Counter
import math

from database import SessionLocal
from models.models import Alert, TrafficLog
from config import settings
from services.notification_service import notify_alert

logger = logging.getLogger(__name__)

# Import new services
try:
    from services.packet_capture import get_packet_capture_service
    from services.hostgroup_manager import get_hostgroup_manager
    PACKET_CAPTURE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Packet capture or hostgroup features not available: {e}")
    PACKET_CAPTURE_AVAILABLE = False

class AnomalyDetector:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        # Initialize packet capture and hostgroup services if available
        if PACKET_CAPTURE_AVAILABLE:
            try:
                self.packet_capture = get_packet_capture_service()
                self.hostgroup_manager = get_hostgroup_manager()
                print("Packet capture and hostgroup management enabled")
            except Exception as e:
                print(f"Warning: Could not initialize packet capture/hostgroups: {e}")
                self.packet_capture = None
                self.hostgroup_manager = None
        else:
            self.packet_capture = None
            self.hostgroup_manager = None
    
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
                        # Expected key format: syn:{isp_id}:{dst_ip}:{timestamp}
                        parts = key.split(':')
                        if len(parts) >= 4:
                            # For IPv4, dst_ip is at index 2
                            # For IPv6, extract everything between second and last colon
                            dst_ip = ':'.join(parts[2:-1])
                            
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
            dst_ip_packets = defaultdict(int)
            
            # Optimize: scan destination keys once and filter by timestamp
            window_start = current_second - 59
            pattern = f"traffic:dst:{isp_id}:*"
            
            for dst_key in self.redis_client.scan_iter(match=pattern):
                # Expected key format (IPv4): traffic:dst:{isp_id}:{dst_ip}:{second}
                parts = dst_key.split(':')
                if len(parts) < 5:
                    continue
                
                # Extract timestamp
                try:
                    key_second = int(parts[-1])
                except ValueError:
                    continue
                
                # Check if within time window
                if key_second < window_start or key_second > current_second:
                    continue
                
                # Extract destination IP (handle IPv6 with colons)
                dst_ip = ':'.join(parts[3:-1])
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
            
            src_entropy = self.calculate_entropy(source_ips)
            dst_entropy = self.calculate_entropy(dest_ips)
            
            # Low source entropy + low destination entropy = distributed DDoS to single target
            if src_entropy < settings.ENTROPY_THRESHOLD and dst_entropy < 1.0:
                top_attacker = Counter(source_ips).most_common(1)[0][0] if source_ips else 'unknown'
                top_target = Counter(dest_ips).most_common(1)[0][0] if dest_ips else 'unknown'
                
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
                top_target = Counter(dest_ips).most_common(1)[0][0] if dest_ips else 'unknown'
                
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
            dst_ip_packets = defaultdict(int)
            
            # Note: Current implementation sums all traffic to destinations
            # A more accurate implementation would require protocol-specific destination counters
            # such as traffic:dst:icmp:{isp_id}:{dst_ip}:{second}
            
            # Optimize: scan destination keys once and filter by timestamp
            window_start = current_second - 59
            pattern = f"traffic:dst:{isp_id}:*"
            
            for dst_key in self.redis_client.scan_iter(match=pattern):
                # Expected key format: traffic:dst:{isp_id}:{dst_ip}:{second}
                parts = dst_key.split(':')
                if len(parts) < 5:
                    continue
                
                # Extract timestamp
                try:
                    key_second = int(parts[-1])
                except ValueError:
                    continue
                
                # Check if within time window
                if key_second < window_start or key_second > current_second:
                    continue
                
                # Extract destination IP (handle IPv6 with colons)
                dst_ip = ':'.join(parts[3:-1])
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
                'alert_type': alert_type,  # Changed from 'type' to 'alert_type' for consistency
                'severity': severity,
                'target_ip': target_ip,
                'source_ip': source_ip,
                'description': description,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'isp_id': isp_id  # Include ISP ID for tenant isolation
            }
            self.redis_client.setex(
                alert_key,
                3600,  # 1 hour TTL
                json.dumps(alert_data)
            )
            
            # Publish alert to ISP-specific pub/sub channel for tenant isolation
            self.redis_client.publish(f'alerts:new:{isp_id}', json.dumps(alert_data))
            # Also publish to general channel for backwards compatibility
            self.redis_client.publish('alerts:new', json.dumps(alert_data))
            
            # Add to alerts stream
            self.redis_client.xadd('alerts:stream', alert_data, maxlen=1000)
            
            print(f"Alert created: {alert_type} [{severity}] - {description}")
            
            # Capture attack fingerprint in PCAP format if enabled
            if self.packet_capture and getattr(settings, 'PCAP_ENABLED', True):
                if target_ip and alert_type in ['syn_flood', 'udp_flood', 'icmp_flood']:
                    try:
                        print(f"Capturing attack fingerprint for {alert_type} on {target_ip}")
                        self.packet_capture.capture_attack_fingerprint(
                            alert_id=alert.id,
                            target_ip=target_ip,
                            attack_type=alert_type,
                            duration=30  # 30 seconds capture
                        )
                    except Exception as e:
                        print(f"Error capturing attack fingerprint: {e}")
            
            # Send notifications asynchronously
            # If an event loop is running, schedule the task; otherwise run it in a
            # temporary event loop so notifications are not silently skipped.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop in this thread: run the coroutine to completion.
                try:
                    asyncio.run(self._send_alert_notifications(alert_data))
                except Exception as e:
                    print(f"Error sending alert notifications (asyncio.run): {e}")
            else:
                # Event loop is running: schedule fire-and-forget task.
                try:
                    loop.create_task(self._send_alert_notifications(alert_data))
                except Exception as e:
                    print(f"Error scheduling alert notifications: {e}")
            
        except Exception as e:
            print(f"Error creating alert: {e}")
        finally:
            db.close()
    
    async def _send_alert_notifications(self, alert_data: dict):
        """Send alert notifications through configured channels"""
        try:
            # Send notifications (email, SMS, Telegram)
            await notify_alert(alert_data)
        except Exception as e:
            print(f"Error sending alert notifications: {e}")
    
    def run_detection_loop(self):
        """Main detection loop"""
        print("Starting anomaly detection engine...")
        print("Detection methods:")
        print("  - SYN Flood Detection")
        print("  - UDP Flood Detection")
        print("  - ICMP Flood Detection")
        print("  - DNS Amplification Detection")
        print("  - Multi-dimensional Entropy Analysis")
        if self.hostgroup_manager:
            print("  - Hostgroup Threshold Monitoring")
        
        while True:
            try:
                # Run all detections
                self.detect_syn_flood()
                self.detect_udp_flood()
                self.detect_icmp_flood()
                self.detect_dns_amplification()
                self.detect_entropy_anomaly()
                
                # Check hostgroup thresholds if available
                if self.hostgroup_manager:
                    self.hostgroup_manager.monitor_traffic()
                
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
