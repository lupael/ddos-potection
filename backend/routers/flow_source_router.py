"""
Flow source management router.
Allows ISP admins to register/list/remove authorised NetFlow/sFlow/IPFIX
source router IPs.
"""
import ipaddress
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import FlowSource, User
from routers.auth_router import get_current_user
from services.flow_auth import flow_authenticator

router = APIRouter(prefix="/api/v1/flow-sources", tags=["Flow Sources"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FlowSourceCreate(BaseModel):
    source_ip: str
    description: Optional[str] = None


class FlowSourceOut(BaseModel):
    id: int
    isp_id: int
    source_ip: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[FlowSourceOut], summary="List registered flow sources")
def list_flow_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all registered NetFlow/sFlow/IPFIX source IPs for the caller's ISP."""
    return flow_authenticator.get_sources(current_user.isp_id, db)


@router.post("/", response_model=FlowSourceOut, status_code=201,
             summary="Register a new flow source IP")
def create_flow_source(
    payload: FlowSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a router IP as an authorised flow source.  Requires **admin** role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        ipaddress.ip_address(payload.source_ip)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid IP address")

    # Check for duplicates within the same ISP
    existing = (
        db.query(FlowSource)
        .filter(
            FlowSource.isp_id == current_user.isp_id,
            FlowSource.source_ip == payload.source_ip,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Source IP {payload.source_ip} already registered",
        )

    return flow_authenticator.add_source(
        source_ip=payload.source_ip,
        isp_id=current_user.isp_id,
        description=payload.description,
        db=db,
    )


@router.delete("/{source_id}", status_code=204, summary="Remove a flow source")
def delete_flow_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a registered flow source.  Requires **admin** role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    source = (
        db.query(FlowSource)
        .filter(
            FlowSource.id == source_id,
            FlowSource.isp_id == current_user.isp_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Flow source not found")

    db.delete(source)
    db.commit()
    # Invalidate the Redis authorization cache for the removed IP
    flow_authenticator._redis.delete(
        f"flow_auth:authorized:{current_user.isp_id}:{source.source_ip}"
    )
