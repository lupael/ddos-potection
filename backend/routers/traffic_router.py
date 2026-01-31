from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models.models import TrafficLog
from routers.auth_router import get_current_user, User

router = APIRouter()

class TrafficStats(BaseModel):
    timestamp: datetime
    total_packets: int
    total_bytes: int
    anomalies: int

@router.get("/stats")
async def get_traffic_stats(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real-time traffic statistics"""
    logs = db.query(TrafficLog).filter(
        TrafficLog.isp_id == current_user.isp_id
    ).order_by(TrafficLog.timestamp.desc()).limit(limit).all()
    
    return {
        "total_entries": len(logs),
        "logs": [
            {
                "timestamp": log.timestamp,
                "source_ip": log.source_ip,
                "dest_ip": log.dest_ip,
                "protocol": log.protocol,
                "packets": log.packets,
                "bytes": log.bytes,
                "is_anomaly": log.is_anomaly
            }
            for log in logs
        ]
    }

@router.get("/realtime")
async def get_realtime_traffic(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real-time traffic data for dashboard"""
    from sqlalchemy import func
    
    # Get traffic in last 5 minutes
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    
    stats = db.query(
        func.sum(TrafficLog.packets).label("total_packets"),
        func.sum(TrafficLog.bytes).label("total_bytes"),
        func.count(TrafficLog.id).label("total_flows")
    ).filter(
        TrafficLog.isp_id == current_user.isp_id,
        TrafficLog.timestamp >= five_min_ago
    ).first()
    
    return {
        "total_packets": stats.total_packets or 0,
        "total_bytes": stats.total_bytes or 0,
        "total_flows": stats.total_flows or 0,
        "timeframe": "5_minutes"
    }

from datetime import timedelta

@router.get("/protocols")
async def get_protocol_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get protocol distribution"""
    from sqlalchemy import func
    
    protocols = db.query(
        TrafficLog.protocol,
        func.count(TrafficLog.id).label("count"),
        func.sum(TrafficLog.bytes).label("bytes")
    ).filter(
        TrafficLog.isp_id == current_user.isp_id
    ).group_by(TrafficLog.protocol).all()
    
    return {
        "protocols": [
            {
                "protocol": p.protocol,
                "count": p.count,
                "bytes": p.bytes
            }
            for p in protocols
        ]
    }
