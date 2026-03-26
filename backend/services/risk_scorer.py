"""
Daily attack-probability risk scoring per network prefix.

Scores are in the range 0–100 and drive pre-emptive mitigation decisions.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_THRESHOLDS = {
    "monitor": 30,
    "pre-emptive_rate_limit": 70,
    "pre-emptive_block": 90,
}


class RiskScorer:
    """Calculates daily attack-probability risk scores for network prefixes."""

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def calculate_prefix_risk(
        self,
        prefix: str,
        historical_attacks: list[dict[str, Any]],
        threat_intel_hits: int = 0,
    ) -> dict[str, Any]:
        """Calculate a risk score (0–100) for a single prefix.

        Scoring factors:
        * **Attack frequency** – number of attacks in the last 30 days.
        * **Recency** – attacks in the last 7 days carry extra weight.
        * **Threat-intel hits** – external reputation boosts score.

        Args:
            prefix: CIDR or IP string identifying the prefix.
            historical_attacks: List of attack dicts.  Each dict should have
                a ``created_at`` key (ISO-8601 string or :class:`datetime`).
            threat_intel_hits: Number of threat-intelligence hits for this
                prefix.  Defaults to ``0``.

        Returns:
            Dict with ``prefix``, ``risk_score``, ``factors``, and
            ``recommendation`` keys.
        """
        now = datetime.now(timezone.utc)
        cutoff_30d = now - timedelta(days=30)
        cutoff_7d = now - timedelta(days=7)

        attacks_30d: list[dict] = []
        attacks_7d: list[dict] = []

        for attack in historical_attacks:
            ts = attack.get("created_at")
            if ts is None:
                continue
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    continue
            # Ensure timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if ts >= cutoff_30d:
                attacks_30d.append(attack)
            if ts >= cutoff_7d:
                attacks_7d.append(attack)

        freq_30d = len(attacks_30d)
        freq_7d = len(attacks_7d)

        # Base score: up to 50 points from 30-day frequency
        base_score = min(50.0, freq_30d * 5.0)

        # Recency boost: up to 30 points from 7-day frequency
        recency_boost = min(30.0, freq_7d * 10.0)

        # Threat-intel boost: up to 20 points
        intel_boost = min(20.0, threat_intel_hits * 4.0)

        risk_score = min(100.0, base_score + recency_boost + intel_boost)

        factors = {
            "attacks_last_30d": freq_30d,
            "attacks_last_7d": freq_7d,
            "threat_intel_hits": threat_intel_hits,
            "base_score": round(base_score, 1),
            "recency_boost": round(recency_boost, 1),
            "intel_boost": round(intel_boost, 1),
        }

        recommendation = self.get_preemptive_action(risk_score)

        return {
            "prefix": prefix,
            "risk_score": round(risk_score, 1),
            "factors": factors,
            "recommendation": recommendation,
        }

    def batch_score_prefixes(
        self, prefixes_data: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Score multiple prefixes.

        Args:
            prefixes_data: Mapping of ``prefix -> {"attacks": [...],
                "threat_intel_hits": int}``.

        Returns:
            List of risk-score dicts sorted by ``risk_score`` descending.
        """
        results: list[dict[str, Any]] = []
        for prefix, data in prefixes_data.items():
            attacks = data.get("attacks", [])
            hits = int(data.get("threat_intel_hits", 0))
            result = self.calculate_prefix_risk(prefix, attacks, hits)
            results.append(result)
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results

    def should_preempt(self, prefix: str, risk_score: float) -> bool:
        """Return ``True`` when the risk score warrants pre-emptive action.

        Args:
            prefix: Prefix string (informational only).
            risk_score: Numeric risk score (0–100).

        Returns:
            ``True`` if *risk_score* > 70.
        """
        return risk_score > 70.0

    def get_preemptive_action(self, risk_score: float) -> str:
        """Map a risk score to a recommended action string.

        Args:
            risk_score: Numeric risk score (0–100).

        Returns:
            One of ``"monitor"``, ``"pre-emptive_rate_limit"``, or
            ``"pre-emptive_block"``.
        """
        if risk_score >= _THRESHOLDS["pre-emptive_block"]:
            return "pre-emptive_block"
        if risk_score >= _THRESHOLDS["pre-emptive_rate_limit"]:
            return "pre-emptive_rate_limit"
        return "monitor"
