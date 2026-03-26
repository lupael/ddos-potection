"""XDP program loader for the DDoS Protection Platform.

Provides an interface to load/unload eBPF XDP programs on network interfaces
using the ``ip`` command (iproute2), without shell=True.
"""
from __future__ import annotations

import logging
import re
import subprocess
from typing import List

logger = logging.getLogger(__name__)

_IFACE_RE = re.compile(r"^[a-zA-Z0-9._-]{1,15}$")


class XDPLoader:
    """Load and unload XDP eBPF programs on network interfaces."""

    @staticmethod
    def validate_interface(name: str) -> bool:
        """Return True if *name* is a valid Linux network interface name.

        Args:
            name: Interface name to validate.

        Returns:
            ``True`` if valid, ``False`` otherwise.
        """
        return bool(_IFACE_RE.match(name))

    def load_program(
        self,
        interface: str,
        xdp_obj_path: str,
        mode: str = "native",
    ) -> bool:
        """Attach an XDP program to *interface*.

        Args:
            interface: Network interface name (e.g. ``eth0``).
            xdp_obj_path: Absolute path to the compiled XDP .o file.
            mode: XDP attach mode: ``native``, ``skb``, or ``offload``.

        Returns:
            ``True`` if the program was loaded successfully.

        Raises:
            ValueError: If *interface* or *mode* fails validation.
        """
        if not self.validate_interface(interface):
            raise ValueError(f"Invalid interface name: {interface!r}")
        if mode not in ("native", "skb", "offload"):
            raise ValueError(f"Invalid XDP mode: {mode!r}")

        cmd: List[str] = [
            "ip", "link", "set", interface,
            "xdp", "obj", xdp_obj_path,
            "sec", "xdp",
        ]
        if mode == "skb":
            cmd = [
                "ip", "link", "set", interface,
                "xdpgeneric", "obj", xdp_obj_path,
                "sec", "xdp",
            ]
        elif mode == "offload":
            cmd = [
                "ip", "link", "set", interface,
                "xdpoffload", "obj", xdp_obj_path,
                "sec", "xdp",
            ]

        try:
            result = subprocess.run(  # noqa: S603 — no shell=True
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(
                    "XDP load failed (rc=%d): %s", result.returncode, result.stderr
                )
                return False
            logger.info("XDP program loaded on %s", interface)
            return True
        except subprocess.TimeoutExpired:
            logger.error("XDP load timed out for interface %s", interface)
            return False
        except FileNotFoundError:
            logger.error("'ip' command not found — install iproute2")
            return False

    def unload_program(self, interface: str) -> bool:
        """Detach any XDP program from *interface*.

        Args:
            interface: Network interface name.

        Returns:
            ``True`` if unloaded successfully.

        Raises:
            ValueError: If *interface* fails validation.
        """
        if not self.validate_interface(interface):
            raise ValueError(f"Invalid interface name: {interface!r}")

        cmd: List[str] = ["ip", "link", "set", interface, "xdp", "off"]
        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(
                    "XDP unload failed (rc=%d): %s", result.returncode, result.stderr
                )
                return False
            logger.info("XDP program unloaded from %s", interface)
            return True
        except subprocess.TimeoutExpired:
            logger.error("XDP unload timed out for interface %s", interface)
            return False
        except FileNotFoundError:
            logger.error("'ip' command not found — install iproute2")
            return False
