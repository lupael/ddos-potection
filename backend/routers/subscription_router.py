from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from database import get_db
from models.models import ISP, User, Subscription
from routers.auth_router import get_current_user

router = APIRouter()

# Subscription plan pricing
SUBSCRIPTION_PLANS = {
    "basic": {"price": Decimal("29.99"), "features": ["Up to 1 Gbps protection", "Basic dashboard", "Email alerts"]},
    "professional": {"price": Decimal("99.99"), "features": ["Up to 10 Gbps protection", "Advanced analytics", "24/7 support", "SMS alerts"]},
    "enterprise": {"price": Decimal("299.99"), "features": ["Unlimited protection", "Custom rules", "Dedicated support", "All integrations"]}
}

class SubscriptionCreate(BaseModel):
    plan_name: str
    billing_cycle: str = "monthly"

class SubscriptionUpdate(BaseModel):
    auto_renew: Optional[bool] = None

class SubscriptionResponse(BaseModel):
    id: int
    plan_name: str
    plan_price: Decimal
    billing_cycle: str
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    auto_renew: bool
    
    class Config:
        from_attributes = True

@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "name": plan_name,
                "price": str(details["price"]),
                "features": details["features"]
            }
            for plan_name, details in SUBSCRIPTION_PLANS.items()
        ]
    }

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current active subscription for the ISP"""
    subscription = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    return subscription

@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate plan
    if subscription_data.plan_name not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    # Validate billing cycle
    if subscription_data.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid billing cycle. Must be 'monthly' or 'yearly'")
    
    # Check if there's an active subscription
    active_sub = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id,
        Subscription.status == "active"
    ).first()
    
    if active_sub:
        raise HTTPException(status_code=400, detail="Active subscription already exists. Please cancel or upgrade.")
    
    # Calculate end date
    start_date = datetime.utcnow()
    if subscription_data.billing_cycle == "monthly":
        end_date = start_date + timedelta(days=30)
    else:  # yearly
        end_date = start_date + timedelta(days=365)
    
    plan_details = SUBSCRIPTION_PLANS[subscription_data.plan_name]
    
    # Create subscription
    new_subscription = Subscription(
        isp_id=current_user.isp_id,
        plan_name=subscription_data.plan_name,
        plan_price=plan_details["price"],
        billing_cycle=subscription_data.billing_cycle,
        status="active",
        start_date=start_date,
        end_date=end_date,
        auto_renew=True
    )
    db.add(new_subscription)
    
    # Update ISP subscription info
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    isp.subscription_plan = subscription_data.plan_name
    isp.subscription_status = "active"
    
    db.commit()
    db.refresh(new_subscription)
    
    return new_subscription

@router.put("/upgrade")
async def upgrade_subscription(
    new_plan: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade/downgrade subscription plan (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate plan
    if new_plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if subscription.plan_name == new_plan:
        raise HTTPException(status_code=400, detail="Already on this plan")
    
    # Update subscription
    plan_details = SUBSCRIPTION_PLANS[new_plan]
    subscription.plan_name = new_plan
    subscription.plan_price = plan_details["price"]
    
    # Update ISP info
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    isp.subscription_plan = new_plan
    
    db.commit()
    
    return {"message": f"Subscription upgraded to {new_plan}", "new_price": str(plan_details["price"])}

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get current subscription
    subscription = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    # Cancel subscription
    subscription.status = "cancelled"
    subscription.auto_renew = False
    
    # Update ISP status
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    isp.subscription_status = "cancelled"
    
    db.commit()
    
    return {"message": "Subscription cancelled successfully. Access will remain until end date.", "end_date": subscription.end_date}

@router.get("/history", response_model=List[SubscriptionResponse])
async def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get subscription history for the ISP"""
    subscriptions = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id
    ).order_by(Subscription.created_at.desc()).all()
    
    return subscriptions

@router.put("/auto-renew", response_model=SubscriptionResponse)
async def update_auto_renew(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update auto-renewal setting (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    subscription = db.query(Subscription).filter(
        Subscription.isp_id == current_user.isp_id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if subscription_update.auto_renew is not None:
        subscription.auto_renew = subscription_update.auto_renew
    
    db.commit()
    db.refresh(subscription)
    
    return subscription
