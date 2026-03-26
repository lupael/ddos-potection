"""
GeoIP service using MaxMind GeoLite2 database.
Falls back to stub data if database not available.
"""
import hashlib
import logging

from config import settings

logger = logging.getLogger(__name__)


class GeoIPService:
    """Looks up geographic information for IP addresses."""

    def __init__(self):
        self.available = False
        self._reader = None

        db_path = getattr(settings, "GEOIP_CITY_DB_PATH", settings.GEOIP_DATABASE_PATH)
        try:
            import geoip2.database  # type: ignore
            self._reader = geoip2.database.Reader(db_path)
            self.available = True
            logger.info("GeoIP database loaded from %s", db_path)
        except ImportError:
            logger.warning("geoip2 library not installed; using stub GeoIP data")
        except FileNotFoundError:
            logger.warning("GeoIP database not found at %s; using stub data", db_path)
        except Exception as exc:
            logger.warning("Failed to open GeoIP database: %s; using stub data", exc)

    def lookup(self, ip: str) -> dict:
        """Return geo information for *ip*.

        Returns a dict with keys: country, city, lat, lon.
        Falls back to deterministic hash-based coordinates when the database
        is not available.
        """
        if not ip or ip in ("unknown", ""):
            return {"country": "Unknown", "city": "Unknown", "lat": 0.0, "lon": 0.0}

        if self.available and self._reader is not None:
            try:
                record = self._reader.city(ip)
                return {
                    "country": record.country.iso_code or "Unknown",
                    "city": record.city.name or "Unknown",
                    "lat": float(record.location.latitude or 0.0),
                    "lon": float(record.location.longitude or 0.0),
                }
            except Exception:
                pass

        # Deterministic stub based on IP hash (sha256, no cryptographic use)
        hash_bytes = hashlib.sha256(ip.encode()).digest()
        hash_val = int.from_bytes(hash_bytes[:8], "big")
        lat = ((hash_val % 180) - 90) + (hash_val % 100) / 1000.0
        lon = (((hash_val // 180) % 360) - 180) + (hash_val % 100) / 1000.0
        return {
            "country": "Unknown",
            "city": "Unknown",
            "lat": round(lat, 4),
            "lon": round(lon, 4),
        }

    def get_country(self, ip: str) -> str:
        """Convenience method — returns the ISO country code for *ip*."""
        return self.lookup(ip).get("country", "Unknown")

    def __del__(self):
        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass


# Module-level singleton
geoip_service = GeoIPService()
