"""
Attack campaign tracking service.
Groups related alerts into campaigns based on time proximity and source similarity.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models.models import AttackCampaign

logger = logging.getLogger(__name__)

_CAMPAIGN_WINDOW_HOURS = 4


class CampaignTracker:

    async def correlate_alert(self, alert_dict: dict, db: Session) -> Optional[AttackCampaign]:
        """
        Check if alert belongs to an existing active campaign (same source ASN pattern,
        within 4h window), or creates a new campaign.
        """
        isp_id = alert_dict.get("isp_id")
        if not isp_id:
            return None

        window_start = datetime.now(timezone.utc) - timedelta(hours=_CAMPAIGN_WINDOW_HOURS)
        alert_source_asn = alert_dict.get("source_asn")

        candidates = (
            db.query(AttackCampaign)
            .filter(
                AttackCampaign.isp_id == isp_id,
                AttackCampaign.status == "active",
                AttackCampaign.last_seen >= window_start,
            )
            .all()
        )

        for campaign in candidates:
            if alert_source_asn and campaign.source_asns:
                if alert_source_asn in campaign.source_asns:
                    await self.update_campaign_stats(campaign.id, alert_dict, db)
                    return campaign

        campaign = AttackCampaign(
            isp_id=isp_id,
            name=f"Campaign-{isp_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            campaign_type=_infer_campaign_type(alert_dict.get("alert_type", "")),
            source_asns=[alert_source_asn] if alert_source_asn else [],
            target_prefixes=[alert_dict.get("target_ip")] if alert_dict.get("target_ip") else [],
            total_alerts=1,
            peak_pps=alert_dict.get("pps", 0),
            peak_bps=alert_dict.get("bps", 0),
            last_seen=datetime.now(timezone.utc),
            status="active",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign

    async def update_campaign_stats(
        self, campaign_id: int, alert_dict: dict, db: Session
    ) -> None:
        campaign = db.query(AttackCampaign).filter(AttackCampaign.id == campaign_id).first()
        if not campaign:
            return

        campaign.total_alerts = (campaign.total_alerts or 0) + 1
        campaign.last_seen = datetime.now(timezone.utc)

        pps = alert_dict.get("pps", 0)
        bps = alert_dict.get("bps", 0)
        if pps > (campaign.peak_pps or 0):
            campaign.peak_pps = pps
        if bps > (campaign.peak_bps or 0):
            campaign.peak_bps = bps

        asn = alert_dict.get("source_asn")
        if asn:
            asns = list(campaign.source_asns or [])
            if asn not in asns:
                asns.append(asn)
                campaign.source_asns = asns

        db.commit()

    async def get_active_campaigns(self, isp_id: int, db: Session) -> list:
        return (
            db.query(AttackCampaign)
            .filter(
                AttackCampaign.isp_id == isp_id,
                AttackCampaign.status == "active",
            )
            .order_by(AttackCampaign.last_seen.desc())
            .all()
        )


    async def cross_isp_correlate(
        self, db: Session, window_hours: int = 1
    ) -> list[dict]:
        """Detect coordinated botnet campaigns spanning multiple ISP tenants.

        Looks for ``AttackCampaign`` records across *different* ISPs that share
        one or more source ASNs within the given time window.  A match indicates
        that the same botnet is attacking multiple customers simultaneously.

        Args:
            db: SQLAlchemy database session.
            window_hours: Look-back window in hours (default 1).

        Returns:
            List of correlation dicts, each containing::

                {
                    "source_asn": str,
                    "campaign_ids": [int, ...],
                    "isp_ids": [int, ...],
                    "total_alerts": int,
                    "peak_pps": int,
                }
        """
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        active = (
            db.query(AttackCampaign)
            .filter(
                AttackCampaign.status == "active",
                AttackCampaign.last_seen >= window_start,
            )
            .all()
        )

        # Build index: source_asn -> [campaign_id, ...]
        asn_index: dict[str, list] = {}
        for campaign in active:
            for asn in campaign.source_asns or []:
                asn_index.setdefault(str(asn), []).append(campaign)

        correlations: list[dict] = []
        for asn, campaigns in asn_index.items():
            isp_ids = list({c.isp_id for c in campaigns if c.isp_id})
            if len(isp_ids) < 2:
                # Only interesting when >= 2 different ISPs are attacked
                continue
            correlations.append(
                {
                    "source_asn": asn,
                    "campaign_ids": [c.id for c in campaigns],
                    "isp_ids": isp_ids,
                    "total_alerts": sum(c.total_alerts or 0 for c in campaigns),
                    "peak_pps": max((c.peak_pps or 0) for c in campaigns),
                }
            )

        correlations.sort(key=lambda x: x["peak_pps"], reverse=True)
        if correlations:
            logger.warning(
                "Cross-ISP correlation: %d coordinated campaign group(s) detected",
                len(correlations),
            )
        return correlations


def _infer_campaign_type(alert_type: str) -> str:
    volumetric = {"syn_flood", "udp_flood", "icmp_flood", "volumetric"}
    application = {"dns_amplification", "http_flood", "slowloris", "application"}
    if alert_type.lower() in volumetric:
        return "volumetric"
    if alert_type.lower() in application:
        return "application"
    return "mixed"
