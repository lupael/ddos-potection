"""
Flow authentication service: validates that NetFlow/sFlow/IPFIX packets
arrive from registered router IPs.
"""
import ipaddress
import logging
from typing import List, Optional

import redis

from config import settings
from models.models import FlowSource

logger = logging.getLogger(__name__)

_CACHE_TTL = 60  # seconds
_CACHE_KEY_PREFIX = "flow_auth:authorized:"


class FlowAuthenticator:
    """Validates incoming flow packet source IPs against registered sources."""

    def __init__(self):
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    # ------------------------------------------------------------------
    # Authorization check
    # ------------------------------------------------------------------

    def is_authorized(self, source_ip: str, isp_id: int, db) -> bool:
        """Return True if *source_ip* is a registered flow source for *isp_id*.

        Results are cached in Redis for ``_CACHE_TTL`` seconds to avoid
        per-packet database queries.
        """
        # Validate IP to prevent injection
        try:
            ipaddress.ip_address(source_ip)
        except ValueError:
            logger.warning("Invalid source IP in is_authorized: %s", source_ip)
            return False

        cache_key = f"{_CACHE_KEY_PREFIX}{isp_id}:{source_ip}"
        cached = self._redis.get(cache_key)
        if cached is not None:
            return cached == "1"

        result = (
            db.query(FlowSource)
            .filter(
                FlowSource.isp_id == isp_id,
                FlowSource.source_ip == source_ip,
                FlowSource.is_active.is_(True),
            )
            .first()
        )

        authorized = result is not None
        self._redis.setex(cache_key, _CACHE_TTL, "1" if authorized else "0")
        return authorized

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def add_source(
        self,
        source_ip: str,
        isp_id: int,
        description: Optional[str],
        db,
    ) -> FlowSource:
        """Register a new flow source IP for *isp_id*."""
        try:
            ipaddress.ip_address(source_ip)
        except ValueError:
            raise ValueError(f"Invalid IP address: {source_ip}")

        flow_source = FlowSource(
            isp_id=isp_id,
            source_ip=source_ip,
            description=description,
            is_active=True,
        )
        db.add(flow_source)
        db.commit()
        db.refresh(flow_source)

        # Invalidate cache
        cache_key = f"{_CACHE_KEY_PREFIX}{isp_id}:{source_ip}"
        self._redis.delete(cache_key)

        logger.info("Registered flow source %s for ISP %d", source_ip, isp_id)
        return flow_source

    def get_sources(self, isp_id: int, db) -> List[FlowSource]:
        """Return all registered flow sources for *isp_id*."""
        return (
            db.query(FlowSource)
            .filter(FlowSource.isp_id == isp_id)
            .order_by(FlowSource.id)
            .all()
        )


# Module-level singleton
flow_authenticator = FlowAuthenticator()
