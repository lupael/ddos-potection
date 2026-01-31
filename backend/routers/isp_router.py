from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from models.models import ISP, User
from routers.auth_router import get_current_user

router = APIRouter()

class ISPUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    subscription_plan: Optional[str] = None

class ISPResponse(BaseModel):
    id: int
    name: str
    email: str
    subscription_status: str
    subscription_plan: str
    api_key: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/me", response_model=ISPResponse)
async def get_my_isp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's ISP information"""
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    if not isp:
        raise HTTPException(status_code=404, detail="ISP not found")
    return isp

@router.put("/me", response_model=ISPResponse)
async def update_my_isp(
    isp_update: ISPUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update ISP information (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    if not isp:
        raise HTTPException(status_code=404, detail="ISP not found")
    
    for key, value in isp_update.dict(exclude_unset=True).items():
        setattr(isp, key, value)
    
    db.commit()
    db.refresh(isp)
    return isp

@router.post("/regenerate-api-key")
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate API key (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    import secrets
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    if not isp:
        raise HTTPException(status_code=404, detail="ISP not found")
    
    isp.api_key = secrets.token_urlsafe(32)
    db.commit()
    
    return {"api_key": isp.api_key}

@router.get("/users")
async def list_isp_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all users in the ISP (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = db.query(User).filter(User.isp_id == current_user.isp_id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at
        }
        for u in users
    ]
