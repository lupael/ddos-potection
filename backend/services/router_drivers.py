"""
Multi-vendor router driver implementations for ACL/filter push.
Supports: Cisco IOS/IOS-XR (Netmiko), Juniper JunOS (NAPALM), Arista EOS (eAPI),
          Nokia SROS (Netmiko)
"""
import ipaddress
import logging
from dataclasses import dataclass, field
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    from netmiko import ConnectHandler  # type: ignore
    _NETMIKO_AVAILABLE = True
except ImportError:
    _NETMIKO_AVAILABLE = False
    logger.warning("netmiko not installed; Cisco/Arista drivers disabled")

try:
    import napalm  # type: ignore
    _NAPALM_AVAILABLE = True
except ImportError:
    _NAPALM_AVAILABLE = False
    logger.warning("napalm not installed; Juniper driver disabled")


@dataclass
class RouterCredentials:
    hostname: str
    username: str
    password: str
    port: int = 22
    device_type: str = "cisco_ios"


class CiscoIOSDriver:
    """Push ACLs to Cisco IOS / IOS-XR devices via Netmiko."""

    def apply_acl(
        self, creds: RouterCredentials, acl_name: str, entries: List[str]
    ) -> bool:
        """Create or update an extended ACL on the device."""
        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not available")
            return False
        commands = [f"ip access-list extended {acl_name}"] + list(entries)
        try:
            connection = ConnectHandler(
                device_type=creds.device_type,
                host=creds.hostname,
                username=creds.username,
                password=creds.password,
                port=creds.port,
            )
            connection.send_config_set(commands)
            connection.disconnect()
            logger.info("Applied ACL %s on %s", acl_name, creds.hostname)
            return True
        except Exception as exc:
            logger.error("Failed to apply ACL on %s: %s", creds.hostname, exc)
            return False

    def remove_acl_entry(
        self, creds: RouterCredentials, acl_name: str, entry: str
    ) -> bool:
        """Remove a single entry from an extended ACL."""
        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not available")
            return False
        commands = [f"ip access-list extended {acl_name}", f"no {entry}"]
        try:
            connection = ConnectHandler(
                device_type=creds.device_type,
                host=creds.hostname,
                username=creds.username,
                password=creds.password,
                port=creds.port,
            )
            connection.send_config_set(commands)
            connection.disconnect()
            logger.info("Removed ACL entry from %s on %s", acl_name, creds.hostname)
            return True
        except Exception as exc:
            logger.error("Failed to remove ACL entry on %s: %s", creds.hostname, exc)
            return False


class JuniperDriver:
    """Push firewall filters to Juniper JunOS devices via NAPALM."""

    def _build_filter_config(self, filter_name: str, terms: List[Dict]) -> str:
        lines = [f"set firewall family inet filter {filter_name}"]
        for term in terms:
            term_name = term.get("name", "term1")
            if "source_address" in term:
                lines.append(
                    f"set firewall family inet filter {filter_name} "
                    f"term {term_name} from source-address {term['source_address']}"
                )
            if "destination_address" in term:
                lines.append(
                    f"set firewall family inet filter {filter_name} "
                    f"term {term_name} from destination-address {term['destination_address']}"
                )
            action = term.get("action", "discard")
            lines.append(
                f"set firewall family inet filter {filter_name} "
                f"term {term_name} then {action}"
            )
        return "\n".join(lines)

    def apply_firewall_filter(
        self, creds: RouterCredentials, filter_name: str, terms: List[Dict]
    ) -> bool:
        """Load a firewall filter onto a JunOS device."""
        if not _NAPALM_AVAILABLE:
            logger.error("napalm not available")
            return False
        config = self._build_filter_config(filter_name, terms)
        try:
            driver = napalm.get_network_driver("junos")
            device = driver(
                hostname=creds.hostname,
                username=creds.username,
                password=creds.password,
                optional_args={"port": creds.port},
            )
            device.open()
            device.load_merge_candidate(config=config)
            device.commit_config()
            device.close()
            logger.info("Applied firewall filter %s on %s", filter_name, creds.hostname)
            return True
        except Exception as exc:
            logger.error("Failed to apply filter on %s: %s", creds.hostname, exc)
            return False

    def remove_firewall_filter(
        self, creds: RouterCredentials, filter_name: str
    ) -> bool:
        """Remove a firewall filter from a JunOS device."""
        if not _NAPALM_AVAILABLE:
            logger.error("napalm not available")
            return False
        config = f"delete firewall family inet filter {filter_name}"
        try:
            driver = napalm.get_network_driver("junos")
            device = driver(
                hostname=creds.hostname,
                username=creds.username,
                password=creds.password,
                optional_args={"port": creds.port},
            )
            device.open()
            device.load_merge_candidate(config=config)
            device.commit_config()
            device.close()
            logger.info("Removed firewall filter %s from %s", filter_name, creds.hostname)
            return True
        except Exception as exc:
            logger.error("Failed to remove filter on %s: %s", creds.hostname, exc)
            return False


class AristaEOSDriver:
    """Push ACLs to Arista EOS devices via Netmiko."""

    def apply_acl(
        self, creds: RouterCredentials, acl_name: str, entries: List[str]
    ) -> bool:
        """Create or update an ACL on an Arista EOS device."""
        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not available")
            return False
        commands = [f"ip access-list {acl_name}"] + list(entries)
        try:
            connection = ConnectHandler(
                device_type="arista_eos",
                host=creds.hostname,
                username=creds.username,
                password=creds.password,
                port=creds.port,
            )
            connection.send_config_set(commands)
            connection.disconnect()
            logger.info("Applied ACL %s on Arista %s", acl_name, creds.hostname)
            return True
        except Exception as exc:
            logger.error("Failed to apply ACL on Arista %s: %s", creds.hostname, exc)
            return False


