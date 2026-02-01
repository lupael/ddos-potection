"""
Packet capture service supporting PCAP, AF_PACKET, and AF_XDP
Includes VLAN untagging and attack fingerprint capture
"""
import socket
import struct
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
import redis
import json
import logging

logger = logging.getLogger(__name__)

try:
    from scapy.all import wrpcap, Ether
    from scapy.layers.dot1q import Dot1Q
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("Scapy not available. PCAP features will be limited.")

from config import settings
from database import SessionLocal

# AF_PACKET constants for Linux raw sockets
if hasattr(socket, 'AF_PACKET'):
    AF_PACKET = socket.AF_PACKET
    ETH_P_ALL = 0x0003  # All protocols
else:
    AF_PACKET = None
    ETH_P_ALL = None


class PacketCaptureService:
    """Service for advanced packet capture and fingerprinting"""
    
    def __init__(self, capture_dir: Optional[str] = None):
        """
        Initialize packet capture service
        
        Args:
            capture_dir: Directory to store PCAP files. If not provided,
                defaults to settings.PCAP_DIR, with a fallback to the
                legacy path "/var/lib/ddos-protection/pcaps".
        """
        default_capture_dir = getattr(settings, "PCAP_DIR", "/var/lib/ddos-protection/pcaps")
        effective_capture_dir = capture_dir or default_capture_dir
        self.capture_dir = Path(effective_capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False
        )
        
        # Capture state
        self.capturing = {}
        self.capture_threads = {}
        self.packet_buffers = {}
        
        # Configuration
        self.max_packets_per_file = getattr(settings, 'PCAP_MAX_PACKETS', 10000)
        self.vlan_untagging_enabled = getattr(settings, 'VLAN_UNTAGGING_ENABLED', True)
        
        logger.info(f"PacketCaptureService initialized. PCAP directory: {self.capture_dir}")
        if not SCAPY_AVAILABLE:
            logger.warning("Scapy not available. PCAP features will be limited.")
    
    def untag_vlan(self, packet_data: bytes) -> bytes:
        """
        Remove VLAN tags from Ethernet frame
        
        Args:
            packet_data: Raw packet bytes
            
        Returns:
            Packet data with VLAN tags removed
        """
        if len(packet_data) < 18:  # Minimum Ethernet + VLAN header
            return packet_data
        
        # Check for VLAN tag (0x8100)
        ether_type = struct.unpack('!H', packet_data[12:14])[0]
        
        if ether_type == 0x8100:  # 802.1Q VLAN tag
            # Remove VLAN tag (4 bytes: 2 for tag, 2 for TCI)
            # Keep destination MAC (6) + source MAC (6) + new ethertype (2)
            return packet_data[:12] + packet_data[16:]
        
        # Check for double VLAN tag (0x88a8 or 0x9100)
        if ether_type in (0x88a8, 0x9100):  # 802.1ad (QinQ)
            # Remove both VLAN tags (8 bytes total)
            if len(packet_data) >= 22:
                return packet_data[:12] + packet_data[20:]
        
        return packet_data
    
    def start_pcap_capture(self, interface: str, filter_bpf: str = "", 
                          duration: int = 60, target_ip: Optional[str] = None) -> str:
        """
        Start PCAP capture on network interface
        
        Args:
            interface: Network interface name (e.g., 'eth0')
            filter_bpf: BPF filter string (e.g., 'tcp and port 80')
            duration: Capture duration in seconds
            target_ip: Optional target IP for focused capture
            
        Returns:
            Capture ID (filename stem)
        """
        if not SCAPY_AVAILABLE:
            raise RuntimeError("Scapy not available for PCAP capture")
        
        from scapy.all import sniff
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        capture_id = f"capture_{timestamp}"
        if target_ip:
            capture_id = f"capture_{target_ip}_{timestamp}"
        
        pcap_file = self.capture_dir / f"{capture_id}.pcap"
        
        def capture_worker():
            try:
                logger.info(f"Starting PCAP capture on {interface} for {duration}s")
                logger.info(f"Filter: {filter_bpf if filter_bpf else 'none'}")
                
                packets = sniff(
                    iface=interface,
                    filter=filter_bpf,
                    timeout=duration,
                    count=self.max_packets_per_file
                )
                
                # Apply VLAN untagging if enabled
                if self.vlan_untagging_enabled:
                    cleaned_packets = []
                    for pkt in packets:
                        # Remove all stacked VLAN layers (handles 802.1Q and 802.1ad)
                        while pkt.haslayer(Dot1Q):
                            pkt = pkt[Dot1Q].payload
                        cleaned_packets.append(pkt)
                    packets = cleaned_packets
                
                wrpcap(str(pcap_file), packets)
                print(f"Captured {len(packets)} packets to {pcap_file}")
                
                self.capturing[capture_id] = False
                
            except Exception as e:
                print(f"Error in PCAP capture: {e}")
                self.capturing[capture_id] = False
        
        self.capturing[capture_id] = True
        thread = threading.Thread(target=capture_worker, daemon=True)
        thread.start()
        self.capture_threads[capture_id] = thread
        
        return capture_id
    
    def start_af_packet_capture(self, interface: str, duration: int = 60) -> str:
        """
        Start AF_PACKET raw socket capture (Linux only)
        High-performance packet capture bypassing kernel networking stack
        
        Args:
            interface: Network interface name
            duration: Capture duration in seconds
            
        Returns:
            Capture ID
        """
        if AF_PACKET is None:
            raise RuntimeError("AF_PACKET not supported on this platform (Linux only)")
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        capture_id = f"af_packet_{timestamp}"
        pcap_file = self.capture_dir / f"{capture_id}.pcap"
        
        def capture_worker():
            try:
                # Create raw AF_PACKET socket
                sock = socket.socket(AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
                sock.bind((interface, ETH_P_ALL))
                sock.settimeout(1.0)  # 1 second timeout for checking stop condition
                
                packets = []
                start_time = datetime.now(timezone.utc)
                
                print(f"Starting AF_PACKET capture on {interface} for {duration}s")
                
                while (datetime.now(timezone.utc) - start_time).total_seconds() < duration:
                    if not self.capturing.get(capture_id, False):
                        break
                    
                    try:
                        data = sock.recv(65535)
                        
                        # Apply VLAN untagging if enabled
                        if self.vlan_untagging_enabled:
                            data = self.untag_vlan(data)
                        
                        # Convert to Scapy packet for PCAP writing
                        if SCAPY_AVAILABLE:
                            pkt = Ether(data)
                            packets.append(pkt)
                        else:
                            # Store raw bytes if scapy not available
                            packets.append(data)
                        
                        if len(packets) >= self.max_packets_per_file:
                            break
                            
                    except socket.timeout:
                        continue
                
                sock.close()
                
                # Write to PCAP
                if SCAPY_AVAILABLE and packets:
                    wrpcap(str(pcap_file), packets)
                    print(f"AF_PACKET captured {len(packets)} packets to {pcap_file}")
                
                self.capturing[capture_id] = False
                
            except Exception as e:
                print(f"Error in AF_PACKET capture: {e}")
                self.capturing[capture_id] = False
        
        self.capturing[capture_id] = True
        thread = threading.Thread(target=capture_worker, daemon=True)
        thread.start()
        self.capture_threads[capture_id] = thread
        
        return capture_id
    
    def start_af_xdp_capture(self, interface: str, duration: int = 60) -> str:
        """
        Start AF_XDP (Express Data Path) capture
        Ultra-high-performance packet processing using eBPF
        
        Note: Requires libxdp and proper kernel support (Linux 4.18+)
        This is a placeholder implementation that falls back to AF_PACKET
        For production, integrate with python-xdp or similar library
        
        Args:
            interface: Network interface name
            duration: Capture duration in seconds
            
        Returns:
            Capture ID
        """
        print("AF_XDP capture requested - falling back to AF_PACKET")
        print("For full AF_XDP support, install libxdp and configure kernel")
        
        # Fallback to AF_PACKET for now
        # In production, this would use AF_XDP socket with UMEM rings
        capture_id = self.start_af_packet_capture(interface, duration)
        
        return capture_id
    
    def capture_attack_fingerprint(self, alert_id: int, target_ip: str, 
                                   attack_type: str, duration: int = 30) -> Optional[str]:
        """
        Capture attack fingerprint in PCAP format
        Records packets associated with an attack for analysis
        
        Args:
            alert_id: Alert ID triggering the capture
            target_ip: Target IP address under attack
            attack_type: Type of attack (syn_flood, udp_flood, etc.)
            duration: Capture duration in seconds
            
        Returns:
            Path to PCAP file or None if capture failed
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            capture_id = f"fingerprint_{attack_type}_{target_ip}_{timestamp}"
            pcap_file = self.capture_dir / f"{capture_id}.pcap"
            
            # Build BPF filter based on attack type and target
            if attack_type == 'syn_flood':
                filter_bpf = f"dst host {target_ip} and tcp[tcpflags] & tcp-syn != 0"
            elif attack_type == 'udp_flood':
                filter_bpf = f"dst host {target_ip} and udp"
            elif attack_type == 'icmp_flood':
                filter_bpf = f"dst host {target_ip} and icmp"
            else:
                filter_bpf = f"dst host {target_ip}"
            
            # Start capture with target-specific filter
            if SCAPY_AVAILABLE:
                from scapy.all import sniff
                
                logger.info(f"Capturing attack fingerprint for {attack_type} on {target_ip}")
                
                packets = sniff(
                    filter=filter_bpf,
                    timeout=duration,
                    count=self.max_packets_per_file
                )
                
                # Apply VLAN untagging - remove all stacked VLAN layers
                if self.vlan_untagging_enabled:
                    cleaned_packets = []
                    for pkt in packets:
                        # Remove all stacked VLAN layers (handles 802.1Q and 802.1ad)
                        while pkt.haslayer(Dot1Q):
                            pkt = pkt[Dot1Q].payload
                        cleaned_packets.append(pkt)
                    packets = cleaned_packets
                
                wrpcap(str(pcap_file), packets)
                logger.info(f"Captured attack fingerprint: {len(packets)} packets -> {pcap_file}")
                
                # Store metadata in Redis
                metadata = {
                    'alert_id': alert_id,
                    'target_ip': target_ip,
                    'attack_type': attack_type,
                    'timestamp': timestamp,
                    'packet_count': len(packets),
                    'pcap_file': str(pcap_file)
                }
                self.redis_client.setex(
                    f"fingerprint:{alert_id}",
                    86400,  # 24 hours
                    json.dumps(metadata)
                )
                
                return str(pcap_file)
            else:
                logger.warning("Scapy not available - cannot capture fingerprint")
                return None
                
        except Exception as e:
            print(f"Error capturing attack fingerprint: {e}")
            return None
    
    def stop_capture(self, capture_id: str) -> bool:
        """
        Stop an ongoing packet capture
        
        Args:
            capture_id: Capture ID to stop
            
        Returns:
            True if stopped successfully
        """
        if capture_id in self.capturing:
            self.capturing[capture_id] = False
            
            # Wait for thread to finish
            if capture_id in self.capture_threads:
                thread = self.capture_threads[capture_id]
                thread.join(timeout=5.0)
                del self.capture_threads[capture_id]
            
            del self.capturing[capture_id]
            return True
        
        return False
    
    def get_capture_status(self, capture_id: str) -> Dict[str, Any]:
        """
        Get status of a capture
        
        Args:
            capture_id: Capture ID
            
        Returns:
            Status dictionary
        """
        pcap_file = self.capture_dir / f"{capture_id}.pcap"
        
        return {
            'capture_id': capture_id,
            'active': self.capturing.get(capture_id, False),
            'pcap_file': str(pcap_file) if pcap_file.exists() else None,
            'file_size': pcap_file.stat().st_size if pcap_file.exists() else 0
        }
    
    def list_captures(self) -> List[Dict[str, Any]]:
        """
        List all PCAP captures
        
        Returns:
            List of capture information
        """
        captures = []
        
        for pcap_file in self.capture_dir.glob("*.pcap"):
            stat = pcap_file.stat()
            captures.append({
                'filename': pcap_file.name,
                'path': str(pcap_file),
                'size_bytes': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            })
        
        return sorted(captures, key=lambda x: x['created'], reverse=True)
    
    def cleanup_old_captures(self, max_age_days: int = 7) -> int:
        """
        Clean up old PCAP files
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
        
        for pcap_file in self.capture_dir.glob("*.pcap"):
            if pcap_file.stat().st_mtime < cutoff_time:
                try:
                    pcap_file.unlink()
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {pcap_file}: {e}")
        
        return deleted


# Module-level singleton
_packet_capture_service = None

def get_packet_capture_service() -> PacketCaptureService:
    """Get or create packet capture service singleton"""
    global _packet_capture_service
    if _packet_capture_service is None:
        _packet_capture_service = PacketCaptureService()
    return _packet_capture_service
