"""
Business Intelligence router — MRR, attack cost, ROI, KPI dashboard, and
capacity forecasting.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import Alert, Subscription, User
from routers.auth_router import get_current_user
from services.business_intelligence import BIService
from services.capacity_planner import CapacityPlanner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bi", tags=["Business Intelligence"])

_bi = BIService()
_planner = CapacityPlanner()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ROIRequest(BaseModel):
    cost_usd: float
    savings_usd: float
    period_days: int = 365


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _sub_to_dict(sub: Subscription) -> dict[str, Any]:
    return {
        "plan_price": float(sub.plan_price or 0),
        "billing_cycle": sub.billing_cycle or "monthly",
        "status": sub.status or "active",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/mrr")
async def get_mrr(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return MRR analytics for the current ISP (admin only)."""
    _require_admin(current_user)

    subs = (
        db.query(Subscription)
        .filter(Subscription.isp_id == current_user.isp_id)
        .all()
    )
    return _bi.calculate_mrr([_sub_to_dict(s) for s in subs])


@router.get("/attack-cost/{alert_id}")
async def get_attack_cost(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return estimated financial cost for a specific attack alert."""
    alert: Alert | None = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.isp_id == current_user.isp_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    duration_secs = 0
    if alert.resolved_at and alert.created_at:
        diff = alert.resolved_at - alert.created_at
        duration_secs = int(diff.total_seconds())

    attack_dict = {
        "severity": alert.severity,
        "peak_gbps": 0.0,   # Not stored in Alert model; extend when available
        "duration_seconds": duration_secs,
    }
    return _bi.calculate_attack_cost(attack_dict)


@router.get("/roi")
async def get_roi(
    cost_usd: float = 0.0,
    savings_usd: float = 0.0,
    period_days: int = 365,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return ROI calculation for the platform."""
    _require_admin(current_user)
    return _bi.calculate_roi(
        costs={"total": cost_usd, "period_days": period_days},
        savings={"total": savings_usd},
    )


@router.get("/kpi-dashboard")
async def get_kpi_dashboard(
    period_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return executive KPI dashboard metrics."""
    base = _bi.get_executive_kpis(current_user.isp_id, period_days)

    subs = (
        db.query(Subscription)
        .filter(Subscription.isp_id == current_user.isp_id)
        .all()
    )
    mrr_data = _bi.calculate_mrr([_sub_to_dict(s) for s in subs])
    base["mrr"] = mrr_data["mrr"]

    return base


@router.get("/capacity-forecast")
async def get_capacity_forecast(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return capacity planning projections for the current ISP."""
    return _planner.generate_capacity_report(isp_id=current_user.isp_id)
