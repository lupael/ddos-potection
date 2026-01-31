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
    
    # Execute mitigation based on action_type
    try:
        if mitigation.action_type == "firewall":
            # Apply iptables/nftables rules
            ip = mitigation.details.get('ip')
            protocol = mitigation.details.get('protocol')
            if ip:
                success = service.apply_iptables_rule('block', ip, protocol)
        
        elif mitigation.action_type == "bgp_blackhole":
            # Announce BGP blackhole (RTBH)
            prefix = mitigation.details.get('prefix')
            nexthop = mitigation.details.get('nexthop')
            if prefix:
                success = service.announce_bgp_blackhole(prefix, nexthop)
            else:
                error_message = "BGP blackhole requires a 'prefix' in CIDR notation (e.g., 192.0.2.1/32) in mitigation details"
        
        elif mitigation.action_type == "flowspec":
            # Send FlowSpec update
            source = mitigation.details.get('source')
            dest = mitigation.details.get('destination')
            protocol = mitigation.details.get('protocol')
            success = service.send_flowspec_rule(source, dest, protocol)
        
        else:
            error_message = f"Unknown action type: {mitigation.action_type}"
    
    except Exception as e:
        error_message = str(e)
    
    if success:
        mitigation.status = "active"
        db.commit()
        return {"message": "Mitigation executed successfully", "status": "active"}
    else:
        mitigation.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500, 
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
        mitigation.completed_at = datetime.utcnow()
        db.commit()
        return {"message": "Mitigation stopped successfully", "status": "completed"}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop mitigation: {error_message or 'Unknown error'}"
        )
