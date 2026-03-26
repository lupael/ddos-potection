"""
Phase 3 mitigation feature tests.

Covers:
- NokiaSROSDriver instantiation and validation
- ScrubbingCentre.divert_traffic with valid/invalid prefix
- ScrubbingCentreManager.select_centre with multiple centres
- CooldownManager with mock Redis
- MitigationSelector.select_action for various attack types
- AutoEscalationManager.get_next_action (mock Redis)
- SLAComplianceChecker.check_ttd for standard/pro/enterprise tiers
- SLAComplianceChecker.calculate_breach_credit
- SLAComplianceChecker.generate_monthly_report
"""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# NokiaSROSDriver
# ---------------------------------------------------------------------------

class TestNokiaSROSDriver(unittest.TestCase):
    def _get_driver_class(self):
        from services.router_drivers import NokiaSROSDriver
        return NokiaSROSDriver

    def test_instantiation_valid_ip(self):
        NokiaSROSDriver = self._get_driver_class()
        drv = NokiaSROSDriver(host="192.0.2.1", port=22, username="admin", password="secret")
        self.assertEqual(drv._host, "192.0.2.1")
        self.assertEqual(drv._port, 22)
        self.assertEqual(drv._username, "admin")

    def test_instantiation_invalid_ip_raises(self):
        NokiaSROSDriver = self._get_driver_class()
        with self.assertRaises(ValueError):
            NokiaSROSDriver(host="not-an-ip", port=22, username="admin", password="x")

    def test_get_status_not_connected(self):
        NokiaSROSDriver = self._get_driver_class()
        drv = NokiaSROSDriver(host="10.0.0.1", port=22, username="u", password="p")
        status = drv.get_status()
        self.assertFalse(status["connected"])
        self.assertEqual(status["host"], "10.0.0.1")

    def test_push_acl_invalid_prefix_returns_false(self):
        NokiaSROSDriver = self._get_driver_class()
        drv = NokiaSROSDriver(host="10.0.0.1", port=22, username="u", password="p")
        result = drv.push_acl("not-a-prefix")
        self.assertFalse(result)

    def test_push_acl_invalid_action_returns_false(self):
        NokiaSROSDriver = self._get_driver_class()
        drv = NokiaSROSDriver(host="10.0.0.1", port=22, username="u", password="p")
        result = drv.push_acl("192.0.2.0/24", action="INVALID")
        self.assertFalse(result)

    def test_withdraw_acl_invalid_prefix_returns_false(self):
        NokiaSROSDriver = self._get_driver_class()
        drv = NokiaSROSDriver(host="10.0.0.1", port=22, username="u", password="p")
        result = drv.withdraw_acl("bad-prefix!!")
        self.assertFalse(result)

    def test_connect_without_netmiko_returns_false(self):
        """When netmiko is not available connect() should return False gracefully."""
        import services.router_drivers as rd
        original = rd._NETMIKO_AVAILABLE
        rd._NETMIKO_AVAILABLE = False
        try:
            from services.router_drivers import NokiaSROSDriver
            drv = NokiaSROSDriver(host="10.0.0.1", port=22, username="u", password="p")
            self.assertFalse(drv.connect())
        finally:
            rd._NETMIKO_AVAILABLE = original


# ---------------------------------------------------------------------------
# ScrubbingCentre
# ---------------------------------------------------------------------------

