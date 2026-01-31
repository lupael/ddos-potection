"""
Traffic collector service for NetFlow/sFlow/IPFIX
"""
import socket
import struct
from typing import Dict, Any
import redis

from database import SessionLocal
from models.models import TrafficLog
from config import settings

class TrafficCollector:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )
    
    def parse_netflow_v5(self, data: bytes) -> Dict[str, Any]:
        """Parse NetFlow v5 packet"""
        # Simplified NetFlow v5 parsing
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
                'packets': flow_data[6],
                'bytes': flow_data[7],
                'protocol': flow_data[11]
            }
            flows.append(flow)
            offset += 48
        
        return {'version': version, 'count': count, 'flows': flows}
    
    def parse_sflow(self, data: bytes) -> Dict[str, Any]:
        """Parse sFlow packet"""
        # Simplified sFlow parsing
        # In production, use proper sFlow library
        return {'protocol': 'sflow', 'data': 'parsed'}
    
    def store_traffic(self, flow: Dict[str, Any], isp_id: int = 1):
        """
        Store traffic data in database
        
        Note: In production, isp_id should be determined from router source IP
        or a configuration mapping. Current default is for single-tenant testing.
        """
        db = SessionLocal()
        try:
            traffic_log = TrafficLog(
                isp_id=isp_id,
                source_ip=flow.get('src_ip'),
                dest_ip=flow.get('dst_ip'),
                protocol=self.get_protocol_name(flow.get('protocol', 0)),
                packets=flow.get('packets', 0),
                bytes=flow.get('bytes', 0),
                is_anomaly=False
            )
            db.add(traffic_log)
            db.commit()
            
            # Update Redis counters for real-time analysis
            key = f"traffic:{isp_id}:{flow.get('src_ip')}:{flow.get('protocol')}"
            self.redis_client.incr(key)
            self.redis_client.expire(key, 60)  # 1 minute TTL
            
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
        """Start NetFlow collector"""
        port = port or settings.NETFLOW_PORT
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to all interfaces to receive NetFlow data from routers
        # This is intentional and secured by Docker network isolation
        sock.bind(('0.0.0.0', port))
        
        print(f"NetFlow collector listening on port {port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(65535)
                flows_data = self.parse_netflow_v5(data)
                
                for flow in flows_data.get('flows', []):
                    self.store_traffic(flow)
                    
            except Exception as e:
                print(f"Error processing NetFlow packet: {e}")
                continue

def main():
    collector = TrafficCollector()
    collector.start_netflow_collector()

if __name__ == "__main__":
    main()
