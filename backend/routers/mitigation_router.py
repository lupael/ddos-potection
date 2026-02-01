from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from database import get_db
from models.models import MitigationAction, Alert, User
from routers.auth_router import get_current_user

router = APIRouter()

class MitigationCreate(BaseModel):
    alert_id: int
    action_type: str
    details: dict

class MitigationResponse(BaseModel):
    id: int
    alert_id: int
    action_type: str
    details: dict
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[MitigationResponse])
async def list_mitigations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all mitigation actions"""
    mitigations = db.query(MitigationAction).join(Alert).filter(
        Alert.isp_id == current_user.isp_id
    ).all()
    return mitigations

@router.post("/", response_model=MitigationResponse)
async def create_mitigation(
    mitigation: MitigationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new mitigation action"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify alert belongs to user's ISP
    alert = db.query(Alert).filter(
        Alert.id == mitigation.alert_id,
        Alert.isp_id == current_user.isp_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db_mitigation = MitigationAction(
        alert_id=mitigation.alert_id,
        action_type=mitigation.action_type,
        details=mitigation.details,
        status="pending"
    )
    db.add(db_mitigation)
    db.commit()
    db.refresh(db_mitigation)
    
    # Trigger actual mitigation action
    # This would call services to apply firewall rules, BGP updates, etc.
    
    return db_mitigation

@router.post("/{mitigation_id}/execute")
async def execute_mitigation(
    mitigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a mitigation action"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    mitigation = db.query(MitigationAction).join(Alert).filter(
        MitigationAction.id == mitigation_id,
        Alert.isp_id == current_user.isp_id
    ).first()
    
    if not mitigation:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    
    # Import mitigation service
    from services.mitigation_service import MitigationService
    service = MitigationService()
    
    success = False
    error_message = None
    is_client_error = False
    
    # Execute mitigation based on action_type
    try:
        if mitigation.action_type == "firewall":
            # Apply iptables/nftables rules
            ip = mitigation.details.get('ip')
            protocol = mitigation.details.get('protocol')
            if ip:
                success = service.apply_iptables_rule('block', ip, protocol)
            else:
                error_message = "Firewall mitigation requires an 'ip' address in mitigation details"
                is_client_error = True
        
        elif mitigation.action_type == "bgp_blackhole":
            # Announce BGP blackhole (RTBH)
            prefix = mitigation.details.get('prefix')
            nexthop = mitigation.details.get('nexthop')
            if prefix:
                success = service.announce_bgp_blackhole(prefix, nexthop)
            else:
                error_message = "BGP blackhole requires a 'prefix' in CIDR notation (e.g., 192.0.2.1/32) in mitigation details"
                is_client_error = True
        
        elif mitigation.action_type == "flowspec":
            # Send FlowSpec update
            source = mitigation.details.get('source')
            dest = mitigation.details.get('destination')
            protocol = mitigation.details.get('protocol')
            success = service.send_flowspec_rule(source, dest, protocol)
        
        else:
            error_message = f"Unknown action type: {mitigation.action_type}"
            is_client_error = True
    
    except Exception as e:
        error_message = str(e)
    
    if success:
        mitigation.status = "active"
        db.commit()
        return {"message": "Mitigation executed successfully", "status": "active"}
    else:
        # Determine HTTP status code based on error type
        status_code = 400 if is_client_error else 500
        
        # Only mark as failed for server errors, not client errors
        if status_code >= 500:
            mitigation.status = "failed"
            db.commit()
        
        raise HTTPException(
            status_code=status_code,
            detail=f"Mitigation execution failed: {error_message or 'Unknown error'}"
        )

@router.post("/{mitigation_id}/stop")
async def stop_mitigation(
    mitigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop a mitigation action"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    mitigation = db.query(MitigationAction).join(Alert).filter(
        MitigationAction.id == mitigation_id,
        Alert.isp_id == current_user.isp_id
    ).first()
    
    if not mitigation:
        raise HTTPException(status_code=404, detail="Mitigation not found")
    
    # Import mitigation service
    from services.mitigation_service import MitigationService
    service = MitigationService()
    
    success = False
    error_message = None
    
    # Stop mitigation based on action_type
    try:
        if mitigation.action_type == "firewall":
            # Remove iptables/nftables rules
            ip = mitigation.details.get('ip')
            protocol = mitigation.details.get('protocol')
            if ip:
                success = service.apply_iptables_rule('unblock', ip, protocol)
        
        elif mitigation.action_type == "bgp_blackhole":
            # Withdraw BGP blackhole route
            prefix = mitigation.details.get('prefix')
            if prefix:
                success = service.withdraw_bgp_blackhole(prefix)
            else:
                error_message = "Missing 'prefix' in mitigation details"
        
        elif mitigation.action_type == "flowspec":
            # Withdraw FlowSpec rule (implementation depends on BGP daemon)
            success = True  # Placeholder
        
        else:
            error_message = f"Unknown action type: {mitigation.action_type}"
    
    except Exception as e:
        error_message = str(e)
    
    if success:
        mitigation.status = "completed"
        mitigation.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"message": "Mitigation stopped successfully", "status": "completed"}
    else:
        # Persist the failure state so operators can see it
        mitigation.status = "failed"
        if error_message:
            # Store error in details for debugging
            if not mitigation.details:
                mitigation.details = {}
            mitigation.details['stop_error'] = error_message
        db.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop mitigation: {error_message or 'Unknown error'}"
        )


@router.get("/status/active")
async def get_active_mitigations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active mitigations with detailed status"""
    from sqlalchemy import func
    
    active_mitigations = db.query(
        MitigationAction,
        Alert.target_ip,
        Alert.source_ip,
        Alert.alert_type,
        Alert.severity
    ).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.status == 'active'
    ).all()
    
    result = []
    for mitigation, target_ip, source_ip, alert_type, severity in active_mitigations:
        duration_seconds = (datetime.now(timezone.utc) - mitigation.created_at).total_seconds()
        result.append({
            'id': mitigation.id,
            'alert_id': mitigation.alert_id,
            'action_type': mitigation.action_type,
            'status': mitigation.status,
            'details': mitigation.details,
            'created_at': mitigation.created_at.isoformat(),
            'duration_seconds': int(duration_seconds),
            'alert': {
                'type': alert_type,
                'severity': severity,
                'target_ip': target_ip,
                'source_ip': source_ip
            }
        })
    
    return {
        'total': len(result),
        'mitigations': result
    }


