"""
Threat scoring service.

Computes a 0–100 threat score for an alert based on multiple threat
intelligence signals (bad-actor feed, RPKI, geo-block, ML confidence).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThreatScorer:
    """Compute a composite 0–100 threat score from alert metadata."""

    # Individual signal weights
    BAD_ACTOR_POINTS: int = 40
    RPKI_INVALID_POINTS: int = 20
    GEO_BLOCKED_POINTS: int = 20
    ML_CONFIDENCE_POINTS: int = 20
    ML_CONFIDENCE_THRESHOLD: float = 0.7

    def calculate_score(self, alert_data: dict) -> int:
        """Compute a 0–100 threat score for *alert_data*.

        Args:
            alert_data: Mapping that may include:
                - ``bad_actor`` (bool): IP matched threat-intel bad-actor feed.
                - ``rpki_invalid`` (bool): Source prefix has RPKI invalid status.
                - ``geo_blocked`` (bool): Source region is geo-blocked.
                - ``ml_confidence`` (float): ML model confidence value 0–1.

        Returns:
            Integer threat score clamped to [0, 100].
        """
        score = 0

        if alert_data.get("bad_actor"):
            score += self.BAD_ACTOR_POINTS

        if alert_data.get("rpki_invalid"):
            score += self.RPKI_INVALID_POINTS

        if alert_data.get("geo_blocked"):
            score += self.GEO_BLOCKED_POINTS

        ml_confidence = float(alert_data.get("ml_confidence", 0.0))
        if ml_confidence >= self.ML_CONFIDENCE_THRESHOLD:
            score += self.ML_CONFIDENCE_POINTS

        return min(100, score)


def get_threat_score(
    alert_data: dict,
    redis_client=None,
) -> int:
    """Compute a threat score, optionally checking Redis threat-intel feed.

    Checks the Redis SET ``threat_intel:bad_actors`` for the source IP.
    If found, sets ``alert_data["bad_actor"] = True`` before scoring.

    Args:
        alert_data:   Alert metadata dict (see :meth:`ThreatScorer.calculate_score`).
        redis_client: Optional Redis client.  When provided, a ``SISMEMBER``
                      check is performed against ``threat_intel:bad_actors``.

    Returns:
        Integer threat score in [0, 100].
    """
    if redis_client is not None:
        src_ip: Optional[str] = alert_data.get("source_ip") or alert_data.get("src_ip")
        if src_ip:
            try:
                hit = redis_client.sismember("threat_intel:bad_actors", src_ip)
                if hit:
                    alert_data = dict(alert_data)  # avoid mutating the caller's dict
                    alert_data["bad_actor"] = True
            except Exception as exc:
                logger.warning("threat_intel Redis check failed: %s", exc)

    scorer = ThreatScorer()
    return scorer.calculate_score(alert_data)
