"""
Attack Map API endpoints for real-time visualization
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
import json
import asyncio

from database import get_db
from models.models import Alert, User
from routers.auth_router import get_current_user
import redis
from config import settings
from jose import jwt, JWTError

router = APIRouter()

# Redis client for real-time data
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


@router.get("/live-attacks")
async def get_live_attacks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time attack data for map visualization
    Returns active attacks with geographic information
    """
    # Get active alerts from last 10 minutes
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    active_alerts = db.query(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.status == 'active',
        Alert.created_at >= ten_min_ago
    ).order_by(desc(Alert.created_at)).limit(50).all()
    
    attacks = []
    for alert in active_alerts:
        # In a real implementation, you would lookup geolocation for IPs
        # For now, we'll create a simplified structure
        attack_data = {
            'id': alert.id,
            'type': alert.alert_type,
            'severity': alert.severity,
            'source_ip': alert.source_ip,
            'target_ip': alert.target_ip,
            'description': alert.description,
            'timestamp': alert.created_at.isoformat(),
            # Placeholder coordinates - in production, use a GeoIP service
            'source_location': get_ip_location(alert.source_ip),
            'target_location': get_ip_location(alert.target_ip)
        }
        attacks.append(attack_data)
    
    return {
        'total': len(attacks),
        'attacks': attacks,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }


@router.get("/attack-heatmap")
async def get_attack_heatmap(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get attack data for heatmap visualization
    Returns aggregated attack data by geographic region
    """
    time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get alerts grouped by target IP
    attack_stats = db.query(
        Alert.target_ip,
        Alert.alert_type,
        func.count(Alert.id).label('count'),
        func.max(Alert.severity).label('max_severity')
    ).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= time_ago
    ).group_by(Alert.target_ip, Alert.alert_type).all()
    
    heatmap_data = []
    for stat in attack_stats:
        location = get_ip_location(stat.target_ip)
        if location:
            heatmap_data.append({
                'target_ip': stat.target_ip,
                'attack_type': stat.alert_type,
                'count': stat.count,
                'severity': stat.max_severity,
                'location': location
            })
    
    return {
        'period_hours': hours,
        'heatmap': heatmap_data,
        'generated_at': datetime.now(timezone.utc).isoformat()
    }


@router.get("/attack-statistics")
async def get_attack_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get attack statistics for dashboard
    """
    # Last 24 hours
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # Total attacks
    total_attacks = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= last_24h
    ).scalar()
    
    # Active attacks
    active_attacks = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.status == 'active'
    ).scalar()
    
    # Attacks by type
    attacks_by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= last_24h
    ).group_by(Alert.alert_type).all()
    
    # Top targeted IPs
    top_targets = db.query(
        Alert.target_ip,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= last_24h
    ).group_by(Alert.target_ip).order_by(desc('count')).limit(10).all()
    
    return {
        'total_attacks_24h': total_attacks,
        'active_attacks': active_attacks,
        'attacks_by_type': {stat.alert_type: stat.count for stat in attacks_by_type},
        'top_targets': [{'ip': t.target_ip, 'count': t.count} for t in top_targets]
    }


@router.websocket("/ws/live-attacks")
async def websocket_live_attacks(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time attack updates
    Streams new attacks as they are detected
    Requires authentication via token query parameter
    """
    # Authenticate the WebSocket connection
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    try:
        # Verify JWT token
        from routers.auth_router import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Get user and ISP ID for filtering
        from models.models import User
        user = db.query(User).filter(User.username == username).first()
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
        
        isp_id = user.isp_id
        
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    await websocket.accept()
    
    # Subscribe to ISP-specific Redis channel for real-time alerts
    pubsub = redis_client.pubsub()
    # Subscribe to ISP-specific channel for tenant isolation
    pubsub.subscribe(f'alerts:new:{isp_id}')
    
    try:
        while True:
            # Check for new messages from Redis
            message = pubsub.get_message()
            if message and message['type'] == 'message':
                try:
                    alert_data = json.loads(message['data'])
                    
                    # Verify the alert belongs to this ISP (double-check)
                    if alert_data.get('isp_id') == isp_id:
                        # Add location data
                        alert_data['source_location'] = get_ip_location(alert_data.get('source_ip', 'unknown'))
                        alert_data['target_location'] = get_ip_location(alert_data.get('target_ip', 'unknown'))
                        
                        # Send to WebSocket client
                        await websocket.send_json({
                            'type': 'new_attack',
                            'data': alert_data
                        })
                except json.JSONDecodeError:
                    # Ignore malformed JSON messages
                    pass
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        print(f"WebSocket client disconnected (ISP: {isp_id})")
    finally:
        pubsub.close()


def get_ip_location(ip_address: str) -> Dict:
    """
    Get geographic location for an IP address
    In production, use a GeoIP service like MaxMind or ip-api.com
    
    For now, returns placeholder data
    """
    if not ip_address or ip_address == 'unknown':
        return None
    
    # Placeholder implementation
    # In production, integrate with GeoIP database or API
    # Example with ip-api.com (free tier):
    # response = requests.get(f"http://ip-api.com/json/{ip_address}")
    # data = response.json()
    # return {'lat': data['lat'], 'lon': data['lon'], 'country': data['country'], 'city': data['city']}
    
    # For demo purposes, assign random-ish locations based on IP hash
    import hashlib
    hash_val = int(hashlib.md5(ip_address.encode()).hexdigest(), 16)
    
    # Generate pseudo-random coordinates within reasonable ranges
    lat = (hash_val % 180) - 90  # -90 to 90
    lon = ((hash_val // 180) % 360) - 180  # -180 to 180
    
    return {
        'lat': lat / 1.0,
        'lon': lon / 1.0,
        'country': 'Unknown',
        'city': 'Unknown'
    }
