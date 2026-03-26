"""
Signature library router — BPF / FlowSpec attack signatures.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import Alert, Signature, User
from routers.auth_router import get_current_user
from services.signature_library import AttackSignature, SignatureLibrary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/signatures", tags=["Signatures"])

# Module-level library instance (in-memory; replace with DB-backed if needed)
_library = SignatureLibrary()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SignatureResponse(BaseModel):
    id: str
    name: str
    attack_type: str
    bpf_filter: str
    flowspec_rule: str
    confidence: float
    created_at: str
    isp_id: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sig_to_response(sig: AttackSignature) -> SignatureResponse:
    return SignatureResponse(
        id=sig.id,
        name=sig.name,
        attack_type=sig.attack_type,
        bpf_filter=sig.bpf_filter,
        flowspec_rule=sig.flowspec_rule,
        confidence=sig.confidence,
        created_at=sig.created_at.isoformat(),
        isp_id=sig.isp_id,
    )


def _persist_signature(sig: AttackSignature, db: Session) -> None:
    """Persist a signature to the database Signature table."""
    db_sig = Signature(
        isp_id=sig.isp_id,
        name=sig.name,
        attack_type=sig.attack_type,
        bpf_filter=sig.bpf_filter,
        flowspec_rule=sig.flowspec_rule,
        confidence=sig.confidence,
        is_active=True,
    )
    db.add(db_sig)
    db.commit()
    db.refresh(db_sig)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SignatureResponse])
async def list_signatures(
    attack_type: str | None = Query(None, description="Filter by attack type"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
) -> list[SignatureResponse]:
    """List signatures, optionally filtered by attack_type."""
    sigs = _library.search_signatures(
        attack_type=attack_type, min_confidence=min_confidence
    )
    # Only return signatures belonging to this ISP
    sigs = [s for s in sigs if s.isp_id == current_user.isp_id]
    return [_sig_to_response(s) for s in sigs]


@router.post("/extract", response_model=SignatureResponse)
async def extract_signature(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SignatureResponse:
    """Extract a BPF/FlowSpec signature from an existing alert."""
    alert: Alert | None = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.isp_id == current_user.isp_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_dict: dict[str, Any] = {
        "source_ip": alert.source_ip,
        "target_ip": alert.target_ip,
        "alert_type": alert.alert_type,
    }

    bpf = _library.extract_bpf_from_alert(alert_dict) or ""
    flowspec = _library.extract_flowspec_from_alert(alert_dict) or ""

    sig = AttackSignature(
        id=str(uuid.uuid4()),
        name=f"Auto: {alert.alert_type} #{alert.id}",
        attack_type=alert.alert_type,
        bpf_filter=bpf,
        flowspec_rule=flowspec,
        confidence=0.7,
        created_at=datetime.now(timezone.utc),
        isp_id=current_user.isp_id,
    )
    _library.add_signature(sig)
    _persist_signature(sig, db)
    return _sig_to_response(sig)


@router.get("/{sig_id}/bpf")
async def get_bpf_filter(
    sig_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Return the BPF filter string for a signature."""
    sigs = _library.search_signatures(min_confidence=0.0)
    sig = next((s for s in sigs if s.id == sig_id and s.isp_id == current_user.isp_id), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    return {"id": sig_id, "bpf_filter": sig.bpf_filter}


@router.get("/{sig_id}/flowspec")
async def get_flowspec_rule(
    sig_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Return the FlowSpec rule string for a signature."""
    sigs = _library.search_signatures(min_confidence=0.0)
    sig = next((s for s in sigs if s.id == sig_id and s.isp_id == current_user.isp_id), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    return {"id": sig_id, "flowspec_rule": sig.flowspec_rule}
