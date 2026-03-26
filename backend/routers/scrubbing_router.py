"""
Scrubbing centre diversion API endpoints.

Allows operators to list configured scrubbing centres and trigger/withdraw
traffic diversion via BGP /32 announcements.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
import ipaddress

from routers.auth_router import get_current_user
from models.models import User
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scrubbing", tags=["Scrubbing"])

# ---------------------------------------------------------------------------
# Lazy-initialise the manager from configuration
# ---------------------------------------------------------------------------

_manager = None  # ScrubbingCentreManager | None


def _get_manager():
    """Return a lazily-initialised ScrubbingCentreManager built from settings."""
    global _manager
    if _manager is not None:
        return _manager

    from services.scrubbing_centre import ScrubbingCentre, ScrubbingCentreManager

    centres = []
    if settings.SCRUBBING_ENABLED and settings.SCRUBBING_CENTRES:
        try:
            centre_configs = json.loads(settings.SCRUBBING_CENTRES)
            for cfg in centre_configs:
                centres.append(
                    ScrubbingCentre(
                        centre_id=cfg["centre_id"],
                        name=cfg["name"],
                        bgp_nexthop=cfg["bgp_nexthop"],
                        gre_endpoint=cfg["gre_endpoint"],
                        capacity_gbps=cfg.get("capacity_gbps", 100),
                    )
                )
        except Exception as exc:
            logger.error("Failed to parse SCRUBBING_CENTRES config: %s", exc)

    _manager = ScrubbingCentreManager(centres)
    return _manager


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class DivertRequest(BaseModel):
    """Request body for traffic diversion."""
    target_prefix: str
    reason: Optional[str] = None

    @field_validator("target_prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"target_prefix must be a valid IP or CIDR, got {v!r}")
        return v


class ReturnRequest(BaseModel):
    """Request body for traffic return (withdraw diversion)."""
    target_prefix: str

    @field_validator("target_prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(f"target_prefix must be a valid IP or CIDR, got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin_or_operator(user: User) -> None:
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/centres", summary="List configured scrubbing centres")
def list_centres(current_user: User = Depends(get_current_user)):
    """Return details for all configured scrubbing centres.

    Requires **admin** or **operator** role.
    """
    _require_admin_or_operator(current_user)
    mgr = _get_manager()
    return [
        {
            "centre_id": c.centre_id,
            "name": c.name,
            "bgp_nexthop": c.bgp_nexthop,
            "gre_endpoint": c.gre_endpoint,
            "capacity_gbps": c.capacity_gbps,
            "utilization": c.get_utilization(),
        }
        for c in mgr._centres
    ]


@router.post("/divert", summary="Divert traffic to a scrubbing centre")
def divert_traffic(
    payload: DivertRequest,
    current_user: User = Depends(get_current_user),
):
    """Divert traffic for the given prefix to the best available scrubbing centre.

    Requires **admin** or **operator** role.
    """
    _require_admin_or_operator(current_user)
    mgr = _get_manager()
    if not settings.SCRUBBING_ENABLED:
        raise HTTPException(status_code=503, detail="Scrubbing is not enabled (SCRUBBING_ENABLED=false)")
    result = mgr.divert(payload.target_prefix)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    logger.info(
        "Scrubbing diversion triggered for %s by %s: %s",
        payload.target_prefix, current_user.username, payload.reason,
    )
    return result


@router.post("/return", summary="Withdraw scrubbing diversion")
def return_traffic(
    payload: ReturnRequest,
    current_user: User = Depends(get_current_user),
):
    """Withdraw the diversion announcement for the given prefix from all centres.

    Requires **admin** or **operator** role.
    """
    _require_admin_or_operator(current_user)
    mgr = _get_manager()
    results = mgr.return_all(payload.target_prefix)
    logger.info(
        "Scrubbing return triggered for %s by %s",
        payload.target_prefix, current_user.username,
    )
    return {"results": results}
