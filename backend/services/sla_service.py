"""
Tier-based SLA compliance checking and reporting.

Defines SLA targets for standard/pro/enterprise tiers and provides helpers
to evaluate per-incident compliance, calculate breach credits, and generate
monthly compliance reports.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# SLA tier targets (seconds)
SLA_TIERS: dict = {
    "standard": {"ttd_secs": 300, "ttm_secs": 900},
    "pro":      {"ttd_secs": 120, "ttm_secs": 300},
    "enterprise": {"ttd_secs": 30,  "ttm_secs": 120},
}

# Credit percentage per breach, capped at MAX_CREDIT_PCT
_CREDIT_PER_BREACH_PCT: float = 5.0
_MAX_CREDIT_PCT: float = 30.0


class SLAComplianceChecker:
    """Evaluates SLA compliance for individual incidents and aggregates monthly reports."""

    def check_ttd(self, tier: str, actual_ttd_secs: float) -> dict:
        """Check whether a time-to-detect value meets the SLA target for a tier.

        Args:
            tier: SLA tier name — one of "standard", "pro", "enterprise".
            actual_ttd_secs: Actual time-to-detect in seconds.

        Returns:
            Dictionary with keys:
                - compliant (bool): True if actual <= target.
                - target_secs (int): SLA target in seconds for this tier.
                - breach_margin_secs (float): How far over the target (negative if compliant).

        Raises:
            ValueError: If the tier is not recognised.
        """
        tier_cfg = self._get_tier(tier)
        target = tier_cfg["ttd_secs"]
        breach_margin = actual_ttd_secs - target
        return {
            "compliant": actual_ttd_secs <= target,
            "target_secs": target,
            "breach_margin_secs": breach_margin,
        }

    def check_ttm(self, tier: str, actual_ttm_secs: float) -> dict:
        """Check whether a time-to-mitigate value meets the SLA target for a tier.

        Args:
            tier: SLA tier name — one of "standard", "pro", "enterprise".
            actual_ttm_secs: Actual time-to-mitigate in seconds.

        Returns:
            Dictionary with keys:
                - compliant (bool): True if actual <= target.
                - target_secs (int): SLA target in seconds for this tier.
                - breach_margin_secs (float): How far over the target (negative if compliant).

        Raises:
            ValueError: If the tier is not recognised.
        """
        tier_cfg = self._get_tier(tier)
        target = tier_cfg["ttm_secs"]
        breach_margin = actual_ttm_secs - target
        return {
            "compliant": actual_ttm_secs <= target,
            "target_secs": target,
            "breach_margin_secs": breach_margin,
        }

    def calculate_breach_credit(
        self, tier: str, breach_type: str, breach_count: int
    ) -> float:
        """Calculate the service credit percentage owed for a number of SLA breaches.

        Args:
            tier: SLA tier name (used for future per-tier credit rules).
            breach_type: One of "ttd" or "ttm" (currently informational).
            breach_count: Number of individual SLA breaches in the period.

        Returns:
            Credit percentage (0–30) as a float.  5% per breach, capped at 30%.
        """
        if breach_count <= 0:
            return 0.0
        credit = min(breach_count * _CREDIT_PER_BREACH_PCT, _MAX_CREDIT_PCT)
        logger.info(
            "SLAComplianceChecker: tier=%s breach_type=%s count=%d → credit=%.1f%%",
            tier, breach_type, breach_count, credit,
        )
        return credit

    def generate_monthly_report(self, records: list[dict], tier: str) -> dict:
        """Compute a monthly SLA compliance report from a list of incident records.

        Each record in *records* should be a dict with optional keys:
            - ``ttd_seconds`` (int/float): measured time-to-detect.
            - ``ttm_seconds`` (int/float): measured time-to-mitigate.

        Args:
            records: List of incident record dicts.
            tier: SLA tier name to evaluate against.

        Returns:
            Dictionary with:
                - tier (str)
                - total_incidents (int)
                - ttd_compliance_pct (float): percentage of incidents with TTD met.
                - ttm_compliance_pct (float): percentage of incidents with TTM met.
                - ttd_breach_count (int)
                - ttm_breach_count (int)
                - ttd_credit_pct (float)
                - ttm_credit_pct (float)
                - overall_credit_pct (float): max of TTD and TTM credits.
        """
        tier_cfg = self._get_tier(tier)
        ttd_target = tier_cfg["ttd_secs"]
        ttm_target = tier_cfg["ttm_secs"]

        total = len(records)
        ttd_breach = 0
        ttm_breach = 0
        ttd_evaluated = 0
        ttm_evaluated = 0

        for rec in records:
            ttd = rec.get("ttd_seconds")
            ttm = rec.get("ttm_seconds")
            if ttd is not None:
                ttd_evaluated += 1
                if float(ttd) > ttd_target:
                    ttd_breach += 1
            if ttm is not None:
                ttm_evaluated += 1
                if float(ttm) > ttm_target:
                    ttm_breach += 1

        ttd_compliant = ttd_evaluated - ttd_breach
        ttm_compliant = ttm_evaluated - ttm_breach

        ttd_compliance_pct = (ttd_compliant / ttd_evaluated * 100.0) if ttd_evaluated else 100.0
        ttm_compliance_pct = (ttm_compliant / ttm_evaluated * 100.0) if ttm_evaluated else 100.0

        ttd_credit = self.calculate_breach_credit(tier, "ttd", ttd_breach)
        ttm_credit = self.calculate_breach_credit(tier, "ttm", ttm_breach)
        overall_credit = max(ttd_credit, ttm_credit)

        return {
            "tier": tier,
            "total_incidents": total,
            "ttd_compliance_pct": round(ttd_compliance_pct, 2),
            "ttm_compliance_pct": round(ttm_compliance_pct, 2),
            "ttd_breach_count": ttd_breach,
            "ttm_breach_count": ttm_breach,
            "ttd_credit_pct": ttd_credit,
            "ttm_credit_pct": ttm_credit,
            "overall_credit_pct": overall_credit,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tier(self, tier: str) -> dict:
        """Return tier configuration or raise ValueError for unknown tiers."""
        cfg = SLA_TIERS.get(tier.lower())
        if cfg is None:
            raise ValueError(
                f"Unknown SLA tier '{tier}'. Supported: {list(SLA_TIERS.keys())}"
            )
        return cfg
