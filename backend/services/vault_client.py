"""HashiCorp Vault client for the DDoS Protection Platform.

Supports async (aiohttp) with sync (urllib) fallback.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import aiohttp as _aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class VaultClient:
    """Client for reading/writing secrets from/to HashiCorp Vault."""

    def __init__(
        self,
        vault_addr: str,
        vault_token: Optional[str] = None,
        vault_role: Optional[str] = None,
    ) -> None:
        """Initialise the Vault client.

        Args:
            vault_addr: Base URL of the Vault server (e.g. ``http://vault:8200``).
            vault_token: Vault token for authentication.
            vault_role: Vault Kubernetes/AWS auth role (used for k8s auth flow).
        """
        self.vault_addr = vault_addr.rstrip("/")
        self.vault_token = vault_token or ""
        self.vault_role = vault_role or ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.vault_token:
            headers["X-Vault-Token"] = self.vault_token
        return headers

    def _url(self, path: str) -> str:
        return f"{self.vault_addr}/v1/{path.lstrip('/')}"

    # ------------------------------------------------------------------
    # Async API (aiohttp)
    # ------------------------------------------------------------------

    async def read_secret(self, path: str) -> Optional[dict[str, Any]]:
        """Read a secret from Vault at *path*.

        Uses aiohttp when available, falls back to urllib (sync).

        Args:
            path: Vault KV path, e.g. ``secret/data/ddos/database``.

        Returns:
            Parsed JSON response dict or ``None`` on failure.
        """
        url = self._url(path)
        if _AIOHTTP_AVAILABLE:
            return await self._async_get(url)
        return self._sync_get(url)

    async def write_secret(self, path: str, data: dict[str, Any]) -> bool:
        """Write *data* to Vault at *path*.

        Args:
            path: Vault KV path.
            data: Dict to write as the secret payload.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        url = self._url(path)
        payload = json.dumps({"data": data}).encode()
        if _AIOHTTP_AVAILABLE:
            return await self._async_post(url, payload)
        return self._sync_post(url, payload)

    async def read_db_credentials(self) -> Optional[dict[str, Any]]:
        """Read database credentials from Vault.

        Returns:
            Dict with DB_URL and DB_PASSWORD keys, or ``None``.
        """
        return await self.read_secret("secret/data/ddos/database")

    async def read_app_secrets(self) -> Optional[dict[str, Any]]:
        """Read application secrets from Vault.

        Returns:
            Dict with SECRET_KEY and JWT_SECRET keys, or ``None``.
        """
        return await self.read_secret("secret/data/ddos/app")

    # ------------------------------------------------------------------
    # aiohttp helpers
    # ------------------------------------------------------------------

    async def _async_get(self, url: str) -> Optional[dict[str, Any]]:
        import aiohttp
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    logger.warning("Vault GET %s returned %s", url, resp.status)
                    return None
        except Exception as exc:
            logger.error("Vault GET error: %s", exc)
            return None

    async def _async_post(self, url: str, payload: bytes) -> bool:
        import aiohttp
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.post(url, data=payload) as resp:
                    return resp.status in (200, 204)
        except Exception as exc:
            logger.error("Vault POST error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # urllib fallback (sync)
    # ------------------------------------------------------------------

    def _sync_get(self, url: str) -> Optional[dict[str, Any]]:
        import urllib.request
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.error("Vault sync GET error: %s", exc)
            return None

    def _sync_post(self, url: str, payload: bytes) -> bool:
        import urllib.request
        req = urllib.request.Request(
            url,
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                return resp.status in (200, 204)
        except Exception as exc:
            logger.error("Vault sync POST error: %s", exc)
            return False
