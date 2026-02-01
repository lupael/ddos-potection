from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.models import ISP, User
from routers.auth_router import get_current_user, get_password_hash

router = APIRouter()

class ISPUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    subscription_plan: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "viewer"

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

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

@router.get("/users", response_model=List[UserResponse])
async def list_isp_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all users in the ISP (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = db.query(User).filter(User.isp_id == current_user.isp_id).all()
    return users

@router.post("/users", response_model=UserResponse)
async def create_isp_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user in the ISP (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate role
    if user_data.role not in ["admin", "operator", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, operator, or viewer")
    
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        isp_id=current_user.isp_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_isp_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a user in the ISP (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.isp_id == current_user.isp_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role if provided
    if user_update.role and user_update.role not in ["admin", "operator", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, operator, or viewer")
    
    # Update user fields
    if user_update.email:
        # Check if email is already taken by another user
        existing_email = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = user_update.email
    
    if user_update.role:
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}")
async def delete_isp_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user from the ISP (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.isp_id == current_user.isp_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete your own account. Please have another admin delete this account or transfer admin rights first."
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for the ISP"""
    from models.models import Alert, Rule, TrafficLog
    from sqlalchemy import func
    from datetime import timedelta
    
    # Get counts
    total_users = db.query(func.count(User.id)).filter(User.isp_id == current_user.isp_id).scalar()
    total_rules = db.query(func.count(Rule.id)).filter(Rule.isp_id == current_user.isp_id).scalar()
    active_alerts = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.status == "active"
    ).scalar()
    
    # Get ISP info
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    
    # Get recent activity
    recent_alerts = db.query(Alert).filter(
        Alert.isp_id == current_user.isp_id
    ).order_by(Alert.created_at.desc()).limit(5).all()
    
    return {
        "isp": {
            "name": isp.name,
            "subscription_plan": isp.subscription_plan,
            "subscription_status": isp.subscription_status
        },
        "stats": {
            "total_users": total_users,
            "total_rules": total_rules,
            "active_alerts": active_alerts
        },
        "recent_alerts": [
            {
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "created_at": alert.created_at
            }
            for alert in recent_alerts
        ]
    }
