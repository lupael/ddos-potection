"""
GRE decapsulation service.

Supports standard GRE (RFC 2784) and enhanced GRE with Key and Sequence
Number extensions (RFC 2890).
"""
import logging
import struct
from typing import Optional

logger = logging.getLogger(__name__)

# IP protocol number for GRE
_GRE_PROTO = 47

# GRE EtherType values for inner payload
_ETHERTYPE_IPV4 = 0x0800
_ETHERTYPE_IPV6 = 0x86DD

# Minimum sizes
_IP_HEADER_MIN = 20   # bytes
_GRE_HEADER_MIN = 4   # bytes (flags/version word + protocol type word)


class GREDecapsulator:
    """Decapsulate GRE-encapsulated IP packets."""

    def is_gre_packet(self, raw_packet: bytes) -> bool:
        """Return ``True`` if *raw_packet* is an IPv4 packet with protocol=GRE (47).

        Args:
            raw_packet: Raw bytes starting at the IP header.

        Returns:
            ``True`` when the IP protocol field equals 47.
        """
        try:
            if len(raw_packet) < _IP_HEADER_MIN:
                return False
            protocol = raw_packet[9]
            return protocol == _GRE_PROTO
        except Exception as exc:
            logger.debug("is_gre_packet error: %s", exc)
            return False

    def parse_gre_header(self, data: bytes) -> dict:
        """Parse a GRE header starting at *data* (after the outer IP header).

        Handles standard GRE (RFC 2784) and optional Key/Sequence Number
        extensions (RFC 2890).

        Args:
            data: Bytes starting at the first byte of the GRE header.

        Returns:
            Dict with keys:
            - ``checksum_present`` (bool)
            - ``key_present`` (bool)
            - ``sequence_present`` (bool)
            - ``protocol_type`` (int): EtherType of inner payload.
            - ``checksum`` (int | None)
            - ``key`` (int | None)
            - ``sequence_number`` (int | None)
            - ``header_length`` (int): total byte length of the GRE header.
        """
        if len(data) < _GRE_HEADER_MIN:
            return {}

        flags_ver, protocol_type = struct.unpack("!HH", data[:4])
        checksum_present = bool(flags_ver & 0x8000)
        key_present = bool(flags_ver & 0x2000)
        sequence_present = bool(flags_ver & 0x1000)

        result: dict = {
            "checksum_present": checksum_present,
            "key_present": key_present,
            "sequence_present": sequence_present,
            "protocol_type": protocol_type,
            "checksum": None,
            "key": None,
            "sequence_number": None,
            "header_length": _GRE_HEADER_MIN,
        }

        offset = _GRE_HEADER_MIN
        if checksum_present:
            if len(data) < offset + 4:
                return result
            (checksum,) = struct.unpack("!H", data[offset : offset + 2])
            result["checksum"] = checksum
            offset += 4  # checksum (2) + reserved (2)
            result["header_length"] = offset

        if key_present:
            if len(data) < offset + 4:
                return result
            (key,) = struct.unpack("!I", data[offset : offset + 4])
            result["key"] = key
            offset += 4
            result["header_length"] = offset

        if sequence_present:
            if len(data) < offset + 4:
                return result
            (seq,) = struct.unpack("!I", data[offset : offset + 4])
            result["sequence_number"] = seq
            offset += 4
            result["header_length"] = offset

        return result

    def decapsulate(self, raw_packet: bytes) -> Optional[bytes]:
        """Strip the outer IP and GRE headers and return the inner payload.

        Supports IPv4 and IPv6 inner payloads (EtherType 0x0800 / 0x86DD).

        Args:
            raw_packet: Raw bytes starting at the outer IPv4 header.

        Returns:
            Inner payload bytes, or ``None`` if the packet cannot be parsed
            or the inner protocol is not IPv4/IPv6.
        """
        try:
            if not self.is_gre_packet(raw_packet):
                return None

            # Determine outer IP header length from IHL field
            ihl = (raw_packet[0] & 0x0F) * 4
            if len(raw_packet) < ihl + _GRE_HEADER_MIN:
                return None

            gre_data = raw_packet[ihl:]
            parsed = self.parse_gre_header(gre_data)
            if not parsed:
                return None

            protocol_type: int = parsed.get("protocol_type") or 0
            if protocol_type not in (_ETHERTYPE_IPV4, _ETHERTYPE_IPV6):
                logger.debug(
                    "decapsulate: unsupported inner EtherType 0x%04x", protocol_type
                )
                return None

            gre_hdr_len: int = parsed.get("header_length", _GRE_HEADER_MIN)
            inner_payload = gre_data[gre_hdr_len:]
            return inner_payload if inner_payload else None

        except Exception as exc:
            logger.debug("GREDecapsulator.decapsulate error: %s", exc)
            return None
