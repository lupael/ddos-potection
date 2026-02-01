from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from database import get_db
from models.models import TrafficLog, Alert
from routers.auth_router import get_current_user, User
from config import settings
import redis
from collections import Counter
import math

router = APIRouter()

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

@router.get("/config")
async def get_detection_config(current_user: User = Depends(get_current_user)):
    """
    Get current detection configuration.
    
    Returns:
        dict: Detection threshold configuration including SYN flood, UDP flood,
              ICMP flood, DNS amplification, and entropy thresholds.
    """
    return {
        "syn_flood_threshold": settings.SYN_FLOOD_THRESHOLD,
        "udp_flood_threshold": settings.UDP_FLOOD_THRESHOLD,
        "entropy_threshold": settings.ENTROPY_THRESHOLD,
        "icmp_flood_threshold": settings.ICMP_FLOOD_THRESHOLD,
        "dns_amplification_threshold": settings.DNS_AMPLIFICATION_THRESHOLD
    }

@router.get("/status")
async def get_collection_status(current_user: User = Depends(get_current_user)):
    """
    Get traffic collection status for NetFlow/sFlow/IPFIX collectors.
    
    Returns:
        dict: Status information for each collector type including ports and versions.
    
    Note: Currently returns static configuration. Future enhancement could check
          if collectors are actually listening on ports.
    """
    return {
        "netflow": {
            "enabled": True,
            "port": settings.NETFLOW_PORT,
            "version": ["v5", "v9"]
        },
        "sflow": {
            "enabled": True,
            "port": settings.SFLOW_PORT,
            "version": "v5"
        },
        "ipfix": {
            "enabled": True,
            "port": settings.IPFIX_PORT,
            "rfc": "5101"
        }
    }

@router.get("/routers")
async def get_router_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detected routers and their vendors.
    
    Returns:
        dict: List of detected routers with vendor info, flow counts per router,
              and last seen timestamps.
    
    Note: Router vendors are cached in Redis by the traffic_collector service.
          Flow statistics are queried per router from the database.
    """
    routers_list = []
    
    try:
        from sqlalchemy import func
        
        # Limit to first 50 routers to prevent performance issues
        router_count = 0
        max_routers = 50
        
        # Scan for router vendor keys in Redis
        for key in redis_client.scan_iter(match="router:vendor:*", count=100):
            if router_count >= max_routers:
                break
            
            router_ip = key.replace("router:vendor:", "")
            
            # Validate IP format using standard library
            try:
                import ipaddress
                ipaddress.ip_address(router_ip)
            except ValueError:
                continue  # Skip invalid IP addresses
            
            vendor = redis_client.get(key) or "Auto-detected"
            
            # Get flow count from database for this specific router and ISP
            # Note: This assumes traffic logs contain router identification
            # In practice, you may need to join with a router tracking table
            flow_stats = db.query(
                func.count(TrafficLog.id).label("flow_count"),
                func.max(TrafficLog.timestamp).label("last_seen")
            ).filter(
                TrafficLog.isp_id == current_user.isp_id
            ).first()
            
            if flow_stats:
                routers_list.append({
                    "ip": router_ip,
                    "vendor": vendor,
                    "flow_count": flow_stats.flow_count if flow_stats.flow_count else 0,
                    "last_seen": flow_stats.last_seen.isoformat() if flow_stats.last_seen else None
                })
                router_count += 1
                
    except redis.RedisError as e:
        print(f"Redis error fetching router info: {e}")
    except Exception as e:
        print(f"Database error fetching router info: {e}")
    
    # If no routers found in cache, return empty list with helpful message
    if not routers_list:
        try:
            from sqlalchemy import func
            recent_stats = db.query(
                func.count(TrafficLog.id).label("total_flows"),
                func.max(TrafficLog.timestamp).label("last_activity")
            ).filter(
                TrafficLog.isp_id == current_user.isp_id
            ).first()
            
            return {
                "routers": [],
                "total_flows": recent_stats.total_flows if recent_stats and recent_stats.total_flows else 0,
                "last_activity": recent_stats.last_activity.isoformat() if recent_stats and recent_stats.last_activity else None
            }
        except Exception as e:
            print(f"Error fetching fallback stats: {e}")
            return {"routers": [], "total_flows": 0, "last_activity": None}
    
    return {"routers": routers_list}

@router.get("/entropy")
async def get_entropy_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time entropy analysis on recent traffic.
    
    Analyzes up to 5000 flow records from the last 5 minutes to calculate
    multi-dimensional Shannon entropy and detect attack patterns.
    
    Returns:
        dict: Entropy values for source/destination IPs and protocols,
              detected attack pattern, and sample size.
    """
    # Get recent traffic logs
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    
    try:
        logs = db.query(TrafficLog).filter(
            TrafficLog.isp_id == current_user.isp_id,
            TrafficLog.timestamp >= five_min_ago
        ).order_by(TrafficLog.timestamp.desc()).limit(5000).all()
    except Exception as e:
        print(f"Database error in entropy analysis: {e}")
        return {
            "source_entropy": 0.0,
            "destination_entropy": 0.0,
            "protocol_entropy": 0.0,
            "attack_pattern": "error",
            "sample_size": 0
        }
    
    if not logs or len(logs) < 10:
        return {
            "source_entropy": 0.0,
            "destination_entropy": 0.0,
            "protocol_entropy": 0.0,
            "attack_pattern": "none",
            "sample_size": 0
        }
    
    # Calculate entropy for different dimensions using a single pass
    # More memory efficient than creating three separate lists
    source_counts = Counter()
    dest_counts = Counter()
    protocol_counts = Counter()
    
    for log in logs:
        source_counts[log.source_ip] += 1
        dest_counts[log.dest_ip] += 1
        protocol_counts[log.protocol] += 1
    
    def calculate_entropy_from_counter(frequencies: Counter, total: int) -> float:
        """
        Calculate Shannon entropy from a frequency counter.
        
        Args:
            frequencies: Counter object with item frequencies
            total: Total number of items
            
        Returns:
            float: Shannon entropy value
        """
        if not frequencies or total <= 0:
            return 0.0
        
        entropy = 0.0
        for count in frequencies.values():
            probability = count / total
            if probability > 0:  # Avoid log(0)
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    total_logs = len(logs)
    src_entropy = calculate_entropy_from_counter(source_counts, total_logs)
    dst_entropy = calculate_entropy_from_counter(dest_counts, total_logs)
    proto_entropy = calculate_entropy_from_counter(protocol_counts, total_logs)
    
    # Determine attack pattern using configurable thresholds
    attack_pattern = "normal"
    if src_entropy < settings.ENTROPY_THRESHOLD and dst_entropy < 1.0:
        attack_pattern = "distributed_ddos"
    elif src_entropy > settings.VOLUMETRIC_SRC_ENTROPY_THRESHOLD and dst_entropy < settings.VOLUMETRIC_DST_ENTROPY_THRESHOLD:
        attack_pattern = "volumetric_attack"
    elif src_entropy > settings.SCANNING_SRC_ENTROPY_THRESHOLD and dst_entropy > settings.SCANNING_DST_ENTROPY_THRESHOLD:
        attack_pattern = "scanning"
    
    return {
        "source_entropy": round(src_entropy, 2),
        "destination_entropy": round(dst_entropy, 2),
        "protocol_entropy": round(proto_entropy, 2),
        "attack_pattern": attack_pattern,
        "sample_size": len(logs),
        "threshold": settings.ENTROPY_THRESHOLD
    }

