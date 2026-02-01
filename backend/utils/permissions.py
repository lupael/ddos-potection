"""
Permission utilities for fine-grained access control

These permission checkers work with FastAPI's dependency injection system.
Use them as dependencies in your endpoints for role-based access control.
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from models.models import User
from database import get_db
from routers.auth_router import get_current_user


class PermissionChecker:
    """
    Class-based permission checker for dependency injection
    
    Usage:
        admin_only = PermissionChecker(["admin"])
        
        @router.get("/admin-endpoint")
        async def admin_endpoint(current_user: User = Depends(admin_only)):
            return {"message": "Admin access granted"}
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


class SubscriptionChecker:
    """
    Check if user has active subscription
    
    Usage:
        require_active_sub = SubscriptionChecker()
        
        @router.get("/premium-feature")
        async def premium_feature(
            current_user: User = Depends(require_active_sub),
            db: Session = Depends(get_db)
        ):
            return {"message": "Premium feature accessed"}
    """
    def __call__(self, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        from models.models import ISP
        isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
        
        if not isp or isp.subscription_status not in ["active", "trial"]:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required to access this feature"
            )
        return current_user


class PlanChecker:
    """
    Check if user has required subscription plan
    
    Usage:
        require_enterprise = PlanChecker(["enterprise"])
        
        @router.get("/enterprise-feature")
        async def enterprise_feature(
            current_user: User = Depends(require_enterprise),
            db: Session = Depends(get_db)
        ):
            return {"message": "Enterprise feature accessed"}
    """
    def __init__(self, required_plans: List[str]):
        self.required_plans = required_plans
    
    def __call__(self, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        from models.models import ISP
        isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
        
        if not isp or isp.subscription_plan not in self.required_plans:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires one of these plans: {', '.join(self.required_plans)}"
            )
        return current_user


# Pre-defined permission checkers - use these as dependencies
admin_only = PermissionChecker(["admin"])
admin_or_operator = PermissionChecker(["admin", "operator"])
all_roles = PermissionChecker(["admin", "operator", "viewer"])

# Subscription checkers
require_active_subscription = SubscriptionChecker()
require_professional = PlanChecker(["professional", "enterprise"])
require_enterprise = PlanChecker(["enterprise"])


def check_admin(current_user: User = Depends(get_current_user)):
    """
    Simple function to check admin role
    Can be used as a dependency
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def check_admin_or_operator(current_user: User = Depends(get_current_user)):
    """
    Simple function to check admin or operator role
    Can be used as a dependency
    """
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Admin or operator access required")
    return current_user
