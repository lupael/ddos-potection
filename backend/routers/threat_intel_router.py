"""
Threat intelligence router.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.models import User
from routers.auth_router import get_current_user
from services.threat_intel import threat_intel_service

router = APIRouter(prefix="/api/v1/threat-intel", tags=["Threat Intelligence"])


class IPCheckResponse(BaseModel):
    ip: str
    is_malicious: bool
    threat_score: int


@router.get("/stats", summary="Threat intelligence feed statistics")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Return per-feed entry counts and total blocklist size."""
    return threat_intel_service.get_feed_stats()


@router.get("/check/{ip}", response_model=IPCheckResponse, summary="Check if IP is malicious")
async def check_ip(ip: str, current_user: User = Depends(get_current_user)):
    """Check whether *ip* appears in any threat intelligence feed."""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid IP address")

    return IPCheckResponse(
        ip=ip,
        is_malicious=threat_intel_service.is_malicious(ip),
        threat_score=threat_intel_service.get_threat_score(ip),
    )


@router.post("/refresh", summary="Trigger manual feed refresh (admin only)")
async def refresh_feeds(current_user: User = Depends(get_current_user)):
    """Trigger an immediate refresh of all threat intelligence feeds."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    import asyncio
    asyncio.create_task(threat_intel_service.refresh_all_feeds())
    return {"message": "Feed refresh initiated"}
