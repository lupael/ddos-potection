"""
SLA compliance reporting endpoints.

Exposes monthly compliance reports and tier definitions.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import SLARecord, User
from routers.auth_router import get_current_user
from services.sla_service import SLAComplianceChecker, SLA_TIERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sla/compliance", tags=["SLA Compliance"])

_checker = SLAComplianceChecker()


def _require_auth(user: User) -> None:
    """Allow any authenticated user (admin, operator, viewer)."""
    pass  # JWT is enforced by the Depends(get_current_user) injection


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/tiers", summary="List SLA tier definitions")
def list_tiers(current_user: User = Depends(get_current_user)):
    """Return the SLA targets for all available tiers.

    Requires JWT authentication.
    """
    return SLA_TIERS


@router.get("/monthly", summary="Monthly SLA compliance report")
def monthly_report(
    year: int = Query(..., ge=2000, le=2100, description="Report year"),
    month: int = Query(..., ge=1, le=12, description="Report month (1–12)"),
    tier: str = Query("standard", description="SLA tier: standard, pro, enterprise"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a monthly SLA compliance report for the authenticated ISP.

    Queries SLA records for the specified year/month, evaluates them against
    the chosen tier targets, and returns compliance percentages plus breach
    credit information.

    Requires JWT authentication.
    """
    if tier.lower() not in SLA_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown tier '{tier}'. Supported: {list(SLA_TIERS.keys())}",
        )

    # Build date range for the requested month
    import calendar
    from datetime import datetime, timezone

    _, last_day = calendar.monthrange(year, month)
    period_start = datetime(year, month, 1, tzinfo=timezone.utc)
    period_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    records_q = (
        db.query(SLARecord)
        .filter(
            SLARecord.isp_id == current_user.isp_id,
            SLARecord.detected_at >= period_start,
            SLARecord.detected_at <= period_end,
        )
        .all()
    )

    record_dicts = [
        {
            "ttd_seconds": r.ttd_seconds,
            "ttm_seconds": r.ttm_seconds,
        }
        for r in records_q
    ]

    report = _checker.generate_monthly_report(record_dicts, tier.lower())
    report["year"] = year
    report["month"] = month
    report["period_start"] = period_start.isoformat()
    report["period_end"] = period_end.isoformat()
    return report