class TestScrubbingCentre(unittest.TestCase):
    def _make_centre(self):
        from services.scrubbing_centre import ScrubbingCentre
        return ScrubbingCentre(
            centre_id="sc1",
            name="Test Centre",
            bgp_nexthop="10.0.0.1",
            gre_endpoint="10.0.0.2",
            capacity_gbps=100,
        )

    def test_init_invalid_bgp_nexthop(self):
        from services.scrubbing_centre import ScrubbingCentre
        with self.assertRaises(ValueError):
            ScrubbingCentre("sc1", "Test", "not-an-ip", "10.0.0.2")

    def test_init_invalid_gre_endpoint(self):
        from services.scrubbing_centre import ScrubbingCentre
        with self.assertRaises(ValueError):
            ScrubbingCentre("sc1", "Test", "10.0.0.1", "bad-gre")

    def test_divert_traffic_valid_prefix(self):
        centre = self._make_centre()
        result = centre.divert_traffic("203.0.113.5")
        self.assertEqual(result["action"], "divert")
        self.assertEqual(result["bgp_nexthop"], "10.0.0.1")
        self.assertIn("203.0.113.5", result["host_route"])
        self.assertEqual(result["status"], "announced")

    def test_divert_traffic_valid_cidr(self):
        centre = self._make_centre()
        result = centre.divert_traffic("192.0.2.0/24")
        self.assertEqual(result["action"], "divert")
        self.assertIn("/32", result["host_route"])

    def test_divert_traffic_invalid_prefix_raises(self):
        centre = self._make_centre()
        with self.assertRaises(ValueError):
            centre.divert_traffic("not-a-prefix")

    def test_return_traffic_valid_prefix(self):
        centre = self._make_centre()
        centre.divert_traffic("203.0.113.5")
        result = centre.return_traffic("203.0.113.5")
        self.assertEqual(result["action"], "return")
        self.assertEqual(result["status"], "withdrawn")

    def test_return_traffic_invalid_prefix_raises(self):
        centre = self._make_centre()
        with self.assertRaises(ValueError):
            centre.return_traffic("bad!!")

    def test_get_utilization_stub(self):
        centre = self._make_centre()
        util = centre.get_utilization()
        self.assertIsInstance(util, float)
        self.assertGreaterEqual(util, 0.0)
        self.assertLessEqual(util, 1.0)


# ---------------------------------------------------------------------------
# ScrubbingCentreManager
# ---------------------------------------------------------------------------

class TestScrubbingCentreManager(unittest.TestCase):
    def _make_manager(self):
        from services.scrubbing_centre import ScrubbingCentre, ScrubbingCentreManager

        c1 = ScrubbingCentre("sc1", "Centre 1", "10.1.0.1", "10.1.0.2", capacity_gbps=100)
        c2 = ScrubbingCentre("sc2", "Centre 2", "10.2.0.1", "10.2.0.2", capacity_gbps=200)
        # Patch utilization so we get deterministic selection
        c1.get_utilization = lambda: 0.8
        c2.get_utilization = lambda: 0.3
        return ScrubbingCentreManager([c1, c2])

    def test_select_centre_picks_lowest_utilization(self):
        mgr = self._make_manager()
        selected = mgr.select_centre("203.0.113.0/24")
        self.assertIsNotNone(selected)
        self.assertEqual(selected.centre_id, "sc2")

    def test_select_centre_empty_returns_none(self):
        from services.scrubbing_centre import ScrubbingCentreManager
        mgr = ScrubbingCentreManager([])
        self.assertIsNone(mgr.select_centre("1.2.3.4"))

    def test_divert_returns_action(self):
        mgr = self._make_manager()
        result = mgr.divert("203.0.113.5")
        self.assertEqual(result["action"], "divert")
        self.assertEqual(result["centre_id"], "sc2")

    def test_divert_no_centres_returns_error(self):
        from services.scrubbing_centre import ScrubbingCentreManager
        mgr = ScrubbingCentreManager([])
        result = mgr.divert("1.2.3.4")
        self.assertIn("error", result)

    def test_return_all(self):
        mgr = self._make_manager()
        mgr.divert("203.0.113.5")
        results = mgr.return_all("203.0.113.5")
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r["action"], "return")


# ---------------------------------------------------------------------------
# CooldownManager
# ---------------------------------------------------------------------------

