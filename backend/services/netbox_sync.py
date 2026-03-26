"""
NetBox IPAM synchronization service.
Auto-imports prefixes/IP ranges and pushes mitigations as journal entries.
"""
import logging
from typing import List, Dict

import httpx

from config import settings

logger = logging.getLogger(__name__)


class NetboxSyncService:
    """Synchronizes prefix/IP data with a NetBox IPAM instance."""

    def __init__(self):
        self.base_url = settings.NETBOX_URL.rstrip("/") if settings.NETBOX_URL else ""
        self.token = settings.NETBOX_TOKEN
        self.enabled = settings.NETBOX_ENABLED

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers(), timeout=30)

    # ------------------------------------------------------------------
    # Prefix sync
    # ------------------------------------------------------------------

    async def fetch_prefixes(self, isp_id: int) -> List[Dict]:
        """Fetch prefixes tagged with 'ddos-protection' from NetBox."""
        if not self.enabled or not self.base_url:
            logger.info("NetBox sync disabled or URL not configured")
            return []

        url = f"{self.base_url}/api/ipam/prefixes/"
        params = {"tag": "ddos-protection", "limit": 1000}
        try:
            async with self._client() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            logger.info("Fetched %d prefixes from NetBox for ISP %d", len(results), isp_id)
            return results
        except Exception as exc:
            logger.error("Failed to fetch NetBox prefixes: %s", exc)
            return []

    async def sync_prefixes_to_db(self, isp_id: int, db) -> int:
        """Fetch NetBox prefixes and upsert them into local Rule records.

        Returns the number of records synced.
        """
        prefixes = await self.fetch_prefixes(isp_id)
        if not prefixes:
            return 0

        from models.models import Rule

        count = 0
        for prefix_obj in prefixes:
            prefix = prefix_obj.get("prefix", "")
            if not prefix:
                continue

            existing = (
                db.query(Rule)
                .filter(
                    Rule.isp_id == isp_id,
                    Rule.name == f"netbox:{prefix}",
                )
                .first()
            )
            if existing is None:
                rule = Rule(
                    isp_id=isp_id,
                    name=f"netbox:{prefix}",
                    rule_type="ip_block",
                    condition={"prefix": prefix, "source": "netbox"},
                    action="alert",
                    priority=50,
                    is_active=True,
                )
                db.add(rule)
                count += 1

        db.commit()
        logger.info("Synced %d new prefixes from NetBox for ISP %d", count, isp_id)
        return count

    # ------------------------------------------------------------------
    # Journal entries
    # ------------------------------------------------------------------

    async def push_mitigation_journal(
        self, prefix: str, action: str, comment: str
    ) -> bool:
        """POST a journal entry to NetBox for a mitigation action."""
        if not self.enabled or not self.base_url:
            return False

        url = f"{self.base_url}/api/extras/journal-entries/"
        payload = {
            "assigned_object_type": "ipam.prefix",
            "comments": f"[{action.upper()}] {prefix} — {comment}",
            "kind": "info",
        }
        try:
            async with self._client() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            logger.info("Posted NetBox journal entry for %s", prefix)
            return True
        except Exception as exc:
            logger.error("Failed to post NetBox journal entry: %s", exc)
            return False

    # ------------------------------------------------------------------
    # IP info
    # ------------------------------------------------------------------

    async def get_ip_info(self, ip: str) -> Dict:
        """Query NetBox for IPAM information about a specific address."""
        if not self.enabled or not self.base_url:
            return {}

        url = f"{self.base_url}/api/ipam/ip-addresses/"
        params = {"address": ip}
        try:
            async with self._client() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            return results[0] if results else {}
        except Exception as exc:
            logger.error("Failed to get NetBox IP info for %s: %s", ip, exc)
            return {}


# Module-level singleton
netbox_sync_service = NetboxSyncService()
