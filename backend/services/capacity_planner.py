"""
Capacity planning service: traffic growth projection and capacity estimates.
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CapacityPlanner:
    """Projects network capacity needs based on historical traffic trends."""

    def project_traffic_growth(
        self,
        historical_data: list[dict[str, Any]],
        months: int = 3,
    ) -> dict[str, Any]:
        """Project traffic growth using simple linear regression.

        Args:
            historical_data: List of dicts with ``timestamp`` (ISO-8601 or
                :class:`datetime`) and ``gbps`` (float) keys, ordered oldest
                first.
            months: Number of months to project into the future.

        Returns:
            Dict with ``current_gbps``, ``projected_gbps``, ``growth_rate``,
            ``months``, and ``data_points`` keys.
        """
        if not historical_data:
            return {
                "current_gbps": 0.0,
                "projected_gbps": 0.0,
                "growth_rate": 0.0,
                "months": months,
                "data_points": 0,
            }

        values: list[float] = []
        for entry in historical_data:
            gbps = float(entry.get("gbps", 0) or 0)
            values.append(gbps)

        n = len(values)
        current = values[-1] if values else 0.0

        if n < 2:
            return {
                "current_gbps": round(current, 3),
                "projected_gbps": round(current, 3),
                "growth_rate": 0.0,
                "months": months,
                "data_points": n,
            }

        # Simple linear regression (least squares)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator else 0.0

        # Project *months* steps ahead (each step = one data interval)
        projected = current + slope * months
        projected = max(0.0, projected)

        growth_rate = (slope / current * 100.0) if current else 0.0

        return {
            "current_gbps": round(current, 3),
            "projected_gbps": round(projected, 3),
            "growth_rate": round(growth_rate, 2),
            "months": months,
            "data_points": n,
        }

    def estimate_capacity_needs(
        self,
        current_gbps: float,
        growth_rate: float,
        months: int = 12,
    ) -> list[dict[str, Any]]:
        """Return month-by-month capacity estimates.

        Args:
            current_gbps: Current peak throughput in Gbps.
            growth_rate: Monthly growth rate as a percentage (e.g. ``5.0``
                means 5 % per month).
            months: Number of months to project.

        Returns:
            List of dicts, one per month, each with ``month``,
            ``estimated_gbps``, and ``headroom_recommended_gbps`` keys.
        """
        results: list[dict[str, Any]] = []
        rate = growth_rate / 100.0
        gbps = current_gbps

        for m in range(1, months + 1):
            gbps = gbps * (1 + rate)
            # Recommended headroom: 30 % above projected
            results.append({
                "month": m,
                "estimated_gbps": round(gbps, 3),
                "headroom_recommended_gbps": round(gbps * 1.3, 3),
            })

        return results

    def generate_capacity_report(
        self,
        isp_id: int,
        redis_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a full capacity planning report for an ISP.

        Args:
            isp_id: ISP primary key (informational).
            redis_data: Optional dict of recent traffic metrics from Redis
                (``{timestamp_key: gbps_value}``).  When omitted or empty the
                projection will be based on zero data points and callers should
                populate this from their traffic store (e.g. Redis TSDB keys or
                a DB query against ``TrafficLog``).

        Returns:
            Capacity report dict.
        """
        historical: list[dict[str, Any]] = []

        if redis_data:
            for ts_key, gbps_val in sorted(redis_data.items()):
                try:
                    historical.append({"timestamp": ts_key, "gbps": float(gbps_val)})
                except (TypeError, ValueError):
                    pass

        projection = self.project_traffic_growth(historical, months=3)
        monthly_needs = self.estimate_capacity_needs(
            current_gbps=projection["current_gbps"],
            growth_rate=max(projection["growth_rate"], 5.0),  # floor at 5 %
            months=6,
        )

        return {
            "isp_id": isp_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "projection_3m": projection,
            "monthly_capacity_needs": monthly_needs,
        }