class TestCooldownManager(unittest.TestCase):
    def _get_class(self):
        from services.mitigation_service import CooldownManager
        return CooldownManager

    def test_no_cooldown_by_default(self):
        CooldownManager = self._get_class()
        mgr = CooldownManager()
        self.assertFalse(mgr.is_in_cooldown("mit-001"))

    def test_start_and_check_cooldown(self):
        CooldownManager = self._get_class()
        mgr = CooldownManager(default_cooldown_secs=300)
        mgr.start_cooldown("mit-001")
        self.assertTrue(mgr.is_in_cooldown("mit-001"))

    def test_cancel_cooldown(self):
        CooldownManager = self._get_class()
        mgr = CooldownManager()
        mgr.start_cooldown("mit-001", duration_secs=300)
        self.assertTrue(mgr.is_in_cooldown("mit-001"))
        mgr.cancel_cooldown("mit-001")
        self.assertFalse(mgr.is_in_cooldown("mit-001"))

    def test_get_remaining_secs(self):
        CooldownManager = self._get_class()
        mgr = CooldownManager(default_cooldown_secs=300)
        mgr.start_cooldown("mit-001", duration_secs=300)
        remaining = mgr.get_remaining_secs("mit-001")
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 300)

    def test_get_remaining_secs_no_cooldown_returns_zero(self):
        CooldownManager = self._get_class()
        mgr = CooldownManager()
        self.assertEqual(mgr.get_remaining_secs("nonexistent"), 0)

    def test_with_mock_redis(self):
        CooldownManager = self._get_class()
        mock_redis = MagicMock()
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = b"9999999999.0"  # far future timestamp
        mock_redis.ttl.return_value = 250
        mock_redis.delete.return_value = 1

        mgr = CooldownManager(redis_client=mock_redis, default_cooldown_secs=300)
        self.assertTrue(mgr.start_cooldown("m1"))
        mock_redis.setex.assert_called_once()

        self.assertTrue(mgr.is_in_cooldown("m1"))
        mock_redis.get.assert_called_once()

        remaining = mgr.get_remaining_secs("m1")
        self.assertEqual(remaining, 250)

        mgr.cancel_cooldown("m1")
        mock_redis.delete.assert_called_once()

    def test_expired_cooldown_returns_false(self):
        import time
        CooldownManager = self._get_class()
        mgr = CooldownManager(default_cooldown_secs=300)
        # Manually insert an already-expired end time
        key = mgr._key("mit-expired")
        mgr._local[key] = time.time() - 1  # past
        self.assertFalse(mgr.is_in_cooldown("mit-expired"))
        self.assertEqual(mgr.get_remaining_secs("mit-expired"), 0)


# ---------------------------------------------------------------------------
# MitigationSelector
# ---------------------------------------------------------------------------

class TestMitigationSelector(unittest.TestCase):
    def _get_selector(self):
        from services.mitigation_selector import MitigationSelector
        return MitigationSelector()

    def test_syn_flood_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("syn_flood", 0), "rate_limit_syn")

    def test_syn_flood_level_1(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("syn_flood", 1), "iptables_block")

    def test_syn_flood_level_3(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("syn_flood", 3), "bgp_blackhole")

    def test_udp_flood_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("udp_flood", 0), "rate_limit_udp")

    def test_dns_amplification_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("dns_amplification", 0), "block_udp_53")

    def test_ntp_amplification_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("ntp_amplification", 0), "block_udp_123")

    def test_memcached_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("memcached", 0), "block_udp_11211")

    def test_http_flood_level_0(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("http_flood", 0), "rate_limit_http")

    def test_unknown_attack_type_falls_back_to_default(self):
        s = self._get_selector()
        chain = s.get_escalation_chain("mystery_attack")
        from services.mitigation_selector import MitigationSelector
        self.assertEqual(chain, MitigationSelector.ATTACK_TYPE_MATRIX["default"])

    def test_escalation_level_clamped_to_last(self):
        s = self._get_selector()
        # Escalation level 99 should return the last action in the chain
        last = s.select_action("syn_flood", 99)
        self.assertEqual(last, "bgp_blackhole")

    def test_get_escalation_chain_returns_full_list(self):
        s = self._get_selector()
        chain = s.get_escalation_chain("udp_flood")
        self.assertIn("rate_limit_udp", chain)
        self.assertIn("bgp_blackhole", chain)

    def test_case_insensitive_lookup(self):
        s = self._get_selector()
        self.assertEqual(s.select_action("SYN_FLOOD", 0), "rate_limit_syn")


