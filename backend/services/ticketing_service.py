"""
Ticketing integrations: ServiceNow, JIRA, and Zendesk.

All HTTP calls use aiohttp (optional dependency). If aiohttp is not installed the
methods log a warning and return an empty dict rather than raising.
"""
import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import aiohttp as _aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _aiohttp = None  # type: ignore[assignment]
    _AIOHTTP_AVAILABLE = False


# ---------------------------------------------------------------------------
# ServiceNow
# ---------------------------------------------------------------------------

class ServiceNowClient:
    """Client for the ServiceNow REST Table API."""

    def __init__(self, instance: str, username: str, password: str) -> None:
        """
        Args:
            instance: ServiceNow instance name, e.g. ``"mycompany.service-now.com"``.
            username: ServiceNow username.
            password: ServiceNow password.
        """
        self._base_url = f"https://{instance}"
        self._auth = base64.b64encode(
            f"{username}:{password}".encode()
        ).decode()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_incident(
        self,
        short_description: str,
        description: str,
        urgency: int = 2,
        impact: int = 2,
    ) -> dict[str, Any]:
        """Create a new ServiceNow incident.

        Args:
            short_description: Brief description of the incident.
            description: Full incident description.
            urgency: 1 (high) – 3 (low). Defaults to 2.
            impact: 1 (high) – 3 (low). Defaults to 2.

        Returns:
            Parsed JSON response from ServiceNow, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot create ServiceNow incident")
            return {}
        url = f"{self._base_url}/api/now/table/incident"
        payload = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "impact": impact,
        }
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("ServiceNow create_incident failed: %s", exc)
            return {}

    async def update_incident(
        self, sys_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Partially update an existing ServiceNow incident.

        Args:
            sys_id: The ``sys_id`` of the incident record.
            fields: Dictionary of fields to update.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot update ServiceNow incident")
            return {}
        url = f"{self._base_url}/api/now/table/incident/{sys_id}"
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.patch(url, json=fields) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("ServiceNow update_incident failed: %s", exc)
            return {}

    async def close_incident(
        self, sys_id: str, resolution: str
    ) -> dict[str, Any]:
        """Close a ServiceNow incident.

        Args:
            sys_id: The ``sys_id`` of the incident record.
            resolution: Resolution notes to attach.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        return await self.update_incident(
            sys_id,
            {
                "state": "7",           # Closed
                "close_notes": resolution,
                "close_code": "Solved (Permanently)",
            },
        )


# ---------------------------------------------------------------------------
# JIRA
# ---------------------------------------------------------------------------

class JIRAClient:
    """Client for the Jira Cloud REST API v3."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
    ) -> None:
        """
        Args:
            base_url: Jira instance base URL, e.g. ``"https://mycompany.atlassian.net"``.
            email: Jira account email.
            api_token: Jira API token.
            project_key: Default project key for new issues.
        """
        self._base_url = base_url.rstrip("/")
        self._project_key = project_key
        raw = f"{email}:{api_token}".encode()
        self._auth = base64.b64encode(raw).decode()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Incident",
        priority: str = "High",
    ) -> dict[str, Any]:
        """Create a Jira issue.

        Args:
            summary: Issue title.
            description: Detailed issue body.
            issue_type: Jira issue type. Defaults to ``"Incident"``.
            priority: Issue priority. Defaults to ``"High"``.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot create JIRA issue")
            return {}
        url = f"{self._base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": summary,
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
            }
        }
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("JIRA create_issue failed: %s", exc)
            return {}

    async def update_issue(
        self, issue_key: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a Jira issue.

        Args:
            issue_key: Issue identifier, e.g. ``"DDOS-123"``.
            fields: Dictionary of fields to update (wrapped in ``{"fields": ...}``
                automatically).

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot update JIRA issue")
            return {}
        url = f"{self._base_url}/rest/api/3/issue/{issue_key}"
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.put(url, json={"fields": fields}) as resp:
                    resp.raise_for_status()
                    data = await resp.text()
                    return {"status": resp.status, "body": data}
        except Exception as exc:
            logger.error("JIRA update_issue failed: %s", exc)
            return {}

    async def add_comment(
        self, issue_key: str, comment: str
    ) -> dict[str, Any]:
        """Add a comment to a Jira issue.

        Args:
            issue_key: Issue identifier.
            comment: Plain-text comment body.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot add JIRA comment")
            return {}
        url = f"{self._base_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("JIRA add_comment failed: %s", exc)
            return {}


# ---------------------------------------------------------------------------
# Zendesk
# ---------------------------------------------------------------------------

class ZendeskClient:
    """Client for the Zendesk Support REST API."""

    def __init__(self, subdomain: str, email: str, api_token: str) -> None:
        """
        Args:
            subdomain: Zendesk subdomain, e.g. ``"mycompany"``
                (resolves to ``mycompany.zendesk.com``).
            email: Agent email address.
            api_token: Zendesk API token.
        """
        self._base_url = f"https://{subdomain}.zendesk.com"
        raw = f"{email}/token:{api_token}".encode()
        self._auth = base64.b64encode(raw).decode()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Basic {self._auth}",
            "Content-Type": "application/json",
        }

    async def create_ticket(
        self,
        subject: str,
        body: str,
        priority: str = "urgent",
    ) -> dict[str, Any]:
        """Create a Zendesk support ticket.

        Args:
            subject: Ticket subject line.
            body: Ticket body / comment.
            priority: ``"urgent"``, ``"high"``, ``"normal"``, or ``"low"``.
                Defaults to ``"urgent"``.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot create Zendesk ticket")
            return {}
        url = f"{self._base_url}/api/v2/tickets.json"
        payload = {
            "ticket": {
                "subject": subject,
                "comment": {"body": body},
                "priority": priority,
            }
        }
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("Zendesk create_ticket failed: %s", exc)
            return {}

    async def update_ticket(
        self,
        ticket_id: int,
        status: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Update a Zendesk ticket status and optionally add a comment.

        Args:
            ticket_id: Numeric Zendesk ticket ID.
            status: New ticket status, e.g. ``"solved"``.
            comment: Optional comment to append.

        Returns:
            Parsed JSON response, or ``{}`` on error.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not installed; cannot update Zendesk ticket")
            return {}
        url = f"{self._base_url}/api/v2/tickets/{ticket_id}.json"
        ticket_payload: dict[str, Any] = {"status": status}
        if comment:
            ticket_payload["comment"] = {"body": comment, "public": False}
        payload = {"ticket": ticket_payload}
        try:
            async with _aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.put(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as exc:
            logger.error("Zendesk update_ticket failed: %s", exc)
            return {}
