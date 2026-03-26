"""
Third-party DDoS scrubbing provider integrations.

Provides stub implementations for Cloudflare Magic Transit, Lumen (DDoS Hyper),
and NSFOCUS with a common interface for activating / deactivating protection.
"""
import logging
from enum import Enum
from typing import Dict, Type

logger = logging.getLogger(__name__)


class CloudflareProvider:
    """Cloudflare Magic Transit scrubbing provider integration."""

    def activate_protection(self, prefix: str, tunnel_id: str) -> dict:
        """Activate DDoS protection for a prefix via Cloudflare Magic Transit.

        Args:
            prefix: The IP prefix to protect (e.g., "203.0.113.0/24").
            tunnel_id: The Cloudflare GRE/IPsec tunnel identifier for return traffic.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "CloudflareProvider: activating protection for prefix=%s tunnel_id=%s",
            prefix, tunnel_id,
        )
        return {
            "provider": "cloudflare",
            "action": "activate",
            "prefix": prefix,
            "tunnel_id": tunnel_id,
            "status": "requested",
        }

    def deactivate_protection(self, prefix: str) -> dict:
        """Deactivate DDoS protection for a prefix.

        Args:
            prefix: The IP prefix to stop protecting.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "CloudflareProvider: deactivating protection for prefix=%s", prefix,
        )
        return {
            "provider": "cloudflare",
            "action": "deactivate",
            "prefix": prefix,
            "status": "requested",
        }


class LumenProvider:
    """Lumen (formerly CenturyLink) DDoS Hyper scrubbing provider integration."""

    def activate_protection(self, prefix: str, tunnel_id: str) -> dict:
        """Activate DDoS Hyper protection for a prefix via Lumen.

        Args:
            prefix: The IP prefix to protect.
            tunnel_id: The tunnel identifier for traffic return.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "LumenProvider: activating DDoS Hyper protection for prefix=%s tunnel_id=%s",
            prefix, tunnel_id,
        )
        return {
            "provider": "lumen",
            "action": "activate",
            "prefix": prefix,
            "tunnel_id": tunnel_id,
            "status": "requested",
        }

    def deactivate_protection(self, prefix: str) -> dict:
        """Deactivate DDoS Hyper protection for a prefix.

        Args:
            prefix: The IP prefix to stop protecting.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "LumenProvider: deactivating DDoS Hyper protection for prefix=%s", prefix,
        )
        return {
            "provider": "lumen",
            "action": "deactivate",
            "prefix": prefix,
            "status": "requested",
        }


class NSFOCUSProvider:
    """NSFOCUS Anti-DDoS scrubbing provider integration."""

    def activate_protection(self, prefix: str, tunnel_id: str) -> dict:
        """Activate NSFOCUS Anti-DDoS protection for a prefix.

        Args:
            prefix: The IP prefix to protect.
            tunnel_id: The tunnel identifier for traffic return.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "NSFOCUSProvider: activating protection for prefix=%s tunnel_id=%s",
            prefix, tunnel_id,
        )
        return {
            "provider": "nsfocus",
            "action": "activate",
            "prefix": prefix,
            "tunnel_id": tunnel_id,
            "status": "requested",
        }

    def deactivate_protection(self, prefix: str) -> dict:
        """Deactivate NSFOCUS Anti-DDoS protection for a prefix.

        Args:
            prefix: The IP prefix to stop protecting.

        Returns:
            Dictionary describing the action taken.
        """
        logger.info(
            "NSFOCUSProvider: deactivating protection for prefix=%s", prefix,
        )
        return {
            "provider": "nsfocus",
            "action": "deactivate",
            "prefix": prefix,
            "status": "requested",
        }


class ScrubProviderName(str, Enum):
    """Enumeration of supported third-party scrubbing providers."""
    CLOUDFLARE = "cloudflare"
    LUMEN = "lumen"
    NSFOCUS = "nsfocus"


# Registry mapping provider names to their implementation classes
ScrubProvider: Dict[str, Type] = {
    ScrubProviderName.CLOUDFLARE: CloudflareProvider,
    ScrubProviderName.LUMEN: LumenProvider,
    ScrubProviderName.NSFOCUS: NSFOCUSProvider,
}


def get_provider(name: str):
    """Instantiate and return a scrubbing provider by name.

    Args:
        name: Provider name — one of "cloudflare", "lumen", "nsfocus".

    Returns:
        An instance of the matching provider class.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    provider_cls = ScrubProvider.get(name.lower())
    if provider_cls is None:
        raise ValueError(
            f"Unknown scrubbing provider '{name}'. "
            f"Supported: {list(ScrubProvider.keys())}"
        )
    return provider_cls()