# ---------------------------------------------------------------------------
# AutoEscalationManager
# ---------------------------------------------------------------------------

class TestAutoEscalationManager(unittest.TestCase):
    def _get_class(self):
        from services.mitigation_selector import AutoEscalationManager
        return AutoEscalationManager

    def test_get_next_action_no_attempts(self):
        AutoEscalationManager = self._get_class()
        mgr = AutoEscalationManager(escalation_timeout_mins=5)
        action = mgr.get_next_action("inc-1", "syn_flood")
        self.assertEqual(action, "rate_limit_syn")

    def test_get_next_action_after_one_attempt(self):
        AutoEscalationManager = self._get_class()
        mgr = AutoEscalationManager(escalation_timeout_mins=5)
        mgr.record_mitigation_attempt("inc-1", "rate_limit_syn")
        action = mgr.get_next_action("inc-1", "syn_flood")
        self.assertEqual(action, "iptables_block")

    def test_get_next_action_exhausted_returns_none(self):
        AutoEscalationManager = self._get_class()
        mgr = AutoEscalationManager(escalation_timeout_mins=5)
        for action in ["rate_limit_syn", "iptables_block", "flowspec_block", "bgp_blackhole"]:
            mgr.record_mitigation_attempt("inc-2", action)
        self.assertIsNone(mgr.get_next_action("inc-2", "syn_flood"))

    def test_should_not_escalate_immediately(self):
        AutoEscalationManager = self._get_class()
        mgr = AutoEscalationManager(escalation_timeout_mins=5)
        mgr.record_mitigation_attempt("inc-3", "rate_limit_syn")
        self.assertFalse(mgr.should_escalate("inc-3"))

    def test_should_escalate_after_timeout(self):
        import time
        AutoEscalationManager = self._get_class()
        mgr = AutoEscalationManager(escalation_timeout_mins=5)
        # Manually backdate the first-attempt timestamp
        ts_key = mgr._ts_key("inc-4")
        mgr._local_ts[ts_key] = time.time() - 400  # 400 s ago > 300 s timeout
        attempt_key = mgr._attempt_key("inc-4")
        mgr._local_attempts[attempt_key] = ["rate_limit_syn"]
        self.assertTrue(mgr.should_escalate("inc-4"))

    def test_with_mock_redis(self):
        AutoEscalationManager = self._get_class()
        mock_redis = MagicMock()
        mock_redis.pipeline.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_redis.pipeline.return_value.__exit__ = MagicMock(return_value=False)
        mock_redis.pipeline.return_value.execute = MagicMock()
        mock_redis.get.return_value = None  # no timestamp stored yet
        mock_redis.lrange.return_value = []

        mgr = AutoEscalationManager(redis_client=mock_redis, escalation_timeout_mins=5)
        action = mgr.get_next_action("inc-5", "udp_flood")
        self.assertEqual(action, "rate_limit_udp")


# ---------------------------------------------------------------------------
# SLAComplianceChecker
# ---------------------------------------------------------------------------

