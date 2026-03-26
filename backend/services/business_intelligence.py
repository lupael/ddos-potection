"""
Business Intelligence service: MRR, attack-cost modelling, ROI, and KPI dashboard.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class BIService:
    """Provides business intelligence metrics for the platform."""

    # ------------------------------------------------------------------
    # MRR
    # ------------------------------------------------------------------

    def calculate_mrr(self, subscriptions: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate Monthly Recurring Revenue (MRR) from active subscriptions.

        Args:
            subscriptions: List of subscription dicts.  Each must have
                ``plan_price`` (float), ``billing_cycle``
                (``"monthly"``/``"yearly"``), and ``status`` (str) fields.

        Returns:
            Dict with ``mrr``, ``arr``, ``active_count``, ``cancelled_count``,
            and ``churn_rate`` keys.
        """
        total_mrr = 0.0
        active_count = 0
        cancelled_count = 0

        for sub in subscriptions:
            status = str(sub.get("status", "")).lower()
            price = float(sub.get("plan_price", 0) or 0)
            cycle = str(sub.get("billing_cycle", "monthly")).lower()

            if status in ("active",):
                monthly = price / 12 if cycle == "yearly" else price
                total_mrr += monthly
                active_count += 1
            elif status in ("cancelled", "expired"):
                cancelled_count += 1

        total = active_count + cancelled_count
        churn_rate = (cancelled_count / total * 100.0) if total else 0.0

        return {
            "mrr": round(total_mrr, 2),
            "arr": round(total_mrr * 12, 2),
            "active_count": active_count,
            "cancelled_count": cancelled_count,
            "churn_rate": round(churn_rate, 2),
        }

    # ------------------------------------------------------------------
    # Attack cost
    # ------------------------------------------------------------------

    def calculate_attack_cost(
        self,
        attack: dict[str, Any],
        cost_per_gbps_hour: float = 500.0,
    ) -> dict[str, Any]:
        """Estimate the financial cost of a DDoS attack.

        Args:
            attack: Attack / alert dict.  Expected keys: ``peak_gbps`` (float),
                ``duration_seconds`` (int), ``severity`` (str).
            cost_per_gbps_hour: Cost in USD per Gbps per hour of scrubbing.
                Defaults to ``500.0``.

        Returns:
            Dict with ``total_cost_usd``, ``breakdown``, and ``severity``
            keys.
        """
        peak_gbps: float = float(attack.get("peak_gbps", 0) or 0)
        duration_secs: int = int(attack.get("duration_seconds", 0) or 0)
        severity: str = str(attack.get("severity", "medium"))

        duration_hours = duration_secs / 3600.0

        scrubbing_cost = peak_gbps * duration_hours * cost_per_gbps_hour

        # Severity multiplier for operational overhead
        severity_multiplier = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0,
            "critical": 3.0,
        }.get(severity.lower(), 1.5)

        operational_cost = scrubbing_cost * 0.2 * severity_multiplier
        downtime_cost = peak_gbps * duration_hours * 50.0  # flat estimate

        total = scrubbing_cost + operational_cost + downtime_cost

        return {
            "total_cost_usd": round(total, 2),
            "breakdown": {
                "scrubbing_cost": round(scrubbing_cost, 2),
                "operational_cost": round(operational_cost, 2),
                "downtime_cost": round(downtime_cost, 2),
            },
            "severity": severity,
            "peak_gbps": peak_gbps,
            "duration_hours": round(duration_hours, 3),
        }

    # ------------------------------------------------------------------
    # ROI
    # ------------------------------------------------------------------

    def calculate_roi(
        self, costs: dict[str, Any], savings: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate return on investment.

        Args:
            costs: Dict with ``total`` (float, USD) and optional ``period_days``
                (int) keys representing platform costs.
            savings: Dict with ``total`` (float, USD) key representing
                estimated savings from prevented attacks.

        Returns:
            Dict with ``roi_percent``, ``net_benefit``, ``payback_days``, and
            ``breakeven`` keys.
        """
        total_cost = float(costs.get("total", 0) or 0)
        total_savings = float(savings.get("total", 0) or 0)
        period_days = int(costs.get("period_days", 365) or 365)

        net_benefit = total_savings - total_cost
        roi_percent = (net_benefit / total_cost * 100.0) if total_cost else 0.0

        daily_savings = total_savings / period_days if period_days else 0.0
        payback_days = (
            round(total_cost / daily_savings)
            if daily_savings > 0
            else None
        )

        return {
            "roi_percent": round(roi_percent, 2),
            "net_benefit": round(net_benefit, 2),
            "total_cost": round(total_cost, 2),
            "total_savings": round(total_savings, 2),
            "payback_days": payback_days,
            "breakeven": net_benefit >= 0,
        }

    # ------------------------------------------------------------------
    # KPI dashboard
    # ------------------------------------------------------------------

    def get_executive_kpis(
        self, isp_id: int, period_days: int = 30
    ) -> dict[str, Any]:
        """Return an aggregate executive KPI dict.

        In production this would query the database.  Here we return a
        structure showing what the response looks like; callers that have a DB
        session should call the individual methods and merge the results.

        Args:
            isp_id: ISP primary key.
            period_days: Look-back window in days.

        Returns:
            KPI dict with keys ``isp_id``, ``period_days``, ``mrr``,
            ``total_attacks``, ``mitigated_attacks``, ``mean_ttm_seconds``,
            ``estimated_savings_usd``.
        """
        return {
            "isp_id": isp_id,
            "period_days": period_days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mrr": 0.0,
            "total_attacks": 0,
            "mitigated_attacks": 0,
            "mean_ttm_seconds": 0,
            "estimated_savings_usd": 0.0,
            "note": "Populate by injecting live DB data into calculate_mrr / calculate_attack_cost.",
        }
