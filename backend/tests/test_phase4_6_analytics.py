"""
Tests for Phase 4/6 analytics features:
  - Ticketing integrations (ServiceNow, JIRA, Zendesk)
  - Branded email templates
  - Custom domain manager
  - Signature library
  - Botnet C2 fingerprinter
  - Risk scorer
  - Business intelligence
  - Capacity planner
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ticketing
# ---------------------------------------------------------------------------

from services.ticketing_service import JIRAClient, ServiceNowClient, ZendeskClient


class TestServiceNowClient:
    def test_instantiation(self):
        client = ServiceNowClient("myco.service-now.com", "admin", "pass")
        assert client._base_url == "https://myco.service-now.com"

    @pytest.mark.asyncio
    async def test_create_incident_no_aiohttp(self, monkeypatch):
        """When aiohttp is unavailable create_incident returns {}."""
        import services.ticketing_service as ts

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", False)
        client = ServiceNowClient("myco.service-now.com", "admin", "pass")
        result = await client.create_incident("Test", "Details")
        assert result == {}

    @pytest.mark.asyncio
    async def test_create_incident_with_aiohttp(self, monkeypatch):
        """create_incident returns parsed JSON on success."""
        import services.ticketing_service as ts

        fake_response = AsyncMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json = AsyncMock(return_value={"result": {"sys_id": "abc123"}})
        fake_response.__aenter__ = AsyncMock(return_value=fake_response)
        fake_response.__aexit__ = AsyncMock(return_value=False)

        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value=fake_response)
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)

        fake_aiohttp = MagicMock()
        fake_aiohttp.ClientSession = MagicMock(return_value=fake_session)

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", True)
        monkeypatch.setattr(ts, "_aiohttp", fake_aiohttp)

        client = ServiceNowClient("myco.service-now.com", "admin", "pass")
        result = await client.create_incident("Test incident", "Full description")
        assert result == {"result": {"sys_id": "abc123"}}


class TestJIRAClient:
    def test_instantiation(self):
        client = JIRAClient("https://myco.atlassian.net", "me@x.com", "token", "DDOS")
        assert "atlassian" in client._base_url
        assert client._project_key == "DDOS"

    @pytest.mark.asyncio
    async def test_create_issue_no_aiohttp(self, monkeypatch):
        import services.ticketing_service as ts

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", False)
        client = JIRAClient("https://myco.atlassian.net", "me@x.com", "token", "DDOS")
        result = await client.create_issue("Summary", "Body")
        assert result == {}

    @pytest.mark.asyncio
    async def test_create_issue_with_aiohttp(self, monkeypatch):
        import services.ticketing_service as ts

        fake_response = AsyncMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json = AsyncMock(return_value={"id": "10001", "key": "DDOS-1"})
        fake_response.__aenter__ = AsyncMock(return_value=fake_response)
        fake_response.__aexit__ = AsyncMock(return_value=False)

        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value=fake_response)
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)

        fake_aiohttp = MagicMock()
        fake_aiohttp.ClientSession = MagicMock(return_value=fake_session)

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", True)
        monkeypatch.setattr(ts, "_aiohttp", fake_aiohttp)

        client = JIRAClient("https://myco.atlassian.net", "me@x.com", "token", "DDOS")
        result = await client.create_issue("DDoS detected", "Attack on 10.0.0.1")
        assert result.get("key") == "DDOS-1"


class TestZendeskClient:
    def test_instantiation(self):
        client = ZendeskClient("myco", "me@x.com", "token")
        assert client._base_url == "https://myco.zendesk.com"

    @pytest.mark.asyncio
    async def test_create_ticket_no_aiohttp(self, monkeypatch):
        import services.ticketing_service as ts

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", False)
        client = ZendeskClient("myco", "me@x.com", "token")
        result = await client.create_ticket("Subject", "Body")
        assert result == {}

    @pytest.mark.asyncio
    async def test_create_ticket_with_aiohttp(self, monkeypatch):
        import services.ticketing_service as ts

        fake_response = AsyncMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json = AsyncMock(return_value={"ticket": {"id": 42, "status": "new"}})
        fake_response.__aenter__ = AsyncMock(return_value=fake_response)
        fake_response.__aexit__ = AsyncMock(return_value=False)

        fake_session = MagicMock()
        fake_session.post = MagicMock(return_value=fake_response)
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)

        fake_aiohttp = MagicMock()
        fake_aiohttp.ClientSession = MagicMock(return_value=fake_session)

        monkeypatch.setattr(ts, "_AIOHTTP_AVAILABLE", True)
        monkeypatch.setattr(ts, "_aiohttp", fake_aiohttp)

        client = ZendeskClient("myco", "me@x.com", "token")
        result = await client.create_ticket("DDoS alert", "Details here")
        assert result["ticket"]["id"] == 42


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

from services.email_templates import BrandedEmailRenderer


class TestBrandedEmailRenderer:
    BRANDING = {
        "brand_primary_color": "#e84040",
        "brand_logo_url": "https://cdn.example.com/logo.png",
        "brand_company_name": "TestISP",
        "brand_support_email": "support@testisp.com",
        "brand_portal_domain": "portal.testisp.com",
    }

    ALERT = {
        "alert_type": "syn_flood",
        "severity": "critical",
        "target_ip": "192.168.1.1",
        "source_ip": "10.0.0.1",
        "description": "SYN flood detected",
        "timestamp": "2024-01-01T00:00:00",
    }

    def test_render_alert_email_returns_html(self):
        renderer = BrandedEmailRenderer()
        html = renderer.render_alert_email(self.ALERT, self.BRANDING)
        assert "<!DOCTYPE html>" in html
        assert "SYN flood detected" in html
        assert "#e84040" in html
        assert "TestISP" in html

    def test_render_monthly_report_email(self):
        renderer = BrandedEmailRenderer()
        report = {
            "period": "January 2024",
            "total_attacks": 42,
            "peak_gbps": 15.3,
            "mitigated": 40,
            "top_attack_types": ["syn_flood", "udp_flood"],
        }
        html = renderer.render_monthly_report_email(report, self.BRANDING)
        assert "42" in html
        assert "syn_flood" in html
        assert "TestISP" in html

    def test_render_welcome_email(self):
        renderer = BrandedEmailRenderer()
        user = {"username": "alice", "email": "alice@example.com", "role": "admin"}
        html = renderer.render_welcome_email(user, self.BRANDING)
        assert "alice" in html
        assert "TestISP" in html
        # Portal link should appear in the email body as an href
        assert 'href="https://portal.testisp.com"' in html

    def test_render_alert_email_missing_fields(self):
        renderer = BrandedEmailRenderer()
        # Should not raise even with minimal data
        html = renderer.render_alert_email({}, {})
        assert "<!DOCTYPE html>" in html


# ---------------------------------------------------------------------------
# Custom domain
# ---------------------------------------------------------------------------

from services.custom_domain import CustomDomainManager


class TestCustomDomainManager:
    def setup_method(self):
        self.mgr = CustomDomainManager()

    def test_validate_domain_valid(self):
        assert self.mgr.validate_domain("portal.myisp.com") is True
        assert self.mgr.validate_domain("sub.domain.example.co.uk") is True
        assert self.mgr.validate_domain("a.io") is True

    def test_validate_domain_invalid(self):
        assert self.mgr.validate_domain("") is False
        assert self.mgr.validate_domain("not_a_domain") is False
        assert self.mgr.validate_domain("-bad.example.com") is False
        assert self.mgr.validate_domain("has space.com") is False

    def test_verify_cname_stub(self):
        result = self.mgr.verify_cname("portal.myisp.com", "target.example.com")
        assert result["verified"] is False
        assert result["cname_target"] == "target.example.com"
        assert "stub" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_set_domain_invalid(self):
        with pytest.raises(ValueError, match="Invalid domain"):
            await self.mgr.set_domain(1, "not valid!", db=None)

    @pytest.mark.asyncio
    async def test_set_domain_valid(self):
        mock_isp = MagicMock()
        mock_isp.brand_portal_domain = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_isp
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = await self.mgr.set_domain(1, "portal.myisp.com", mock_db)
        assert result.get("domain") == "portal.myisp.com"


# ---------------------------------------------------------------------------
# Signature library
# ---------------------------------------------------------------------------

from services.signature_library import AttackSignature, SignatureLibrary


class TestSignatureLibrary:
    def setup_method(self):
        self.lib = SignatureLibrary()

    def test_extract_bpf_from_alert_full(self):
        alert = {
            "source_ip": "1.2.3.4",
            "target_ip": "5.6.7.8",
            "protocol": "TCP",
            "dst_port": 80,
        }
        bpf = self.lib.extract_bpf_from_alert(alert)
        assert bpf is not None
        assert "1.2.3.4" in bpf
        assert "5.6.7.8" in bpf
        assert "tcp" in bpf
        assert "80" in bpf

    def test_extract_bpf_from_alert_empty(self):
        bpf = self.lib.extract_bpf_from_alert({})
        assert bpf is None

    def test_extract_flowspec_from_alert(self):
        alert = {"source_ip": "1.2.3.4", "target_ip": "10.0.0.1", "protocol": "udp"}
        fs = self.lib.extract_flowspec_from_alert(alert)
        assert fs is not None
        assert "10.0.0.1" in fs
        assert "17" in fs  # UDP protocol number

    def test_add_and_search_signatures(self):
        sig = AttackSignature(
            id="sig-1",
            name="Test",
            attack_type="syn_flood",
            bpf_filter="tcp and src port 0",
            flowspec_rule="match destination 1.2.3.4/32 then discard",
            confidence=0.9,
            created_at=datetime.now(timezone.utc),
            isp_id=1,
        )
        assert self.lib.add_signature(sig) is True
        assert self.lib.add_signature(sig) is False  # duplicate

        results = self.lib.search_signatures(attack_type="syn_flood")
        assert len(results) == 1

        results_low = self.lib.search_signatures(min_confidence=0.95)
        assert len(results_low) == 0

    def test_export_json(self):
        sig = AttackSignature(
            id="sig-2",
            name="Test JSON",
            attack_type="udp_flood",
            bpf_filter="udp",
            flowspec_rule="match protocol 17 then discard",
            confidence=0.8,
            created_at=datetime.now(timezone.utc),
            isp_id=1,
        )
        self.lib.add_signature(sig)
        exported = self.lib.export_signatures("json")
        data = json.loads(exported)
        assert any(d["id"] == "sig-2" for d in data)

    def test_export_bpf(self):
        sig = AttackSignature(
            id="sig-3",
            name="BPF export",
            attack_type="icmp_flood",
            bpf_filter="icmp",
            flowspec_rule="",
            confidence=0.75,
            created_at=datetime.now(timezone.utc),
            isp_id=1,
        )
        self.lib.add_signature(sig)
        exported = self.lib.export_signatures("bpf")
        assert "icmp" in exported


# ---------------------------------------------------------------------------
# Botnet C2
# ---------------------------------------------------------------------------

from services.botnet_c2 import BotnetC2Fingerprinter


class TestBotnetC2Fingerprinter:
    def setup_method(self):
        self.fp = BotnetC2Fingerprinter()

    def test_analyze_flow_mirai_match(self):
        flow = {"protocol": "tcp", "dst_port": 23, "src_ip": "1.2.3.4", "dst_ip": "5.6.7.8"}
        result = self.fp.analyze_flow(flow)
        assert result is not None
        assert result["family"] == "Mirai"

    def test_analyze_flow_no_match(self):
        flow = {"protocol": "tcp", "dst_port": 12345}
        result = self.fp.analyze_flow(flow)
        assert result is None

    def test_analyze_flow_irc_match(self):
        flow = {"protocol": "tcp", "dst_port": 6667}
        result = self.fp.analyze_flow(flow)
        assert result is not None
        assert result["family"] == "IRC-C2"

    def test_get_c2_report(self):
        flows = [
            {"protocol": "tcp", "dst_port": 23},
            {"protocol": "tcp", "dst_port": 80},
            {"protocol": "tcp", "dst_port": 6667},
        ]
        report = self.fp.get_c2_report(flows)
        assert report["total_flows"] == 3
        assert report["matched_flows"] >= 1
        assert "Mirai" in report["c2_families"] or "IRC-C2" in report["c2_families"]

    def test_generate_c2_alert(self):
        flow = {"protocol": "tcp", "dst_port": 23, "src_ip": "1.1.1.1", "dst_ip": "2.2.2.2"}
        match = self.fp.analyze_flow(flow)
        assert match is not None
        alert = self.fp.generate_c2_alert(match)
        assert alert["alert_type"] == "botnet_c2"
        assert alert["severity"] == "critical"
        assert "Mirai" in alert["description"]


# ---------------------------------------------------------------------------
# Risk scorer
# ---------------------------------------------------------------------------

from services.risk_scorer import RiskScorer


class TestRiskScorer:
    def setup_method(self):
        self.scorer = RiskScorer()

    def _make_attacks(self, count: int, days_ago: int) -> list[dict]:
        ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return [{"created_at": ts.isoformat(), "severity": "high"}] * count

    def test_calculate_prefix_risk_no_attacks(self):
        result = self.scorer.calculate_prefix_risk("10.0.0.0/24", [])
        assert result["risk_score"] == 0.0
        assert result["recommendation"] == "monitor"

    def test_calculate_prefix_risk_low(self):
        attacks = self._make_attacks(3, days_ago=20)
        result = self.scorer.calculate_prefix_risk("10.0.0.1", attacks)
        assert 0 < result["risk_score"] < 70
        assert result["recommendation"] == "monitor"

    def test_calculate_prefix_risk_high(self):
        attacks = self._make_attacks(10, days_ago=2)
        result = self.scorer.calculate_prefix_risk("10.0.0.1", attacks, threat_intel_hits=5)
        assert result["risk_score"] >= 70
        assert result["recommendation"] in ("pre-emptive_rate_limit", "pre-emptive_block")

    def test_should_preempt(self):
        assert self.scorer.should_preempt("10.0.0.1", 75.0) is True
        assert self.scorer.should_preempt("10.0.0.1", 50.0) is False

    def test_get_preemptive_action(self):
        assert self.scorer.get_preemptive_action(95.0) == "pre-emptive_block"
        assert self.scorer.get_preemptive_action(75.0) == "pre-emptive_rate_limit"
        assert self.scorer.get_preemptive_action(20.0) == "monitor"

    def test_batch_score_sorted(self):
        data = {
            "10.0.0.1": {"attacks": self._make_attacks(5, days_ago=1), "threat_intel_hits": 0},
            "10.0.0.2": {"attacks": [], "threat_intel_hits": 0},
        }
        results = self.scorer.batch_score_prefixes(data)
        assert results[0]["risk_score"] >= results[1]["risk_score"]


# ---------------------------------------------------------------------------
# Business intelligence
# ---------------------------------------------------------------------------

from services.business_intelligence import BIService


class TestBIService:
    def setup_method(self):
        self.bi = BIService()

    def test_calculate_mrr_monthly(self):
        subs = [
            {"plan_price": 100.0, "billing_cycle": "monthly", "status": "active"},
            {"plan_price": 200.0, "billing_cycle": "monthly", "status": "active"},
            {"plan_price": 50.0, "billing_cycle": "monthly", "status": "cancelled"},
        ]
        result = self.bi.calculate_mrr(subs)
        assert result["mrr"] == 300.0
        assert result["active_count"] == 2
        assert result["cancelled_count"] == 1
        assert result["arr"] == pytest.approx(3600.0)

    def test_calculate_mrr_yearly(self):
        subs = [
            {"plan_price": 1200.0, "billing_cycle": "yearly", "status": "active"},
        ]
        result = self.bi.calculate_mrr(subs)
        assert result["mrr"] == pytest.approx(100.0)

    def test_calculate_mrr_empty(self):
        result = self.bi.calculate_mrr([])
        assert result["mrr"] == 0.0
        assert result["churn_rate"] == 0.0

    def test_calculate_attack_cost(self):
        attack = {"peak_gbps": 10.0, "duration_seconds": 3600, "severity": "high"}
        result = self.bi.calculate_attack_cost(attack)
        assert result["total_cost_usd"] > 0
        assert "scrubbing_cost" in result["breakdown"]
        assert result["peak_gbps"] == 10.0

    def test_calculate_attack_cost_zero(self):
        result = self.bi.calculate_attack_cost({})
        assert result["total_cost_usd"] == 0.0

    def test_calculate_roi_positive(self):
        result = self.bi.calculate_roi(
            costs={"total": 10000.0, "period_days": 365},
            savings={"total": 50000.0},
        )
        assert result["roi_percent"] > 0
        assert result["breakeven"] is True
        assert result["payback_days"] is not None

    def test_calculate_roi_negative(self):
        result = self.bi.calculate_roi(
            costs={"total": 50000.0},
            savings={"total": 10000.0},
        )
        assert result["roi_percent"] < 0
        assert result["breakeven"] is False


# ---------------------------------------------------------------------------
# Capacity planner
# ---------------------------------------------------------------------------

from services.capacity_planner import CapacityPlanner


class TestCapacityPlanner:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_project_traffic_growth_empty(self):
        result = self.planner.project_traffic_growth([])
        assert result["current_gbps"] == 0.0
        assert result["data_points"] == 0

    def test_project_traffic_growth_single(self):
        result = self.planner.project_traffic_growth([{"gbps": 10.0}])
        assert result["current_gbps"] == 10.0
        assert result["projected_gbps"] == 10.0

    def test_project_traffic_growth_linear(self):
        data = [{"gbps": float(i)} for i in range(1, 6)]  # 1,2,3,4,5 Gbps
        result = self.planner.project_traffic_growth(data, months=3)
        assert result["current_gbps"] == 5.0
        assert result["projected_gbps"] > 5.0  # trending upward

    def test_estimate_capacity_needs(self):
        needs = self.planner.estimate_capacity_needs(10.0, 10.0, months=3)
        assert len(needs) == 3
        assert needs[0]["month"] == 1
        assert needs[0]["estimated_gbps"] > 10.0
        assert needs[0]["headroom_recommended_gbps"] > needs[0]["estimated_gbps"]

    def test_generate_capacity_report(self):
        report = self.planner.generate_capacity_report(isp_id=1)
        assert report["isp_id"] == 1
        assert "projection_3m" in report
        assert "monthly_capacity_needs" in report
