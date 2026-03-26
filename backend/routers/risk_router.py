"""
Risk scoring router — daily attack-probability scores per prefix.
"""
import logging
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import Alert, User
from routers.auth_router import get_current_user
from services.risk_scorer import RiskScorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/risk", tags=["Risk Scoring"])

_scorer = RiskScorer()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PreemptRequest(BaseModel):
    prefix: str
    risk_score: float
    reason: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alerts_for_prefix(
    prefix: str, isp_id: int, db: Session
) -> list[dict[str, Any]]:
    """Return alert dicts whose target_ip matches the prefix string."""
    alerts = (
        db.query(Alert)
        .filter(
            Alert.isp_id == isp_id,
            Alert.target_ip == prefix,
        )
        .all()
    )
    return [{"created_at": a.created_at, "severity": a.severity} for a in alerts]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/scores")
async def get_all_risk_scores(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return risk scores for all unique target prefixes in this ISP's alerts."""
    rows = (
        db.query(Alert.target_ip)
        .filter(Alert.isp_id == current_user.isp_id)
        .distinct()
        .all()
    )
    prefixes = [r.target_ip for r in rows if r.target_ip]

    results: list[dict[str, Any]] = []
    for prefix in prefixes:
        attacks = _alerts_for_prefix(prefix, current_user.isp_id, db)
        score = _scorer.calculate_prefix_risk(prefix, attacks)
        results.append(score)

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


@router.get("/scores/{prefix:path}")
async def get_prefix_risk_score(
    prefix: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the risk score for a specific prefix."""
    prefix = unquote(prefix)
    attacks = _alerts_for_prefix(prefix, current_user.isp_id, db)
    return _scorer.calculate_prefix_risk(prefix, attacks)


@router.post("/preempt")
async def trigger_preemptive_mitigation(
    payload: PreemptRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger pre-emptive mitigation for a high-risk prefix.

    Returns the recommended action and whether mitigation was triggered.
    """
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Admin or operator role required")

    should = _scorer.should_preempt(payload.prefix, payload.risk_score)
    action = _scorer.get_preemptive_action(payload.risk_score)

    return {
        "prefix": payload.prefix,
        "risk_score": payload.risk_score,
        "preemption_triggered": should,
        "recommended_action": action,
        "reason": payload.reason,
        "note": "Connect to mitigation_service.apply_mitigation() to take real action.",
    }
