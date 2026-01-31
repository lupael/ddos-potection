from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.models import Rule, User
from routers.auth_router import get_current_user

router = APIRouter()

class RuleCreate(BaseModel):
    name: str
    rule_type: str
    condition: dict
    action: str
    priority: int = 100
    is_active: bool = True

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    condition: Optional[dict] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class RuleResponse(BaseModel):
    id: int
    name: str
    rule_type: str
    condition: dict
    action: str
    priority: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all rules for the ISP"""
    rules = db.query(Rule).filter(Rule.isp_id == current_user.isp_id).all()
    return rules

@router.post("/", response_model=RuleResponse)
async def create_rule(
    rule: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new firewall/mitigation rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    db_rule = Rule(
        isp_id=current_user.isp_id,
        name=rule.name,
        rule_type=rule.rule_type,
        condition=rule.condition,
        action=rule.action,
        priority=rule.priority,
        is_active=rule.is_active
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific rule"""
    rule = db.query(Rule).filter(
        Rule.id == rule_id,
        Rule.isp_id == current_user.isp_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rule

@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    rule = db.query(Rule).filter(
        Rule.id == rule_id,
        Rule.isp_id == current_user.isp_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    for key, value in rule_update.dict(exclude_unset=True).items():
        setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a rule"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    rule = db.query(Rule).filter(
        Rule.id == rule_id,
        Rule.isp_id == current_user.isp_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted successfully"}
