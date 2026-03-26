"""
Two-Factor Authentication (TOTP) endpoints using pyotp (RFC 6238).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.models import User
from routers.auth_router import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Two-Factor Authentication"])

try:
    import pyotp  # type: ignore
    _PYOTP_AVAILABLE = True
except ImportError:
    _PYOTP_AVAILABLE = False
    logger.warning("pyotp not installed; TOTP endpoints will return 501")


def _require_pyotp():
    if not _PYOTP_AVAILABLE:
        raise HTTPException(status_code=501, detail="pyotp library not installed")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TOTPSetupResponse(BaseModel):
    provisioning_uri: str
    secret: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPDisableRequest(BaseModel):
    code: str


class TOTPValidateRequest(BaseModel):
    code: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/totp/setup", response_model=TOTPSetupResponse, summary="Generate TOTP secret")
def totp_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new TOTP secret and return the provisioning URI for QR-code apps."""
    _require_pyotp()

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=current_user.email or current_user.username,
        issuer_name="DDoS Protection Platform",
    )

    # Store the raw secret (in production you may want to encrypt it at rest)
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()

    return TOTPSetupResponse(provisioning_uri=uri, secret=secret)


@router.post("/totp/verify", summary="Verify TOTP code and enable 2FA")
def totp_verify(
    payload: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the provided TOTP code and enable 2FA on the account."""
    _require_pyotp()

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up; call /totp/setup first")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/totp/disable", summary="Disable 2FA (requires current TOTP code)")
def totp_disable(
    payload: TOTPDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable 2FA after verifying the current TOTP code."""
    _require_pyotp()

    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is not enabled on this account")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    current_user.totp_secret = None
    current_user.totp_enabled = False
    db.commit()
    return {"message": "2FA disabled successfully"}


@router.post("/totp/validate", summary="Validate a TOTP code (used during login)")
def totp_validate(
    payload: TOTPValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate a TOTP code for the authenticated user."""
    _require_pyotp()

    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is not enabled on this account")

    totp = pyotp.TOTP(current_user.totp_secret)
    valid = totp.verify(payload.code, valid_window=1)
    return {"valid": valid}
