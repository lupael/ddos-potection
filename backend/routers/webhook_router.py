"""
Webhook management router.

ISP admins can register, list, update, and delete outbound webhook endpoints
that will receive alert and mitigation events via signed HTTP POST callbacks.
"""
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from database import get_db
from models.models import Webhook, User
from routers.auth_router import get_current_user

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

# Event types that can be subscribed to
VALID_EVENTS = {
    "alert.created",
    "alert.resolved",
    "mitigation.started",
    "mitigation.stopped",
    "mitigation.failed",
}


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: List[str]
    secret: Optional[str] = None  # auto-generated when omitted


class WebhookUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookOut(BaseModel):
    id: int
    isp_id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: object
    updated_at: Optional[object] = None

    class Config:
        from_attributes = True


class WebhookCreatedOut(WebhookOut):
    """Returned only at creation time — includes the signing secret."""
    secret: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_events(events: List[str]) -> None:
    invalid = set(events) - VALID_EVENTS
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event type(s): {', '.join(sorted(invalid))}. "
                   f"Valid events: {', '.join(sorted(VALID_EVENTS))}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=WebhookCreatedOut, status_code=201,
             summary="Register a new webhook endpoint")
def create_webhook(
    payload: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a URL to receive signed event callbacks.

    The response includes the **secret** used to compute the
    ``X-DDoS-Signature`` HMAC-SHA256 header.  Store it securely —
    it will not be returned again.

    Requires **admin** role.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    _validate_events(payload.events)

    signing_secret = payload.secret or secrets.token_hex(32)

    webhook = Webhook(
        isp_id=current_user.isp_id,
        url=str(payload.url),
        secret=signing_secret,
        events=payload.events,
        is_active=True,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    # Return secret only at creation time
    result = WebhookCreatedOut(
        id=webhook.id,
        isp_id=webhook.isp_id,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        secret=signing_secret,
    )
    return result


@router.get("/", response_model=List[WebhookOut],
            summary="List all webhooks for the caller's ISP")
def list_webhooks(
    active_only: bool = Query(False, description="Return only active webhooks"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List registered webhooks.  Requires **admin** or **operator** role."""
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(Webhook).filter(Webhook.isp_id == current_user.isp_id)
    if active_only:
        query = query.filter(Webhook.is_active.is_(True))
    return query.order_by(Webhook.id).all()


@router.get("/{webhook_id}", response_model=WebhookOut,
            summary="Get a single webhook")
def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch details of a specific webhook.  Requires **admin** or **operator** role."""
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.isp_id == current_user.isp_id,
    ).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookOut,
              summary="Update a webhook")
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update URL, event subscriptions, or active state.  Requires **admin** role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.isp_id == current_user.isp_id,
    ).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if payload.url is not None:
        webhook.url = str(payload.url)
    if payload.events is not None:
        _validate_events(payload.events)
        webhook.events = payload.events
    if payload.is_active is not None:
        webhook.is_active = payload.is_active

    db.commit()
    db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204,
               summary="Delete a webhook")
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a webhook registration.  Requires **admin** role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.isp_id == current_user.isp_id,
    ).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    db.delete(webhook)
    db.commit()
