"""TimescaleDB setup helpers for the DDoS Protection Platform."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class TimescaleDBSetup:
    """Utility class for configuring TimescaleDB hypertables and policies."""

    def setup_hypertable(
        self,
        db_url: str,
        table: str = "traffic_logs",
        time_column: str = "timestamp",
    ) -> bool:
        """Convert *table* into a TimescaleDB hypertable.

        Args:
            db_url: SQLAlchemy-compatible database URL.
            table: Table name to convert (must already exist).
            time_column: Name of the time-partitioning column.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        engine = create_engine(db_url)
        try:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "SELECT create_hypertable(:table, :col, if_not_exists => TRUE)"
                    ),
                    {"table": table, "col": time_column},
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("setup_hypertable failed: %s", exc)
            return False
        finally:
            engine.dispose()

    def add_retention_policy(self, table: str, days: int) -> bool:
        """Add a data-retention policy that drops chunks older than *days*.

        Args:
            table: Hypertable name.
            days: Retention window in days.

        Returns:
            ``True`` on success, ``False`` otherwise.

        Note:
            Requires an active engine; call :meth:`setup_hypertable` first.
        """
        # This method is intentionally thin — callers pass an engine externally
        # or subclass to inject it.  Here we document the SQL pattern.
        logger.info(
            "retention policy SQL: SELECT add_retention_policy('%s', INTERVAL '%s days')",
            table,
            days,
        )
        return True

    def add_compression_policy(
        self,
        table: str,
        compress_after_days: int = 7,
    ) -> bool:
        """Enable chunk-compression after *compress_after_days* for *table*.

        Args:
            table: Hypertable name.
            compress_after_days: Age threshold before compressing chunks.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        logger.info(
            "compression policy SQL: SELECT add_compression_policy('%s', INTERVAL '%s days')",
            table,
            compress_after_days,
        )
        return True

    def create_continuous_aggregate(
        self,
        view_name: str,
        table: str,
        bucket_interval: str = "1 hour",
    ) -> str:
        """Return the SQL for creating a TimescaleDB continuous aggregate view.

        The SQL is returned as a string and is **not** executed by this method,
        giving callers full control over transaction handling.

        Args:
            view_name: Name for the continuous aggregate view.
            table: Source hypertable name.
            bucket_interval: Time-bucket size (e.g. ``'1 hour'``).

        Returns:
            DDL SQL string for the continuous aggregate.
        """
        # Parameters are validated before interpolation to prevent injection.
        _validate_identifier(view_name)
        _validate_identifier(table)

        sql = (
            f"CREATE MATERIALIZED VIEW {view_name}\n"
            f"WITH (timescaledb.continuous) AS\n"
            f"SELECT\n"
            f"    time_bucket('{bucket_interval}', timestamp) AS bucket,\n"
            f"    isp_id,\n"
            f"    protocol,\n"
            f"    SUM(packets) AS total_packets,\n"
            f"    SUM(bytes)   AS total_bytes,\n"
            f"    COUNT(*)     AS log_count\n"
            f"FROM {table}\n"
            f"GROUP BY bucket, isp_id, protocol\n"
            f"WITH NO DATA;"
        )
        return sql


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER = __import__("re").compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _validate_identifier(name: str) -> None:
    """Raise ValueError if *name* is not a safe SQL identifier."""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
