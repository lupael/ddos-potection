"""
Unit tests for traffic collector service
"""
import pytest
import struct
import socket
from unittest.mock import MagicMock, patch

from services.traffic_collector import TrafficCollector


class TestTrafficCollector:
    """Test cases for TrafficCollector"""
    
    @pytest.fixture
    def collector(self):
        """Create a TrafficCollector instance with mocked Redis"""
        with patch('services.traffic_collector.redis.Redis') as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            collector = TrafficCollector()
            collector.redis_client = mock_redis_instance
            return collector
    
    def test_netflow_v5_parsing(self, collector):
        """Test NetFlow v5 packet parsing (RFC 3954 compliant 48-byte flow record)"""
        # Create a mock NetFlow v5 header
        header = struct.pack('!HHIIIIBBH', 5, 1, 0, 0, 0, 0, 0, 0, 0)
        
        # Create a RFC-compliant 48-byte flow record:
        # srcaddr(4) dstaddr(4) nexthop(4) input(2) output(2)
        # dPkts(4) dOctets(4) First(4) Last(4)
        # srcport(2) dstport(2) pad1(1) tcp_flags(1) prot(1) tos(1)
        # src_as(2) dst_as(2) src_mask(1) dst_mask(1) pad2(2)
        FLOW_FMT = '!IIIHHIIIIHHxBBBHHBBxx'
        src_ip_int = struct.unpack('!I', socket.inet_aton('192.168.1.100'))[0]
        dst_ip_int = struct.unpack('!I', socket.inet_aton('10.0.0.50'))[0]
        nexthop_int = struct.unpack('!I', socket.inet_aton('192.168.1.1'))[0]
        flow_record = struct.pack(
            FLOW_FMT,
            src_ip_int,   # srcaddr
            dst_ip_int,   # dstaddr
            nexthop_int,  # nexthop
            0,            # input interface
            0,            # output interface
            100,          # dPkts (packets)
            50000,        # dOctets (bytes)
            0,            # First (uptime ms)
            0,            # Last  (uptime ms)
            54321,        # srcport
            80,           # dstport
            # pad1 auto-filled by 'x'
            0x02,         # tcp_flags
            6,            # prot (TCP)
            0,            # tos
            0,            # src_as
            0,            # dst_as
            0,            # src_mask
            0,            # dst_mask
            # pad2 auto-filled by 'xx'
        )
        
        packet = header + flow_record
        
        result = collector.parse_netflow_v5(packet)
        
        assert result['version'] == 5
        assert result['count'] == 1
        assert len(result['flows']) == 1
        
        flow = result['flows'][0]
        assert flow['src_ip'] == '192.168.1.100'
        assert flow['dst_ip'] == '10.0.0.50'
        assert flow['src_port'] == 54321
        assert flow['dst_port'] == 80
        assert flow['packets'] == 100
        assert flow['bytes'] == 50000
        assert flow['protocol'] == 6
    
    def test_netflow_v5_invalid_packet(self, collector):
        """Test NetFlow v5 parsing with invalid packet"""
        # Too short packet
        packet = b'short'
        result = collector.parse_netflow_v5(packet)
        
        assert result['version'] == 5
        assert result['count'] == 0
        assert len(result['flows']) == 0
    
    def test_netflow_v9_template_parsing(self, collector):
        """Test NetFlow v9 template parsing"""
        # Create NetFlow v9 header
        header = struct.pack('!HHIIII', 9, 1, 0, 0, 0, 1)  # version, count, uptime, unix_secs, seq, source_id
        
        # Create template FlowSet
        flowset_id = 0  # Template FlowSet
        template_id = 256
        field_count = 3
        
        template_header = struct.pack('!HH', template_id, field_count)
        
        # Add fields: src IP (type 8), dst IP (type 12), protocol (type 4)
        fields = struct.pack('!HH', 8, 4)  # sourceIPv4Address, length 4
        fields += struct.pack('!HH', 12, 4)  # destinationIPv4Address, length 4
        fields += struct.pack('!HH', 4, 1)  # protocolIdentifier, length 1
        
        template = template_header + fields
        flowset_length = 4 + len(template)  # 4 bytes for flowset header
        flowset = struct.pack('!HH', flowset_id, flowset_length) + template
        
        packet = header + flowset
        
        result = collector.parse_netflow_v9(packet, '192.168.1.1')
        
        assert result['version'] == 9
        # Template packets don't contain data flows
        assert result['count'] == 0
        
        # Check that template was cached
        template_key = "192.168.1.1:1:256"
        assert template_key in collector.netflow_templates
        assert len(collector.netflow_templates[template_key]) == 3
    
    def test_sflow_parsing_basic(self, collector):
        """Test basic sFlow packet parsing"""
        # Create sFlow header (version 5)
        version = 5
        addr_type = 1  # IPv4
        agent_addr = struct.unpack('!I', socket.inet_aton('192.168.1.1'))[0]
        sub_agent_id = 0
        sequence = 1
        uptime = 1000
        num_samples = 0
        
        header = struct.pack('!IIIIIII', version, addr_type, agent_addr, sub_agent_id, sequence, uptime, num_samples)
        
        result = collector.parse_sflow(header)
        
        assert result['version'] == 5
        assert result['count'] == 0
    
    def test_ipfix_parsing_basic(self, collector):
        """Test basic IPFIX packet parsing"""
        # Create IPFIX header
        version = 10
        length = 16
        export_time = 1000
        sequence = 1
        observation_domain = 1
        
        header = struct.pack('!HHIII', version, length, export_time, sequence, observation_domain)
        
        result = collector.parse_ipfix(header, '192.168.1.1')
        
        assert result['version'] == 10
        assert result['count'] == 0
    
    def test_protocol_name_conversion(self, collector):
        """Test protocol number to name conversion"""
        assert collector.get_protocol_name(1) == 'ICMP'
        assert collector.get_protocol_name(6) == 'TCP'
        assert collector.get_protocol_name(17) == 'UDP'
        assert collector.get_protocol_name(47) == 'GRE'
        assert collector.get_protocol_name(99) == 'PROTO_99'
    
    def test_router_vendor_detection(self, collector):
        """Test router vendor detection"""
        # NetFlow v9 packet (MikroTik)
        packet_v9 = struct.pack('!H', 9) + b'\x00' * 18
        vendor = collector.detect_router_vendor('192.168.1.1', packet_v9)
        assert vendor == 'mikrotik'
        
        # NetFlow v5 packet (Cisco)
        packet_v5 = struct.pack('!H', 5) + b'\x00' * 22
        vendor = collector.detect_router_vendor('192.168.1.2', packet_v5)
        assert vendor == 'cisco'
        
        # IPFIX packet
        packet_ipfix = struct.pack('!H', 10) + b'\x00' * 14
        vendor = collector.detect_router_vendor('192.168.1.3', packet_ipfix)
        assert vendor == 'cisco'
        
        # Check caching
        vendor = collector.detect_router_vendor('192.168.1.1', b'')
        assert vendor == 'mikrotik'
    
    def test_publish_to_redis_stream(self, collector):
        """Test publishing flow to Redis stream"""
        flow = {
            'src_ip': '192.168.1.100',
            'dst_ip': '10.0.0.50',
            'src_port': 54321,
            'dst_port': 80,
            'protocol': 6,
            'packets': 100,
            'bytes': 50000,
            'tcp_flags': 0x02
        }
        
        collector.publish_to_redis_stream(flow)
        
        # Verify Redis stream methods were called
        assert collector.redis_client.xadd.called
        assert collector.redis_client.publish.called
    
    @patch('services.traffic_collector.SessionLocal')
    def test_store_traffic(self, mock_session, collector):
        """Test storing traffic to database"""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        flow = {
            'src_ip': '192.168.1.100',
            'dst_ip': '10.0.0.50',
            'src_port': 54321,
            'dst_port': 80,
            'protocol': 6,
            'packets': 100,
            'bytes': 50000,
            'tcp_flags': 0x02  # SYN flag
        }
        
        collector.store_traffic(flow, isp_id=1)
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.close.called
        
        # Verify Redis operations
        assert collector.redis_client.incrby.called
        assert collector.redis_client.expire.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
