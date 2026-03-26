"""
Phase 2 detection feature tests.

Covers:
- ThreatScorer.calculate_score
- GREDecapsulator.is_gre_packet
- AWSVPCFlowParser.parse_line
- GCPFlowParser.parse_record
- LSTMPredictor.prepare_features
- TLSFlowReceiver.create_ssl_context (mocked)
"""
import struct
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# ThreatScorer
# ---------------------------------------------------------------------------

class TestThreatScorer(unittest.TestCase):
    def _get_scorer(self):
        from services.threat_score import ThreatScorer
        return ThreatScorer()

    def test_zero_score_empty_alert(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({}), 0)

    def test_bad_actor_only(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({"bad_actor": True}), 40)

    def test_rpki_invalid_only(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({"rpki_invalid": True}), 20)

    def test_geo_blocked_only(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({"geo_blocked": True}), 20)

    def test_ml_confidence_below_threshold(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({"ml_confidence": 0.5}), 0)

    def test_ml_confidence_at_threshold(self):
        scorer = self._get_scorer()
        self.assertEqual(scorer.calculate_score({"ml_confidence": 0.7}), 20)

    def test_all_signals_capped_at_100(self):
        scorer = self._get_scorer()
        score = scorer.calculate_score({
            "bad_actor": True,
            "rpki_invalid": True,
            "geo_blocked": True,
            "ml_confidence": 0.9,
        })
        self.assertEqual(score, 100)

    def test_partial_combination(self):
        scorer = self._get_scorer()
        # bad_actor (40) + rpki_invalid (20) = 60
        score = scorer.calculate_score({"bad_actor": True, "rpki_invalid": True})
        self.assertEqual(score, 60)


class TestGetThreatScore(unittest.TestCase):
    def test_no_redis(self):
        from services.threat_score import get_threat_score
        score = get_threat_score({"bad_actor": True})
        self.assertEqual(score, 40)

    def test_redis_hit(self):
        from services.threat_score import get_threat_score
        redis_mock = MagicMock()
        redis_mock.sismember.return_value = True
        score = get_threat_score({"source_ip": "1.2.3.4"}, redis_client=redis_mock)
        self.assertEqual(score, 40)
        redis_mock.sismember.assert_called_once_with("threat_intel:bad_actors", "1.2.3.4")

    def test_redis_miss(self):
        from services.threat_score import get_threat_score
        redis_mock = MagicMock()
        redis_mock.sismember.return_value = False
        score = get_threat_score({"source_ip": "5.6.7.8"}, redis_client=redis_mock)
        self.assertEqual(score, 0)


# ---------------------------------------------------------------------------
# GREDecapsulator
# ---------------------------------------------------------------------------

def _build_ip_header(protocol: int = 47, ihl: int = 5) -> bytes:
    """Build a minimal IPv4 header with the given protocol field."""
    version_ihl = (4 << 4) | ihl
    total_length = ihl * 4 + 8
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,       # version + IHL
        0,                 # DSCP/ECN
        total_length,      # total length
        0,                 # identification
        0,                 # flags + fragment offset
        64,                # TTL
        protocol,          # protocol
        0,                 # checksum
        b"\xc0\x00\x02\x01",  # src 192.0.2.1
        b"\xc0\x00\x02\x02",  # dst 192.0.2.2
    )
    return header


