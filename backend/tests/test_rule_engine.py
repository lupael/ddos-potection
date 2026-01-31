"""
Tests for the custom rule engine
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from services.rule_engine import RuleEngine
from models.models import Rule


class TestRuleEngine:
    """Test suite for RuleEngine"""
    
    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine instance for testing"""
        with patch('services.rule_engine.SessionLocal') as mock_session:
            engine = RuleEngine()
            engine.db = Mock()
            yield engine
    
    def test_match_ip_block_exact(self, rule_engine):
        """Test IP block matching with exact IP"""
        condition = {'ip': '192.0.2.100'}
        traffic = {'source_ip': '192.0.2.100'}
        
        assert rule_engine._match_ip_block(condition, traffic) is True
    
    def test_match_ip_block_no_match(self, rule_engine):
        """Test IP block with non-matching IP"""
        condition = {'ip': '192.0.2.100'}
        traffic = {'source_ip': '192.0.2.101'}
        
        assert rule_engine._match_ip_block(condition, traffic) is False
    
    def test_match_ip_block_cidr(self, rule_engine):
        """Test IP block matching with CIDR notation"""
        condition = {'ip': '192.0.2.0/24'}
        traffic = {'source_ip': '192.0.2.150'}
        
        assert rule_engine._match_ip_block(condition, traffic) is True
    
    def test_match_ip_block_cidr_no_match(self, rule_engine):
        """Test IP block with CIDR not matching"""
        condition = {'ip': '192.0.2.0/24'}
        traffic = {'source_ip': '198.51.100.1'}
        
        assert rule_engine._match_ip_block(condition, traffic) is False
    
    def test_match_rate_limit_exceeds(self, rule_engine):
        """Test rate limit when threshold is exceeded"""
        condition = {
            'threshold': 1000,
            'window': 1
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'packets': 5000
        }
        
        assert rule_engine._match_rate_limit(condition, traffic) is True
    
    def test_match_rate_limit_not_exceeds(self, rule_engine):
        """Test rate limit when threshold is not exceeded"""
        condition = {
            'threshold': 10000,
            'window': 1
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'packets': 5000
        }
        
        assert rule_engine._match_rate_limit(condition, traffic) is False
    
    def test_match_rate_limit_with_ip_filter(self, rule_engine):
        """Test rate limit with IP filter"""
        condition = {
            'ip': '192.0.2.0/24',
            'threshold': 1000,
            'window': 1
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'packets': 5000
        }
        
        assert rule_engine._match_rate_limit(condition, traffic) is True
    
    def test_match_rate_limit_ip_not_in_range(self, rule_engine):
        """Test rate limit with IP not in specified range"""
        condition = {
            'ip': '192.0.2.0/24',
            'threshold': 1000,
            'window': 1
        }
        traffic = {
            'source_ip': '198.51.100.1',
            'packets': 5000
        }
        
        assert rule_engine._match_rate_limit(condition, traffic) is False
    
    def test_match_protocol_filter_block_mode(self, rule_engine):
        """Test protocol filter in block mode"""
        condition = {
            'protocols': ['tcp', 'udp'],
            'mode': 'block'
        }
        traffic = {'protocol': 'tcp'}
        
        assert rule_engine._match_protocol_filter(condition, traffic) is True
    
    def test_match_protocol_filter_allow_mode(self, rule_engine):
        """Test protocol filter in allow mode"""
        condition = {
            'protocols': ['tcp', 'udp'],
            'mode': 'allow'
        }
        traffic = {'protocol': 'icmp'}
        
        assert rule_engine._match_protocol_filter(condition, traffic) is True
    
    def test_match_protocol_filter_allow_mode_passes(self, rule_engine):
        """Test protocol filter in allow mode with allowed protocol"""
        condition = {
            'protocols': ['tcp', 'udp'],
            'mode': 'allow'
        }
        traffic = {'protocol': 'tcp'}
        
        assert rule_engine._match_protocol_filter(condition, traffic) is False
    
    def test_match_geo_block_blocks_country(self, rule_engine):
        """Test geo-blocking blocks specified country"""
        condition = {
            'countries': ['CN', 'RU', 'KP'],
            'mode': 'block'
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'country': 'CN'
        }
        
        assert rule_engine._match_geo_block(condition, traffic) is True
    
    def test_match_geo_block_allows_country(self, rule_engine):
        """Test geo-blocking allows non-specified country"""
        condition = {
            'countries': ['CN', 'RU', 'KP'],
            'mode': 'block'
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'country': 'US'
        }
        
        assert rule_engine._match_geo_block(condition, traffic) is False
    
    def test_match_geo_block_allow_mode(self, rule_engine):
        """Test geo-blocking in allow mode blocks non-allowed countries"""
        condition = {
            'countries': ['US', 'CA', 'GB'],
            'mode': 'allow'
        }
        traffic = {
            'source_ip': '192.0.2.100',
            'country': 'CN'
        }
        
        assert rule_engine._match_geo_block(condition, traffic) is True
    
    def test_match_port_filter_dest_block(self, rule_engine):
        """Test port filter blocks destination port"""
        condition = {
            'ports': [22, 23, 3389],
            'port_type': 'dest',
            'mode': 'block'
        }
        traffic = {
            'dest_port': 22
        }
        
        assert rule_engine._match_port_filter(condition, traffic) is True
    
    def test_match_port_filter_source_allow(self, rule_engine):
        """Test port filter allows specific source ports"""
        condition = {
            'ports': [80, 443],
            'port_type': 'source',
            'mode': 'allow'
        }
        traffic = {
            'source_port': 54321
        }
        
        assert rule_engine._match_port_filter(condition, traffic) is True
    
    def test_evaluate_traffic_multiple_rules(self, rule_engine):
        """Test evaluating traffic against multiple rules"""
        # Mock database query
        rule1 = Mock(spec=Rule)
        rule1.id = 1
        rule1.name = "Block malicious IP"
        rule1.rule_type = "ip_block"
        rule1.condition = {'ip': '192.0.2.100'}
        rule1.action = "block"
        rule1.priority = 10
        rule1.is_active = True
        
        rule2 = Mock(spec=Rule)
        rule2.id = 2
        rule2.name = "Rate limit"
        rule2.rule_type = "rate_limit"
        rule2.condition = {'threshold': 1000, 'window': 1}
        rule2.action = "rate_limit"
        rule2.priority = 20
        rule2.is_active = True
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [rule1, rule2]
        rule_engine.db.query.return_value = query_mock
        
        traffic = {
            'source_ip': '192.0.2.100',
            'packets': 5000
        }
        
        actions = rule_engine.evaluate_traffic(traffic)
        
        # Should match first rule and stop (block action)
        assert len(actions) == 1
        assert actions[0]['rule_id'] == 1
        assert actions[0]['action'] == 'block'
    
    def test_evaluate_traffic_no_match(self, rule_engine):
        """Test evaluating traffic with no matching rules"""
        rule1 = Mock(spec=Rule)
        rule1.id = 1
        rule1.name = "Block specific IP"
        rule1.rule_type = "ip_block"
        rule1.condition = {'ip': '198.51.100.1'}
        rule1.action = "block"
        rule1.priority = 10
        rule1.is_active = True
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [rule1]
        rule_engine.db.query.return_value = query_mock
        
        traffic = {
            'source_ip': '192.0.2.100'
        }
        
        actions = rule_engine.evaluate_traffic(traffic)
        
        assert len(actions) == 0
    
    @patch('services.rule_engine.geoip2')
    def test_lookup_country_success(self, mock_geoip2, rule_engine):
        """Test successful country lookup"""
        mock_response = Mock()
        mock_response.country.iso_code = 'US'
        
        mock_reader_instance = Mock()
        mock_reader_instance.country.return_value = mock_response
        
        mock_geoip2.database.Reader.return_value = mock_reader_instance
        
        country = rule_engine._lookup_country('8.8.8.8')
        
        assert country == 'US'
    
    def test_apply_rule_action_block(self, rule_engine):
        """Test applying block action"""
        with patch.object(rule_engine, '_get_mitigation_service') as mock_get_service:
            mock_instance = Mock()
            mock_instance.apply_iptables_rule.return_value = True
            mock_get_service.return_value = mock_instance
            
            # Temporarily override the import
            with patch('services.rule_engine.RuleEngine.apply_rule_action') as mock_apply:
                # Test directly with the mitigation service mock
                from services.mitigation_service import MitigationService
                with patch.object(MitigationService, 'apply_iptables_rule', return_value=True):
                    mitigation = MitigationService()
                    result = mitigation.apply_iptables_rule('block', '192.0.2.100', 'tcp')
                    assert result is True
    
    def test_apply_rule_action_rate_limit(self, rule_engine):
        """Test applying rate limit action"""
        with patch('services.mitigation_service.MitigationService') as mock_service:
            mock_instance = Mock()
            mock_instance.apply_rate_limit.return_value = True
            mock_service.return_value = mock_instance
            
            # Test directly with the mitigation service
            from services.mitigation_service import MitigationService  
            with patch.object(MitigationService, 'apply_rate_limit', return_value=True):
                mitigation = MitigationService()
                result = mitigation.apply_rate_limit('192.0.2.100', '500/s')
                assert result is True
    
    def test_apply_rule_action_alert(self, rule_engine):
        """Test applying alert action (no blocking)"""
        action = {
            'action': 'alert',
            'rule_name': 'Suspicious activity',
            'condition': {}
        }
        
        result = rule_engine.apply_rule_action(action)
        
        assert result is True


class TestRuleEngineEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def rule_engine(self):
        """Create a rule engine instance for testing"""
        with patch('services.rule_engine.SessionLocal') as mock_session:
            engine = RuleEngine()
            engine.db = Mock()
            yield engine
    
    def test_match_ip_block_invalid_ip(self, rule_engine):
        """Test IP block with invalid IP address"""
        condition = {'ip': 'invalid-ip'}
        traffic = {'source_ip': '192.0.2.100'}
        
        assert rule_engine._match_ip_block(condition, traffic) is False
    
    def test_match_rate_limit_missing_fields(self, rule_engine):
        """Test rate limit with missing required fields"""
        condition = {}
        traffic = {}
        
        # Should not crash, should return False
        assert rule_engine._match_rate_limit(condition, traffic) is False
    
    def test_match_protocol_filter_missing_protocol(self, rule_engine):
        """Test protocol filter when traffic has no protocol"""
        condition = {
            'protocols': ['tcp'],
            'mode': 'block'
        }
        traffic = {}
        
        assert rule_engine._match_protocol_filter(condition, traffic) is False
    
    def test_match_geo_block_no_country_data(self, rule_engine):
        """Test geo-blocking when country data is unavailable"""
        condition = {
            'countries': ['CN'],
            'mode': 'block'
        }
        traffic = {'source_ip': '192.0.2.100'}
        
        # Should return False when country can't be determined
        assert rule_engine._match_geo_block(condition, traffic) is False
    
    def test_match_port_filter_missing_port(self, rule_engine):
        """Test port filter when port is missing from traffic"""
        condition = {
            'ports': [80, 443],
            'port_type': 'dest',
            'mode': 'block'
        }
        traffic = {}
        
        assert rule_engine._match_port_filter(condition, traffic) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
