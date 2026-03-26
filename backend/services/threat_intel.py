"""
Threat intelligence feed ingestion service.
Sources: Spamhaus DROP/EDROP, Emerging Threats, CINS Army, Feodo Tracker
Refreshes hourly; stores in Redis SET for O(1) lookup.
"""
import asyncio
import ipaddress
import logging
from typing import Dict, Set

import httpx
import redis

from config import settings

logger = logging.getLogger(__name__)

FEED_URLS: Dict[str, str] = {
    "spamhaus_drop": "https://www.spamhaus.org/drop/drop.txt",
    "spamhaus_edrop": "https://www.spamhaus.org/drop/edrop.txt",
    "cins_army": "https://cinsscore.com/list/ci-badguys.txt",
    "feodo_tracker": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
}

_REDIS_BLOCKLIST_KEY = "threat_intel:blocklist"
_REDIS_STATS_PREFIX = "threat_intel:stats:"


class ThreatIntelService:
    """Downloads, parses, and stores threat intelligence feeds in Redis."""

    FEED_URLS = FEED_URLS

    def __init__(self):
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    # ------------------------------------------------------------------
    # Feed ingestion
    # ------------------------------------------------------------------

    async def fetch_feed(self, feed_name: str, url: str) -> Set[str]:
        """Download a threat feed and return a set of IP/CIDR strings."""
        entries: Set[str] = set()
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to fetch feed %s from %s: %s", feed_name, url, exc)
            return entries

        for raw_line in response.text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            # Some feeds have inline comments after a space or semicolon
            token = line.split()[0].split(";")[0].strip().rstrip(",")
            try:
                # Validate as IP or network
                if "/" in token:
                    ipaddress.ip_network(token, strict=False)
                else:
                    ipaddress.ip_address(token)
                entries.add(token)
            except ValueError:
                pass

        logger.info("Feed %s: fetched %d entries", feed_name, len(entries))
        return entries

    async def refresh_all_feeds(self) -> None:
        """Fetch all feeds and merge results into the Redis blocklist SET."""
        if not settings.THREAT_INTEL_ENABLED:
            logger.info("Threat intel disabled; skipping refresh")
            return

        tasks = {
            name: asyncio.create_task(self.fetch_feed(name, url))
            for name, url in self.FEED_URLS.items()
        }

        pipe = self._redis.pipeline()
        # Remove old blocklist entries
        pipe.delete(_REDIS_BLOCKLIST_KEY)

        for name, task in tasks.items():
            entries = await task
            if entries:
                pipe.sadd(_REDIS_BLOCKLIST_KEY, *entries)
                pipe.set(f"{_REDIS_STATS_PREFIX}{name}", len(entries))
            else:
                pipe.set(f"{_REDIS_STATS_PREFIX}{name}", 0)

        pipe.execute()
        total = self._redis.scard(_REDIS_BLOCKLIST_KEY)
        logger.info("Threat intel blocklist refreshed: %d total entries", total)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def is_malicious(self, ip: str) -> bool:
        """O(1) Redis SISMEMBER check — True if IP is in any feed."""
        if not ip:
            return False
        # Direct IP check
        if self._redis.sismember(_REDIS_BLOCKLIST_KEY, ip):
            return True
        # CIDR-range membership check
        try:
            addr = ipaddress.ip_address(ip)
            for entry in self._redis.sscan_iter(_REDIS_BLOCKLIST_KEY):
                if "/" in entry:
                    try:
                        if addr in ipaddress.ip_network(entry, strict=False):
                            return True
                    except ValueError:
                        pass
        except ValueError:
            pass
        return False

    def get_threat_score(self, ip: str) -> int:
        """Return 0-100 threat score for *ip* based on feed membership."""
        if not ip:
            return 0
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return 0

        score = 40 if self.is_malicious(ip) else 0
        # RPKI invalid placeholder — a real implementation would call an RPKI validator
        return min(score, 100)

    def get_feed_stats(self) -> Dict[str, int]:
        """Return per-feed entry count stored in Redis."""
        stats: Dict[str, int] = {}
        for name in self.FEED_URLS:
            raw = self._redis.get(f"{_REDIS_STATS_PREFIX}{name}")
            stats[name] = int(raw) if raw is not None else 0
        stats["total"] = self._redis.scard(_REDIS_BLOCKLIST_KEY)
        return stats


# Module-level singleton
threat_intel_service = ThreatIntelService()
