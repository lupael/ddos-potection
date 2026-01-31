"""
Unit tests for anomaly detector service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from services.anomaly_detector import AnomalyDetector


class TestAnomalyDetector:
    """Test cases for AnomalyDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector instance with mocked Redis"""
        with patch('services.anomaly_detector.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            detector = AnomalyDetector()
            detector.redis_client = mock_redis_instance
            return detector
    
    def test_calculate_entropy_uniform(self, detector):
        """Test entropy calculation with uniform distribution"""
        # Uniform distribution should have high entropy
        data = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        entropy = detector.calculate_entropy(data)
        
        # Entropy of uniform distribution of 8 elements = log2(8) = 3.0
        assert entropy == pytest.approx(3.0, rel=0.01)
    
    def test_calculate_entropy_concentrated(self, detector):
        """Test entropy calculation with concentrated distribution"""
        # Concentrated distribution should have low entropy
        data = ['a'] * 100 + ['b'] * 5
        entropy = detector.calculate_entropy(data)
        
        # Low entropy for concentrated data
        assert entropy < 1.0
    
    def test_calculate_entropy_empty(self, detector):
        """Test entropy calculation with empty data"""
        data = []
        entropy = detector.calculate_entropy(data)
        assert entropy == 0.0
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_syn_flood_threshold_exceeded(self, mock_session, detector):
        """Test SYN flood detection when threshold is exceeded"""
        # Mock Redis to return high SYN count
        detector.redis_client.scan_iter.return_value = [
            'syn:1:10.0.0.50:1234567890'
        ]
        detector.redis_client.get.return_value = 15000  # Above threshold
        
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        result = detector.detect_syn_flood(isp_id=1)
        
        assert result is True
        # Alert should be created
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_syn_flood_below_threshold(self, mock_session, detector):
        """Test SYN flood detection when below threshold"""
        # Mock Redis to return low SYN count
        detector.redis_client.scan_iter.return_value = [
            'syn:1:10.0.0.50:1234567890'
        ]
        detector.redis_client.get.return_value = 100  # Below threshold
        
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        result = detector.detect_syn_flood(isp_id=1)
        
        assert result is False
        # No alert should be created
        assert not mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_udp_flood(self, mock_session, detector):
        """Test UDP flood detection"""
        # Mock Redis to return high UDP count for a destination
        detector.redis_client.scan_iter.return_value = [
            'traffic:dst:1:10.0.0.50:1234567890'
        ]
        detector.redis_client.get.side_effect = lambda key: 60000 if '10.0.0.50' in key else 0
        
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        result = detector.detect_udp_flood(isp_id=1)
        
        assert result is True
        assert mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_icmp_flood(self, mock_session, detector):
        """Test ICMP flood detection"""
        # Mock Redis to return high ICMP count
        detector.redis_client.scan_iter.return_value = [
            'traffic:dst:1:10.0.0.50:1234567890'
        ]
        detector.redis_client.get.side_effect = lambda key: 15000 if '10.0.0.50' in key else 0
        
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        result = detector.detect_icmp_flood(isp_id=1)
        
        assert result is True
        assert mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_entropy_anomaly_distributed_ddos(self, mock_session, detector):
        """Test entropy-based detection of distributed DDoS"""
        # Create mock traffic logs with low entropy (concentrated attack)
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Simulate concentrated attack from few sources to single target
        mock_logs = []
        for i in range(100):
            mock_log = MagicMock()
            mock_log.source_ip = f'192.168.1.{i % 3}'  # Only 3 sources
            mock_log.dest_ip = '10.0.0.50'  # Single target
            mock_log.protocol = 'TCP'
            mock_logs.append(mock_log)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.limit.return_value.all.return_value = mock_logs
        
        result = detector.detect_entropy_anomaly(isp_id=1)
        
        # Should detect distributed DDoS due to low source and destination entropy
        assert result is True
        assert mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_entropy_anomaly_volumetric(self, mock_session, detector):
        """Test entropy-based detection of volumetric attack"""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Simulate volumetric attack from many sources to few targets
        mock_logs = []
        for i in range(1000):
            mock_log = MagicMock()
            mock_log.source_ip = f'192.168.{i // 256}.{i % 256}'  # Many sources
            mock_log.dest_ip = f'10.0.0.{i % 2}'  # Only 2 targets
            mock_log.protocol = 'UDP'
            mock_logs.append(mock_log)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.limit.return_value.all.return_value = mock_logs
        
        result = detector.detect_entropy_anomaly(isp_id=1)
        
        # Should detect volumetric attack due to high source entropy, low dest entropy
        assert result is True
        assert mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_detect_dns_amplification(self, mock_session, detector):
        """Test DNS amplification attack detection"""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Create mock query result with high bytes-per-packet ratio
        mock_stat = MagicMock()
        mock_stat.dest_ip = '10.0.0.50'
        mock_stat.total_packets = 2000
        mock_stat.total_bytes = 1200000  # 600 bytes per packet (typical DNS amplification)
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.group_by.return_value.all.return_value = [mock_stat]
        
        result = detector.detect_dns_amplification(isp_id=1)
        
        assert result is True
        assert mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_create_alert_no_duplicate(self, mock_session, detector):
        """Test that duplicate alerts are not created"""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Simulate existing alert
        mock_existing_alert = MagicMock()
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = mock_existing_alert
        
        detector.create_alert(
            isp_id=1,
            alert_type='syn_flood',
            severity='high',
            target_ip='10.0.0.50',
            description='Test alert'
        )
        
        # Should not create new alert
        assert not mock_db.add.called
    
    @patch('services.anomaly_detector.SessionLocal')
    def test_create_alert_new(self, mock_session, detector):
        """Test creating a new alert"""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # No existing alert
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = None
        
        # Mock the alert object
        mock_alert = MagicMock()
        mock_alert.id = 123
        mock_db.add = MagicMock()
        
        detector.create_alert(
            isp_id=1,
            alert_type='udp_flood',
            severity='critical',
            target_ip='10.0.0.50',
            description='Test UDP flood',
            source_ip='192.168.1.100'
        )
        
        # Should create new alert
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Should publish to Redis
        assert detector.redis_client.setex.called
        assert detector.redis_client.publish.called
        assert detector.redis_client.xadd.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
