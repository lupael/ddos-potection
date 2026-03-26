"""
ML-based adaptive baseline service using Isolation Forest.
Learns normal traffic patterns and detects statistical anomalies.
"""
import json
import logging
from typing import Optional

import numpy as np
import redis
from sklearn.ensemble import IsolationForest

from config import settings

logger = logging.getLogger(__name__)

# Redis key template for per-prefix rolling buffers
_BUFFER_KEY = "baseline:{prefix}:{metric}"
_BUFFER_ALL_KEY = "baseline:{prefix}:_all"


class BaselineService:
    """Adaptive baseline using a Redis-backed circular buffer and Isolation Forest."""

    def __init__(self) -> None:
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self.window_size: int = getattr(settings, "BASELINE_WINDOW_SIZE", 1000)
        self.min_samples: int = getattr(settings, "BASELINE_MIN_SAMPLES", 100)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _push(self, key: str, value) -> None:
        """Append *value* to the circular buffer at *key*, trimming to window."""
        pipe = self.redis_client.pipeline()
        pipe.rpush(key, value)
        pipe.ltrim(key, -self.window_size, -1)
        pipe.execute()

    def _get_buffer(self, key: str) -> list[float]:
        """Return all values currently stored in the buffer."""
        raw = self.redis_client.lrange(key, 0, -1)
        return [float(v) for v in raw]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_baseline(self, prefix: str, pps: float, bps: float, fps: float) -> None:
        """Append a new observation to the per-prefix rolling buffers.

        Args:
            prefix: Network prefix (e.g. ``"192.0.2.0/24"``).
            pps:    Packets per second.
            bps:    Bytes per second.
            fps:    Flows per second.
        """
        try:
            self._push(_BUFFER_KEY.format(prefix=prefix, metric="pps"), pps)
            self._push(_BUFFER_KEY.format(prefix=prefix, metric="bps"), bps)
            self._push(_BUFFER_KEY.format(prefix=prefix, metric="fps"), fps)
            # Combined buffer stores [pps, bps, fps] as a JSON array for the
            # multi-variate Isolation Forest.
            self._push(
                _BUFFER_ALL_KEY.format(prefix=prefix),
                json.dumps([pps, bps, fps]),
            )
        except Exception as e:
            logger.error("BaselineService.update_baseline error: %s", e)

    def is_anomalous(
        self, prefix: str, pps: float, bps: float, fps: float
    ) -> tuple[bool, float]:
        """Determine whether the observation is anomalous.

        Uses a multi-variate Isolation Forest trained on historical data for
        *prefix*.

        Returns:
            ``(is_anomaly, anomaly_score)`` where *anomaly_score* is the raw
            ``decision_function`` value from Isolation Forest (more negative →
            more anomalous).  In shadow mode (insufficient data) returns
            ``(False, 0.0)``.
        """
        try:
            raw = self.redis_client.lrange(
                _BUFFER_ALL_KEY.format(prefix=prefix), 0, -1
            )
            if len(raw) < self.min_samples:
                return False, 0.0

            X = np.array([json.loads(v) for v in raw], dtype=float)
            sample = np.array([[pps, bps, fps]], dtype=float)

            clf = IsolationForest(contamination=0.05, random_state=42)
            clf.fit(X)

            score = float(clf.decision_function(sample)[0])
            prediction = clf.predict(sample)[0]  # -1 = anomaly, 1 = normal
            return prediction == -1, score

        except Exception as e:
            logger.error("BaselineService.is_anomalous error: %s", e)
            return False, 0.0

    def get_adaptive_threshold(
        self, prefix: str, metric: str, multiplier: float = 3.0
    ) -> float:
        """Compute mean + N×std from historical data for a single metric.

        Args:
            prefix:     Network prefix.
            metric:     One of ``"pps"``, ``"bps"``, ``"fps"``.
            multiplier: Number of standard deviations above mean (default 3.0).

        Returns:
            Adaptive threshold value, or 0.0 if insufficient data.
        """
        try:
            data = self._get_buffer(
                _BUFFER_KEY.format(prefix=prefix, metric=metric)
            )
            if len(data) < self.min_samples:
                return 0.0

            arr = np.array(data, dtype=float)
            return float(np.mean(arr) + multiplier * np.std(arr))
        except Exception as e:
            logger.error("BaselineService.get_adaptive_threshold error: %s", e)
            return 0.0