class TestGREDecapsulator(unittest.TestCase):
    def _get_decap(self):
        from services.gre_decap import GREDecapsulator
        return GREDecapsulator()

    def test_is_gre_packet_true(self):
        decap = self._get_decap()
        pkt = _build_ip_header(protocol=47)
        self.assertTrue(decap.is_gre_packet(pkt))

    def test_is_gre_packet_false_tcp(self):
        decap = self._get_decap()
        pkt = _build_ip_header(protocol=6)
        self.assertFalse(decap.is_gre_packet(pkt))

    def test_is_gre_packet_too_short(self):
        decap = self._get_decap()
        self.assertFalse(decap.is_gre_packet(b"\x00" * 5))

    def test_parse_gre_header_standard(self):
        from services.gre_decap import GREDecapsulator
        decap = GREDecapsulator()
        # Standard GRE header: flags=0x0000, protocol=0x0800
        gre_bytes = struct.pack("!HH", 0x0000, 0x0800)
        result = decap.parse_gre_header(gre_bytes)
        self.assertEqual(result["protocol_type"], 0x0800)
        self.assertFalse(result["key_present"])
        self.assertFalse(result["checksum_present"])
        self.assertEqual(result["header_length"], 4)

    def test_decapsulate_ipv4_inner(self):
        from services.gre_decap import GREDecapsulator
        decap = GREDecapsulator()
        outer_ip = _build_ip_header(protocol=47)
        # GRE header: no flags, IPv4 inner
        gre_hdr = struct.pack("!HH", 0x0000, 0x0800)
        inner_ip = _build_ip_header(protocol=6)  # TCP inner
        pkt = outer_ip + gre_hdr + inner_ip
        result = decap.decapsulate(pkt)
        self.assertIsNotNone(result)
        self.assertEqual(result, inner_ip)

    def test_decapsulate_non_gre_returns_none(self):
        decap = self._get_decap()
        pkt = _build_ip_header(protocol=6)
        self.assertIsNone(decap.decapsulate(pkt))


# ---------------------------------------------------------------------------
# AWSVPCFlowParser
# ---------------------------------------------------------------------------

_SAMPLE_AWS_LINE = (
    "2 123456789012 eni-abc12345 10.0.1.5 10.0.2.10 443 54321 6 20 4000 "
    "1620000000 1620000060 ACCEPT OK"
)

class TestAWSVPCFlowParser(unittest.TestCase):
    def _get_parser(self):
        from services.cloud_flow_ingestion import AWSVPCFlowParser
        return AWSVPCFlowParser()

    def test_parse_valid_line(self):
        parser = self._get_parser()
        flow = parser.parse_line(_SAMPLE_AWS_LINE)
        self.assertIsNotNone(flow)
        self.assertEqual(flow["src_ip"], "10.0.1.5")
        self.assertEqual(flow["dst_ip"], "10.0.2.10")
        self.assertEqual(flow["src_port"], 443)
        self.assertEqual(flow["dst_port"], 54321)
        self.assertEqual(flow["protocol"], "TCP")
        self.assertEqual(flow["packets"], 20)
        self.assertEqual(flow["bytes"], 4000)
        self.assertEqual(flow["action"], "ACCEPT")

    def test_parse_header_line_returns_none(self):
        parser = self._get_parser()
        self.assertIsNone(parser.parse_line("version account-id interface-id"))

    def test_parse_empty_line_returns_none(self):
        parser = self._get_parser()
        self.assertIsNone(parser.parse_line(""))

    def test_parse_file(self):
        parser = self._get_parser()
        content = "version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status\n"
        content += _SAMPLE_AWS_LINE + "\n"
        content += _SAMPLE_AWS_LINE + "\n"
        flows = parser.parse_file(content)
        self.assertEqual(len(flows), 2)

    def test_parse_nodata_skipped(self):
        parser = self._get_parser()
        line = "2 123456789012 eni-abc12345 - - - - - - - 1620000000 1620000060 - NODATA"
        self.assertIsNone(parser.parse_line(line))


# ---------------------------------------------------------------------------
# GCPFlowParser
# ---------------------------------------------------------------------------

_SAMPLE_GCP_RECORD = {
    "connection": {
        "src_ip": "10.1.0.2",
        "dest_ip": "10.2.0.5",
        "src_port": 54000,
        "dest_port": 80,
        "protocol": 6,
    },
    "bytes_sent": 8192,
    "packets_sent": 10,
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T00:00:01Z",
    "src_instance": {"vm_name": "vm-a"},
    "dest_instance": {"vm_name": "vm-b"},
}

