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
    
    # Execute mitigation based on action_type
    if mitigation.action_type == "firewall":
        # Apply iptables/nftables rules
        pass
    elif mitigation.action_type == "bgp_blackhole":
        # Announce BGP blackhole
        pass
    elif mitigation.action_type == "flowspec":
        # Send FlowSpec update
        pass
    
    mitigation.status = "active"
    mitigation.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Mitigation executed successfully", "status": "active"}

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
    
    mitigation.status = "completed"
    mitigation.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Mitigation stopped successfully", "status": "completed"}
