"""
SLA (Service Level Agreement) tracking router.

Records and exposes TTD (time-to-detect) and TTM (time-to-mitigate) metrics
for every DDoS incident handled by the platform.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import SLARecord, Alert, User
from routers.auth_router import get_current_user

router = APIRouter(prefix="/api/v1/sla", tags=["SLA Tracking"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SLARecordCreate(BaseModel):
    """Payload to create a new SLA record when an alert is detected."""
    alert_id: int
    attack_started_at: Optional[datetime] = None


class SLARecordUpdate(BaseModel):
    """Payload to update SLA timestamps (e.g., when mitigation is applied)."""
    mitigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class SLARecordOut(BaseModel):
    id: int
    isp_id: int
    alert_id: int
    attack_started_at: Optional[datetime]
    detected_at: datetime
    mitigated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    ttd_seconds: Optional[int]
    ttm_seconds: Optional[int]
    sla_met: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True


# SLA targets (seconds) keyed by subscription plan
_SLA_TTD: dict[str, int] = {
    "basic": 300,        # 5 minutes
    "professional": 120,  # 2 minutes
    "enterprise": 30,    # 30 seconds
}
_SLA_TTM: dict[str, int] = {
    "basic": 900,        # 15 minutes
    "professional": 300, # 5 minutes
    "enterprise": 120,   # 2 minutes
}


def _compute_sla_met(record: SLARecord, plan: str) -> Optional[bool]:
    """Return True if both TTD and TTM are within the plan's SLA targets."""
    ttd_target = _SLA_TTD.get(plan)
    ttm_target = _SLA_TTM.get(plan)
    if record.ttd_seconds is None or ttd_target is None:
        return None
    if record.ttm_seconds is None or ttm_target is None:
        return None
    return record.ttd_seconds <= ttd_target and record.ttm_seconds <= ttm_target


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=SLARecordOut, status_code=201,
             summary="Create SLA record for an alert")
def create_sla_record(
    payload: SLARecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new SLA record when an alert is first detected.

    Requires **admin** or **operator** role.
    """
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Verify alert belongs to the caller's ISP
    alert = db.query(Alert).filter(
        Alert.id == payload.alert_id,
        Alert.isp_id == current_user.isp_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Prevent duplicate records for the same alert
    existing = db.query(SLARecord).filter(
        SLARecord.alert_id == payload.alert_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="SLA record already exists for this alert")

    now = datetime.now(timezone.utc)
    detected_at = now
    ttd_seconds: Optional[int] = None
    if payload.attack_started_at:
        started = payload.attack_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        ttd_seconds = max(0, int((detected_at - started).total_seconds()))

    record = SLARecord(
        isp_id=current_user.isp_id,
        alert_id=payload.alert_id,
        attack_started_at=payload.attack_started_at,
        detected_at=detected_at,
        ttd_seconds=ttd_seconds,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}", response_model=SLARecordOut,
              summary="Update SLA record with mitigation/resolution timestamps")
def update_sla_record(
    record_id: int,
    payload: SLARecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update mitigation or resolution timestamps and recalculate durations.

    Requires **admin** or **operator** role.
    """
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    record = db.query(SLARecord).filter(
        SLARecord.id == record_id,
        SLARecord.isp_id == current_user.isp_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="SLA record not found")

    if payload.mitigated_at is not None:
        mitigated_at = payload.mitigated_at
        if mitigated_at.tzinfo is None:
            mitigated_at = mitigated_at.replace(tzinfo=timezone.utc)
        record.mitigated_at = mitigated_at
        detected_at = record.detected_at
        if detected_at.tzinfo is None:
            detected_at = detected_at.replace(tzinfo=timezone.utc)
        record.ttm_seconds = max(0, int((mitigated_at - detected_at).total_seconds()))

    if payload.resolved_at is not None:
        resolved_at = payload.resolved_at
        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)
        record.resolved_at = resolved_at

    # Evaluate SLA compliance once we have both durations
    plan = "basic"
    try:
        alert = db.query(Alert).filter(Alert.id == record.alert_id).first()
        if alert and alert.isp:
            plan = alert.isp.subscription_plan or "basic"
    except Exception:
        pass
    record.sla_met = _compute_sla_met(record, plan)

    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[SLARecordOut],
            summary="List SLA records for the caller's ISP")
def list_sla_records(
    alert_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return SLA records, optionally filtered by alert_id."""
    query = db.query(SLARecord).filter(SLARecord.isp_id == current_user.isp_id)
    if alert_id is not None:
        query = query.filter(SLARecord.alert_id == alert_id)
    records = query.order_by(SLARecord.detected_at.desc()).offset(offset).limit(limit).all()
    return records


@router.get("/{record_id}", response_model=SLARecordOut,
            summary="Get a single SLA record")
def get_sla_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a single SLA record by ID."""
    record = db.query(SLARecord).filter(
        SLARecord.id == record_id,
        SLARecord.isp_id == current_user.isp_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="SLA record not found")
    return record
