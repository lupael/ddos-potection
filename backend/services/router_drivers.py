"""
Multi-vendor router driver implementations for ACL/filter push.
Supports: Cisco IOS/IOS-XR (Netmiko), Juniper JunOS (NAPALM), Arista EOS (eAPI)
"""
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
