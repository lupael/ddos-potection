"""
SNMP trap sender for NMS integration (Zabbix/Nagios).
Sends SNMPv2c traps for attack-start and attack-end events.
"""
import logging
import socket
import struct
import time
from typing import Dict

from config import settings

logger = logging.getLogger(__name__)

try:
    from pysnmp.hlapi import (  # type: ignore
        CommunityData,
        ContextData,
        NotificationType,
        ObjectIdentity,
        ObjectType,
        OctetString,
        Integer,
        UdpTransportTarget,
        sendNotification,
        SnmpEngine,
    )
    _PYSNMP_AVAILABLE = True
except ImportError:
    _PYSNMP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Minimal BER/SNMPv2c encoder (used when pysnmp is not available)
# ---------------------------------------------------------------------------

def _ber_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    encoded = []
    while n:
        encoded.append(n & 0xFF)
        n >>= 8
    encoded.reverse()
    return bytes([0x80 | len(encoded)] + encoded)


def _ber_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _ber_length(len(value)) + value


def _ber_integer(value: int) -> bytes:
    if value == 0:
        return _ber_tlv(0x02, b"\x00")
    result = []
    n = value
    while n:
        result.append(n & 0xFF)
        n >>= 8
    result.reverse()
    if result[0] & 0x80:
        result.insert(0, 0x00)
    return _ber_tlv(0x02, bytes(result))


def _ber_octet_string(value: str) -> bytes:
    return _ber_tlv(0x04, value.encode("utf-8", errors="replace"))


def _ber_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.split(".")]
    if len(parts) < 2:
        raise ValueError(f"Invalid OID: {oid}")
    encoded = bytes([40 * parts[0] + parts[1]])
    for part in parts[2:]:
        if part == 0:
            encoded += b"\x00"
        else:
            septets = []
            n = part
            while n:
                septets.append(n & 0x7F)
                n >>= 7
            septets.reverse()
            encoded += bytes(
                [(s | 0x80) if i < len(septets) - 1 else s for i, s in enumerate(septets)]
            )
    return _ber_tlv(0x06, encoded)


def _build_snmpv2c_trap(
    community: str,
    enterprise_oid: str,
    varbinds: Dict[str, str],
) -> bytes:
    """Build a minimal SNMPv2c Trap PDU (no pysnmp required)."""
    version = _ber_integer(1)  # SNMPv2c = 1
    comm = _ber_octet_string(community)

    # Build varbind list
    varbind_seq_items = b""
    sys_uptime_oid = "1.3.6.1.2.1.1.3.0"
    snmp_trap_oid_oid = "1.3.6.1.6.3.1.1.4.1.0"

    uptime_val = _ber_tlv(0x43, struct.pack("!I", int(time.monotonic() * 100) & 0xFFFFFFFF))
    uptime_vb = _ber_tlv(0x30, _ber_oid(sys_uptime_oid) + uptime_val)

    trap_oid_val = _ber_oid(enterprise_oid)
    trap_oid_vb = _ber_tlv(0x30, _ber_oid(snmp_trap_oid_oid) + trap_oid_val)

    varbind_seq_items += uptime_vb + trap_oid_vb

    for oid, val in varbinds.items():
        vb = _ber_tlv(0x30, _ber_oid(oid) + _ber_octet_string(str(val)))
        varbind_seq_items += vb

    varbind_list = _ber_tlv(0x30, varbind_seq_items)

    # Trap PDU (SNMPv2 Trap = 0xA7)
    request_id = _ber_integer(int(time.time()) & 0x7FFFFFFF)
    error_status = _ber_integer(0)
    error_index = _ber_integer(0)
    pdu = _ber_tlv(0xA7, request_id + error_status + error_index + varbind_list)

    message = _ber_tlv(0x30, version + comm + pdu)
    return message


class SNMPTrapSender:
    """Sends SNMPv2c traps to the configured NMS."""

    def __init__(self):
        self.enabled = settings.SNMP_ENABLED
        self.manager_host = settings.SNMP_MANAGER_HOST
        self.manager_port = settings.SNMP_MANAGER_PORT
        self.community = settings.SNMP_COMMUNITY
        self.enterprise_oid = settings.SNMP_ENTERPRISE_OID

    def send_trap(self, trap_type: str, varbinds: Dict[str, str]) -> bool:
        """Send an SNMPv2c trap to the NMS manager."""
        if not self.enabled or not self.manager_host:
            logger.debug("SNMP traps disabled or manager host not configured")
            return False

        # Build OID for the specific trap type
        trap_oid = f"{self.enterprise_oid}.1"
        if trap_type == "attack_start":
            trap_oid = f"{self.enterprise_oid}.1.1"
        elif trap_type == "attack_end":
            trap_oid = f"{self.enterprise_oid}.1.2"

        if _PYSNMP_AVAILABLE:
            return self._send_via_pysnmp(trap_oid, varbinds)
        return self._send_via_socket(trap_oid, varbinds)

    def _send_via_pysnmp(self, trap_oid: str, varbinds: Dict[str, str]) -> bool:
        try:
            var_bind_objects = [
                ObjectType(ObjectIdentity(oid), OctetString(str(val)))
                for oid, val in varbinds.items()
            ]
            error_indication, error_status, _, _ = next(
                sendNotification(
                    SnmpEngine(),
                    CommunityData(self.community),
                    UdpTransportTarget((self.manager_host, self.manager_port)),
                    ContextData(),
                    "trap",
                    NotificationType(ObjectIdentity(trap_oid)).addVarBinds(*var_bind_objects),
                )
            )
            if error_indication:
                logger.error("pysnmp error: %s", error_indication)
                return False
            return True
        except Exception as exc:
            logger.error("Failed to send SNMP trap via pysnmp: %s", exc)
            return False

    def _send_via_socket(self, trap_oid: str, varbinds: Dict[str, str]) -> bool:
        try:
            packet = _build_snmpv2c_trap(self.community, trap_oid, varbinds)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(packet, (self.manager_host, self.manager_port))
            logger.info("SNMP trap sent to %s:%d", self.manager_host, self.manager_port)
            return True
        except Exception as exc:
            logger.error("Failed to send SNMP trap via socket: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def send_attack_start_trap(
        self,
        source_ip: str,
        target_ip: str,
        attack_type: str,
        pps: int,
    ) -> bool:
        """Send a trap signalling the start of an attack."""
        varbinds = {
            f"{self.enterprise_oid}.2.1": source_ip,
            f"{self.enterprise_oid}.2.2": target_ip,
            f"{self.enterprise_oid}.2.3": attack_type,
            f"{self.enterprise_oid}.2.4": str(pps),
        }
        return self.send_trap("attack_start", varbinds)

    def send_attack_end_trap(
        self,
        source_ip: str,
        target_ip: str,
        duration_seconds: int,
    ) -> bool:
        """Send a trap signalling the end of an attack."""
        varbinds = {
            f"{self.enterprise_oid}.2.1": source_ip,
            f"{self.enterprise_oid}.2.2": target_ip,
            f"{self.enterprise_oid}.2.5": str(duration_seconds),
        }
        return self.send_trap("attack_end", varbinds)


# Module-level singleton
snmp_sender = SNMPTrapSender()