class TestGCPFlowParser(unittest.TestCase):
    def _get_parser(self):
        from services.cloud_flow_ingestion import GCPFlowParser
        return GCPFlowParser()

    def test_parse_valid_record(self):
        parser = self._get_parser()
        flow = parser.parse_record(_SAMPLE_GCP_RECORD)
        self.assertIsNotNone(flow)
        self.assertEqual(flow["src_ip"], "10.1.0.2")
        self.assertEqual(flow["dst_ip"], "10.2.0.5")
        self.assertEqual(flow["src_port"], 54000)
        self.assertEqual(flow["dst_port"], 80)
        self.assertEqual(flow["protocol"], "TCP")
        self.assertEqual(flow["packets"], 10)
        self.assertEqual(flow["bytes"], 8192)

    def test_parse_none_returns_none(self):
        parser = self._get_parser()
        self.assertIsNone(parser.parse_record(None))

    def test_parse_empty_dict_returns_result(self):
        parser = self._get_parser()
        # Empty dict should produce a result with None fields (graceful)
        flow = parser.parse_record({})
        self.assertIsNotNone(flow)


# ---------------------------------------------------------------------------
# LSTMPredictor
# ---------------------------------------------------------------------------

class TestLSTMPredictor(unittest.TestCase):
    def _get_predictor(self):
        from services.lstm_predictor import LSTMPredictor
        return LSTMPredictor(sequence_length=10)

    def test_prepare_features_extracts_correct_keys(self):
        predictor = self._get_predictor()
        data = [
            {"pps": 100.0, "bps": 5000.0, "syn_ratio": 0.1, "udp_ratio": 0.3, "icmp_ratio": 0.05},
            {"pps": 200.0, "bps": 10000.0, "syn_ratio": 0.2, "udp_ratio": 0.4, "icmp_ratio": 0.1},
        ]
        features = predictor.prepare_features(data)
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0], [100.0, 5000.0, 0.1, 0.3, 0.05])
        self.assertEqual(features[1], [200.0, 10000.0, 0.2, 0.4, 0.1])

    def test_prepare_features_missing_keys_default_zero(self):
        predictor = self._get_predictor()
        features = predictor.prepare_features([{}])
        self.assertEqual(features, [[0.0, 0.0, 0.0, 0.0, 0.0]])

    def test_predict_untrained_returns_zero(self):
        predictor = self._get_predictor()
        result = predictor.predict([{"pps": 100}])
        self.assertEqual(result["attack_probability"], 0.0)
        self.assertEqual(result["confidence"], 0.0)

    def test_predict_empty_data_returns_zero(self):
        predictor = self._get_predictor()
        result = predictor.predict([])
        self.assertEqual(result["attack_probability"], 0.0)


# ---------------------------------------------------------------------------
# TLSFlowReceiver.create_ssl_context
# ---------------------------------------------------------------------------

class TestTLSFlowReceiver(unittest.TestCase):
    def test_create_ssl_context_calls_load_cert_chain(self):
        """create_ssl_context should load certfile/keyfile onto the SSLContext."""
        import ssl
        from services.tls_flow_receiver import TLSFlowReceiver

        mock_ctx = MagicMock(spec=ssl.SSLContext)
        with patch("ssl.SSLContext", return_value=mock_ctx) as mock_cls:
            ctx = TLSFlowReceiver.create_ssl_context(
                certfile="/fake/cert.pem",
                keyfile="/fake/key.pem",
            )
            mock_ctx.load_cert_chain.assert_called_once_with(
                certfile="/fake/cert.pem", keyfile="/fake/key.pem"
            )
            # No CA provided → verify_mode should NOT be set to CERT_REQUIRED
            self.assertNotIn(
                ssl.CERT_REQUIRED,
                [call.args for call in mock_ctx.mock_calls],
            )

    def test_create_ssl_context_with_cafile(self):
        """When cafile is provided, mutual TLS should be configured."""
        import ssl
        from services.tls_flow_receiver import TLSFlowReceiver

        mock_ctx = MagicMock(spec=ssl.SSLContext)
        with patch("ssl.SSLContext", return_value=mock_ctx):
            TLSFlowReceiver.create_ssl_context(
                certfile="/fake/cert.pem",
                keyfile="/fake/key.pem",
                cafile="/fake/ca.pem",
            )
            mock_ctx.load_verify_locations.assert_called_once_with(cafile="/fake/ca.pem")
            self.assertEqual(mock_ctx.verify_mode, ssl.CERT_REQUIRED)


if __name__ == "__main__":
    unittest.main()
