"""
Prometheus metrics collector for DDoS protection platform
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
import time
from datetime import datetime, timedelta, timezone
from typing import Dict

from database import SessionLocal
from models.models import Alert, TrafficLog, MitigationAction
from config import settings

# Create a global registry
registry = CollectorRegistry()

# Traffic Metrics
traffic_packets_total = Counter(
    'ddos_traffic_packets_total',
    'Total packets processed',
    ['isp_id', 'protocol'],
    registry=registry
)

traffic_bytes_total = Counter(
    'ddos_traffic_bytes_total',
    'Total bytes processed',
    ['isp_id', 'protocol'],
    registry=registry
)

traffic_flows_total = Counter(
    'ddos_traffic_flows_total',
    'Total flows processed',
    ['isp_id'],
    registry=registry
)

# Alert Metrics
alerts_total = Counter(
    'ddos_alerts_total',
    'Total alerts generated',
    ['isp_id', 'alert_type', 'severity'],
    registry=registry
)

alerts_active = Gauge(
    'ddos_alerts_active',
    'Number of active alerts',
    ['isp_id', 'severity'],
    registry=registry
)

alerts_resolved_total = Counter(
    'ddos_alerts_resolved_total',
    'Total alerts resolved',
    ['isp_id', 'alert_type'],
    registry=registry
)

# Mitigation Metrics
mitigations_total = Counter(
    'ddos_mitigations_total',
    'Total mitigations applied',
    ['isp_id', 'action_type'],
    registry=registry
)

mitigations_active = Gauge(
    'ddos_mitigations_active',
    'Number of active mitigations',
    ['isp_id', 'action_type'],
    registry=registry
)

mitigation_duration_seconds = Histogram(
    'ddos_mitigation_duration_seconds',
    'Duration of mitigations in seconds',
    ['isp_id', 'action_type'],
    registry=registry
)

# Attack Detection Metrics
attacks_detected_total = Counter(
    'ddos_attacks_detected_total',
    'Total attacks detected',
    ['isp_id', 'attack_type'],
    registry=registry
)

attack_volume_packets = Gauge(
    'ddos_attack_volume_packets',
    'Current attack volume in packets per second',
    ['isp_id', 'target_ip'],
    registry=registry
)

attack_volume_bytes = Gauge(
    'ddos_attack_volume_bytes',
    'Current attack volume in bytes per second',
    ['isp_id', 'target_ip'],
    registry=registry
)

# System Health Metrics
system_health = Gauge(
    'ddos_system_health',
    'System health status (1=healthy, 0=unhealthy)',
    ['component'],
    registry=registry
)

api_requests_total = Counter(
    'ddos_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

api_request_duration_seconds = Histogram(
    'ddos_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

# Database Metrics
database_connections = Gauge(
    'ddos_database_connections',
    'Number of database connections',
    ['state'],
    registry=registry
)

database_query_duration_seconds = Histogram(
    'ddos_database_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    registry=registry
)


class MetricsCollector:
    """Collect and update Prometheus metrics from the database"""
    
    def __init__(self):
        self.registry = registry
    
    def update_alert_metrics(self):
        """Update alert-related metrics from database"""
        db = SessionLocal()
        try:
            # Count active alerts by severity
            from sqlalchemy import func
            
            active_alerts = db.query(
                Alert.isp_id,
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                Alert.status == 'active'
            ).group_by(Alert.isp_id, Alert.severity).all()
            
            # Clear existing gauges
            for isp_id in [1]:  # Can expand to all ISPs
                for severity in ['low', 'medium', 'high', 'critical']:
                    alerts_active.labels(isp_id=str(isp_id), severity=severity).set(0)
            
            # Update gauges
            for alert in active_alerts:
                alerts_active.labels(
                    isp_id=str(alert.isp_id),
                    severity=alert.severity
                ).set(alert.count)
            
        except Exception as e:
            print(f"Error updating alert metrics: {e}")
        finally:
            db.close()
    
    def update_mitigation_metrics(self):
        """Update mitigation-related metrics from database"""
        db = SessionLocal()
        try:
            from sqlalchemy import func
            
            # Count active mitigations by type
            active_mitigations = db.query(
                MitigationAction.action_type,
                func.count(MitigationAction.id).label('count')
            ).filter(
                MitigationAction.status == 'active'
            ).group_by(MitigationAction.action_type).all()
            
            # Clear existing gauges
            for action_type in ['firewall', 'bgp_blackhole', 'flowspec', 'rate_limit']:
                mitigations_active.labels(isp_id='1', action_type=action_type).set(0)
            
            # Update gauges
            for mitigation in active_mitigations:
                mitigations_active.labels(
                    isp_id='1',
                    action_type=mitigation.action_type
                ).set(mitigation.count)
            
            # Calculate mitigation durations for completed mitigations
            completed_mitigations = db.query(MitigationAction).filter(
                MitigationAction.status == 'completed',
                MitigationAction.completed_at.isnot(None),
                MitigationAction.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).all()
            
            for mitigation in completed_mitigations:
                duration = (mitigation.completed_at - mitigation.created_at).total_seconds()
                mitigation_duration_seconds.labels(
                    isp_id='1',
                    action_type=mitigation.action_type
                ).observe(duration)
            
        except Exception as e:
            print(f"Error updating mitigation metrics: {e}")
        finally:
            db.close()
    
    def update_traffic_metrics(self):
        """Update traffic-related metrics from database"""
        db = SessionLocal()
        try:
            from sqlalchemy import func
            
            # Get traffic stats from last minute
            one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
            
            traffic_stats = db.query(
                TrafficLog.protocol,
                func.sum(TrafficLog.packets).label('total_packets'),
                func.sum(TrafficLog.bytes).label('total_bytes'),
                func.count(TrafficLog.id).label('flow_count')
            ).filter(
                TrafficLog.timestamp >= one_min_ago
            ).group_by(TrafficLog.protocol).all()
            
            # Note: These counters should only increment with new data
            # In a production implementation, we would need to track which records
            # have already been counted to avoid double-counting.
            # For now, we skip incrementing to avoid incorrect cumulative values.
            # A better approach would be to use a separate tracking table or
            # implement this as a background job that processes new records.
            
            # Future implementation:
            # - Add a 'processed_for_metrics' flag to TrafficLog
            # - Only count unprocessed records
            # - Mark records as processed after counting
            
        except Exception as e:
            print(f"Error updating traffic metrics: {e}")
        finally:
            db.close()
    
    def update_system_health(self):
        """Update system health metrics"""
        try:
            # Check Redis connectivity
            import redis
            try:
                r = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    socket_connect_timeout=2
                )
                r.ping()
                system_health.labels(component='redis').set(1)
            except:
                system_health.labels(component='redis').set(0)
            
            # Check database connectivity
            try:
                db = SessionLocal()
                db.execute("SELECT 1")
                db.close()
                system_health.labels(component='database').set(1)
            except:
                system_health.labels(component='database').set(0)
            
            # Check API health (always 1 if this code is running)
            system_health.labels(component='api').set(1)
            
        except Exception as e:
            print(f"Error updating system health metrics: {e}")
    
    def collect_all_metrics(self):
        """Collect all metrics from database"""
        self.update_alert_metrics()
        self.update_mitigation_metrics()
        self.update_traffic_metrics()
        self.update_system_health()
    
    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format"""
        self.collect_all_metrics()
        return generate_latest(self.registry)


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_content():
    """Get metrics content for HTTP response"""
    return metrics_collector.get_metrics()
