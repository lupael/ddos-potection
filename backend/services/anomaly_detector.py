"""
Anomaly detection engine for DDoS attacks
"""
import redis
import time
from datetime import datetime, timedelta
from typing import Dict, List
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
            db=settings.REDIS_DB
        )
    
    def detect_syn_flood(self, isp_id: int = 1) -> bool:
        """Detect SYN flood attacks"""
        db = SessionLocal()
        try:
            # Check TCP traffic in last minute
            one_min_ago = datetime.utcnow() - timedelta(minutes=1)
            
            tcp_packets = db.query(TrafficLog).filter(
                TrafficLog.isp_id == isp_id,
                TrafficLog.protocol == 'TCP',
                TrafficLog.timestamp >= one_min_ago
            ).all()
            
            # Count SYN packets per destination
            syn_counts = defaultdict(int)
            for log in tcp_packets:
                if log.flags and 'S' in log.flags:
                    syn_counts[log.dest_ip] += log.packets
            
            # Check threshold
            for dest_ip, count in syn_counts.items():
                if count > settings.SYN_FLOOD_THRESHOLD:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='syn_flood',
                        severity='high',
                        target_ip=dest_ip,
                        description=f'SYN flood detected: {count} SYN packets/min to {dest_ip}'
                    )
                    return True
            
            return False
        finally:
            db.close()
    
    def detect_udp_flood(self, isp_id: int = 1) -> bool:
        """Detect UDP flood attacks"""
        db = SessionLocal()
        try:
            one_min_ago = datetime.utcnow() - timedelta(minutes=1)
            
            from sqlalchemy import func
            udp_stats = db.query(
                TrafficLog.dest_ip,
                func.sum(TrafficLog.packets).label('total_packets')
            ).filter(
                TrafficLog.isp_id == isp_id,
                TrafficLog.protocol == 'UDP',
                TrafficLog.timestamp >= one_min_ago
            ).group_by(TrafficLog.dest_ip).all()
            
            for stat in udp_stats:
                if stat.total_packets > settings.UDP_FLOOD_THRESHOLD:
                    self.create_alert(
                        isp_id=isp_id,
                        alert_type='udp_flood',
                        severity='high',
                        target_ip=stat.dest_ip,
                        description=f'UDP flood detected: {stat.total_packets} packets/min to {stat.dest_ip}'
                    )
                    return True
            
            return False
        finally:
            db.close()
    
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
        """Detect anomalies using entropy analysis"""
        db = SessionLocal()
        try:
            one_min_ago = datetime.utcnow() - timedelta(minutes=1)
            
            logs = db.query(TrafficLog).filter(
                TrafficLog.isp_id == isp_id,
                TrafficLog.timestamp >= one_min_ago
            ).all()
            
            # Analyze source IP entropy
            source_ips = [log.source_ip for log in logs]
            entropy = self.calculate_entropy(source_ips)
            
            # Low entropy indicates possible DDoS (many packets from few sources)
            if entropy < settings.ENTROPY_THRESHOLD:
                top_sources = defaultdict(int)
                for ip in source_ips:
                    top_sources[ip] += 1
                
                top_attacker = max(top_sources.items(), key=lambda x: x[1])[0]
                
                self.create_alert(
                    isp_id=isp_id,
                    alert_type='entropy_anomaly',
                    severity='medium',
                    source_ip=top_attacker,
                    target_ip='various',
                    description=f'Low entropy detected ({entropy:.2f}): possible DDoS from concentrated sources'
                )
                return True
            
            return False
        finally:
            db.close()
    
    def create_alert(self, isp_id: int, alert_type: str, severity: str, 
                     target_ip: str, description: str, source_ip: str = 'unknown'):
        """Create an alert in the database"""
        db = SessionLocal()
        try:
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
            
            # Store in Redis for real-time dashboard
            alert_key = f"alert:{alert.id}"
            self.redis_client.setex(
                alert_key,
                3600,  # 1 hour TTL
                f"{alert_type}:{severity}:{target_ip}"
            )
            
            print(f"Alert created: {alert_type} - {description}")
        finally:
            db.close()
    
    def run_detection_loop(self):
        """Main detection loop"""
        print("Starting anomaly detection engine...")
        
        while True:
            try:
                # Run all detections
                self.detect_syn_flood()
                self.detect_udp_flood()
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
