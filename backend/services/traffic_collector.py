"""
Traffic collector service for NetFlow/sFlow/IPFIX
"""
import socket
import struct
from typing import Dict, Any, List, Tuple
import redis
import json
import threading
from datetime import datetime, timezone

from database import SessionLocal
from models.models import TrafficLog
from config import settings

class TrafficCollector:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False
        )
        # NetFlow v9 template cache
        self.netflow_templates = {}
        # IPFIX template cache  
        self.ipfix_templates = {}
        # Router vendor detection cache
        self.router_vendors = {}
    
    def parse_netflow_v5(self, data: bytes) -> Dict[str, Any]:
        """Parse NetFlow v5 packet"""
        if len(data) < 24:
            return {'version': 5, 'count': 0, 'flows': []}
            
        header = struct.unpack('!HHIIIIBBH', data[:24])
        version, count = header[0], header[1]
        
        flows = []
        offset = 24
        for i in range(count):
            if offset + 48 > len(data):
                break
            
            flow_data = struct.unpack('!IIIHHIIIIHHBBBBHHH', data[offset:offset+48])
            flow = {
                'src_ip': socket.inet_ntoa(struct.pack('!I', flow_data[0])),
                'dst_ip': socket.inet_ntoa(struct.pack('!I', flow_data[1])),
                'next_hop': socket.inet_ntoa(struct.pack('!I', flow_data[2])),
                'src_port': flow_data[4],
                'dst_port': flow_data[5],
                'packets': flow_data[6],
                'bytes': flow_data[7],
                'protocol': flow_data[11],
                'tcp_flags': flow_data[12],
                'tos': flow_data[13]
            }
            flows.append(flow)
            offset += 48
        
        return {'version': version, 'count': count, 'flows': flows}
    
    def parse_netflow_v9(self, data: bytes, source_ip: str) -> Dict[str, Any]:
        """Parse NetFlow v9 packet with template support"""
        if len(data) < 20:
            return {'version': 9, 'count': 0, 'flows': []}
        
        # Parse header
        header = struct.unpack('!HHIIII', data[:20])
        version, count, uptime, unix_secs, sequence, source_id = header
        
        flows = []
        offset = 20
        
        while offset < len(data):
            if offset + 4 > len(data):
                break
                
            flowset_id, length = struct.unpack('!HH', data[offset:offset+4])
            
            if length < 4 or offset + length > len(data):
                break
            
            flowset_data = data[offset+4:offset+length]
            
            # Template FlowSet (ID 0)
            if flowset_id == 0:
                self._parse_netflow_v9_template(flowset_data, source_ip, source_id)
            # Data FlowSet (ID > 255)
            elif flowset_id > 255:
                template_key = f"{source_ip}:{source_id}:{flowset_id}"
                if template_key in self.netflow_templates:
                    template = self.netflow_templates[template_key]
                    flows.extend(self._parse_netflow_v9_data(flowset_data, template))
            
            offset += length
        
        return {'version': version, 'count': len(flows), 'flows': flows}
    
    def _parse_netflow_v9_template(self, data: bytes, source_ip: str, source_id: int):
        """Parse NetFlow v9 template"""
        offset = 0
        while offset + 4 <= len(data):
            template_id, field_count = struct.unpack('!HH', data[offset:offset+4])
            offset += 4
            
            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break
                field_type, field_length = struct.unpack('!HH', data[offset:offset+4])
                fields.append({'type': field_type, 'length': field_length})
                offset += 4
            
            template_key = f"{source_ip}:{source_id}:{template_id}"
            self.netflow_templates[template_key] = fields
    
    def _parse_netflow_v9_data(self, data: bytes, template: List[Dict]) -> List[Dict]:
        """Parse NetFlow v9 data using template"""
        flows = []
        offset = 0
        record_length = sum(field['length'] for field in template)
        
        while offset + record_length <= len(data):
            flow = {}
            field_offset = offset
            
            for field in template:
                field_data = data[field_offset:field_offset+field['length']]
                field_offset += field['length']
                
                # Parse common field types
                if field['type'] == 8:  # IPV4_SRC_ADDR
                    flow['src_ip'] = socket.inet_ntoa(field_data[:4])
                elif field['type'] == 12:  # IPV4_DST_ADDR
                    flow['dst_ip'] = socket.inet_ntoa(field_data[:4])
                elif field['type'] == 7:  # L4_SRC_PORT
                    flow['src_port'] = struct.unpack('!H', field_data)[0]
                elif field['type'] == 11:  # L4_DST_PORT
                    flow['dst_port'] = struct.unpack('!H', field_data)[0]
                elif field['type'] == 4:  # PROTOCOL
                    flow['protocol'] = struct.unpack('!B', field_data)[0]
                elif field['type'] == 2:  # PKTS
                    if field['length'] == 4:
                        flow['packets'] = struct.unpack('!I', field_data)[0]
                    elif field['length'] == 8:
                        flow['packets'] = struct.unpack('!Q', field_data)[0]
                elif field['type'] == 1:  # BYTES
                    if field['length'] == 4:
                        flow['bytes'] = struct.unpack('!I', field_data)[0]
                    elif field['length'] == 8:
                        flow['bytes'] = struct.unpack('!Q', field_data)[0]
                elif field['type'] == 6:  # TCP_FLAGS
                    flow['tcp_flags'] = struct.unpack('!B', field_data)[0]
            
            if flow:
                flows.append(flow)
            offset += record_length
        
        return flows
    
    def parse_sflow(self, data: bytes) -> Dict[str, Any]:
        """Parse sFlow v5 packet"""
        if len(data) < 28:
            return {'version': 0, 'count': 0, 'flows': []}
        
        # Parse sFlow header
        version, addr_type, agent_addr, sub_agent_id, sequence, uptime, num_samples = struct.unpack(
            '!IIIIIII', data[:28]
        )
        
        flows = []
        offset = 28
        
        for _ in range(num_samples):
            if offset + 8 > len(data):
                break
            
            # Parse sample header
            sample_type, sample_length = struct.unpack('!II', data[offset:offset+8])
            offset += 8
            
            if offset + sample_length > len(data):
                break
            
            sample_data = data[offset:offset+sample_length]
            
            # Flow sample (type 1)
            if sample_type == 1:
                flows.extend(self._parse_sflow_sample(sample_data))
            
            offset += sample_length
        
        return {'version': version, 'count': len(flows), 'flows': flows}
    
    def _parse_sflow_sample(self, data: bytes) -> List[Dict]:
        """Parse sFlow flow sample"""
        if len(data) < 24:
            return []
        
        # Parse sample header
        sequence, source_id, sampling_rate, sample_pool, drops, input_if, output_if, num_records = struct.unpack(
            '!IIIIIIII', data[:32]
        )
        
        flows = []
        offset = 32
        
        for _ in range(num_records):
            if offset + 8 > len(data):
                break
            
            record_type, record_length = struct.unpack('!II', data[offset:offset+8])
            offset += 8
            
            if offset + record_length > len(data):
                break
            
            record_data = data[offset:offset+record_length]
            
            # Raw packet header (type 1)
            if record_type == 1 and len(record_data) >= 16:
                protocol = struct.unpack('!I', record_data[:4])[0]
                frame_length = struct.unpack('!I', record_data[4:8])[0]
                header_length = struct.unpack('!I', record_data[12:16])[0]
                
                # Parse Ethernet/IP header from captured data
                if header_length >= 34:  # Minimum for Ethernet + IPv4
                    header_data = record_data[16:16+header_length]
                    flow = self._parse_sflow_packet_header(header_data)
                    if flow:
                        flow['packets'] = 1
                        flow['bytes'] = frame_length
                        flows.append(flow)
            
            offset += record_length
        
        return flows
    
    def _parse_sflow_packet_header(self, data: bytes) -> Dict[str, Any]:
        """Parse packet header from sFlow sample"""
        if len(data) < 34:
            return {}
        
        # Skip Ethernet header (14 bytes)
        ip_data = data[14:]
        
        if len(ip_data) < 20:
            return {}
        
        # Parse IP header
        version_ihl = struct.unpack('!B', ip_data[0:1])[0]
        version = version_ihl >> 4
        
        if version != 4:
            return {}
        
        protocol = struct.unpack('!B', ip_data[9:10])[0]
        src_ip = socket.inet_ntoa(ip_data[12:16])
        dst_ip = socket.inet_ntoa(ip_data[16:20])
        
        flow = {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'protocol': protocol
        }
        
        # Parse TCP/UDP ports
        ihl = (version_ihl & 0x0F) * 4
        if len(ip_data) >= ihl + 4:
            l4_data = ip_data[ihl:]
            if protocol == 6 or protocol == 17:  # TCP or UDP
                src_port, dst_port = struct.unpack('!HH', l4_data[:4])
                flow['src_port'] = src_port
                flow['dst_port'] = dst_port
                
                # TCP flags
                if protocol == 6 and len(l4_data) >= 14:
                    tcp_flags = struct.unpack('!B', l4_data[13:14])[0]
                    flow['tcp_flags'] = tcp_flags
        
        return flow
    
    def parse_ipfix(self, data: bytes, source_ip: str) -> Dict[str, Any]:
        """Parse IPFIX packet"""
        if len(data) < 16:
            return {'version': 10, 'count': 0, 'flows': []}
        
        # Parse IPFIX header
        version, length, export_time, sequence, observation_domain = struct.unpack(
            '!HHIII', data[:16]
        )
        
        if version != 10:
            return {'version': version, 'count': 0, 'flows': []}
        
        flows = []
        offset = 16
        
        while offset < len(data):
            if offset + 4 > len(data):
                break
            
            set_id, set_length = struct.unpack('!HH', data[offset:offset+4])
            
            if set_length < 4 or offset + set_length > len(data):
                break
            
            set_data = data[offset+4:offset+set_length]
            
            # Template Set (ID 2)
            if set_id == 2:
                self._parse_ipfix_template(set_data, source_ip, observation_domain)
            # Data Set (ID > 255)
            elif set_id > 255:
                template_key = f"{source_ip}:{observation_domain}:{set_id}"
                if template_key in self.ipfix_templates:
                    template = self.ipfix_templates[template_key]
                    flows.extend(self._parse_ipfix_data(set_data, template))
            
            offset += set_length
        
        return {'version': version, 'count': len(flows), 'flows': flows}
    
    def _parse_ipfix_template(self, data: bytes, source_ip: str, observation_domain: int):
        """Parse IPFIX template"""
        offset = 0
        while offset + 4 <= len(data):
            template_id, field_count = struct.unpack('!HH', data[offset:offset+4])
            offset += 4
            
            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break
                
                field_id, field_length = struct.unpack('!HH', data[offset:offset+4])
                offset += 4
                
                # Check for enterprise bit
                enterprise_number = None
                if field_id & 0x8000:
                    field_id = field_id & 0x7FFF
                    if offset + 4 <= len(data):
                        enterprise_number = struct.unpack('!I', data[offset:offset+4])[0]
                        offset += 4
                
                fields.append({
                    'id': field_id,
                    'length': field_length,
                    'enterprise': enterprise_number
                })
            
            template_key = f"{source_ip}:{observation_domain}:{template_id}"
            self.ipfix_templates[template_key] = fields
    
    def _parse_ipfix_data(self, data: bytes, template: List[Dict]) -> List[Dict]:
        """Parse IPFIX data using template"""
        flows = []
        offset = 0
        record_length = sum(field['length'] for field in template)
        
        while offset + record_length <= len(data):
            flow = {}
            field_offset = offset
            
            for field in template:
                field_data = data[field_offset:field_offset+field['length']]
                field_offset += field['length']
                
                # Skip enterprise fields
                if field['enterprise'] is not None:
                    continue
                
                # Parse standard IPFIX fields (same as NetFlow v9)
                if field['id'] == 8:  # sourceIPv4Address
                    flow['src_ip'] = socket.inet_ntoa(field_data[:4])
                elif field['id'] == 12:  # destinationIPv4Address
                    flow['dst_ip'] = socket.inet_ntoa(field_data[:4])
                elif field['id'] == 7:  # sourceTransportPort
                    flow['src_port'] = struct.unpack('!H', field_data)[0]
                elif field['id'] == 11:  # destinationTransportPort
                    flow['dst_port'] = struct.unpack('!H', field_data)[0]
                elif field['id'] == 4:  # protocolIdentifier
                    flow['protocol'] = struct.unpack('!B', field_data)[0]
                elif field['id'] == 2:  # packetDeltaCount
                    if field['length'] == 4:
                        flow['packets'] = struct.unpack('!I', field_data)[0]
                    elif field['length'] == 8:
                        flow['packets'] = struct.unpack('!Q', field_data)[0]
                elif field['id'] == 1:  # octetDeltaCount
                    if field['length'] == 4:
                        flow['bytes'] = struct.unpack('!I', field_data)[0]
                    elif field['length'] == 8:
                        flow['bytes'] = struct.unpack('!Q', field_data)[0]
                elif field['id'] == 6:  # tcpControlBits
                    flow['tcp_flags'] = struct.unpack('!B', field_data)[0]
            
            if flow:
                flows.append(flow)
            offset += record_length
        
        return flows
    
    def detect_router_vendor(self, addr: str, data: bytes) -> str:
        """Detect router vendor from packet characteristics"""
        if addr in self.router_vendors:
            return self.router_vendors[addr]
        
        vendor = 'unknown'
        
        # Check packet characteristics
        if len(data) >= 2:
            version = struct.unpack('!H', data[:2])[0]
            
            # MikroTik typically uses NetFlow v9
            if version == 9:
                vendor = 'mikrotik'
            # Cisco commonly uses NetFlow v5 or v9
            elif version == 5:
                vendor = 'cisco'
            # Juniper often uses sFlow or IPFIX
            elif version == 5 and len(data) > 28:
                vendor = 'juniper'
            # IPFIX
            elif version == 10:
                vendor = 'cisco'  # or other IPFIX-capable vendor
        
        self.router_vendors[addr] = vendor
        return vendor
    
    def publish_to_redis_stream(self, flow: Dict[str, Any], stream_name: str = 'traffic:stream'):
        """Publish flow to Redis stream for real-time processing"""
        try:
            flow_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'src_ip': flow.get('src_ip', ''),
                'dst_ip': flow.get('dst_ip', ''),
                'src_port': str(flow.get('src_port', 0)),
                'dst_port': str(flow.get('dst_port', 0)),
                'protocol': str(flow.get('protocol', 0)),
                'packets': str(flow.get('packets', 0)),
                'bytes': str(flow.get('bytes', 0)),
                'tcp_flags': str(flow.get('tcp_flags', 0))
            }
            
            # Add to Redis stream
            self.redis_client.xadd(stream_name, flow_data, maxlen=10000)
            
            # Publish to pub/sub for real-time alerts
            self.redis_client.publish('traffic:events', json.dumps(flow_data))
            
        except Exception as e:
            print(f"Error publishing to Redis stream: {e}")
    
    def store_traffic(self, flow: Dict[str, Any], isp_id: int = 1):
        # Publish to Redis stream first for real-time processing
        self.publish_to_redis_stream(flow)
        
        db = SessionLocal()
        try:
            # Extract TCP flags
            tcp_flags = flow.get('tcp_flags', 0)
            protocol = flow.get('protocol', 0)
            src_ip = flow.get('src_ip')
            packets = flow.get('packets', 0)
            bytes_count = flow.get('bytes', 0)
            
            # Store to database
            traffic_log = TrafficLog(
                isp_id=isp_id,
                source_ip=src_ip,
                dest_ip=flow.get('dst_ip'),
                protocol=self.get_protocol_name(protocol),
                packets=packets,
                bytes=bytes_count,
                is_anomaly=False
            )
            db.add(traffic_log)
            db.commit()
            
            # Redis sliding window counters for traffic analysis
            current_time = int(datetime.now(timezone.utc).timestamp())
            window_key = f"traffic:window:{isp_id}:{src_ip}"
            
            # Add to sorted set with timestamp as score
            self.redis_client.zadd(window_key, {f"{current_time}:{packets}:{bytes_count}": current_time})
            # Keep only last 60 seconds
            self.redis_client.zremrangebyscore(window_key, 0, current_time - 60)
            self.redis_client.expire(window_key, 120)
            
            # Track SYN floods (TCP protocol = 6, SYN flag = 0x02)
            if protocol == 6 and (tcp_flags & 0x02):
                syn_key = f"syn_flood:{isp_id}:{src_ip}"
                self.redis_client.incr(syn_key)
                self.redis_client.expire(syn_key, 10)
                
                # Check for SYN flood threshold
                syn_count = int(self.redis_client.get(syn_key) or 0)
                if syn_count > 100:
                    alert_key = f"alert:syn_flood:{src_ip}"
                    self.redis_client.setex(alert_key, 60, syn_count)
            
        finally:
            db.close()
    
    def get_protocol_name(self, protocol_num: int) -> str:
        """Convert protocol number to name"""
        protocols = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            47: 'GRE',
            50: 'ESP',
            51: 'AH'
        }
        return protocols.get(protocol_num, f'PROTO_{protocol_num}')
    
    def start_netflow_collector(self, port: int = None):
        """Start NetFlow collector supporting v5, v9"""
        port = port or settings.NETFLOW_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to all interfaces to receive NetFlow data from routers
        # This is intentional and secured by Docker network isolation
        sock.bind(('0.0.0.0', port))
        
        print(f"NetFlow collector listening on port {port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                
                # Detect router vendor
                vendor = self.detect_router_vendor(addr[0], data)
                
                # Determine NetFlow version
                if len(data) >= 2:
                    version = struct.unpack('!H', data[:2])[0]
                    
                    if version == 5:
                        flows_data = self.parse_netflow_v5(data)
                    elif version == 9:
                        flows_data = self.parse_netflow_v9(data, addr[0])
                    else:
                        print(f"Unsupported NetFlow version {version} from {addr[0]}")
                        continue
                    
                    for flow in flows_data.get('flows', []):
                        self.store_traffic(flow)
                    
                    if flows_data.get('count', 0) > 0:
                        print(f"Processed {flows_data['count']} flows from {vendor} router at {addr[0]}")
                    
            except Exception as e:
                print(f"Error processing NetFlow packet from {addr[0]}: {e}")
                continue
    
    def start_sflow_collector(self, port: int = None):
        """Start sFlow collector"""
        port = port or settings.SFLOW_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        
        print(f"sFlow collector listening on port {port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                flows_data = self.parse_sflow(data)
                
                for flow in flows_data.get('flows', []):
                    self.store_traffic(flow)
                
                if flows_data.get('count', 0) > 0:
                    print(f"Processed {flows_data['count']} sFlow samples from {addr[0]}")
                    
            except Exception as e:
                print(f"Error processing sFlow packet from {addr[0]}: {e}")
                continue
    
    def start_ipfix_collector(self, port: int = None):
        """Start IPFIX collector"""
        port = port or settings.IPFIX_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        
        print(f"IPFIX collector listening on port {port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                flows_data = self.parse_ipfix(data, addr[0])
                
                for flow in flows_data.get('flows', []):
                    self.store_traffic(flow)
                
                if flows_data.get('count', 0) > 0:
                    print(f"Processed {flows_data['count']} IPFIX records from {addr[0]}")
                    
            except Exception as e:
                print(f"Error processing IPFIX packet from {addr[0]}: {e}")
                continue
    
    def start_all_collectors(self):
        """Start all collectors in separate threads"""
        netflow_thread = threading.Thread(target=self.start_netflow_collector, daemon=True)
        sflow_thread = threading.Thread(target=self.start_sflow_collector, daemon=True)
        ipfix_thread = threading.Thread(target=self.start_ipfix_collector, daemon=True)
        
        netflow_thread.start()
        sflow_thread.start()
        ipfix_thread.start()
        
        print("All traffic collectors started")
        print(f"  - NetFlow (v5/v9) on port {settings.NETFLOW_PORT}")
        print(f"  - sFlow (v5) on port {settings.SFLOW_PORT}")
        print(f"  - IPFIX on port {settings.IPFIX_PORT}")
        
        # Keep main thread alive
        netflow_thread.join()

def main():
    collector = TrafficCollector()
    collector.start_all_collectors()

if __name__ == "__main__":
    main()
