from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from models.models import Alert, User
from routers.auth_router import get_current_user

router = APIRouter()

class AlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    source_ip: str
    target_ip: str
    description: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all alerts for the ISP"""
    query = db.query(Alert).filter(Alert.isp_id == current_user.isp_id)
    
    if status:
        query = query.filter(Alert.status == status)
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    return alerts

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific alert"""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.isp_id == current_user.isp_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return alert

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark an alert as resolved"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.isp_id == current_user.isp_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Alert resolved successfully"}

@router.get("/stats/summary")
async def get_alert_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get alert statistics summary"""
    from sqlalchemy import func
    
    stats = db.query(
        Alert.status,
        func.count(Alert.id).label("count")
    ).filter(
        Alert.isp_id == current_user.isp_id
    ).group_by(Alert.status).all()
    
    severity_stats = db.query(
        Alert.severity,
        func.count(Alert.id).label("count")
    ).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.status == "active"
    ).group_by(Alert.severity).all()
    
    return {
        "by_status": {s.status: s.count for s in stats},
        "by_severity": {s.severity: s.count for s in severity_stats}
    }
