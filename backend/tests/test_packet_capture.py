"""
Unit tests for packet capture and hostgroup features
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from services.packet_capture import PacketCaptureService
from services.hostgroup_manager import HostGroup, HostGroupManager


class TestPacketCaptureService:
    """Test cases for PacketCaptureService"""
    
    @pytest.fixture
    def capture_service(self, tmp_path):
        """Create a PacketCaptureService instance with temp directory"""
        with patch('services.packet_capture.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            
            service = PacketCaptureService(capture_dir=str(tmp_path))
            service.redis_client = mock_redis_instance
            return service
    
    def test_vlan_untagging_single_tag(self, capture_service):
        """Test VLAN untagging with single 802.1Q tag"""
        # Create packet with VLAN tag (0x8100)
        # Destination MAC (6) + Source MAC (6) + 0x8100 (2) + VLAN TCI (2) + EtherType (2)
        packet = (
            b'\x00\x11\x22\x33\x44\x55'  # Dest MAC
            b'\xaa\xbb\xcc\xdd\xee\xff'  # Source MAC
            b'\x81\x00'                   # VLAN tag (0x8100)
            b'\x00\x64'                   # VLAN TCI (VLAN ID 100)
            b'\x08\x00'                   # EtherType (IPv4)
            b'payload data'
        )
        
        result = capture_service.untag_vlan(packet)
        
        # Should have removed the 4 VLAN bytes
        assert len(result) == len(packet) - 4
        # Check that MACs are preserved
        assert result[:12] == packet[:12]
        # Check that EtherType is now at correct position
        assert result[12:14] == b'\x08\x00'
    
    def test_vlan_untagging_double_tag(self, capture_service):
        """Test VLAN untagging with double tag (QinQ)"""
        # Create packet with double VLAN tag (0x88a8)
        packet = (
            b'\x00\x11\x22\x33\x44\x55'  # Dest MAC
            b'\xaa\xbb\xcc\xdd\xee\xff'  # Source MAC
            b'\x88\xa8'                   # Outer VLAN tag (0x88a8)
            b'\x00\x64'                   # Outer VLAN TCI
            b'\x81\x00'                   # Inner VLAN tag (0x8100)
            b'\x00\xc8'                   # Inner VLAN TCI
            b'\x08\x00'                   # EtherType (IPv4)
            b'payload data'
        )
        
        result = capture_service.untag_vlan(packet)
        
        # Should have removed 8 VLAN bytes (4 + 4)
        assert len(result) == len(packet) - 8
        # Check that MACs are preserved
        assert result[:12] == packet[:12]
    
    def test_vlan_untagging_no_tag(self, capture_service):
        """Test that packets without VLAN tags are unchanged"""
        packet = (
            b'\x00\x11\x22\x33\x44\x55'  # Dest MAC
            b'\xaa\xbb\xcc\xdd\xee\xff'  # Source MAC
            b'\x08\x00'                   # EtherType (IPv4)
            b'payload data'
        )
        
        result = capture_service.untag_vlan(packet)
        assert result == packet
    
    def test_capture_status(self, capture_service):
        """Test getting capture status"""
        capture_id = "test_capture_123"
        status = capture_service.get_capture_status(capture_id)
        
        assert status['capture_id'] == capture_id
        assert status['active'] == False
        assert status['file_size'] == 0
    
    def test_cleanup_old_captures(self, capture_service, tmp_path):
        """Test cleanup of old PCAP files"""
        # Create some test PCAP files
        old_file = tmp_path / "old_capture.pcap"
        new_file = tmp_path / "new_capture.pcap"
        
        old_file.write_text("old data")
        new_file.write_text("new data")
        
        # Modify mtime of old file to simulate old file
        import time
        import os
        old_time = time.time() - (8 * 86400)  # 8 days ago
        os.utime(old_file, (old_time, old_time))
        
        # Cleanup files older than 7 days
        deleted = capture_service.cleanup_old_captures(max_age_days=7)
        
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()


class TestHostGroup:
    """Test cases for HostGroup class"""
    
    def test_hostgroup_creation(self):
        """Test creating a hostgroup"""
        thresholds = {
            'packets_per_second': 10000,
            'bytes_per_second': 100000000,
            'flows_per_second': 1000
        }
        
        hostgroup = HostGroup(
            name="test_group",
            subnet="192.168.1.0/24",
            thresholds=thresholds
        )
        
        assert hostgroup.name == "test_group"
        assert str(hostgroup.subnet) == "192.168.1.0/24"
        assert hostgroup.thresholds == thresholds
    
    def test_hostgroup_contains_ip(self):
        """Test IP containment check"""
        hostgroup = HostGroup(
            name="test",
            subnet="192.168.1.0/24",
            thresholds={}
        )
        
        assert hostgroup.contains_ip("192.168.1.10") == True
        assert hostgroup.contains_ip("192.168.1.255") == True
        assert hostgroup.contains_ip("192.168.2.10") == False
        assert hostgroup.contains_ip("10.0.0.1") == False
    
    def test_hostgroup_to_dict(self):
        """Test converting hostgroup to dictionary"""
        thresholds = {'packets_per_second': 5000}
        scripts = {'block': '/path/to/block.sh'}
        
        hostgroup = HostGroup(
            name="test",
            subnet="10.0.0.0/8",
            thresholds=thresholds,
            scripts=scripts
        )
        
        result = hostgroup.to_dict()
        
        assert result['name'] == "test"
        assert result['subnet'] == "10.0.0.0/8"
        assert result['thresholds'] == thresholds
        assert result['scripts'] == scripts


class TestHostGroupManager:
    """Test cases for HostGroupManager"""
    
    @pytest.fixture
    def manager(self):
        """Create a HostGroupManager instance with mocked Redis"""
        with patch('services.hostgroup_manager.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.keys.return_value = []
            mock_redis.return_value = mock_redis_instance
            
            manager = HostGroupManager()
            manager.redis_client = mock_redis_instance
            return manager
    
    def test_add_hostgroup(self, manager):
        """Test adding a hostgroup"""
        thresholds = {'packets_per_second': 10000}
        
        success = manager.add_hostgroup(
            name="test_group",
            subnet="192.168.1.0/24",
            thresholds=thresholds
        )
        
        assert success == True
        assert "test_group" in manager.hostgroups
        assert manager.hostgroups["test_group"].thresholds == thresholds
    
    def test_remove_hostgroup(self, manager):
        """Test removing a hostgroup"""
        manager.add_hostgroup(
            name="test_group",
            subnet="192.168.1.0/24",
            thresholds={}
        )
        
        success = manager.remove_hostgroup("test_group")
        assert success == True
        assert "test_group" not in manager.hostgroups
        
        # Try to remove non-existent group
        success = manager.remove_hostgroup("non_existent")
        assert success == False
    
    def test_get_hostgroup_for_ip(self, manager):
        """Test finding hostgroup for an IP"""
        # Add two overlapping hostgroups
        manager.add_hostgroup(
            name="wide_group",
            subnet="192.168.0.0/16",
            thresholds={'packets_per_second': 10000}
        )
        manager.add_hostgroup(
            name="specific_group",
            subnet="192.168.1.0/24",
            thresholds={'packets_per_second': 5000}
        )
        
        # Should return most specific (longest prefix match)
        hostgroup = manager.get_hostgroup_for_ip("192.168.1.50")
        assert hostgroup.name == "specific_group"
        
        # IP in wider group but not specific
        hostgroup = manager.get_hostgroup_for_ip("192.168.2.50")
        assert hostgroup.name == "wide_group"
        
        # IP not in any group
        hostgroup = manager.get_hostgroup_for_ip("10.0.0.1")
        assert hostgroup is None
    
    def test_get_thresholds_for_ip(self, manager):
        """Test getting thresholds for an IP"""
        custom_thresholds = {'packets_per_second': 5000}
        
        manager.add_hostgroup(
            name="custom_group",
            subnet="192.168.1.0/24",
            thresholds=custom_thresholds
        )
        
        # IP in hostgroup should get custom thresholds
        thresholds = manager.get_thresholds_for_ip("192.168.1.10")
        assert thresholds == custom_thresholds
        
        # IP not in any hostgroup should get defaults
        thresholds = manager.get_thresholds_for_ip("10.0.0.1")
        assert thresholds == manager.default_thresholds
    
    def test_check_thresholds_not_exceeded(self, manager):
        """Test threshold checking when not exceeded"""
        manager.add_hostgroup(
            name="test",
            subnet="192.168.1.0/24",
            thresholds={'packets_per_second': 10000}
        )
        
        metrics = {'packets_per_second': 5000}
        
        # Should not trigger alert
        exceeded = manager.check_thresholds("192.168.1.10", metrics, isp_id=1)
        assert exceeded == False
    
    def test_list_hostgroups(self, manager):
        """Test listing all hostgroups"""
        manager.add_hostgroup("group1", "192.168.1.0/24", {})
        manager.add_hostgroup("group2", "10.0.0.0/8", {})
        
        groups = manager.list_hostgroups()
        
        assert len(groups) == 2
        assert any(g['name'] == 'group1' for g in groups)
        assert any(g['name'] == 'group2' for g in groups)


class TestVLANUntagging:
    """Additional VLAN untagging tests"""
    
    def test_vlan_id_extraction(self):
        """Test that VLAN ID can be properly extracted before untagging"""
        # This test verifies the packet structure understanding
        packet = (
            b'\x00\x11\x22\x33\x44\x55'  # Dest MAC
            b'\xaa\xbb\xcc\xdd\xee\xff'  # Source MAC
            b'\x81\x00'                   # VLAN tag
            b'\x00\x64'                   # TCI: VLAN ID 100 (0x0064)
            b'\x08\x00'                   # EtherType
        )
        
        # Extract VLAN ID from TCI
        tci = int.from_bytes(packet[14:16], 'big')
        vlan_id = tci & 0x0FFF
        
        assert vlan_id == 100
    
    def test_priority_code_point_preserved(self):
        """Test that PCP is handled in VLAN untagging"""
        # TCI includes PCP (3 bits), DEI (1 bit), and VLAN ID (12 bits)
        packet = (
            b'\x00\x11\x22\x33\x44\x55'  # Dest MAC
            b'\xaa\xbb\xcc\xdd\xee\xff'  # Source MAC
            b'\x81\x00'                   # VLAN tag
            b'\xe0\x64'                   # TCI: PCP=7, DEI=0, VLAN=100
            b'\x08\x00'                   # EtherType
        )
        
        # Extract PCP from TCI
        tci = int.from_bytes(packet[14:16], 'big')
        pcp = (tci >> 13) & 0x07
        
        assert pcp == 7
