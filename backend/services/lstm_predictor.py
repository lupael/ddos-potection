"""
LSTM-inspired attack predictor.

Uses a GradientBoostingClassifier as a practical approximation of the
time-series forecasting an LSTM would provide.  The class exposes the same
interface so the router layer is decoupled from the underlying model.
"""
import logging
import warnings
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import GradientBoostingClassifier
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed – LSTMPredictor will use stub predictions")

# Prefer joblib (sklearn-recommended serialiser) over pickle for ML models.
try:
    import joblib as _serialiser
    _USE_JOBLIB = True
except ImportError:
    import pickle as _serialiser  # type: ignore[no-redef]
    _USE_JOBLIB = False


class LSTMPredictor:
    """Time-series attack predictor backed by GradientBoostingClassifier.

    Despite the name the implementation uses gradient boosting (a widely
    available sklearn estimator) as an approximation of the temporal pattern
    recognition that an LSTM would perform.
    """

    FEATURE_KEYS = ("pps", "bps", "syn_ratio", "udp_ratio", "icmp_ratio")

    def __init__(self, sequence_length: int = 60) -> None:
        """Initialise the predictor.

        Args:
            sequence_length: Number of time-steps used as context window.
                             Retained for interface compatibility.
        """
        self.sequence_length = sequence_length
        self._model: Optional[object] = None
        self._trained = False

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def prepare_features(self, traffic_data: list[dict]) -> list[list[float]]:
        """Extract a fixed-length feature vector from each traffic snapshot.

        Args:
            traffic_data: List of per-second traffic dicts.  Each dict may
                contain keys ``pps``, ``bps``, ``syn_ratio``, ``udp_ratio``,
                ``icmp_ratio``.  Missing keys default to ``0.0``.

        Returns:
            List of ``[pps, bps, syn_ratio, udp_ratio, icmp_ratio]`` vectors.
        """
        result: list[list[float]] = []
        for point in traffic_data:
            row = [float(point.get(k, 0.0)) for k in self.FEATURE_KEYS]
            result.append(row)
        return result

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def train(self, X: list, y: list) -> bool:
        """Fit the classifier on labelled traffic feature vectors.

        Args:
            X: Feature matrix – list of ``[pps, bps, syn_ratio, …]`` vectors.
            y: Binary labels – 1 = attack, 0 = benign.

        Returns:
            ``True`` on success, ``False`` if sklearn is unavailable or an
            error occurs.
        """
        if not _SKLEARN_AVAILABLE:
            logger.error("train() called but sklearn is not installed")
            return False
        try:
            self._model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            self._model.fit(X, y)
            self._trained = True
            logger.info("LSTMPredictor trained on %d samples", len(X))
            return True
        except Exception as exc:
            logger.error("LSTMPredictor.train error: %s", exc)
            return False

    def predict(self, recent_data: list[dict]) -> dict:
        """Predict whether an attack is imminent based on recent traffic.

        Args:
            recent_data: Most-recent traffic snapshots (same format as
                         :meth:`prepare_features`).

        Returns:
            Dict with keys:
            - ``attack_probability`` (float 0–1)
            - ``predicted_attack_in_seconds`` (int)
            - ``confidence`` (float 0–1)
        """
        if not _SKLEARN_AVAILABLE or not self._trained or self._model is None:
            return {
                "attack_probability": 0.0,
                "predicted_attack_in_seconds": 0,
                "confidence": 0.0,
            }
        try:
            features = self.prepare_features(recent_data)
            if not features:
                return {
                    "attack_probability": 0.0,
                    "predicted_attack_in_seconds": 0,
                    "confidence": 0.0,
                }
            # Use the last sample for prediction
            sample = [features[-1]]
            proba = self._model.predict_proba(sample)[0]
            # proba[1] = P(attack)
            attack_prob = float(proba[1]) if len(proba) > 1 else 0.0
            # Rough heuristic: if probability is high predict attack in ~30 s
            predicted_seconds = int((1.0 - attack_prob) * self.sequence_length)
            return {
                "attack_probability": round(attack_prob, 4),
                "predicted_attack_in_seconds": predicted_seconds,
                "confidence": round(max(proba), 4),
            }
        except Exception as exc:
            logger.error("LSTMPredictor.predict error: %s", exc)
            return {
                "attack_probability": 0.0,
                "predicted_attack_in_seconds": 0,
                "confidence": 0.0,
            }

    def save_model(self, path: str) -> bool:
        """Persist the trained model to *path* using pickle.

        Args:
            path: Filesystem path for the pickle file.

        Returns:
            ``True`` on success.
        """
        if self._model is None:
            logger.warning("save_model called but no model is trained")
            return False
        try:
            with open(path, "wb") as fh:
                _serialiser.dump(self._model, fh)
            logger.info("LSTMPredictor model saved to %s", path)
            return True
        except Exception as exc:
            logger.error("LSTMPredictor.save_model error: %s", exc)
            return False

    def load_model(self, path: str) -> bool:
        """Load a previously pickled model from *path*.

        Args:
            path: Filesystem path of the pickle file.

        Returns:
            ``True`` on success.
        """
        try:
            with open(path, "rb") as fh:
                self._model = _serialiser.load(fh)
            self._trained = True
            logger.info("LSTMPredictor model loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("LSTMPredictor.load_model error: %s", exc)
            return False