class NokiaSROSDriver:
    """Push CPM (Control Plane Management) filter entries to Nokia SROS devices via Netmiko."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        """Initialise the Nokia SROS driver.

        Args:
            host: Router hostname or IP address.
            port: SSH port (typically 22).
            username: Login username.
            password: Login password.
        """
        ipaddress.ip_address(host)  # raises ValueError for invalid host IP
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._connection = None

    def connect(self) -> bool:
        """Establish an SSH connection to the Nokia SROS device.

        Returns:
            True if the connection was established successfully, False otherwise.
        """
        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not installed; NokiaSROSDriver unavailable")
            return False
        try:
            self._connection = ConnectHandler(
                device_type="nokia_sros",
                host=self._host,
                username=self._username,
                password=self._password,
                port=self._port,
            )
            logger.info("Connected to Nokia SROS device %s", self._host)
            return True
        except Exception as exc:
            logger.error("Failed to connect to Nokia SROS %s: %s", self._host, exc)
            self._connection = None
            return False

    def push_acl(self, prefix: str, action: str = "drop") -> bool:
        """Push a CPM filter entry for the given prefix via Nokia MD-CLI.

        Args:
            prefix: The IP prefix to filter (e.g., "192.0.2.1/32").
            action: Filter action, either "drop" or "accept". Defaults to "drop".

        Returns:
            True if the entry was pushed successfully, False otherwise.
        """
        try:
            ipaddress.ip_network(prefix, strict=False)
        except ValueError:
            logger.error("NokiaSROSDriver.push_acl: invalid prefix %r", prefix)
            return False

        if action not in ("drop", "accept"):
            logger.error("NokiaSROSDriver.push_acl: invalid action %r", action)
            return False

        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not installed; NokiaSROSDriver unavailable")
            return False

        if self._connection is None:
            if not self.connect():
                return False

        # Nokia MD-CLI CPM filter configuration commands
        entry_name = prefix.replace("/", "_").replace(".", "_").replace(":", "_")
        commands = [
            "/configure",
            "system security cpm-filter ip-filter",
            f"entry {entry_name}",
            f"match src-ip {prefix}",
            f"action {action}",
            "exit all",
            "commit",
        ]
        try:
            self._connection.send_config_set(commands)
            logger.info("Pushed Nokia SROS CPM filter entry for %s (%s) on %s", prefix, action, self._host)
            return True
        except Exception as exc:
            logger.error("Failed to push Nokia SROS CPM filter on %s: %s", self._host, exc)
            return False

    def withdraw_acl(self, prefix: str) -> bool:
        """Remove a CPM filter entry for the given prefix.

        Args:
            prefix: The IP prefix whose filter entry should be removed.

        Returns:
            True if the entry was removed successfully, False otherwise.
        """
        try:
            ipaddress.ip_network(prefix, strict=False)
        except ValueError:
            logger.error("NokiaSROSDriver.withdraw_acl: invalid prefix %r", prefix)
            return False

        if not _NETMIKO_AVAILABLE:
            logger.error("netmiko not installed; NokiaSROSDriver unavailable")
            return False

        if self._connection is None:
            if not self.connect():
                return False

        entry_name = prefix.replace("/", "_").replace(".", "_").replace(":", "_")
        commands = [
            "/configure",
            "system security cpm-filter ip-filter",
            f"no entry {entry_name}",
            "exit all",
            "commit",
        ]
        try:
            self._connection.send_config_set(commands)
            logger.info("Withdrew Nokia SROS CPM filter entry for %s on %s", prefix, self._host)
            return True
        except Exception as exc:
            logger.error("Failed to withdraw Nokia SROS CPM filter on %s: %s", self._host, exc)
            return False

    def get_status(self) -> dict:
        """Return connection and platform information for this device.

        Returns:
            Dictionary with keys: connected, host, port, platform_info.
        """
        connected = self._connection is not None
        platform_info: dict = {}
        if connected and _NETMIKO_AVAILABLE:
            try:
                output = self._connection.send_command("show version")
                platform_info["version_output"] = output[:500] if output else ""
            except Exception as exc:
                logger.warning("Nokia SROS get_status: could not fetch version from %s: %s", self._host, exc)
        return {
            "connected": connected,
            "host": self._host,
            "port": self._port,
            "platform_info": platform_info,
        }


class RouterACLService:
    """Factory that returns the correct driver for a given vendor string."""

    _DRIVERS = {
        "cisco": CiscoIOSDriver,
        "cisco_ios": CiscoIOSDriver,
        "cisco_iosxr": CiscoIOSDriver,
        "juniper": JuniperDriver,
        "junos": JuniperDriver,
        "arista": AristaEOSDriver,
        "arista_eos": AristaEOSDriver,
        "nokia": NokiaSROSDriver,
        "nokia_sros": NokiaSROSDriver,
    }

    def get_driver(self, vendor: str):
        """Return an instantiated driver for *vendor*."""
        driver_cls = self._DRIVERS.get(vendor.lower())
        if driver_cls is None:
            raise ValueError(
                f"Unknown vendor '{vendor}'. "
                f"Supported: {list(self._DRIVERS.keys())}"
            )
        return driver_cls()
