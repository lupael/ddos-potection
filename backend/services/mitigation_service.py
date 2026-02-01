"""
Mitigation automation service
"""
import subprocess
import ipaddress
import os
import errno
from datetime import datetime

from database import SessionLocal
from models.models import MitigationAction, Alert
from config import settings

def validate_prefix(prefix: str) -> bool:
    """Validate that prefix is a valid IPv4 or IPv6 CIDR notation
    
    Args:
        prefix: IP prefix in CIDR notation (e.g., "192.0.2.1/32" or "2001:db8::1/128")
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Use ipaddress module for proper validation
        ipaddress.ip_network(prefix, strict=False)
        return True
    except (ValueError, AttributeError):
        return False

class MitigationService:
    def __init__(self):
        pass
    
    def apply_iptables_rule(self, action: str, ip: str, protocol: str = None) -> bool:
        """Apply iptables firewall rule"""
        try:
            if action == "block":
                cmd = ["iptables", "-A", "INPUT"]
                if protocol:
                    cmd.extend(["-p", protocol.lower()])
                cmd.extend(["-s", ip, "-j", "DROP"])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            
            elif action == "unblock":
                cmd = ["iptables", "-D", "INPUT"]
                if protocol:
                    cmd.extend(["-p", protocol.lower()])
                cmd.extend(["-s", ip, "-j", "DROP"])
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
                
        except Exception as e:
            print(f"Error applying iptables rule: {e}")
            return False
            return False
    
    def apply_nftables_rule(self, action: str, ip: str) -> bool:
        """Apply nftables firewall rule"""
        try:
            if action == "block":
                cmd = ["nft", "add", "rule", "inet", "filter", "input", "ip", "saddr", ip, "drop"]
            else:
                cmd = ["nft", "delete", "rule", "inet", "filter", "input", "ip", "saddr", ip, "drop"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error applying nftables rule: {e}")
            return False
    
    def mikrotik_block_ip(self, router_ip: str, username: str, password: str, 
                          target_ip: str, comment: str = "") -> bool:
        """Block IP via MikroTik RouterOS API"""
        try:
            # Using MikroTik REST API or RouterOS API
            # This is a simplified example
            from routeros_api import RouterOsApiPool
            
            connection = RouterOsApiPool(
                router_ip,
                username=username,
                password=password,
                plaintext_login=True
            )
            
            api = connection.get_api()
            
            # Add firewall rule
            firewall = api.get_resource('/ip/firewall/filter')
            firewall.add(
                chain='input',
                action='drop',
                src_address=target_ip,
                comment=comment or f'DDoS mitigation - {datetime.now()}'
            )
            
            connection.disconnect()
            return True
            
        except Exception as e:
            print(f"Error blocking IP on MikroTik: {e}")
            return False
    
    def announce_bgp_blackhole(self, prefix: str, nexthop: str = None) -> bool:
        """Announce BGP blackhole route (RTBH)
        
        Supports multiple BGP daemons: ExaBGP, FRR, BIRD
        See docs/BGP-RTBH.md for setup instructions
        """
        try:
            # Check if BGP is enabled
            bgp_enabled = getattr(settings, 'BGP_ENABLED', False)
            if not bgp_enabled:
                print("BGP blackholing is disabled. Set BGP_ENABLED=true in configuration.")
                return False
            
            # Use configured BGP daemon or default to ExaBGP
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            nexthop = nexthop or getattr(settings, 'BGP_BLACKHOLE_NEXTHOP', '192.0.2.1')
            
            if bgp_daemon == 'exabgp':
                return self._announce_exabgp(prefix, nexthop)
            elif bgp_daemon == 'frr':
                return self._announce_frr(prefix, nexthop)
            elif bgp_daemon == 'bird':
                return self._announce_bird(prefix, nexthop)
            else:
                print(f"Unknown BGP daemon: {bgp_daemon}")
                return False
                
        except Exception as e:
            print(f"Error announcing BGP blackhole: {e}")
            return False
    
    def _announce_exabgp(self, prefix: str, nexthop: str) -> bool:
        """Announce via ExaBGP"""
        try:
            # Validate prefix and nexthop to prevent command injection
            if not validate_prefix(prefix):
                print(f"ExaBGP error: Invalid prefix format: {prefix}")
                return False
            
            # Validate nexthop is a valid IP address
            try:
                ipaddress.ip_address(nexthop)
            except ValueError:
                print(f"ExaBGP error: Invalid nexthop format: {nexthop}")
                return False
            
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            community = getattr(settings, 'BGP_BLACKHOLE_COMMUNITY', '65535:666')
            
            # Use non-blocking open to avoid hanging if ExaBGP is not running
            try:
                fd = os.open(cmd_pipe, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    # Write validated command to ExaBGP pipe
                    command = f'announce route {prefix} next-hop {nexthop} community [{community}]\n'
                    os.write(fd, command.encode())
                    print(f"BGP blackhole announced via ExaBGP: {prefix} -> {nexthop}")
                    return True
                finally:
                    os.close(fd)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    print(f"ExaBGP error: No reader on pipe (ExaBGP not running?)")
                else:
                    print(f"ExaBGP error: Failed to write to pipe: {e}")
                return False
            
        except Exception as e:
            print(f"ExaBGP error: {e}")
            return False
    
    def _announce_frr(self, prefix: str, nexthop: str) -> bool:
        """Announce via FRR (Free Range Routing)
        
        Note: FRR uses route-maps to set the next-hop, so the nexthop parameter
        is not directly used. Configure next-hop in FRR's route-map instead.
        """
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"FRR error: Invalid prefix format: {prefix}")
                return False
            
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            # Add static route with tag 666 (matches route-map for RTBH)
            cmd = [
                vtysh_cmd,
                '-c', 'configure terminal',
                '-c', f'ip route {prefix} Null0 tag 666'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"BGP blackhole announced via FRR: {prefix}")
                return True
            else:
                print(f"FRR error: {result.stderr}")
                return False
        except Exception as e:
            print(f"FRR error: {e}")
            return False
    
    def _announce_bird(self, prefix: str, nexthop: str) -> bool:
        """Announce via BIRD
        
        Note: BIRD configures next-hop and communities via BGP protocol config,
        so the nexthop parameter is not directly used. Configure in BIRD config instead.
        """
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"BIRD error: Invalid prefix format: {prefix}")
                return False
            
            # Get BIRD configuration
            birdc_cmd = getattr(settings, 'BIRD_CMD', 'birdc')
            birdc_socket = getattr(settings, 'BIRD_CONTROL_SOCKET', None)
            
            # For BIRD, we need to add route dynamically using birdc
            # Note: This requires BIRD configuration to allow dynamic routes
            # via the blackhole_routes protocol
            # Using list form prevents shell injection
            cmd = [birdc_cmd]
            if birdc_socket:
                cmd.extend(['-s', birdc_socket])
            cmd.extend(['-r', 'add', 'route', prefix, 'blackhole'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'already exists' in result.stdout.lower():
                print(f"BGP blackhole announced via BIRD: {prefix}")
                return True
            else:
                print(f"BIRD error: {result.stderr}")
                return False
        except Exception as e:
            print(f"BIRD error: {e}")
            return False
    
    def withdraw_bgp_blackhole(self, prefix: str) -> bool:
        """Withdraw BGP blackhole route
        
        Removes previously announced blackhole route
        See docs/BGP-RTBH.md for details
        """
        try:
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            
            if bgp_daemon == 'exabgp':
                return self._withdraw_exabgp(prefix)
            elif bgp_daemon == 'frr':
                return self._withdraw_frr(prefix)
            elif bgp_daemon == 'bird':
                return self._withdraw_bird(prefix)
            else:
                return False
                
        except Exception as e:
            print(f"Error withdrawing BGP blackhole: {e}")
            return False
    
    def _withdraw_exabgp(self, prefix: str) -> bool:
        """Withdraw via ExaBGP"""
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"ExaBGP error: Invalid prefix format: {prefix}")
                return False
            
            # Check for control characters
            if any(ord(ch) < 32 for ch in prefix):
                print(f"ExaBGP error: Prefix contains control characters: {prefix!r}")
                return False
            
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            
            # Use non-blocking open to avoid hanging if ExaBGP is not running
            try:
                fd = os.open(cmd_pipe, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    command = f'withdraw route {prefix}\n'
                    os.write(fd, command.encode())
                    print(f"BGP blackhole withdrawn via ExaBGP: {prefix}")
                    return True
                finally:
                    os.close(fd)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    print(f"ExaBGP error: No reader on pipe (ExaBGP not running?)")
                else:
                    print(f"ExaBGP error: Failed to write to pipe: {e}")
                return False
                
        except Exception as e:
            print(f"ExaBGP withdrawal error: {e}")
            return False
    
    def _withdraw_frr(self, prefix: str) -> bool:
        """Withdraw via FRR"""
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"FRR error: Invalid prefix format: {prefix}")
                return False
            
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            cmd = [
                vtysh_cmd,
                '-c', 'configure terminal',
                '-c', f'no ip route {prefix} Null0 tag 666'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"BGP blackhole withdrawn via FRR: {prefix}")
                return True
            else:
                print(f"FRR withdrawal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"FRR withdrawal error: {e}")
            return False
    
    def _withdraw_bird(self, prefix: str) -> bool:
        """Withdraw via BIRD"""
        try:
            # Validate prefix to prevent command injection
            if not validate_prefix(prefix):
                print(f"BIRD error: Invalid prefix format: {prefix}")
                return False
            
            # Get BIRD configuration
            birdc_cmd = getattr(settings, 'BIRD_CMD', 'birdc')
            birdc_socket = getattr(settings, 'BIRD_CONTROL_SOCKET', None)
            
            # Remove the route dynamically using birdc
            # Using list form prevents shell injection
            cmd = [birdc_cmd]
            if birdc_socket:
                cmd.extend(['-s', birdc_socket])
            cmd.extend(['-r', 'delete', 'route', prefix])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'not found' in result.stdout.lower():
                print(f"BGP blackhole withdrawn via BIRD: {prefix}")
                return True
            else:
                print(f"BIRD withdrawal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"BIRD withdrawal error: {e}")
            return False
    
    def send_flowspec_rule(self, source: str = None, dest: str = None, 
                          protocol: str = None, action: str = "drop",
                          source_port: int = None, dest_port: int = None,
                          packet_length: str = None, dscp: int = None,
                          fragment: str = None, tcp_flags: str = None) -> bool:
        """Send FlowSpec announcement to BGP daemon
        
        Args:
            source: Source IP prefix (CIDR notation, e.g., "192.0.2.0/24")
            dest: Destination IP prefix (CIDR notation)
            protocol: IP protocol (tcp, udp, icmp, or protocol number)
            action: Action to take (drop, rate-limit)
            source_port: Source port number or range
            dest_port: Destination port number or range
            packet_length: Packet length (e.g., ">=64&<=128")
            dscp: DSCP value
            fragment: Fragment type (not-a-fragment, is-fragment, first-fragment, last-fragment)
            tcp_flags: TCP flags (syn, ack, fin, rst, push, urgent)
        
        Returns:
            True if successful, False otherwise
        
        Note:
            FlowSpec requires BGP FlowSpec-capable routers and upstream support.
            See RFC 5575 for FlowSpec specification.
        """
        try:
            # Check if BGP is enabled
            bgp_enabled = getattr(settings, 'BGP_ENABLED', False)
            if not bgp_enabled:
                print("FlowSpec is disabled. Set BGP_ENABLED=true in configuration.")
                return False
            
            # Validate inputs to prevent injection
            if source and not validate_prefix(source):
                print(f"FlowSpec error: Invalid source prefix: {source}")
                return False
            if dest and not validate_prefix(dest):
                print(f"FlowSpec error: Invalid destination prefix: {dest}")
                return False
            
            # Get BGP daemon
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            
            if bgp_daemon == 'exabgp':
                return self._send_flowspec_exabgp(
                    source, dest, protocol, action, source_port, dest_port,
                    packet_length, dscp, fragment, tcp_flags
                )
            elif bgp_daemon == 'frr':
                return self._send_flowspec_frr(
                    source, dest, protocol, action, source_port, dest_port
                )
            elif bgp_daemon == 'bird':
                print("FlowSpec is not yet implemented for BIRD daemon")
                return False
            else:
                print(f"Unknown BGP daemon: {bgp_daemon}")
                return False
            
        except Exception as e:
            print(f"Error sending FlowSpec rule: {e}")
            return False
    
    def _send_flowspec_exabgp(self, source: str, dest: str, protocol: str,
                              action: str, source_port: int, dest_port: int,
                              packet_length: str, dscp: int, fragment: str,
                              tcp_flags: str) -> bool:
        """Send FlowSpec via ExaBGP"""
        try:
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            
            # Build FlowSpec rule
            flow_parts = []
            
            # Destination prefix (required)
            if dest:
                flow_parts.append(f"destination {dest}")
            else:
                print("FlowSpec error: Destination prefix is required")
                return False
            
            # Source prefix (optional)
            if source:
                flow_parts.append(f"source {source}")
            
            # Protocol (optional)
            if protocol:
                # Map protocol names to numbers
                protocol_map = {
                    'tcp': '6',
                    'udp': '17',
                    'icmp': '1',
                    'gre': '47',
                    'esp': '50',
                    'ah': '51'
                }
                proto_key = protocol.lower()
                if proto_key in protocol_map:
                    proto_num = protocol_map[proto_key]
                else:
                    try:
                        proto_int = int(protocol)
                    except (TypeError, ValueError):
                        print(f"FlowSpec error: Invalid protocol value '{protocol}'")
                        return False
                    if proto_int < 0 or proto_int > 255:
                        print(f"FlowSpec error: Protocol number out of range (0-255): {proto_int}")
                        return False
                    proto_num = str(proto_int)
                flow_parts.append(f"protocol [ ={proto_num} ]")
            
            # Port specifications
            if source_port:
                try:
                    port_int = int(source_port)
                    if port_int < 1 or port_int > 65535:
                        print(f"FlowSpec error: Source port out of range (1-65535): {port_int}")
                        return False
                    flow_parts.append(f"source-port [ ={port_int} ]")
                except (TypeError, ValueError):
                    print(f"FlowSpec error: Invalid source port '{source_port}'")
                    return False
            if dest_port:
                try:
                    port_int = int(dest_port)
                    if port_int < 1 or port_int > 65535:
                        print(f"FlowSpec error: Destination port out of range (1-65535): {port_int}")
                        return False
                    flow_parts.append(f"destination-port [ ={port_int} ]")
                except (TypeError, ValueError):
                    print(f"FlowSpec error: Invalid destination port '{dest_port}'")
                    return False
            
            # Packet length
            if packet_length:
                # Validate packet_length contains only safe characters
                import re
                if not re.match(r'^[<>=&0-9\s]+$', str(packet_length)):
                    print(f"FlowSpec error: Invalid packet_length format '{packet_length}'")
                    return False
                flow_parts.append(f"packet-length [ {packet_length} ]")
            
            # DSCP
            if dscp is not None:
                try:
                    dscp_int = int(dscp)
                except (TypeError, ValueError):
                    print("FlowSpec error: DSCP must be an integer between 0 and 63")
                    return False

                if dscp_int < 0 or dscp_int > 63:
                    print("FlowSpec error: DSCP must be in the range 0-63")
                    return False

                flow_parts.append(f"dscp [ ={dscp_int} ]")
            
            # Fragment
            if fragment:
                fragment_map = {
                    'not-a-fragment': 'not-a-fragment',
                    'is-fragment': 'is-fragment',
                    'first-fragment': 'first-fragment',
                    'last-fragment': 'last-fragment'
                }
                if fragment in fragment_map:
                    flow_parts.append(f"fragment [ {fragment_map[fragment]} ]")
                else:
                    print(f"FlowSpec warning: Invalid fragment type '{fragment}' ignored")
            
            # TCP flags
            if tcp_flags:
                allowed_tcp_flags = {"syn", "ack", "fin", "rst", "push", "urgent"}
                sanitized_flags = []
                # Support values separated by spaces and/or commas
                for flag in str(tcp_flags).replace(",", " ").split():
                    normalized_flag = flag.lower()
                    if normalized_flag in allowed_tcp_flags:
                        sanitized_flags.append(normalized_flag)
                    else:
                        print(f"FlowSpec warning: Invalid TCP flag '{flag}' ignored")
                if sanitized_flags:
                    flow_parts.append(f"tcp-flags [ {' '.join(sanitized_flags)} ]")
            
            # Build command
            flow_rule = " ".join(flow_parts)
            
            # Action (community or rate-limit extended community)
            if action == "drop":
                # Use traffic-rate 0 for drop
                action_spec = "rate-limit 0"
            elif action.startswith("rate-limit"):
                # Validate and extract rate
                import re
                match = re.match(r'^rate-limit\s+(\d+)$', action)
                if match:
                    rate_value = match.group(1)
                    action_spec = f"rate-limit {rate_value}"
                else:
                    print(f"FlowSpec error: Invalid action format '{action}'")
                    return False
            else:
                action_spec = "rate-limit 0"
            
            # Use non-blocking write
            try:
                fd = os.open(cmd_pipe, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    command = f"announce flow route {flow_rule} {action_spec}\n"
                    os.write(fd, command.encode())
                    print(f"FlowSpec rule announced via ExaBGP: {flow_rule}")
                    return True
                finally:
                    os.close(fd)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    print("FlowSpec error: ExaBGP not running")
                else:
                    print(f"FlowSpec error: Failed to write to pipe: {e}")
                return False
            
        except Exception as e:
            print(f"FlowSpec ExaBGP error: {e}")
            return False
    
    def _send_flowspec_frr(self, source: str, dest: str, protocol: str,
                           action: str, source_port: int, dest_port: int) -> bool:
        """Send FlowSpec via FRR
        
        Note: FRR FlowSpec support requires BGP flowspec address-family configuration
        """
        try:
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            # Build FRR flowspec command
            cmd_parts = ['configure terminal', 'router bgp']
            
            # FRR FlowSpec syntax
            flowspec_cmd = 'flowspec'
            if dest:
                flowspec_cmd += f' destination-prefix {dest}'
            if source:
                flowspec_cmd += f' source-prefix {source}'
            if protocol:
                protocol_map = {'tcp': '6', 'udp': '17', 'icmp': '1'}
                mapped_proto = protocol_map.get(protocol.lower())
                if mapped_proto is not None:
                    proto_num = mapped_proto
                else:
                    try:
                        proto_int = int(protocol)
                    except (TypeError, ValueError):
                        print(f"Invalid protocol value for FlowSpec: {protocol}")
                        return False
                    if proto_int < 0 or proto_int > 255:
                        print(f"Protocol number out of valid range (0-255) for FlowSpec: {proto_int}")
                        return False
                    proto_num = str(proto_int)
                flowspec_cmd += f' protocol {proto_num}'
            if dest_port:
                try:
                    port_int = int(dest_port)
                    if port_int < 1 or port_int > 65535:
                        print(f"Destination port out of range (1-65535): {port_int}")
                        return False
                    flowspec_cmd += f' destination-port {port_int}'
                except (TypeError, ValueError):
                    print(f"Invalid destination port: {dest_port}")
                    return False
            if source_port:
                try:
                    port_int = int(source_port)
                    if port_int < 1 or port_int > 65535:
                        print(f"Source port out of range (1-65535): {port_int}")
                        return False
                    flowspec_cmd += f' source-port {port_int}'
                except (TypeError, ValueError):
                    print(f"Invalid source port: {source_port}")
                    return False
            
            # Action
            if action == "drop":
                flowspec_cmd += ' rate-limit 0'
            
            cmd_parts.append(flowspec_cmd)
            
            # Build command
            cmd = [vtysh_cmd]
            for part in cmd_parts:
                cmd.extend(['-c', part])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"FlowSpec rule announced via FRR")
                return True
            else:
                print(f"FRR FlowSpec error: {result.stderr}")
                return False
            
        except Exception as e:
            print(f"FRR FlowSpec error: {e}")
            return False
    
    def withdraw_flowspec_rule(self, source: str = None, dest: str = None,
                               protocol: str = None) -> bool:
        """Withdraw FlowSpec rule
        
        Args:
            source: Source IP prefix
            dest: Destination IP prefix
            protocol: IP protocol
        
        Returns:
            True if successful, False otherwise
        """
        try:
            bgp_daemon = getattr(settings, 'BGP_DAEMON', 'exabgp')
            
            if bgp_daemon == 'exabgp':
                return self._withdraw_flowspec_exabgp(source, dest, protocol)
            elif bgp_daemon == 'frr':
                return self._withdraw_flowspec_frr(source, dest, protocol)
            else:
                print(f"FlowSpec withdrawal not implemented for {bgp_daemon}")
                return False
        except Exception as e:
            print(f"Error withdrawing FlowSpec rule: {e}")
            return False
    
    def _withdraw_flowspec_exabgp(self, source: str, dest: str, protocol: str) -> bool:
        """Withdraw FlowSpec via ExaBGP"""
        try:
            cmd_pipe = getattr(settings, 'EXABGP_CMD_PIPE', '/var/run/exabgp.cmd')
            
            # Build withdrawal command
            flow_parts = []
            if dest:
                flow_parts.append(f"destination {dest}")
            if source:
                flow_parts.append(f"source {source}")
            if protocol:
                protocol_map = {'tcp': '6', 'udp': '17', 'icmp': '1'}
                proto_num = protocol_map.get(protocol.lower(), protocol)
                flow_parts.append(f"protocol [ ={proto_num} ]")
            
            flow_rule = " ".join(flow_parts)
            
            try:
                fd = os.open(cmd_pipe, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    command = f"withdraw flow route {flow_rule}\n"
                    os.write(fd, command.encode())
                    print(f"FlowSpec rule withdrawn via ExaBGP")
                    return True
                finally:
                    os.close(fd)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    print("FlowSpec error: ExaBGP not running")
                else:
                    print(f"FlowSpec error: {e}")
                return False
            
        except Exception as e:
            print(f"FlowSpec ExaBGP withdrawal error: {e}")
            return False
    
    def _withdraw_flowspec_frr(self, source: str, dest: str, protocol: str) -> bool:
        """Withdraw FlowSpec via FRR"""
        try:
            vtysh_cmd = getattr(settings, 'FRR_VTYSH_CMD', '/usr/bin/vtysh')
            
            # Build FRR flowspec withdrawal command
            flowspec_cmd = 'no flowspec'
            if dest:
                flowspec_cmd += f' destination-prefix {dest}'
            if source:
                flowspec_cmd += f' source-prefix {source}'
            
            cmd = [
                vtysh_cmd,
                '-c', 'configure terminal',
                '-c', 'router bgp',
                '-c', flowspec_cmd
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"FlowSpec rule withdrawn via FRR")
                return True
            else:
                print(f"FRR FlowSpec withdrawal error: {result.stderr}")
                return False
            
        except Exception as e:
            print(f"FRR FlowSpec withdrawal error: {e}")
            return False
    
    def apply_rate_limit(self, ip: str, rate: str = "1000/s") -> bool:
        """Apply rate limiting using tc (traffic control)"""
        try:
            # Using Linux tc for rate limiting
            cmd = [
                "tc", "filter", "add", "dev", "eth0", "protocol", "ip",
                "parent", "1:0", "prio", "1", "u32",
                "match", "ip", "src", ip,
                "police", "rate", rate, "burst", "100k", "drop"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error applying rate limit: {e}")
            return False
    
    def auto_mitigate_alert(self, alert_id: int) -> bool:
        """Automatically mitigate an alert"""
        db = SessionLocal()
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            # Determine mitigation strategy based on alert type
            if alert.alert_type in ['syn_flood', 'udp_flood']:
                # Block source IP
                success = self.apply_iptables_rule('block', alert.source_ip)
                
                if success:
                    mitigation = MitigationAction(
                        alert_id=alert.id,
                        action_type='firewall',
                        details={'rule': 'iptables', 'ip': alert.source_ip, 'action': 'block'},
                        status='active'
                    )
                    db.add(mitigation)
                    alert.status = 'mitigated'
                    db.commit()
                    return True
            
            elif alert.alert_type == 'dns_amplification':
                # Rate limit UDP/53
                success = self.apply_rate_limit(alert.source_ip, '100/s')
                
                if success:
                    mitigation = MitigationAction(
                        alert_id=alert.id,
                        action_type='rate_limit',
                        details={'ip': alert.source_ip, 'rate': '100/s'},
                        status='active'
                    )
                    db.add(mitigation)
                    alert.status = 'mitigated'
                    db.commit()
                    return True
            
            return False
            
        finally:
            db.close()

def main():
    MitigationService()
    print("Mitigation service initialized")

if __name__ == "__main__":
    main()
