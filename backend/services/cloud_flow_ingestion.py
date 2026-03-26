"""
Cloud VPC Flow Log ingestion service.

Supports AWS VPC Flow Logs (text format) and GCP VPC Flow Logs (JSON format).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# AWS VPC Flow Log v2 field order
_AWS_FIELDS = [
    "version", "account_id", "interface_id",
    "srcaddr", "dstaddr", "srcport", "dstport",
    "protocol", "packets", "bytes",
    "start", "end", "action", "log_status",
]

# Protocol number → name mapping (subset)
_PROTO_MAP = {
    "6": "TCP",
    "17": "UDP",
    "1": "ICMP",
    "58": "ICMPv6",
    "47": "GRE",
    "50": "ESP",
}


class AWSVPCFlowParser:
    """Parse AWS VPC Flow Log records into normalised flow dicts."""

    def parse_line(self, line: str) -> Optional[dict]:
        """Parse a single AWS VPC Flow Log line.

        Expected format (v2, space-separated):
        ``version account-id interface-id srcaddr dstaddr srcport dstport
        protocol packets bytes start end action log-status``

        Args:
            line: Single log line (leading/trailing whitespace is stripped).

        Returns:
            Normalised flow dict with keys ``src_ip``, ``dst_ip``,
            ``src_port``, ``dst_port``, ``protocol``, ``packets``,
            ``bytes``, ``action``, ``timestamp``.
            Returns ``None`` for header lines or parse errors.
        """
        line = line.strip()
        if not line or line.startswith("version"):
            return None

        parts = line.split()
        if len(parts) < len(_AWS_FIELDS):
            logger.debug("parse_line: too few fields (%d)", len(parts))
            return None

        raw = dict(zip(_AWS_FIELDS, parts))

        # Skip NODATA / SKIPDATA records
        if raw.get("log_status") in ("NODATA", "SKIPDATA"):
            return None

        try:
            protocol_num = raw.get("protocol", "-")
            protocol = _PROTO_MAP.get(protocol_num, protocol_num)

            return {
                "src_ip": raw["srcaddr"],
                "dst_ip": raw["dstaddr"],
                "src_port": _safe_int(raw.get("srcport")),
                "dst_port": _safe_int(raw.get("dstport")),
                "protocol": protocol,
                "packets": _safe_int(raw.get("packets")),
                "bytes": _safe_int(raw.get("bytes")),
                "action": raw.get("action", "-"),
                "timestamp": _safe_int(raw.get("start")),
                "interface_id": raw.get("interface_id"),
                "account_id": raw.get("account_id"),
            }
        except Exception as exc:
            logger.debug("parse_line error: %s", exc)
            return None

    def parse_file(self, content: str) -> list[dict]:
        """Parse an entire AWS VPC Flow Log file.

        Skips the header line and any records that cannot be parsed.

        Args:
            content: Full text content of the log file.

        Returns:
            List of normalised flow dicts.
        """
        flows: list[dict] = []
        for line in content.splitlines():
            flow = self.parse_line(line)
            if flow is not None:
                flows.append(flow)
        return flows


class GCPFlowParser:
    """Parse GCP VPC Flow Log JSON records into normalised flow dicts."""

    def parse_record(self, record: dict) -> Optional[dict]:
        """Parse a single GCP VPC Flow Log JSON record.

        GCP flow logs wrap connection info inside a ``connection`` sub-object.

        Expected keys: ``connection``, ``bytes_sent``, ``packets_sent``,
        ``start_time``, ``end_time``, optionally ``src_instance``,
        ``dest_instance``.

        Args:
            record: Parsed JSON object representing one flow record.

        Returns:
            Normalised flow dict, or ``None`` on parse error.
        """
        if record is None or not isinstance(record, dict):
            return None
        try:
            conn: dict = record.get("connection", {})
            protocol_num = str(conn.get("protocol", ""))
            protocol = _PROTO_MAP.get(protocol_num, protocol_num or "unknown")

            return {
                "src_ip": conn.get("src_ip"),
                "dst_ip": conn.get("dest_ip"),
                "src_port": _safe_int(conn.get("src_port")),
                "dst_port": _safe_int(conn.get("dest_port")),
                "protocol": protocol,
                "packets": _safe_int(record.get("packets_sent")),
                "bytes": _safe_int(record.get("bytes_sent")),
                "action": "ACCEPT",  # GCP VPC Flow Logs only capture accepted flows
                "timestamp": record.get("start_time"),
                "end_time": record.get("end_time"),
                "src_instance": record.get("src_instance", {}).get("vm_name"),
                "dest_instance": record.get("dest_instance", {}).get("vm_name"),
            }
        except Exception as exc:
            logger.debug("GCPFlowParser.parse_record error: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(value) -> Optional[int]:
    """Convert *value* to int, returning None for ``"-"`` or non-numeric input."""
    if value is None or value == "-":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
