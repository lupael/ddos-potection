"""
Permission decorators and utilities for fine-grained access control
"""
from functools import wraps
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Callable

from models.models import User
from database import get_db
from routers.auth_router import get_current_user


def require_role(allowed_roles: List[str]):
    """
    Decorator to require specific roles for accessing an endpoint
    Usage:
        @require_role(["admin", "operator"])
        async def some_endpoint(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """
    Decorator to require admin role
    Usage:
        @require_admin
        async def admin_endpoint(current_user: User = Depends(get_current_user)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, current_user: User = None, **kwargs):
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return await func(*args, current_user=current_user, **kwargs)
    return wrapper


def require_active_subscription(func: Callable):
    """
    Decorator to require an active subscription
    Usage:
        @require_active_subscription
        async def premium_feature(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, current_user: User = None, db: Session = None, **kwargs):
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        from models.models import ISP
        isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
        
        if not isp or isp.subscription_status not in ["active", "trial"]:
            raise HTTPException(
                status_code=403, 
                detail="Active subscription required to access this feature"
            )
        
        return await func(*args, current_user=current_user, db=db, **kwargs)
    return wrapper


def require_subscription_plan(required_plans: List[str]):
    """
    Decorator to require specific subscription plans
    Usage:
        @require_subscription_plan(["professional", "enterprise"])
        async def premium_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, db: Session = None, **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            from models.models import ISP
            isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
            
            if not isp or isp.subscription_plan not in required_plans:
                raise HTTPException(
                    status_code=403, 
                    detail=f"This feature requires one of these plans: {', '.join(required_plans)}"
                )
            
            return await func(*args, current_user=current_user, db=db, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """
    Class-based permission checker for dependency injection
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


# Pre-defined permission checkers
admin_only = PermissionChecker(["admin"])
admin_or_operator = PermissionChecker(["admin", "operator"])
all_roles = PermissionChecker(["admin", "operator", "viewer"])
