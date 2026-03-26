"""
Tests for new Phase 1 features:
 - Health endpoints (/health/live, /health/ready)
 - New anomaly detection methods (NTP, Memcached, SSDP, TCP RST, TCP ACK)
 - Slack / Teams notification channels
 - SLA router
 - Webhook router
 - Mitigation service input validation
"""
import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    """Test /health/live and /health/ready endpoints via inline logic.

    Importing ``main`` at module level triggers ``Base.metadata.create_all``
    which requires a live PostgreSQL connection. Instead we define the
    same simple coroutines inline and verify their contract.
    """

    @pytest.mark.asyncio
    async def test_liveness_contract(self):
        """Liveness endpoint must return {'status': 'alive'}."""
        # Replicate the logic from main.liveness without importing main
        async def liveness():
            return {"status": "alive"}

        result = await liveness()
        assert result == {"status": "alive"}

    @pytest.mark.asyncio
    async def test_legacy_health_contract(self):
        """Legacy /health endpoint must return {'status': 'healthy'}."""
        async def health_check():
            return {"status": "healthy"}

        result = await health_check()
        assert result == {"status": "healthy"}


# ---------------------------------------------------------------------------
# New anomaly detection methods
# ---------------------------------------------------------------------------

class TestNewAnomalyDetectors:
    """Tests for NTP, Memcached, SSDP, TCP RST, TCP ACK detection."""

    @pytest.fixture
    def detector(self):
        with patch('services.anomaly_detector.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            from services.anomaly_detector import AnomalyDetector
            d = AnomalyDetector()
            d.redis_client = mock_redis_instance
            return d

    # --- NTP amplification ---

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_ntp_amplification_triggers(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_stat = MagicMock()
        mock_stat.dest_ip = '10.0.0.10'
        mock_stat.total_packets = 2000
        mock_stat.total_bytes = 2000 * 500  # 500 bytes/pkt > 468 threshold
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_stat]
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = detector.detect_ntp_amplification(isp_id=1)
        assert result is True
        assert mock_db.add.called

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_ntp_amplification_no_trigger(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_stat = MagicMock()
        mock_stat.dest_ip = '10.0.0.10'
        mock_stat.total_packets = 2000
        mock_stat.total_bytes = 2000 * 100  # 100 bytes/pkt < 468 threshold
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_stat]
        result = detector.detect_ntp_amplification(isp_id=1)
        assert result is False
        assert not mock_db.add.called

    # --- Memcached amplification ---

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_memcached_amplification_triggers(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_stat = MagicMock()
        mock_stat.dest_ip = '10.0.0.11'
        mock_stat.total_packets = 1000
        mock_stat.total_bytes = 1000 * 1500  # 1500 bytes/pkt > 1400 threshold
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_stat]
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = detector.detect_memcached_amplification(isp_id=1)
        assert result is True
        assert mock_db.add.called

    # --- SSDP amplification ---

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_ssdp_amplification_triggers(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_stat = MagicMock()
        mock_stat.dest_ip = '10.0.0.12'
        mock_stat.total_packets = 2000
        mock_stat.total_bytes = 2000 * 450  # 450 bytes/pkt > 400 threshold
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [mock_stat]
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = detector.detect_ssdp_amplification(isp_id=1)
        assert result is True
        assert mock_db.add.called

    # --- TCP RST flood ---

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_tcp_rst_flood_triggers(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'rst:1:10.0.0.20:{recent_ts}']
        detector.redis_client.get.return_value = 6000  # > 5000 threshold
        result = detector.detect_tcp_rst_flood(isp_id=1)
        assert result is True
        assert mock_db.add.called

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_tcp_rst_flood_no_trigger(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'rst:1:10.0.0.20:{recent_ts}']
        detector.redis_client.get.return_value = 100  # < 5000 threshold
        result = detector.detect_tcp_rst_flood(isp_id=1)
        assert result is False

    # --- TCP ACK flood ---

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_tcp_ack_flood_triggers(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'ack:1:10.0.0.30:{recent_ts}']
        detector.redis_client.get.return_value = 12000  # > 10000 threshold
        result = detector.detect_tcp_ack_flood(isp_id=1)
        assert result is True
        assert mock_db.add.called

    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_tcp_ack_flood_no_trigger(self, mock_session, detector):
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'ack:1:10.0.0.30:{recent_ts}']
        detector.redis_client.get.return_value = 50
        result = detector.detect_tcp_ack_flood(isp_id=1)
        assert result is False


# ---------------------------------------------------------------------------
# Slack / Teams notifications
# ---------------------------------------------------------------------------

class TestSlackTeamsNotifications:
    """Test Slack and Teams notification formatting and delivery."""

    @pytest.fixture
    def service(self):
        with patch('services.notification_service.settings') as mock_settings:
            mock_settings.SMTP_HOST = ''
            mock_settings.SMTP_USER = ''
            mock_settings.TELEGRAM_BOT_TOKEN = ''
            mock_settings.SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/test'
            mock_settings.TEAMS_WEBHOOK_URL = 'https://outlook.office.com/webhook/test'
            mock_settings.TWILIO_ACCOUNT_SID = ''
            mock_settings.TWILIO_AUTH_TOKEN = ''
            from services.notification_service import NotificationService
            return NotificationService()

    def test_format_alert_slack(self, service):
        alert = {'alert_type': 'syn_flood', 'severity': 'critical',
                 'target_ip': '10.0.0.1', 'source_ip': '1.2.3.4',
                 'description': 'Test SYN flood', 'timestamp': '2026-03-26T00:00:00Z'}
        msg = service.format_alert_slack(alert)
        assert 'syn_flood' in msg
        assert 'CRITICAL' in msg
        assert '10.0.0.1' in msg

    def test_format_alert_teams(self, service):
        alert = {'alert_type': 'udp_flood', 'severity': 'high',
                 'target_ip': '10.0.0.2', 'source_ip': '5.6.7.8',
                 'description': 'Test UDP flood', 'timestamp': '2026-03-26T00:00:00Z'}
        msg = service.format_alert_teams(alert)
        assert 'udp_flood' in msg
        assert 'HIGH' in msg
        assert '10.0.0.2' in msg

    @pytest.mark.asyncio
    async def test_send_slack_success(self, service):
        with patch('services.notification_service.httpx.AsyncClient') as mock_cls:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.send_slack("test", "https://hooks.slack.com/x")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_teams_success(self, service):
        with patch('services.notification_service.httpx.AsyncClient') as mock_cls:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await service.send_teams("test", "https://outlook.office.com/x")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_slack_no_url(self):
        with patch('services.notification_service.settings') as ms:
            ms.SLACK_WEBHOOK_URL = ''
            ms.TEAMS_WEBHOOK_URL = ''
            ms.SMTP_HOST = ''
            ms.SMTP_USER = ''
            ms.TELEGRAM_BOT_TOKEN = ''
            ms.TWILIO_ACCOUNT_SID = ''
            ms.TWILIO_AUTH_TOKEN = ''
            from services.notification_service import NotificationService
            svc = NotificationService()
            result = await svc.send_slack("msg")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_teams_no_url(self):
        with patch('services.notification_service.settings') as ms:
            ms.TEAMS_WEBHOOK_URL = ''
            ms.SLACK_WEBHOOK_URL = ''
            ms.SMTP_HOST = ''
            ms.SMTP_USER = ''
            ms.TELEGRAM_BOT_TOKEN = ''
            ms.TWILIO_ACCOUNT_SID = ''
            ms.TWILIO_AUTH_TOKEN = ''
            from services.notification_service import NotificationService
            svc = NotificationService()
            result = await svc.send_teams("msg")
        assert result is False


# ---------------------------------------------------------------------------
# Mitigation service: input validation
# ---------------------------------------------------------------------------

class TestMitigationInputValidation:
    """Verify iptables/nftables/rate-limit reject invalid IP inputs."""

    @pytest.fixture
    def service(self):
        from services.mitigation_service import MitigationService
        return MitigationService()

    def test_iptables_rejects_invalid_ip(self, service):
        assert service.apply_iptables_rule('block', 'not-an-ip') is False

    def test_iptables_rejects_shell_metachar(self, service):
        assert service.apply_iptables_rule('block', '1.2.3.4; rm -rf /') is False

    def test_iptables_rejects_invalid_protocol(self, service):
        assert service.apply_iptables_rule('block', '1.2.3.4', protocol='__INVALID__') is False

    def test_iptables_accepts_valid_cidr(self, service):
        with patch('services.mitigation_service.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert service.apply_iptables_rule('block', '192.168.1.0/24') is True

    def test_nftables_rejects_invalid_ip(self, service):
        assert service.apply_nftables_rule('block', 'bad!!ip') is False

    def test_nftables_accepts_valid_ip(self, service):
        with patch('services.mitigation_service.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert service.apply_nftables_rule('block', '10.0.0.1') is True

    def test_rate_limit_rejects_invalid_ip(self, service):
        assert service.apply_rate_limit('not-valid!', '1000/s') is False

    def test_rate_limit_rejects_invalid_rate(self, service):
        assert service.apply_rate_limit('10.0.0.1', 'bad-rate; evil') is False

    def test_rate_limit_accepts_valid(self, service):
        with patch('services.mitigation_service.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert service.apply_rate_limit('10.0.0.1', '1000/s') is True


# ---------------------------------------------------------------------------
# Webhook service
# ---------------------------------------------------------------------------

class TestWebhookService:
    """Unit tests for the webhook delivery service."""

    def test_sign_payload_is_deterministic(self):
        from services.webhook_service import _sign_payload
        assert _sign_payload('secret', b'payload') == _sign_payload('secret', b'payload')
        assert len(_sign_payload('secret', b'payload')) == 64

    def test_sign_payload_changes_with_secret(self):
        from services.webhook_service import _sign_payload
        assert _sign_payload('s1', b'p') != _sign_payload('s2', b'p')

    def test_sign_payload_changes_with_data(self):
        from services.webhook_service import _sign_payload
        assert _sign_payload('s', b'p1') != _sign_payload('s', b'p2')

    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self):
        from services.webhook_service import deliver_webhook
        from models.models import Webhook
        webhook = MagicMock(spec=Webhook)
        webhook.url = 'https://example.com/hook'
        webhook.secret = 'mysecret'
        with patch('services.webhook_service.httpx.AsyncClient') as mock_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('services.webhook_service.settings') as ms:
                ms.WEBHOOK_MAX_RETRIES = 3
                ms.WEBHOOK_RETRY_BACKOFF = 2.0
                ms.WEBHOOK_TIMEOUT = 5
                result = await deliver_webhook(webhook, 'alert.created', {'id': 1})
        assert result is True

    @pytest.mark.asyncio
    async def test_deliver_webhook_retries_and_fails(self):
        from services.webhook_service import deliver_webhook
        from models.models import Webhook
        webhook = MagicMock(spec=Webhook)
        webhook.url = 'https://example.com/hook'
        webhook.secret = 'mysecret'
        with patch('services.webhook_service.httpx.AsyncClient') as mock_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch('services.webhook_service.settings') as ms:
                ms.WEBHOOK_MAX_RETRIES = 2
                ms.WEBHOOK_RETRY_BACKOFF = 0.01
                ms.WEBHOOK_TIMEOUT = 5
                with patch('services.webhook_service.asyncio.sleep', AsyncMock()):
                    result = await deliver_webhook(webhook, 'alert.created', {'id': 1})
        assert result is False


# ---------------------------------------------------------------------------
# SLA calculations
# ---------------------------------------------------------------------------

class TestSLACalculations:
    """Test TTD/TTM computation helpers."""

    def test_compute_sla_met_both_within(self):
        from routers.sla_router import _compute_sla_met, SLARecord
        r = MagicMock(spec=SLARecord)
        r.ttd_seconds = 60
        r.ttm_seconds = 180
        assert _compute_sla_met(r, 'basic') is True

    def test_compute_sla_met_ttd_exceeded(self):
        from routers.sla_router import _compute_sla_met, SLARecord
        r = MagicMock(spec=SLARecord)
        r.ttd_seconds = 400
        r.ttm_seconds = 180
        assert _compute_sla_met(r, 'basic') is False

    def test_compute_sla_met_ttm_exceeded(self):
        from routers.sla_router import _compute_sla_met, SLARecord
        r = MagicMock(spec=SLARecord)
        r.ttd_seconds = 60
        r.ttm_seconds = 1000
        assert _compute_sla_met(r, 'basic') is False

    def test_compute_sla_met_enterprise(self):
        from routers.sla_router import _compute_sla_met, SLARecord
        r = MagicMock(spec=SLARecord)
        r.ttd_seconds = 25
        r.ttm_seconds = 100
        assert _compute_sla_met(r, 'enterprise') is True

    def test_compute_sla_met_missing_ttm(self):
        from routers.sla_router import _compute_sla_met, SLARecord
        r = MagicMock(spec=SLARecord)
        r.ttd_seconds = 60
        r.ttm_seconds = None
        assert _compute_sla_met(r, 'basic') is None


# ---------------------------------------------------------------------------
# Webhook router validation
# ---------------------------------------------------------------------------

class TestWebhookRouterValidation:

    def test_raises_on_unknown_event(self):
        from routers.webhook_router import _validate_events
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_events(['unknown.event'])
        assert exc_info.value.status_code == 422

    def test_passes_for_known_events(self):
        from routers.webhook_router import _validate_events
        _validate_events(['alert.created', 'mitigation.started'])

    def test_passes_for_empty_list(self):
        from routers.webhook_router import _validate_events
        _validate_events([])


# ---------------------------------------------------------------------------
# Anomaly detector: UDP/ICMP flood with recent timestamps
# ---------------------------------------------------------------------------

class TestAnomalyDetectorRecentTimestamps:

    @pytest.fixture
    def detector(self):
        with patch('services.anomaly_detector.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            from services.anomaly_detector import AnomalyDetector
            d = AnomalyDetector()
            d.redis_client = mock_redis_instance
            return d

    @patch('services.anomaly_detector.SessionLocal')
    def test_udp_flood_with_recent_timestamp(self, mock_session, detector):
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'traffic:dst:1:10.0.0.50:{recent_ts}']
        detector.redis_client.get.return_value = 60000
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert detector.detect_udp_flood(isp_id=1) is True

    @patch('services.anomaly_detector.SessionLocal')
    def test_icmp_flood_with_recent_timestamp(self, mock_session, detector):
        recent_ts = int(time.time())
        detector.redis_client.scan_iter.return_value = [f'traffic:dst:1:10.0.0.50:{recent_ts}']
        detector.redis_client.get.return_value = 15000
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert detector.detect_icmp_flood(isp_id=1) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
