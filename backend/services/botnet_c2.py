"""
Botnet C2 (Command & Control) flow fingerprinting.

Analyses network flows against a built-in library of known C2 indicators
and produces structured reports suitable for alerting pipelines.
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class BotnetC2Fingerprinter:
    """Detects botnet C2 traffic patterns in network flows."""

    C2_INDICATORS: list[dict[str, Any]] = [
        {
            "name": "Mirai Telnet Brute-Force",
            "protocol": "tcp",
            "ports": [23, 2323],
            "pattern_bytes_hex": "474554202f6269",  # GET /bi (Mirai loader)
            "description": "Mirai botnet Telnet scanner / loader traffic",
            "family": "Mirai",
        },
        {
            "name": "Emotet HTTP Beaconing",
            "protocol": "http",
            "ports": [80, 8080],
            "pattern_bytes_hex": "504f5354202f",    # POST /
            "description": "Emotet periodic HTTP POST beaconing",
            "family": "Emotet",
        },
        {
            "name": "Generic IRC C2",
            "protocol": "tcp",
            "ports": [6667, 6697],
            "pattern_bytes_hex": "4a4f494e20",      # JOIN (IRC)
            "description": "IRC-based botnet command channel",
            "family": "IRC-C2",
        },
        {
            "name": "Generic HTTP Beacon",
            "protocol": "http",
            "ports": [80, 443, 8080],
            "pattern_bytes_hex": "474554202f",      # GET /
            "description": "Periodic HTTP GET beacon (low-and-slow)",
            "family": "HTTP-Beacon",
        },
    ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_flow(self, flow: dict[str, Any]) -> dict[str, Any] | None:
        """Check a single flow against all C2 indicators.

        Args:
            flow: Flow data dict.  Expected keys: ``protocol`` (str),
                ``dst_port`` (int), ``src_port`` (int, optional),
                ``payload_hex`` (str, optional).

        Returns:
            The matching indicator dict (augmented with flow metadata) if a
            match is found, otherwise ``None``.
        """
        protocol: str = str(flow.get("protocol", "")).lower()
        dst_port: int = int(flow.get("dst_port", 0))
        payload_hex: str = str(flow.get("payload_hex", "")).lower()

        for indicator in self.C2_INDICATORS:
            ind_proto: str = indicator["protocol"].lower()
            ind_ports: list[int] = indicator["ports"]

            # Protocol match (http is carried over tcp)
            proto_match = (
                ind_proto == protocol
                or (ind_proto == "http" and protocol in ("tcp", "http"))
            )
            if not proto_match:
                continue

            if dst_port not in ind_ports:
                continue

            # Optional payload pattern check
            pattern: str = indicator["pattern_bytes_hex"].lower()
            if payload_hex and pattern and pattern not in payload_hex:
                continue

            return {
                **indicator,
                "flow": flow,
                "matched_at": datetime.now(timezone.utc).isoformat(),
            }
        return None

    def get_c2_report(self, flows: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate C2 analysis across multiple flows.

        Args:
            flows: List of flow dicts (same schema as :meth:`analyze_flow`).

        Returns:
            Report dict with ``total_flows``, ``matched_flows``,
            ``c2_families``, and ``matches`` keys.
        """
        matches: list[dict[str, Any]] = []
        families: dict[str, int] = {}

        for flow in flows:
            match = self.analyze_flow(flow)
            if match:
                matches.append(match)
                family = match.get("family", "Unknown")
                families[family] = families.get(family, 0) + 1

        return {
            "total_flows": len(flows),
            "matched_flows": len(matches),
            "c2_families": families,
            "matches": matches,
        }

    def generate_c2_alert(self, match: dict[str, Any]) -> dict[str, Any]:
        """Format a C2 match as a structured alert dict.

        Args:
            match: A match dict returned by :meth:`analyze_flow`.

        Returns:
            Alert dict compatible with the platform's alert schema.
        """
        flow = match.get("flow", {})
        return {
            "alert_type": "botnet_c2",
            "severity": "critical",
            "source_ip": flow.get("src_ip", "unknown"),
            "target_ip": flow.get("dst_ip", "unknown"),
            "description": (
                f"Botnet C2 traffic detected: {match['name']} "
                f"(family: {match.get('family', 'unknown')}) — "
                f"{match['description']}"
            ),
            "timestamp": match.get("matched_at", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "family": match.get("family"),
                "protocol": match.get("protocol"),
                "ports": match.get("ports"),
                "pattern_bytes_hex": match.get("pattern_bytes_hex"),
            },
        }
