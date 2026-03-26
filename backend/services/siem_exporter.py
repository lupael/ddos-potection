"""
SIEM export service.
Formats security events as Syslog RFC 5424 and CEF (ArcSight Common Event Format).
Sends over UDP to configured SIEM server.
"""
import asyncio
import logging
import socket
from datetime import datetime, timezone

from config import settings

logger = logging.getLogger(__name__)

_APP_NAME = "DDoS-Protection"
_PRODUCT_VERSION = "1.0"
_VENDOR = "DDoSPlatform"


class SIEMExporter:
    """Formats and ships security events to an external SIEM via UDP."""

    def __init__(self):
        self.enabled = settings.SIEM_ENABLED
        self.host = settings.SIEM_HOST
        self.port = settings.SIEM_PORT
        self.fmt = settings.SIEM_FORMAT.lower()
        self.facility = settings.SIEM_FACILITY
        self._hostname = socket.gethostname()

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _priority(self, severity: str) -> int:
        """Compute syslog priority from facility and severity string."""
        severity_map = {
            "critical": 2,  # syslog CRIT
            "high": 3,       # syslog ERR
            "medium": 4,     # syslog WARNING
            "low": 6,        # syslog INFO
        }
        sev_num = severity_map.get(str(severity).lower(), 5)
        return self.facility * 8 + sev_num

    def format_syslog_rfc5424(self, event: dict) -> str:
        """Return an RFC 5424 formatted syslog string for *event*."""
        priority = self._priority(event.get("severity", "low"))
        version = 1
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        hostname = self._hostname
        app_name = _APP_NAME
        procid = "-"
        msgid = event.get("alert_type", "-").replace(" ", "_") or "-"
        structured_data = "-"

        msg = (
            f"alert_type={event.get('alert_type', 'unknown')} "
            f"source_ip={event.get('source_ip', '-')} "
            f"target_ip={event.get('target_ip', '-')} "
            f"severity={event.get('severity', '-')}"
        )

        return (
            f"<{priority}>{version} {timestamp} {hostname} {app_name} "
            f"{procid} {msgid} {structured_data} {msg}"
        )

    def format_cef(self, event: dict) -> str:
        """Return a CEF (ArcSight Common Event Format) string for *event*."""
        severity_map = {"critical": 10, "high": 8, "medium": 5, "low": 2}
        cef_severity = severity_map.get(str(event.get("severity", "low")).lower(), 3)

        event_class_id = event.get("alert_type", "unknown").replace(" ", "_")
        name = event.get("description", event.get("alert_type", "DDoS Event"))
        # Escape pipe characters in header fields
        name = name.replace("|", "\\|")

        extensions = {
            "src": event.get("source_ip", ""),
            "dst": event.get("target_ip", ""),
            "msg": event.get("description", ""),
            "rt": datetime.now(timezone.utc).strftime("%b %d %Y %H:%M:%S"),
        }
        ext_str = " ".join(f"{k}={v}" for k, v in extensions.items() if v)

        return (
            f"CEF:0|{_VENDOR}|{_APP_NAME}|{_PRODUCT_VERSION}"
            f"|{event_class_id}|{name}|{cef_severity}|{ext_str}"
        )

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_event(self, event: dict) -> None:
        """Format and send *event* over UDP to the configured SIEM server."""
        if not self.enabled or not self.host:
            return

        if self.fmt == "syslog":
            message = self.format_syslog_rfc5424(event)
        else:
            message = self.format_cef(event)

        data = message.encode("utf-8", errors="replace")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._udp_send, data)
        except Exception as exc:
            logger.warning("Failed to send SIEM event: %s", exc)

    def _udp_send(self, data: bytes) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (self.host, self.port))

    async def export_alert(self, alert_dict: dict) -> None:
        """Convenience method — ships an alert dictionary to the SIEM."""
        await self.send_event(alert_dict)


# Module-level singleton
siem_exporter = SIEMExporter()
