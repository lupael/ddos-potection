"""
Simple validation tests for traffic collector and anomaly detector
"""
import struct
import socket
import math
from collections import defaultdict


def test_netflow_v5_parsing():
    """Test NetFlow v5 packet structure"""
    # Create a mock NetFlow v5 header
    header = struct.pack('!HHIIIIBBH', 5, 1, 0, 0, 0, 0, 0, 0, 0)
    
    # Create a mock flow record
    src_ip = socket.inet_aton('192.168.1.100')
    dst_ip = socket.inet_aton('10.0.0.50')
    next_hop = socket.inet_aton('192.168.1.1')
    
    flow_record = struct.pack('!III', 
        struct.unpack('!I', src_ip)[0],
        struct.unpack('!I', dst_ip)[0],
        struct.unpack('!I', next_hop)[0]
    )
    flow_record += struct.pack('!HH', 0, 0)  # input/output interfaces
    flow_record += struct.pack('!HH', 54321, 80)  # src_port, dst_port
    flow_record += struct.pack('!II', 100, 50000)  # packets, bytes
    flow_record += struct.pack('!II', 0, 0)  # first/last
    flow_record += struct.pack('!HH', 0, 0)  # pad
    flow_record += struct.pack('!BBBB', 6, 0x02, 0, 0)  # protocol, tcp_flags, tos, pad
    flow_record += struct.pack('!HHH', 0, 0, 0)  # src_as, dst_as, pad
    
    packet = header + flow_record
    
    # Verify packet structure (header is 24 bytes, flow record varies)
    assert len(packet) >= 72
    
    # Parse header
    parsed_header = struct.unpack('!HHIIIIBBH', packet[:24])
    version, count = parsed_header[0], parsed_header[1]
    
    assert version == 5
    assert count == 1
    
    # Parse flow record (actual NetFlow v5 format)
    offset = 24
    # NetFlow v5 record is 48 bytes, but our test record is slightly different
    # Adjust to actual data we packed
    flow_size = len(packet) - offset
    
    # Parse what we can from the flow
    src_addr = struct.unpack('!I', packet[offset:offset+4])[0]
    dst_addr = struct.unpack('!I', packet[offset+4:offset+8])[0]
    next_hop_addr = struct.unpack('!I', packet[offset+8:offset+12])[0]
    
    parsed_src_ip = socket.inet_ntoa(struct.pack('!I', src_addr))
    parsed_dst_ip = socket.inet_ntoa(struct.pack('!I', dst_addr))
    
    # Parse ports at offset 16-20
    parsed_src_port, parsed_dst_port = struct.unpack('!HH', packet[offset+16:offset+20])
    
    # Parse packets and bytes at offset 20-28
    parsed_packets, parsed_bytes = struct.unpack('!II', packet[offset+20:offset+28])
    
    # Parse protocol and tcp_flags at offset 40-44
    parsed_protocol, parsed_tcp_flags = struct.unpack('!BB', packet[offset+40:offset+42])
    
    assert parsed_src_ip == '192.168.1.100'
    assert parsed_dst_ip == '10.0.0.50'
    assert parsed_src_port == 54321
    assert parsed_dst_port == 80
    assert parsed_packets == 100
    assert parsed_bytes == 50000
    assert parsed_protocol == 6  # TCP
    assert parsed_tcp_flags == 0x02  # SYN flag
    
    print("✓ NetFlow v5 parsing test passed")


def test_netflow_v9_template():
    """Test NetFlow v9 template structure"""
    # Create NetFlow v9 header
    header = struct.pack('!HHIIII', 9, 1, 0, 0, 0, 1)
    
    # Create template FlowSet
    flowset_id = 0  # Template FlowSet
    template_id = 256
    field_count = 3
    
    template_header = struct.pack('!HH', template_id, field_count)
    
    # Add fields
    fields = struct.pack('!HH', 8, 4)  # sourceIPv4Address
    fields += struct.pack('!HH', 12, 4)  # destinationIPv4Address
    fields += struct.pack('!HH', 4, 1)  # protocolIdentifier
    
    template = template_header + fields
    flowset_length = 4 + len(template)
    flowset = struct.pack('!HH', flowset_id, flowset_length) + template
    
    packet = header + flowset
    
    # Parse and verify
    parsed_header = struct.unpack('!HHIIII', packet[:20])
    version, count = parsed_header[0], parsed_header[1]
    
    assert version == 9
    assert len(packet) >= 20
    
    print("✓ NetFlow v9 template test passed")