class TestSLAComplianceChecker(unittest.TestCase):
    def _get_checker(self):
        from services.sla_service import SLAComplianceChecker
        return SLAComplianceChecker()

    # check_ttd
    def test_ttd_standard_compliant(self):
        checker = self._get_checker()
        result = checker.check_ttd("standard", 200)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["target_secs"], 300)
        self.assertLess(result["breach_margin_secs"], 0)

    def test_ttd_standard_breach(self):
        checker = self._get_checker()
        result = checker.check_ttd("standard", 400)
        self.assertFalse(result["compliant"])
        self.assertGreater(result["breach_margin_secs"], 0)

    def test_ttd_pro_compliant(self):
        checker = self._get_checker()
        result = checker.check_ttd("pro", 100)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["target_secs"], 120)

    def test_ttd_pro_breach(self):
        checker = self._get_checker()
        result = checker.check_ttd("pro", 200)
        self.assertFalse(result["compliant"])

    def test_ttd_enterprise_compliant(self):
        checker = self._get_checker()
        result = checker.check_ttd("enterprise", 25)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["target_secs"], 30)

    def test_ttd_enterprise_breach(self):
        checker = self._get_checker()
        result = checker.check_ttd("enterprise", 35)
        self.assertFalse(result["compliant"])

    def test_ttd_unknown_tier_raises(self):
        checker = self._get_checker()
        with self.assertRaises(ValueError):
            checker.check_ttd("platinum", 100)

    # check_ttm
    def test_ttm_standard_compliant(self):
        checker = self._get_checker()
        result = checker.check_ttm("standard", 800)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["target_secs"], 900)

    def test_ttm_standard_breach(self):
        checker = self._get_checker()
        result = checker.check_ttm("standard", 1000)
        self.assertFalse(result["compliant"])

    def test_ttm_enterprise_compliant(self):
        checker = self._get_checker()
        result = checker.check_ttm("enterprise", 119)
        self.assertTrue(result["compliant"])

    # calculate_breach_credit
    def test_zero_breaches_zero_credit(self):
        checker = self._get_checker()
        self.assertEqual(checker.calculate_breach_credit("standard", "ttd", 0), 0.0)

    def test_one_breach_five_percent(self):
        checker = self._get_checker()
        self.assertEqual(checker.calculate_breach_credit("standard", "ttd", 1), 5.0)

    def test_six_breaches_capped_at_30(self):
        checker = self._get_checker()
        self.assertEqual(checker.calculate_breach_credit("enterprise", "ttm", 6), 30.0)

    def test_ten_breaches_still_capped(self):
        checker = self._get_checker()
        self.assertLessEqual(checker.calculate_breach_credit("pro", "ttd", 10), 30.0)

    # generate_monthly_report
    def test_empty_records(self):
        checker = self._get_checker()
        report = checker.generate_monthly_report([], "standard")
        self.assertEqual(report["total_incidents"], 0)
        self.assertEqual(report["ttd_compliance_pct"], 100.0)
        self.assertEqual(report["ttd_breach_count"], 0)
        self.assertEqual(report["overall_credit_pct"], 0.0)

    def test_all_compliant(self):
        checker = self._get_checker()
        records = [
            {"ttd_seconds": 100, "ttm_seconds": 500},
            {"ttd_seconds": 200, "ttm_seconds": 600},
        ]
        report = checker.generate_monthly_report(records, "standard")
        self.assertEqual(report["ttd_breach_count"], 0)
        self.assertEqual(report["ttm_breach_count"], 0)
        self.assertEqual(report["ttd_compliance_pct"], 100.0)
        self.assertEqual(report["overall_credit_pct"], 0.0)

    def test_mixed_compliance(self):
        checker = self._get_checker()
        records = [
            {"ttd_seconds": 100, "ttm_seconds": 500},
            {"ttd_seconds": 400, "ttm_seconds": 1000},  # both breach standard
        ]
        report = checker.generate_monthly_report(records, "standard")
        self.assertEqual(report["ttd_breach_count"], 1)
        self.assertEqual(report["ttm_breach_count"], 1)
        self.assertEqual(report["ttd_compliance_pct"], 50.0)
        self.assertGreater(report["overall_credit_pct"], 0.0)

    def test_enterprise_tier(self):
        checker = self._get_checker()
        records = [
            {"ttd_seconds": 25, "ttm_seconds": 100},
            {"ttd_seconds": 40, "ttm_seconds": 130},  # both breach enterprise
        ]
        report = checker.generate_monthly_report(records, "enterprise")
        self.assertEqual(report["tier"], "enterprise")
        self.assertEqual(report["ttd_breach_count"], 1)
        self.assertEqual(report["ttm_breach_count"], 1)


if __name__ == "__main__":
    unittest.main()
