"""
Audit logging middleware.

Automatically logs every POST, PUT, PATCH, DELETE request to the AuditLog table
so that operators have a full, immutable trail of configuration and mitigation changes.

Sensitive fields (passwords, tokens) are redacted before storage.
"""
import json
import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from database import SessionLocal
from models.models import AuditLog

logger = logging.getLogger(__name__)

# HTTP methods that must be audited
_AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# JSON keys whose values should be redacted in the stored body snapshot
_SENSITIVE_KEYS = {
    "password", "hashed_password", "secret", "token", "access_token",
    "refresh_token", "api_key", "stripe_api_key", "webhook_secret",
    "twilio_auth_token", "smtp_password",
}


def _redact(obj: object) -> object:
    """Recursively redact sensitive keys from a parsed JSON object."""
    if isinstance(obj, dict):
        return {
            k: "***REDACTED***" if k.lower() in _SENSITIVE_KEYS else _redact(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return obj


class AuditMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that writes an AuditLog row for every mutating request."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = 8192) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method.upper() not in _AUDIT_METHODS:
            return await call_next(request)

        # ------------------------------------------------------------------
        # Read request body (must be buffered so the route can also read it)
        # ------------------------------------------------------------------
        body_bytes = await request.body()
        body_snapshot: Optional[str] = None
        if body_bytes:
            try:
                parsed = json.loads(body_bytes[: self.max_body_bytes])
                redacted = _redact(parsed)
                body_snapshot = json.dumps(redacted)
            except Exception:
                body_snapshot = body_bytes[: self.max_body_bytes].decode("utf-8", errors="replace")

        # ------------------------------------------------------------------
        # Extract caller identity from the JWT (best-effort)
        # ------------------------------------------------------------------
        user_id: Optional[int] = None
        username: Optional[str] = None
        isp_id: Optional[int] = None

        try:
            # Import here to avoid circular import at module level
            from routers.auth_router import get_current_user_from_token

            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                user = await get_current_user_from_token(token)
                if user:
                    user_id = user.id
                    username = user.username
                    isp_id = user.isp_id
        except Exception:
            pass  # Unauthenticated request or decode error — still log it

        # ------------------------------------------------------------------
        # Forward request to the route handler
        # ------------------------------------------------------------------
        response = await call_next(request)

        # ------------------------------------------------------------------
        # Write audit record (fire-and-forget; never block the response)
        # ------------------------------------------------------------------
        client_ip = None
        if request.client:
            client_ip = request.client.host
        # Check for forwarded IP (behind a proxy/load-balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        try:
            db = SessionLocal()
            try:
                log_entry = AuditLog(
                    isp_id=isp_id,
                    user_id=user_id,
                    username=username,
                    method=request.method.upper(),
                    path=str(request.url.path),
                    status_code=response.status_code,
                    client_ip=client_ip,
                    request_body=body_snapshot,
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.error("AuditMiddleware: failed to write audit log: %s", exc)

        return response