@router.get("/status/history")
async def get_mitigation_history(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mitigation history with statistics"""
    from sqlalchemy import func
    from datetime import timedelta, timezone
    
    time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get historical mitigations
    history = db.query(MitigationAction, Alert).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.created_at >= time_ago
    ).order_by(MitigationAction.created_at.desc()).limit(100).all()
    
    # Statistics
    stats = db.query(
        MitigationAction.action_type,
        MitigationAction.status,
        func.count(MitigationAction.id).label('count')
    ).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.created_at >= time_ago
    ).group_by(MitigationAction.action_type, MitigationAction.status).all()
    
    # Calculate average duration for completed mitigations
    avg_durations = db.query(
        MitigationAction.action_type,
        func.avg(
            func.extract('epoch', MitigationAction.completed_at - MitigationAction.created_at)
        ).label('avg_duration')
    ).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.status == 'completed',
        MitigationAction.completed_at.isnot(None),
        MitigationAction.created_at >= time_ago
    ).group_by(MitigationAction.action_type).all()
    
    # Format history
    history_list = []
    for mitigation, alert in history:
        duration_seconds = None
        if mitigation.completed_at:
            duration_seconds = (mitigation.completed_at - mitigation.created_at).total_seconds()
        
        history_list.append({
            'id': mitigation.id,
            'action_type': mitigation.action_type,
            'status': mitigation.status,
            'created_at': mitigation.created_at.isoformat(),
            'completed_at': mitigation.completed_at.isoformat() if mitigation.completed_at else None,
            'duration_seconds': int(duration_seconds) if duration_seconds else None,
            'alert': {
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'target_ip': alert.target_ip
            }
        })
    
    # Format statistics
    stats_by_type = {}
    for stat in stats:
        if stat.action_type not in stats_by_type:
            stats_by_type[stat.action_type] = {}
        stats_by_type[stat.action_type][stat.status] = stat.count
    
    # Format average durations
    avg_duration_by_type = {d.action_type: int(d.avg_duration) for d in avg_durations if d.avg_duration}
    
    return {
        'period_hours': hours,
        'total_mitigations': len(history_list),
        'history': history_list,
        'statistics': {
            'by_type_and_status': stats_by_type,
            'average_duration_seconds': avg_duration_by_type
        }
    }


@router.get("/status/analytics")
async def get_mitigation_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive mitigation analytics"""
    from sqlalchemy import func
    from datetime import timedelta, timezone
    
    now = datetime.now(timezone.utc)
    
    # Last 24 hours
    last_24h = now - timedelta(hours=24)
    
    # Total mitigations by period
    total_24h = db.query(func.count(MitigationAction.id)).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.created_at >= last_24h
    ).scalar() or 0
    
    # Active mitigations
    active_count = db.query(func.count(MitigationAction.id)).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.status == 'active'
    ).scalar() or 0
    
    # Success rate (completed vs failed)
    total_completed_or_failed = db.query(func.count(MitigationAction.id)).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.status.in_(['completed', 'failed']),
        MitigationAction.created_at >= last_24h
    ).scalar() or 0
    
    completed_count = db.query(func.count(MitigationAction.id)).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.status == 'completed',
        MitigationAction.created_at >= last_24h
    ).scalar() or 0
    
    success_rate = (completed_count / total_completed_or_failed * 100) if total_completed_or_failed > 0 else 0
    
    # Most used mitigation types
    most_used = db.query(
        MitigationAction.action_type,
        func.count(MitigationAction.id).label('count')
    ).join(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        MitigationAction.created_at >= last_24h
    ).group_by(MitigationAction.action_type).order_by(func.count(MitigationAction.id).desc()).all()
    
    # Average response time (time from alert creation to mitigation creation)
    # This would require joining with alerts and calculating the difference
    
    return {
        'period': '24h',
        'total_mitigations': total_24h,
        'active_mitigations': active_count,
        'success_rate_percent': round(success_rate, 2),
        'most_used_types': [{'type': m.action_type, 'count': m.count} for m in most_used]
    }
