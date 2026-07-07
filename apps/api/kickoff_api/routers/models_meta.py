from __future__ import annotations

from fastapi import APIRouter

from kickoff_api.helpers import require_ready
from kickoff_api.state import STATE

router = APIRouter(tags=["models"])


@router.get("/models/current")
def current_model() -> dict:
    require_ready()
    return {
        "model_card": STATE.model_card,
        "elo_tuning": STATE.elo_tuning,
        "artifact": "ml/artifacts/prediction_bundle.joblib",
    }


@router.get("/models/metrics")
def model_metrics() -> dict:
    require_ready()
    return {
        "metrics": STATE.metrics,
        "comparison": STATE.model_comparison,
        "calibration": STATE.calibration,
    }
