"""
Custom domain / CNAME management for ISP white-label portals.

DNS verification is intentionally a stub — production deployments should
replace ``verify_cname`` with a real DNS resolver (e.g. ``aiodns``).
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# RFC-1123 hostname regex (simplified)
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"          # first char of each label
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"  # rest of label
    r"\.)+"                      # dot separator
    r"[a-zA-Z]{2,63}$"           # TLD
)


class CustomDomainManager:
    """Manages custom portal domains (CNAMEs) for ISPs."""

    def validate_domain(self, domain: str) -> bool:
        """Validate a domain name using a regex — no DNS lookup or shell calls.

        Args:
            domain: The domain string to validate, e.g. ``"portal.myisp.com"``.

        Returns:
            ``True`` if the domain looks syntactically valid.
        """
        if not domain or len(domain) > 253:
            return False
        return bool(_DOMAIN_RE.match(domain))

    async def set_domain(self, isp_id: int, domain: str, db: Any) -> dict[str, Any]:
        """Persist a custom portal domain for an ISP.

        Validates the domain first; raises ``ValueError`` if invalid.

        Args:
            isp_id: Primary key of the ISP record.
            domain: The desired custom domain.
            db: SQLAlchemy ``Session`` instance.

        Returns:
            Updated domain config dict.
        """
        if not self.validate_domain(domain):
            raise ValueError(f"Invalid domain name: {domain!r}")

        from models.models import ISP

        isp = db.query(ISP).filter(ISP.id == isp_id).first()
        if isp is None:
            raise LookupError(f"ISP {isp_id} not found")

        isp.brand_portal_domain = domain
        db.commit()
        db.refresh(isp)
        logger.info("ISP %d: custom domain set to %s", isp_id, domain)
        return self.get_domain_config(isp_id, db) or {}

    def verify_cname(self, domain: str, expected_target: str) -> dict[str, Any]:
        """Stub CNAME verification.

        Real implementations should resolve the CNAME record for *domain* and
        compare it against *expected_target*.

        Args:
            domain: The custom domain to check.
            expected_target: The expected CNAME target hostname.

        Returns:
            A dict with ``verified``, ``cname_target``, and ``message`` keys.
        """
        return {
            "verified": False,
            "cname_target": expected_target,
            "message": "DNS verification not performed in stub",
        }

    def get_domain_config(self, isp_id: int, db: Any) -> dict[str, Any] | None:
        """Return the current domain config for an ISP.

        Args:
            isp_id: Primary key of the ISP record.
            db: SQLAlchemy ``Session`` instance.

        Returns:
            Dict with ``isp_id`` and ``domain`` keys, or ``None`` if the ISP is
            not found or has no domain set.
        """
        from models.models import ISP

        isp = db.query(ISP).filter(ISP.id == isp_id).first()
        if isp is None:
            return None
        return {
            "isp_id": isp_id,
            "domain": isp.brand_portal_domain,
        }
