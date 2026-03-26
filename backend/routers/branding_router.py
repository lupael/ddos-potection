"""
ISP branding router — CSS variable injection, branding CRUD, and custom domain
management.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import ISP, User
from routers.auth_router import get_current_user
from services.custom_domain import CustomDomainManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/branding", tags=["Branding"])

_domain_manager = CustomDomainManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BrandingResponse(BaseModel):
    isp_id: int
    brand_logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_company_name: str | None = None
    brand_portal_domain: str | None = None
    brand_support_email: str | None = None

    class Config:
        from_attributes = True


class BrandingUpdateRequest(BaseModel):
    brand_logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_company_name: str | None = None
    brand_portal_domain: str | None = None
    brand_support_email: str | None = None


class SetDomainRequest(BaseModel):
    domain: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_isp_or_404(isp_id: int, db: Session) -> ISP:
    isp = db.query(ISP).filter(ISP.id == isp_id).first()
    if not isp:
        raise HTTPException(status_code=404, detail="ISP not found")
    return isp


def _isp_to_branding(isp: ISP) -> BrandingResponse:
    return BrandingResponse(
        isp_id=isp.id,
        brand_logo_url=isp.brand_logo_url,
        brand_primary_color=isp.brand_primary_color,
        brand_company_name=isp.brand_company_name,
        brand_portal_domain=isp.brand_portal_domain,
        brand_support_email=isp.brand_support_email,
    )


# ---------------------------------------------------------------------------
# CSS endpoint (public)
# ---------------------------------------------------------------------------

@router.get("/{isp_id}/css", response_class=Response)
async def get_branding_css(
    isp_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Return CSS custom properties for ISP branding (public endpoint, no JWT).

    Returns ``text/css`` containing ``:root { … }`` variable declarations.
    """
    isp = _get_isp_or_404(isp_id, db)

    primary = isp.brand_primary_color or "#1a73e8"
    company = (isp.brand_company_name or "DDoS Protection Platform").replace('"', '\\"')
    logo = (isp.brand_logo_url or "").replace('"', '\\"')

    css = (
        ":root {\n"
        f'  --primary-color: {primary};\n'
        f'  --company-name: "{company}";\n'
        f'  --logo-url: "{logo}";\n'
        "}\n"
    )
    return Response(content=css, media_type="text/css")


# ---------------------------------------------------------------------------
# JSON branding endpoints (JWT required)
# ---------------------------------------------------------------------------

@router.get("/{isp_id}", response_model=BrandingResponse)
async def get_branding(
    isp_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrandingResponse:
    """Return full branding config for an ISP as JSON (JWT required)."""
    isp = _get_isp_or_404(isp_id, db)
    return _isp_to_branding(isp)


@router.put("/{isp_id}", response_model=BrandingResponse)
async def update_branding(
    isp_id: int,
    payload: BrandingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrandingResponse:
    """Update branding fields for an ISP (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if current_user.isp_id != isp_id:
        raise HTTPException(status_code=403, detail="Cannot modify another ISP's branding")

    isp = _get_isp_or_404(isp_id, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(isp, field, value)

    db.commit()
    db.refresh(isp)
    return _isp_to_branding(isp)


# ---------------------------------------------------------------------------
# Custom domain endpoints
# ---------------------------------------------------------------------------

@router.post("/{isp_id}/domain")
async def set_custom_domain(
    isp_id: int,
    payload: SetDomainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Set a custom portal domain for an ISP (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if current_user.isp_id != isp_id:
        raise HTTPException(status_code=403, detail="Cannot modify another ISP's domain")

    try:
        result = await _domain_manager.set_domain(isp_id, payload.domain, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return result


@router.get("/{isp_id}/domain/verify")
async def verify_domain_cname(
    isp_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Verify CNAME configuration for the ISP's custom domain (stub)."""
    config = _domain_manager.get_domain_config(isp_id, db)
    if not config or not config.get("domain"):
        raise HTTPException(status_code=404, detail="No custom domain configured for this ISP")

    domain: str = config["domain"]
    expected_target = f"portal.ddos-platform.example.com"
    return _domain_manager.verify_cname(domain, expected_target)
