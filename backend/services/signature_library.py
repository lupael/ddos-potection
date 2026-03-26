"""
Reusable BPF / FlowSpec attack-signature library.

Signatures can be extracted from live alerts, stored in-memory, searched,
and exported as JSON, raw BPF, or raw FlowSpec strings.
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AttackSignature:
    """A single attack signature containing both BPF and FlowSpec representations."""

    id: str
    name: str
    attack_type: str
    bpf_filter: str
    flowspec_rule: str
    confidence: float
    created_at: datetime
    isp_id: int


class SignatureLibrary:
    """In-memory library for BPF / FlowSpec attack signatures."""

    def __init__(self) -> None:
        self._signatures: list[AttackSignature] = []

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def extract_bpf_from_alert(self, alert: dict[str, Any]) -> str | None:
        """Generate a BPF filter string from alert attributes.

        Constructs the filter from ``src_ip``, ``protocol``, ``src_port``,
        and ``dst_port`` fields present in *alert*.

        Args:
            alert: Alert data dict.

        Returns:
            BPF filter string, or ``None`` if no useful fields are present.
        """
        parts: list[str] = []

        src_ip: str | None = alert.get("source_ip") or alert.get("src_ip")
        dst_ip: str | None = alert.get("target_ip") or alert.get("dst_ip")
        protocol: str | None = alert.get("protocol")
        src_port: int | None = alert.get("src_port")
        dst_port: int | None = alert.get("dst_port")

        if src_ip:
            parts.append(f"src host {src_ip}")
        if dst_ip:
            parts.append(f"dst host {dst_ip}")
        if protocol:
            proto = protocol.lower()
            if proto in ("tcp", "udp", "icmp"):
                parts.append(proto)
        if src_port:
            parts.append(f"src port {src_port}")
        if dst_port:
            parts.append(f"dst port {dst_port}")

        if not parts:
            return None
        return " and ".join(parts)

    def extract_flowspec_from_alert(self, alert: dict[str, Any]) -> str | None:
        """Generate a FlowSpec rule string from alert attributes.

        Args:
            alert: Alert data dict.

        Returns:
            FlowSpec rule string in Cisco-style notation, or ``None`` if no
            useful fields are present.
        """
        parts: list[str] = []

        src_ip: str | None = alert.get("source_ip") or alert.get("src_ip")
        dst_ip: str | None = alert.get("target_ip") or alert.get("dst_ip")
        protocol: str | None = alert.get("protocol")
        src_port: int | None = alert.get("src_port")
        dst_port: int | None = alert.get("dst_port")

        if dst_ip:
            parts.append(f"match destination {dst_ip}/32")
        if src_ip:
            parts.append(f"match source {src_ip}/32")
        if protocol:
            proto_map = {"tcp": "6", "udp": "17", "icmp": "1"}
            p = protocol.lower()
            if p in proto_map:
                parts.append(f"match protocol {proto_map[p]}")
        if src_port:
            parts.append(f"match source-port {src_port}")
        if dst_port:
            parts.append(f"match destination-port {dst_port}")

        if not parts:
            return None

        action = "then discard"
        return " ".join(parts) + " " + action

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_signature(self, sig: AttackSignature) -> bool:
        """Add a signature to the library.

        Args:
            sig: The :class:`AttackSignature` to store.

        Returns:
            ``True`` on success, ``False`` if a signature with the same ``id``
            already exists.
        """
        if any(s.id == sig.id for s in self._signatures):
            logger.warning("Signature %s already exists", sig.id)
            return False
        self._signatures.append(sig)
        return True

    def search_signatures(
        self,
        attack_type: str | None = None,
        min_confidence: float = 0.5,
    ) -> list[AttackSignature]:
        """Search signatures by attack type and minimum confidence.

        Args:
            attack_type: Filter by exact attack type string. ``None`` returns
                all types.
            min_confidence: Minimum confidence score (0.0–1.0).

        Returns:
            Filtered list of :class:`AttackSignature` objects.
        """
        results = [
            s for s in self._signatures if s.confidence >= min_confidence
        ]
        if attack_type is not None:
            results = [s for s in results if s.attack_type == attack_type]
        return results

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_signatures(self, format: str = "json") -> str:
        """Export all signatures in the requested format.

        Args:
            format: One of ``"json"``, ``"bpf"``, or ``"flowspec"``.

        Returns:
            Serialised string in the requested format.
        """
        if format == "bpf":
            lines = [s.bpf_filter for s in self._signatures if s.bpf_filter]
            return "\n".join(lines)

        if format == "flowspec":
            lines = [s.flowspec_rule for s in self._signatures if s.flowspec_rule]
            return "\n".join(lines)

        # Default: JSON
        data = []
        for s in self._signatures:
            d = asdict(s)
            d["created_at"] = s.created_at.isoformat()
            data.append(d)
        return json.dumps(data, indent=2)
