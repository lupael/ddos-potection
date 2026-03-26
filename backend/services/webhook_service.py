"""
Webhook delivery service.

Sends signed HTTP POST callbacks to registered webhook endpoints when
alert or mitigation events occur.  Each request is signed with HMAC-SHA256
using the webhook's secret so that recipients can verify authenticity.

Delivery uses exponential back-off retry (up to WEBHOOK_MAX_RETRIES attempts).
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from config import settings
from database import SessionLocal
from models.models import Webhook

logger = logging.getLogger(__name__)


def _sign_payload(secret: str, payload: bytes) -> str:
    """Return an HMAC-SHA256 hex digest for payload signed with secret."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


async def _deliver_once(url: str, payload: bytes, signature: str, timeout: int) -> bool:
    """Attempt a single webhook delivery.  Returns True on HTTP 2xx."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-DDoS-Signature": f"sha256={signature}",
                    "X-DDoS-Timestamp": str(int(time.time())),
                },
                timeout=timeout,
            )
        if 200 <= response.status_code < 300:
            return True
        logger.warning("Webhook %s returned HTTP %d", url, response.status_code)
        return False
    except Exception as exc:
        logger.warning("Webhook delivery error to %s: %s", url, exc)
        return False


async def deliver_webhook(webhook: Webhook, event: str, data: Dict[str, Any]) -> bool:
    """Deliver a single event to one webhook endpoint with exponential back-off retries.

    Args:
        webhook: The :class:`~models.models.Webhook` ORM instance.
        event: Event name (e.g. ``"alert.created"``).
        data: Event payload as a dict (must be JSON-serialisable).

    Returns:
        True if delivery succeeded, False if all retries were exhausted.
    """
    max_retries: int = getattr(settings, 'WEBHOOK_MAX_RETRIES', 5)
    backoff: float = getattr(settings, 'WEBHOOK_RETRY_BACKOFF', 2.0)
    timeout: int = getattr(settings, 'WEBHOOK_TIMEOUT', 10)

    body = json.dumps({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }).encode("utf-8")
    signature = _sign_payload(webhook.secret, body)

    delay = 1.0
    for attempt in range(1, max_retries + 1):
        success = await _deliver_once(webhook.url, body, signature, timeout)
        if success:
            logger.info("Webhook delivered to %s on attempt %d", webhook.url, attempt)
            return True
        if attempt < max_retries:
            logger.info(
                "Webhook delivery to %s failed (attempt %d/%d); retrying in %.1fs",
                webhook.url, attempt, max_retries, delay,
            )
            await asyncio.sleep(delay)
            delay *= backoff

    logger.error("Webhook delivery to %s failed after %d attempts", webhook.url, max_retries)
    return False


async def dispatch_event(isp_id: int, event: str, data: Dict[str, Any]) -> None:
    """Find all active webhooks for *isp_id* subscribed to *event* and deliver.

    This function is safe to fire-and-forget (``asyncio.create_task``).
    """
    db = SessionLocal()
    try:
        webhooks: List[Webhook] = db.query(Webhook).filter(
            Webhook.isp_id == isp_id,
            Webhook.is_active.is_(True),
        ).all()

        targets = [w for w in webhooks if event in (w.events or [])]
        if not targets:
            return

        await asyncio.gather(
            *[deliver_webhook(w, event, data) for w in targets],
            return_exceptions=True,
        )
    except Exception as exc:
        logger.error("dispatch_event error: %s", exc)
    finally:
        db.close()
