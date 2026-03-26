"""
Ticketing integration router — ServiceNow, JIRA, and Zendesk.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.models import Alert, User
from routers.auth_router import get_current_user
from services.ticketing_service import JIRAClient, ServiceNowClient, ZendeskClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ticketing", tags=["Ticketing"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_operator(current_user: User) -> None:
    """Raise 403 unless user is admin or operator."""
    if current_user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Admin or operator role required")


def _enabled_integrations() -> dict[str, bool]:
    return {
        "servicenow": bool(settings.SERVICENOW_INSTANCE and settings.SERVICENOW_USERNAME),
        "jira": bool(settings.JIRA_BASE_URL and settings.JIRA_EMAIL and settings.JIRA_API_TOKEN),
        "zendesk": bool(settings.ZENDESK_SUBDOMAIN and settings.ZENDESK_EMAIL and settings.ZENDESK_API_TOKEN),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateIncidentRequest(BaseModel):
    alert_id: int
    urgency: int = 2
    impact: int = 2
    priority: str = "High"
    zendesk_priority: str = "urgent"


class CloseIncidentRequest(BaseModel):
    servicenow_sys_id: str | None = None
    jira_issue_key: str | None = None
    zendesk_ticket_id: int | None = None
    resolution: str = "Resolved by DDoS Protection Platform"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_ticketing_config(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return which ticketing integrations are enabled (non-empty config)."""
    _require_operator(current_user)
    return {"integrations": _enabled_integrations()}


@router.post("/incident")
async def create_incident(
    payload: CreateIncidentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create an incident ticket in all enabled systems for a given alert_id."""
    _require_operator(current_user)

    alert: Alert | None = db.query(Alert).filter(
        Alert.id == payload.alert_id,
        Alert.isp_id == current_user.isp_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    short_desc = f"DDoS Alert [{alert.severity.upper()}]: {alert.alert_type}"
    description = (
        f"Target: {alert.target_ip}\n"
        f"Source: {alert.source_ip}\n"
        f"Description: {alert.description}\n"
        f"Status: {alert.status}"
    )

    results: dict[str, Any] = {}
    integrations = _enabled_integrations()

    if integrations["servicenow"]:
        client = ServiceNowClient(
            settings.SERVICENOW_INSTANCE,
            settings.SERVICENOW_USERNAME,
            settings.SERVICENOW_PASSWORD,
        )
        results["servicenow"] = await client.create_incident(
            short_desc, description, urgency=payload.urgency, impact=payload.impact
        )

    if integrations["jira"]:
        client_j = JIRAClient(
            settings.JIRA_BASE_URL,
            settings.JIRA_EMAIL,
            settings.JIRA_API_TOKEN,
            settings.JIRA_PROJECT_KEY,
        )
        results["jira"] = await client_j.create_issue(
            short_desc, description, priority=payload.priority
        )

    if integrations["zendesk"]:
        client_z = ZendeskClient(
            settings.ZENDESK_SUBDOMAIN,
            settings.ZENDESK_EMAIL,
            settings.ZENDESK_API_TOKEN,
        )
        results["zendesk"] = await client_z.create_ticket(
            short_desc, description, priority=payload.zendesk_priority
        )

    return {"alert_id": payload.alert_id, "results": results}


@router.post("/close")
async def close_incident(
    payload: CloseIncidentRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Close an incident in all enabled systems by external ticket ID."""
    _require_operator(current_user)

    results: dict[str, Any] = {}
    integrations = _enabled_integrations()

    if integrations["servicenow"] and payload.servicenow_sys_id:
        client = ServiceNowClient(
            settings.SERVICENOW_INSTANCE,
            settings.SERVICENOW_USERNAME,
            settings.SERVICENOW_PASSWORD,
        )
        results["servicenow"] = await client.close_incident(
            payload.servicenow_sys_id, payload.resolution
        )

    if integrations["jira"] and payload.jira_issue_key:
        client_j = JIRAClient(
            settings.JIRA_BASE_URL,
            settings.JIRA_EMAIL,
            settings.JIRA_API_TOKEN,
            settings.JIRA_PROJECT_KEY,
        )
        results["jira"] = await client_j.update_issue(
            payload.jira_issue_key,
            {"status": {"name": "Done"}},
        )
        await client_j.add_comment(payload.jira_issue_key, payload.resolution)

    if integrations["zendesk"] and payload.zendesk_ticket_id:
        client_z = ZendeskClient(
            settings.ZENDESK_SUBDOMAIN,
            settings.ZENDESK_EMAIL,
            settings.ZENDESK_API_TOKEN,
        )
        results["zendesk"] = await client_z.update_ticket(
            payload.zendesk_ticket_id, "solved", comment=payload.resolution
        )

    return {"results": results}
