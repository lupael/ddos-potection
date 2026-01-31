"""
Tests for mitigation service enhancements
"""
import pytest
import subprocess
from unittest.mock import Mock, patch, mock_open, MagicMock
import os

from services.mitigation_service import MitigationService, validate_prefix


class TestValidatePrefix:
    """Test prefix validation"""
    
    def test_validate_ipv4_prefix(self):
        """Test valid IPv4 CIDR prefix"""
        assert validate_prefix("192.0.2.0/24") is True
        assert validate_prefix("192.0.2.1/32") is True
    
    def test_validate_ipv6_prefix(self):
        """Test valid IPv6 CIDR prefix"""
        assert validate_prefix("2001:db8::/32") is True
        assert validate_prefix("2001:db8::1/128") is True
    
    def test_validate_invalid_prefix(self):
        """Test invalid prefix format"""
        assert validate_prefix("invalid") is False
        assert validate_prefix("256.256.256.256/24") is False
        assert validate_prefix("") is False


class TestMitigationServiceFlowSpec:
    """Test FlowSpec functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a mitigation service instance"""
        return MitigationService()
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_send_flowspec_exabgp_basic(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test sending basic FlowSpec rule via ExaBGP"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp",
            action="drop"
        )
        
        assert result is True
        mock_open.assert_called_once()
        mock_write.assert_called_once()
        mock_close.assert_called_once()
    
    @patch('services.mitigation_service.settings')
    def test_send_flowspec_bgp_disabled(self, mock_settings, service):
        """Test FlowSpec when BGP is disabled"""
        mock_settings.BGP_ENABLED = False
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp"
        )
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    def test_send_flowspec_invalid_prefix(self, mock_settings, service):
        """Test FlowSpec with invalid destination prefix"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        
        result = service.send_flowspec_rule(
            dest="invalid-prefix",
            protocol="tcp"
        )
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_send_flowspec_with_ports(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test FlowSpec with port specifications"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp",
            dest_port=80,
            source_port=54321,
            action="drop"
        )
        
        assert result is True
        # Verify the command includes port specifications
        call_args = mock_write.call_args[0]
        command = call_args[1].decode()
        assert 'destination-port' in command
        assert 'source-port' in command
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_send_flowspec_with_tcp_flags(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test FlowSpec with TCP flags"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp",
            tcp_flags="syn",
            action="drop"
        )
        
        assert result is True
        call_args = mock_write.call_args[0]
        command = call_args[1].decode()
        assert 'tcp-flags' in command
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.subprocess.run')
    def test_send_flowspec_frr(self, mock_run, mock_settings, service):
        """Test FlowSpec via FRR"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'frr'
        mock_settings.FRR_VTYSH_CMD = '/usr/bin/vtysh'
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp",
            dest_port=80
        )
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('services.mitigation_service.settings')
    def test_send_flowspec_bird_not_implemented(self, mock_settings, service):
        """Test that FlowSpec for BIRD returns not implemented"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'bird'
        
        result = service.send_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp"
        )
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_withdraw_flowspec_exabgp(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test withdrawing FlowSpec rule via ExaBGP"""
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.withdraw_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp"
        )
        
        assert result is True
        call_args = mock_write.call_args[0]
        command = call_args[1].decode()
        assert 'withdraw flow route' in command
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.subprocess.run')
    def test_withdraw_flowspec_frr(self, mock_run, mock_settings, service):
        """Test withdrawing FlowSpec rule via FRR"""
        mock_settings.BGP_DAEMON = 'frr'
        mock_settings.FRR_VTYSH_CMD = '/usr/bin/vtysh'
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.withdraw_flowspec_rule(
            dest="192.0.2.100/32",
            protocol="tcp"
        )
        
        assert result is True