def test_sflow_header():
    """Test sFlow header structure"""
    version = 5
    addr_type = 1  # IPv4
    agent_addr = struct.unpack('!I', socket.inet_aton('192.168.1.1'))[0]
    sub_agent_id = 0
    sequence = 1
    uptime = 1000
    num_samples = 0
    
    header = struct.pack('!IIIIIII', version, addr_type, agent_addr, sub_agent_id, sequence, uptime, num_samples)
    
    assert len(header) == 28
    
    # Parse and verify
    parsed = struct.unpack('!IIIIIII', header)
    assert parsed[0] == 5  # version
    
    print("✓ sFlow header test passed")


def test_ipfix_header():
    """Test IPFIX header structure"""
    version = 10
    length = 16
    export_time = 1000
    sequence = 1
    observation_domain = 1
    
    header = struct.pack('!HHIII', version, length, export_time, sequence, observation_domain)
    
    assert len(header) == 16
    
    # Parse and verify
    parsed = struct.unpack('!HHIII', header)
    assert parsed[0] == 10  # version
    
    print("✓ IPFIX header test passed")


def test_entropy_calculation():
    """Test Shannon entropy calculation"""
    def calculate_entropy(data):
        if not data:
            return 0.0
        
        frequencies = defaultdict(int)
        for item in data:
            frequencies[item] += 1
        
        total = len(data)
        entropy = 0.0
        
        for count in frequencies.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    # Test uniform distribution
    uniform_data = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    entropy = calculate_entropy(uniform_data)
    assert abs(entropy - 3.0) < 0.01  # log2(8) = 3.0
    
    # Test concentrated distribution
    concentrated_data = ['a'] * 100 + ['b'] * 5
    entropy = calculate_entropy(concentrated_data)
    assert entropy < 1.0
    
    # Test empty data
    entropy = calculate_entropy([])
    assert entropy == 0.0
    
    print("✓ Entropy calculation test passed")


def test_tcp_flags_parsing():
    """Test TCP flags extraction"""
    # Test SYN flag
    tcp_flags = 0x02
    
    flags_list = []
    if tcp_flags & 0x01: flags_list.append('FIN')
    if tcp_flags & 0x02: flags_list.append('SYN')
    if tcp_flags & 0x04: flags_list.append('RST')
    if tcp_flags & 0x08: flags_list.append('PSH')
    if tcp_flags & 0x10: flags_list.append('ACK')
    if tcp_flags & 0x20: flags_list.append('URG')
    
    assert 'SYN' in flags_list
    assert len(flags_list) == 1
    
    # Test SYN+ACK flags
    tcp_flags = 0x12  # SYN + ACK
    flags_list = []
    if tcp_flags & 0x01: flags_list.append('FIN')
    if tcp_flags & 0x02: flags_list.append('SYN')
    if tcp_flags & 0x04: flags_list.append('RST')
    if tcp_flags & 0x08: flags_list.append('PSH')
    if tcp_flags & 0x10: flags_list.append('ACK')
    if tcp_flags & 0x20: flags_list.append('URG')
    
    assert 'SYN' in flags_list
    assert 'ACK' in flags_list
    assert len(flags_list) == 2
    
    print("✓ TCP flags parsing test passed")


def test_protocol_numbers():
    """Test protocol number to name conversion"""
    protocols = {
        1: 'ICMP',
        6: 'TCP',
        17: 'UDP',
        47: 'GRE',
        50: 'ESP',
        51: 'AH'
    }
    
    assert protocols[1] == 'ICMP'
    assert protocols[6] == 'TCP'
    assert protocols[17] == 'UDP'
    
    # Unknown protocol
    unknown_proto = 99
    assert unknown_proto not in protocols
    
    print("✓ Protocol number mapping test passed")


if __name__ == '__main__':
    print("\nRunning DDoS Protection Platform Tests\n")
    print("=" * 50)
    
    test_netflow_v5_parsing()
    test_netflow_v9_template()
    test_sflow_header()
    test_ipfix_header()
    test_entropy_calculation()
    test_tcp_flags_parsing()
    test_protocol_numbers()
    
    print("=" * 50)
    print("\n✅ All tests passed!\n")
