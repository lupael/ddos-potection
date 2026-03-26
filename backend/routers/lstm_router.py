"""
LSTM attack predictor router.

Provides model status and prediction endpoints backed by
:class:`~services.lstm_predictor.LSTMPredictor`.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from models.models import User
from routers.auth_router import get_current_user
from services.lstm_predictor import LSTMPredictor, _SKLEARN_AVAILABLE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml/lstm", tags=["ML – LSTM Predictor"])

# Module-level predictor instance (lightweight; no heavy state until trained)
_predictor = LSTMPredictor()


@router.get("/status")
async def lstm_status(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return current model status information.

    Returns:
        JSON with ``sklearn_available``, ``model_trained``, and
        ``sequence_length``.
    """
    return {
        "sklearn_available": _SKLEARN_AVAILABLE,
        "model_trained": _predictor._trained,
        "sequence_length": _predictor.sequence_length,
        "isp_id": current_user.isp_id,
    }


@router.post("/predict")
async def lstm_predict(
    payload: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run the attack predictor against recent traffic data.

    Request body (JSON):
    ```json
    {
      "traffic_data": [
        {"pps": 1000, "bps": 5000000, "syn_ratio": 0.1, "udp_ratio": 0.6, "icmp_ratio": 0.05},
        …
      ]
    }
    ```

    Returns:
        Prediction dict with ``attack_probability``, ``predicted_attack_in_seconds``,
        and ``confidence``.
    """
    traffic_data: List[dict] = payload.get("traffic_data", [])
    if not isinstance(traffic_data, list) or not traffic_data:
        raise HTTPException(status_code=422, detail="traffic_data must be a non-empty list")

    result = _predictor.predict(traffic_data)
    result["isp_id"] = current_user.isp_id
    return result