class TestMitigationServiceBGP:
    """Test BGP blackholing functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a mitigation service instance"""
        return MitigationService()
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_announce_bgp_blackhole_exabgp(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test announcing BGP blackhole via ExaBGP"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.BGP_BLACKHOLE_NEXTHOP = '192.0.2.1'
        mock_settings.BGP_BLACKHOLE_COMMUNITY = '65535:666'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is True
        mock_open.assert_called_once()
        call_args = mock_write.call_args[0]
        command = call_args[1].decode()
        assert 'announce route' in command
        assert '192.0.2.100/32' in command
    
    @patch('services.mitigation_service.settings')
    def test_announce_bgp_blackhole_disabled(self, mock_settings, service):
        """Test BGP blackhole when BGP is disabled"""
        mock_settings.BGP_ENABLED = False
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    def test_announce_bgp_blackhole_invalid_prefix(self, mock_settings, service):
        """Test BGP blackhole with invalid prefix"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        
        result = service.announce_bgp_blackhole("invalid-prefix")
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.subprocess.run')
    def test_announce_bgp_blackhole_frr(self, mock_run, mock_settings, service):
        """Test announcing BGP blackhole via FRR"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'frr'
        mock_settings.FRR_VTYSH_CMD = '/usr/bin/vtysh'
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.subprocess.run')
    def test_announce_bgp_blackhole_bird(self, mock_run, mock_settings, service):
        """Test announcing BGP blackhole via BIRD"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'bird'
        mock_settings.BIRD_CMD = 'birdc'
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ''
        mock_run.return_value = mock_result
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is True
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    @patch('services.mitigation_service.os.write')
    @patch('services.mitigation_service.os.close')
    def test_withdraw_bgp_blackhole_exabgp(self, mock_close, mock_write, mock_open, mock_settings, service):
        """Test withdrawing BGP blackhole via ExaBGP"""
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.return_value = 3
        
        result = service.withdraw_bgp_blackhole("192.0.2.100/32")
        
        assert result is True
        call_args = mock_write.call_args[0]
        command = call_args[1].decode()
        assert 'withdraw route' in command


class TestMitigationServiceFirewall:
    """Test firewall rule functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a mitigation service instance"""
        return MitigationService()
    
    @patch('services.mitigation_service.subprocess.run')
    def test_apply_iptables_block(self, mock_run, service):
        """Test applying iptables block rule"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.apply_iptables_rule('block', '192.0.2.100', 'tcp')
        
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'iptables' in call_args
        assert '-A' in call_args
        assert 'DROP' in call_args
    
    @patch('services.mitigation_service.subprocess.run')
    def test_apply_iptables_unblock(self, mock_run, service):
        """Test removing iptables block rule"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.apply_iptables_rule('unblock', '192.0.2.100', 'tcp')
        
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert '-D' in call_args
    
    @patch('services.mitigation_service.subprocess.run')
    def test_apply_nftables_block(self, mock_run, service):
        """Test applying nftables block rule"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = service.apply_nftables_rule('block', '192.0.2.100')
        
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert 'nft' in call_args
        assert 'add' in call_args


class TestMitigationServiceEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def service(self):
        """Create a mitigation service instance"""
        return MitigationService()
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.os.open')
    def test_exabgp_pipe_not_available(self, mock_open, mock_settings, service):
        """Test handling when ExaBGP pipe is not available"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'exabgp'
        mock_settings.EXABGP_CMD_PIPE = '/var/run/exabgp.cmd'
        mock_open.side_effect = OSError()
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is False
    
    @patch('services.mitigation_service.subprocess.run')
    def test_iptables_command_fails(self, mock_run, service):
        """Test handling when iptables command fails"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = service.apply_iptables_rule('block', '192.0.2.100')
        
        assert result is False
    
    @patch('services.mitigation_service.settings')
    @patch('services.mitigation_service.subprocess.run')
    def test_frr_command_timeout(self, mock_run, mock_settings, service):
        """Test handling FRR command timeout"""
        mock_settings.BGP_ENABLED = True
        mock_settings.BGP_DAEMON = 'frr'
        mock_run.side_effect = subprocess.TimeoutExpired('vtysh', 10)
        
        result = service.announce_bgp_blackhole("192.0.2.100/32")
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
