"""
Anomaly detection engine for DDoS attacks
"""
import redis
import time
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
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
                
                self.create_ml_alert(
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
                
                self.create_ml_alert(
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
    
    def detect_ntp_amplification(self, isp_id: int = 1) -> bool:
        """Detect NTP amplification attacks (high UDP/123 response volume).

        Looks for destinations that receive many large UDP packets on port 123.
        NTP monlist responses are 468 bytes, so bytes_per_packet >> request_size
        indicates an amplification attack.
        """
        db = SessionLocal()
        try:
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)

            from sqlalchemy import func
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
            threshold = getattr(settings, 'NTP_AMPLIFICATION_THRESHOLD', 468)
            for stat in udp_stats:
                if stat.total_packets and stat.total_packets > 0:
                    bpp = stat.total_bytes / stat.total_packets
                    if bpp >= threshold and stat.total_packets > 1000:
                        self.create_alert(
                            isp_id=isp_id,
                            alert_type='ntp_amplification',
                            severity='high',
                            target_ip=stat.dest_ip,
                            description=(
                                f'NTP amplification detected: {stat.total_packets} pkts, '
                                f'{bpp:.0f} bytes/pkt to {stat.dest_ip}'
                            )
                        )
                        detected = True
            return detected
        except Exception as e:
            logger.error(f"Error in NTP amplification detection: {e}")
            return False
        finally:
            db.close()

    def detect_memcached_amplification(self, isp_id: int = 1) -> bool:
        """Detect Memcached amplification attacks (UDP/11211 large responses).

        Memcached UDP responses can be up to 1MB, making it a very high-
        amplification vector. We trigger when per-packet size exceeds 1 400 bytes.
        """
        db = SessionLocal()
        try:
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)

            from sqlalchemy import func
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
            threshold = getattr(settings, 'MEMCACHED_AMPLIFICATION_THRESHOLD', 1400)
            for stat in udp_stats:
                if stat.total_packets and stat.total_packets > 0:
                    bpp = stat.total_bytes / stat.total_packets
                    if bpp >= threshold and stat.total_packets > 500:
                        self.create_alert(
                            isp_id=isp_id,
                            alert_type='memcached_amplification',
                            severity='critical',
                            target_ip=stat.dest_ip,
                            description=(
                                f'Memcached amplification detected: {stat.total_packets} pkts, '
                                f'{bpp:.0f} bytes/pkt to {stat.dest_ip}'
                            )
                        )
                        detected = True
            return detected
        except Exception as e:
            logger.error(f"Error in Memcached amplification detection: {e}")
            return False
        finally:
            db.close()

    def detect_ssdp_amplification(self, isp_id: int = 1) -> bool:
        """Detect SSDP amplification attacks (UDP/1900 large responses).

        SSDP (Simple Service Discovery Protocol) responses can be much larger
        than requests, achieving ~30x amplification. We trigger when per-packet
        size is notably large on the SSDP source port.
        """
        db = SessionLocal()
        try:
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)

            from sqlalchemy import func
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
            threshold = getattr(settings, 'SSDP_AMPLIFICATION_THRESHOLD', 400)
            for stat in udp_stats:
                if stat.total_packets and stat.total_packets > 0:
                    bpp = stat.total_bytes / stat.total_packets
                    if bpp >= threshold and stat.total_packets > 1000:
                        self.create_alert(
                            isp_id=isp_id,
                            alert_type='ssdp_amplification',
                            severity='high',
                            target_ip=stat.dest_ip,
                            description=(
                                f'SSDP amplification detected: {stat.total_packets} pkts, '
                                f'{bpp:.0f} bytes/pkt to {stat.dest_ip}'
                            )
                        )
                        detected = True
            return detected
        except Exception as e:
            logger.error(f"Error in SSDP amplification detection: {e}")
            return False
        finally:
            db.close()

    def detect_tcp_rst_flood(self, isp_id: int = 1) -> bool:
        """Detect TCP RST flood attacks.

        Checks for a high rate of TCP RST packets targeting a single destination.
        A high RST-to-total-TCP ratio suggests RST injection or a RST flood.
        """
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            detected = False
            window_start = current_second - 59
            rst_counts: dict = {}

            pattern = f"rst:{isp_id}:*"
            for key in self.redis_client.scan_iter(match=pattern):
                parts = key.split(':')
                if len(parts) < 4:
                    continue
                try:
                    key_second = int(parts[-1])
                except ValueError:
                    continue
                if key_second < window_start or key_second > current_second:
                    continue
                dst_ip = ':'.join(parts[2:-1])
                count = int(self.redis_client.get(key) or 0)
                rst_counts[dst_ip] = rst_counts.get(dst_ip, 0) + count

            threshold = getattr(settings, 'TCP_RST_FLOOD_THRESHOLD', 5000)
            for dst_ip, count in rst_counts.items():
                if count > threshold:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='tcp_rst_flood',
                        severity='high',
                        target_ip=dst_ip,
                        description=f'TCP RST flood detected: {count} RST pkts/min to {dst_ip}'
                    )
                    detected = True
            return detected
        except Exception as e:
            logger.error(f"Error in TCP RST flood detection: {e}")
            return False

    def detect_tcp_ack_flood(self, isp_id: int = 1) -> bool:
        """Detect TCP ACK flood attacks (pure ACK packets without prior SYN).

        Checks Redis counters for high ACK packet rates. Pure ACK floods are
        used to exhaust firewall state-tracking resources.
        """
        try:
            current_second = int(datetime.now(timezone.utc).timestamp())
            detected = False
            window_start = current_second - 59
            ack_counts: dict = {}

            pattern = f"ack:{isp_id}:*"
            for key in self.redis_client.scan_iter(match=pattern):
                parts = key.split(':')
                if len(parts) < 4:
                    continue
                try:
                    key_second = int(parts[-1])
                except ValueError:
                    continue
                if key_second < window_start or key_second > current_second:
                    continue
                dst_ip = ':'.join(parts[2:-1])
                count = int(self.redis_client.get(key) or 0)
                ack_counts[dst_ip] = ack_counts.get(dst_ip, 0) + count

            threshold = getattr(settings, 'TCP_ACK_FLOOD_THRESHOLD', 10000)
            for dst_ip, count in ack_counts.items():
                if count > threshold:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='tcp_ack_flood',
                        severity='high',
                        target_ip=dst_ip,
                        description=f'TCP ACK flood detected: {count} ACK pkts/min to {dst_ip}'
                    )
                    detected = True
            return detected
        except Exception as e:
            logger.error(f"Error in TCP ACK flood detection: {e}")
            return False


    def create_ml_alert(
        self,
        isp_id: int,
        alert_type: str,
        severity: str,
        target_ip: str,
        description: str,
        source_ip: str = "unknown",
        ml_confidence: float = 0.0,
    ) -> None:
        """Create an alert from an ML/baseline detector.

        When ``settings.SHADOW_MODE`` is enabled the alert is tagged with
        ``shadow=True`` and mitigation is suppressed.  The shadow flag is
        stored both in the DB ``description`` prefix and in the Redis payload
        so downstream consumers can filter accordingly.
        """
        shadow = settings.SHADOW_MODE
        shadow_prefix = "[SHADOW] " if shadow else ""
        self.create_alert(
            isp_id=isp_id,
            alert_type=alert_type,
            severity=severity,
            target_ip=target_ip,
            description=f"{shadow_prefix}{description}",
            source_ip=source_ip,
            shadow=shadow,
        )

    def create_alert(self, isp_id: int, alert_type: str, severity: str,
                     target_ip: str, description: str, source_ip: str = 'unknown',
                     shadow: bool = False):
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
                'isp_id': isp_id,  # Include ISP ID for tenant isolation
                'shadow': shadow,  # Shadow mode flag – True means no mitigation
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
            
            # Capture attack fingerprint in PCAP format if enabled (skip in shadow mode)
            if not shadow and self.packet_capture and getattr(settings, 'PCAP_ENABLED', True):
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
            
            # Send notifications asynchronously (skip mitigation-grade notifs in shadow mode)
            # If an event loop is running, schedule the task; otherwise run it in a
            # temporary event loop so notifications are not silently skipped.
            if not shadow:
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
        """Main detection loop driven by Redis pub/sub events.

        Subscribes to ``ddos:flow_events``.  Each incoming message immediately
        triggers all detection methods.  A fallback timer ensures detection
        still runs at least every ``DETECTOR_POLL_INTERVAL`` seconds even when
        no messages arrive.
        """
        print("Starting anomaly detection engine...")
        print("Detection methods:")
        print("  - SYN Flood Detection")
        print("  - UDP Flood Detection")
        print("  - ICMP Flood Detection")
        print("  - DNS Amplification Detection")
        print("  - NTP Amplification Detection")
        print("  - Memcached Amplification Detection")
        print("  - SSDP Amplification Detection")
        print("  - TCP RST Flood Detection")
        print("  - TCP ACK Flood Detection")
        print("  - Multi-dimensional Entropy Analysis")
        if self.hostgroup_manager:
            print("  - Hostgroup Threshold Monitoring")

        poll_interval = getattr(settings, "DETECTOR_POLL_INTERVAL", 30)
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("ddos:flow_events")

        last_run = time.time()

        while True:
            try:
                # Block up to 1 second waiting for a message; avoids busy-spin
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                now = time.time()

                if message is not None or (now - last_run) >= poll_interval:
                    self._run_all_detections()
                    last_run = time.time()

            except Exception as e:
                print(f"Error in detection loop: {e}")
                time.sleep(5)

    def _run_all_detections(self):
        """Execute every registered detection method once."""
        try:
            self.detect_syn_flood()
            self.detect_udp_flood()
            self.detect_icmp_flood()
            self.detect_dns_amplification()
            self.detect_ntp_amplification()
            self.detect_memcached_amplification()
            self.detect_ssdp_amplification()
            self.detect_tcp_rst_flood()
            self.detect_tcp_ack_flood()
            self.detect_entropy_anomaly()

            if self.hostgroup_manager:
                self.hostgroup_manager.monitor_traffic()
        except Exception as e:
            print(f"Error running detections: {e}")

    async def detect_http_flood(
        self,
        target_ip: str,
        http_request_count: int,
        time_window_seconds: int = 60,
        isp_id: int = 1,
    ) -> Optional["Alert"]:
        """Detect HTTP flood: high request rate to a single target.

        Uses Redis counter ``http_req:{target_ip}`` accumulated by the caller.
        Returns a newly created Alert if the threshold is exceeded, else None.
        """
        try:
            threshold = getattr(settings, "HTTP_FLOOD_THRESHOLD", 10000)
            redis_key = f"http_req:{target_ip}"

            current = self.redis_client.incrby(redis_key, http_request_count)
            self.redis_client.expire(redis_key, time_window_seconds)

            if current > threshold:
                self.create_alert(
                    isp_id=isp_id,
                    alert_type="http_flood",
                    severity="high",
                    target_ip=target_ip,
                    description=(
                        f"HTTP flood detected: {current} requests/{time_window_seconds}s "
                        f"to {target_ip} (threshold {threshold})"
                    ),
                )
                db = SessionLocal()
                try:
                    recent = datetime.now(timezone.utc) - timedelta(minutes=1)
                    alert = (
                        db.query(Alert)
                        .filter(
                            Alert.alert_type == "http_flood",
                            Alert.target_ip == target_ip,
                            Alert.created_at >= recent,
                        )
                        .order_by(Alert.created_at.desc())
                        .first()
                    )
                    return alert
                finally:
                    db.close()
        except Exception as e:
            logger.error("Error in HTTP flood detection: %s", e)
        return None

    async def detect_slowloris(
        self,
        target_ip: str,
        half_open_connections: int,
        isp_id: int = 1,
    ) -> Optional["Alert"]:
        """Detect Slowloris: many partial/half-open HTTP connections.

        Returns a newly created Alert if the threshold is exceeded, else None.
        """
        try:
            threshold = getattr(settings, "SLOWLORIS_THRESHOLD", 500)
            if half_open_connections > threshold:
                self.create_alert(
                    isp_id=isp_id,
                    alert_type="slowloris",
                    severity="high",
                    target_ip=target_ip,
                    description=(
                        f"Slowloris detected: {half_open_connections} half-open connections "
                        f"to {target_ip} (threshold {threshold})"
                    ),
                )
                db = SessionLocal()
                try:
                    recent = datetime.now(timezone.utc) - timedelta(minutes=1)
                    alert = (
                        db.query(Alert)
                        .filter(
                            Alert.alert_type == "slowloris",
                            Alert.target_ip == target_ip,
                            Alert.created_at >= recent,
                        )
                        .order_by(Alert.created_at.desc())
                        .first()
                    )
                    return alert
                finally:
                    db.close()
        except Exception as e:
            logger.error("Error in Slowloris detection: %s", e)
        return None

    async def detect_dns_water_torture(
        self,
        target_dns_server: str,
        nxdomain_count: int,
        time_window_seconds: int = 60,
        isp_id: int = 1,
    ) -> Optional["Alert"]:
        """Detect DNS water torture: high NXDOMAIN response rate.

        Uses Redis counter ``dns_nxdomain:{target_dns_server}``.
        Returns a newly created Alert if the threshold is exceeded, else None.
        """
        try:
            threshold = getattr(settings, "DNS_NXDOMAIN_THRESHOLD", 1000)
            redis_key = f"dns_nxdomain:{target_dns_server}"

            current = self.redis_client.incrby(redis_key, nxdomain_count)
            self.redis_client.expire(redis_key, time_window_seconds)

            if current > threshold:
                self.create_alert(
                    isp_id=isp_id,
                    alert_type="dns_water_torture",
                    severity="high",
                    target_ip=target_dns_server,
                    description=(
                        f"DNS water torture detected: {current} NXDOMAINs/{time_window_seconds}s "
                        f"to {target_dns_server} (threshold {threshold})"
                    ),
                )
                db = SessionLocal()
                try:
                    recent = datetime.now(timezone.utc) - timedelta(minutes=1)
                    alert = (
                        db.query(Alert)
                        .filter(
                            Alert.alert_type == "dns_water_torture",
                            Alert.target_ip == target_dns_server,
                            Alert.created_at >= recent,
                        )
                        .order_by(Alert.created_at.desc())
                        .first()
                    )
                    return alert
                finally:
                    db.close()
        except Exception as e:
            logger.error("Error in DNS water torture detection: %s", e)
        return None

    async def detect_bgp_hijack(
        self,
        prefix: str,
        expected_origin_asn: int,
        observed_origin_asn: int,
        isp_id: int = 1,
    ) -> Optional["Alert"]:
        """Detect potential BGP hijack: prefix announced from unexpected ASN.

        Returns a newly created Alert if a mismatch is detected, else None.
        """
        try:
            if observed_origin_asn != expected_origin_asn:
                self.create_alert(
                    isp_id=isp_id,
                    alert_type="bgp_hijack",
                    severity="critical",
                    target_ip=prefix,
                    description=(
                        f"BGP hijack detected for prefix {prefix}: "
                        f"expected ASN {expected_origin_asn}, "
                        f"observed ASN {observed_origin_asn}"
                    ),
                )
                db = SessionLocal()
                try:
                    recent = datetime.now(timezone.utc) - timedelta(minutes=1)
                    alert = (
                        db.query(Alert)
                        .filter(
                            Alert.alert_type == "bgp_hijack",
                            Alert.target_ip == prefix,
                            Alert.created_at >= recent,
                        )
                        .order_by(Alert.created_at.desc())
                        .first()
                    )
                    return alert
                finally:
                    db.close()
        except Exception as e:
            logger.error("Error in BGP hijack detection: %s", e)
        return None

    async def detect_ip_spoofing(
        self,
        source_ip: str,
        ingress_prefix: str,
        registered_prefixes: list,
        isp_id: int = 1,
    ) -> Optional["Alert"]:
        """uRPF-style check: source IP must fall within a registered prefix.

        If *source_ip* is not contained in any of *registered_prefixes*, a
        medium-severity Alert is created and returned.
        """
        import ipaddress
        try:
            try:
                src_addr = ipaddress.ip_address(source_ip)
            except ValueError:
                logger.warning("detect_ip_spoofing: invalid source_ip %r", source_ip)
                return None

            for prefix in registered_prefixes:
                try:
                    if src_addr in ipaddress.ip_network(prefix, strict=False):
                        return None  # source is legitimate
                except ValueError:
                    continue

            # Source not found in any registered prefix → possible spoofing
            self.create_alert(
                isp_id=isp_id,
                alert_type="ip_spoofing",
                severity="medium",
                source_ip=source_ip,
                target_ip=ingress_prefix,
                description=(
                    f"Possible IP spoofing: {source_ip} arrived on {ingress_prefix} "
                    f"but is not in registered prefixes"
                ),
            )
            db = SessionLocal()
            try:
                recent = datetime.now(timezone.utc) - timedelta(minutes=1)
                alert = (
                    db.query(Alert)
                    .filter(
                        Alert.alert_type == "ip_spoofing",
                        Alert.source_ip == source_ip,
                        Alert.created_at >= recent,
                    )
                    .order_by(Alert.created_at.desc())
                    .first()
                )
                return alert
            finally:
                db.close()
        except Exception as e:
            logger.error("Error in IP spoofing detection: %s", e)
        return None


def publish_flow_event(redis_client, flow_data: dict) -> None:
    """Publish a flow event to the ``ddos:flow_events`` Redis channel.

    Call this from the traffic collector after processing each flow so that
    the anomaly detector is triggered immediately rather than waiting for the
    poll interval.
    """
    try:
        redis_client.publish("ddos:flow_events", json.dumps(flow_data))
    except Exception as e:
        logger.warning("Failed to publish flow event: %s", e)


def main():
    detector = AnomalyDetector()
    detector.run_detection_loop()

if __name__ == "__main__":
    main()
