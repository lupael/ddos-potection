"""
Scrubbing centre diversion module.

Manages traffic diversion to scrubbing centres via BGP /32 announcement
with the scrubbing centre as the next-hop.  Traffic is cleaned and returned
via a GRE tunnel.
"""
import ipaddress
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScrubbingCentre:
    """Represents a single scrubbing centre capable of diverting and cleaning traffic."""

    def __init__(
        self,
        centre_id: str,
        name: str,
        bgp_nexthop: str,
        gre_endpoint: str,
        capacity_gbps: int = 100,
    ) -> None:
        """Initialise a scrubbing centre.

        Args:
            centre_id: Unique identifier for this centre.
            name: Human-readable name.
            bgp_nexthop: BGP next-hop IP used for diversion announcements.
            gre_endpoint: GRE tunnel endpoint IP for traffic return.
            capacity_gbps: Total scrubbing capacity in Gbps (default 100).

        Raises:
            ValueError: If bgp_nexthop or gre_endpoint are invalid IP addresses.
        """
        ipaddress.ip_address(bgp_nexthop)
        ipaddress.ip_address(gre_endpoint)
        self.centre_id = centre_id
        self.name = name
        self.bgp_nexthop = bgp_nexthop
        self.gre_endpoint = gre_endpoint
        self.capacity_gbps = capacity_gbps
        self._active_diversions: dict[str, dict] = {}

    def divert_traffic(self, target_prefix: str, announce_as: str = "/32") -> dict:
        """Announce a BGP /32 route pointing to this scrubbing centre's next-hop.

        Args:
            target_prefix: The victim IP or prefix to protect (e.g., "203.0.113.5").
            announce_as: Host-route suffix for the announcement (default "/32").

        Returns:
            Dictionary describing the action taken.

        Raises:
            ValueError: If target_prefix is not a valid IP or CIDR.
        """
        # Validate — strip existing prefix length first so we can normalise
        try:
            net = ipaddress.ip_network(target_prefix, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid target_prefix {target_prefix!r}: {exc}") from exc

        # Build the /32 (or /128 for IPv6) host route
        host_ip = str(net.network_address)
        if net.version == 6:
            host_route = f"{host_ip}/128"
        else:
            host_route = f"{host_ip}{announce_as}"

        action = {
            "centre_id": self.centre_id,
            "centre_name": self.name,
            "action": "divert",
            "host_route": host_route,
            "bgp_nexthop": self.bgp_nexthop,
            "gre_endpoint": self.gre_endpoint,
            "status": "announced",
        }
        self._active_diversions[host_route] = action
        logger.info(
            "ScrubbingCentre %s: diverting %s via %s (nexthop %s)",
            self.centre_id, host_route, self.gre_endpoint, self.bgp_nexthop,
        )
        return action

    def return_traffic(self, target_prefix: str) -> dict:
        """Withdraw the diversion announcement for a previously diverted prefix.

        Args:
            target_prefix: The prefix whose diversion should be withdrawn.

        Returns:
            Dictionary describing the withdrawal action.

        Raises:
            ValueError: If target_prefix is not a valid IP or CIDR.
        """
        try:
            net = ipaddress.ip_network(target_prefix, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid target_prefix {target_prefix!r}: {exc}") from exc

        host_ip = str(net.network_address)
        suffix = "/128" if net.version == 6 else "/32"
        host_route = f"{host_ip}{suffix}"

        self._active_diversions.pop(host_route, None)
        action = {
            "centre_id": self.centre_id,
            "centre_name": self.name,
            "action": "return",
            "host_route": host_route,
            "status": "withdrawn",
        }
        logger.info(
            "ScrubbingCentre %s: returning traffic for %s",
            self.centre_id, host_route,
        )
        return action

    def get_utilization(self) -> float:
        """Return current utilization as a fraction between 0.0 and 1.0.

        Returns:
            Stub implementation returning 0.5 (50% utilization).
        """
        return 0.5


class ScrubbingCentreManager:
    """Manages a pool of scrubbing centres and coordinates traffic diversion."""

    def __init__(self, centres: list[ScrubbingCentre]) -> None:
        """Initialise the manager with a list of scrubbing centres.

        Args:
            centres: List of ScrubbingCentre instances to manage.
        """
        self._centres = list(centres)

    def select_centre(self, target_prefix: str) -> Optional[ScrubbingCentre]:
        """Select the best available scrubbing centre using lowest-utilization anycast.

        Args:
            target_prefix: The prefix requiring protection (used for logging/routing
                hints in future implementations).

        Returns:
            The ScrubbingCentre with the lowest current utilization, or None if
            no centres are available.
        """
        if not self._centres:
            return None
        # Anycast closest-available: select by lowest utilization
        available = sorted(self._centres, key=lambda c: c.get_utilization())
        selected = available[0]
        logger.info(
            "ScrubbingCentreManager: selected centre %s (utilization %.0f%%) for %s",
            selected.centre_id, selected.get_utilization() * 100, target_prefix,
        )
        return selected

    def divert(self, target_prefix: str) -> dict:
        """Divert traffic for a prefix to the best available scrubbing centre.

        Args:
            target_prefix: The victim IP or prefix to protect.

        Returns:
            Action dict from ScrubbingCentre.divert_traffic, with an additional
            "error" key and empty dict if no centre is available.
        """
        centre = self.select_centre(target_prefix)
        if centre is None:
            logger.error("ScrubbingCentreManager: no centres available for diversion of %s", target_prefix)
            return {"error": "no_centres_available", "target_prefix": target_prefix}
        return centre.divert_traffic(target_prefix)

    def return_all(self, target_prefix: str) -> list[dict]:
        """Withdraw diversion for a prefix from ALL scrubbing centres.

        Args:
            target_prefix: The prefix whose diversion should be cancelled everywhere.

        Returns:
            List of action dicts, one per centre.
        """
        results = []
        for centre in self._centres:
            try:
                results.append(centre.return_traffic(target_prefix))
            except ValueError as exc:
                results.append({"centre_id": centre.centre_id, "error": str(exc)})
        return results
