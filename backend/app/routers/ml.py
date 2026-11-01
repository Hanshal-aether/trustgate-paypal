from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app import ml_scoring

router = APIRouter(prefix="/api/ml", tags=["ml"])


class MLScoreRequest(BaseModel):
    email: str
    fingerprint: str
    user_agent: Optional[str] = None


@router.get("/status")
def ml_status():
    return ml_scoring.status()


@router.post("/score")
def ml_score(payload: MLScoreRequest):
    """Dry run: scores an event WITHOUT recording it into the velocity counters."""
    result = ml_scoring.score_event(payload.email, payload.fingerprint, payload.user_agent, record=False)
    if result is None:
        return {"ml_enabled": False, "detail": "model files not found in backend/app/model/"}
    return {"ml_enabled": True, **result}