@router.get("/detection/stats")
async def get_detection_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detection statistics for the last 24 hours.
    
    Returns alert counts by detection type (SYN flood, UDP flood, etc.)
    for the current ISP.
    
    Returns:
        dict: Detection counts by type and time period.
    """
    from sqlalchemy import func
    
    # Get alert counts by type in last 24 hours
    one_day_ago = datetime.utcnow() - timedelta(hours=24)
    
    try:
        alert_stats = db.query(
            Alert.alert_type,
            func.count(Alert.id).label("count")
        ).filter(
            Alert.isp_id == current_user.isp_id,
            Alert.created_at >= one_day_ago
        ).group_by(Alert.alert_type).all()
    except Exception as e:
        print(f"Database error fetching detection stats: {e}")
        return {
            "detection_types": {
                "syn_flood": 0,
                "udp_flood": 0,
                "icmp_flood": 0,
                "dns_amplification": 0,
                "distributed_ddos": 0,
                "volumetric_attack": 0
            },
            "period": "24h"
        }
    
    return {
        "detection_types": {
            "syn_flood": next((s.count for s in alert_stats if s.alert_type == "syn_flood"), 0),
            "udp_flood": next((s.count for s in alert_stats if s.alert_type == "udp_flood"), 0),
            "icmp_flood": next((s.count for s in alert_stats if s.alert_type == "icmp_flood"), 0),
            "dns_amplification": next((s.count for s in alert_stats if s.alert_type == "dns_amplification"), 0),
            "distributed_ddos": next((s.count for s in alert_stats if s.alert_type == "distributed_ddos"), 0),
            "volumetric_attack": next((s.count for s in alert_stats if s.alert_type == "volumetric_attack"), 0)
        },
        "period": "24h"
    }
