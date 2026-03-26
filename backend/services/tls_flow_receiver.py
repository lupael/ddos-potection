"""
TLS-wrapped NetFlow receiver.

Accepts NetFlow/IPFIX bytes over an encrypted TCP connection using asyncio
and the standard ssl module.
"""
import asyncio
import logging
import ssl
from typing import Callable, Optional

from config import settings

logger = logging.getLogger(__name__)


class TLSFlowReceiver:
    """Async TLS TCP server that accepts encrypted NetFlow/IPFIX streams.

    Usage::

        receiver = TLSFlowReceiver(
            host="0.0.0.0",
            port=settings.TLS_FLOW_PORT,
            certfile=settings.TLS_FLOW_CERTFILE,
            keyfile=settings.TLS_FLOW_KEYFILE,
        )
        await receiver.start(on_data_callback)
        # … later …
        await receiver.stop()
    """

    def __init__(
        self,
        host: str,
        port: int,
        certfile: str,
        keyfile: str,
    ) -> None:
        """Initialise the receiver configuration.

        Args:
            host:     Bind address (e.g. ``"0.0.0.0"``).
            port:     TCP port to listen on.
            certfile: Path to PEM-encoded server certificate.
            keyfile:  Path to PEM-encoded private key.
        """
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self._server: Optional[asyncio.AbstractServer] = None

    # ------------------------------------------------------------------
    # SSL context factory
    # ------------------------------------------------------------------

    @staticmethod
    def create_ssl_context(
        certfile: str,
        keyfile: str,
        cafile: Optional[str] = None,
    ) -> ssl.SSLContext:
        """Build an :class:`ssl.SSLContext` for the TLS server.

        Args:
            certfile: Path to server certificate (PEM).
            keyfile:  Path to server private key (PEM).
            cafile:   Optional path to CA certificate for mutual TLS.

        Returns:
            Configured :class:`ssl.SSLContext`.
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)
        if cafile:
            ctx.load_verify_locations(cafile=cafile)
            ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def start(self, on_data_callback: Callable[[bytes], None]) -> None:
        """Start the TLS TCP server.

        Each connected client's data stream is read in chunks and passed to
        *on_data_callback*.  The callback receives raw NetFlow bytes so the
        existing collector can process them without modification.

        Args:
            on_data_callback: Callable that accepts ``bytes``.
        """
        ssl_ctx = self.create_ssl_context(self.certfile, self.keyfile)

        async def _handle_client(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ) -> None:
            peer = writer.get_extra_info("peername")
            logger.info("TLS flow connection from %s", peer)
            try:
                while True:
                    data = await reader.read(65535)
                    if not data:
                        break
                    try:
                        on_data_callback(data)
                    except Exception as exc:
                        logger.error("on_data_callback error: %s", exc)
            except asyncio.IncompleteReadError:
                pass
            except Exception as exc:
                logger.warning("TLS client %s error: %s", peer, exc)
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
                logger.info("TLS flow connection from %s closed", peer)

        self._server = await asyncio.start_server(
            _handle_client,
            host=self.host,
            port=self.port,
            ssl=ssl_ctx,
        )
        logger.info(
            "TLSFlowReceiver listening on %s:%d", self.host, self.port
        )

    async def stop(self) -> None:
        """Shut down the TLS server gracefully."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("TLSFlowReceiver stopped")
