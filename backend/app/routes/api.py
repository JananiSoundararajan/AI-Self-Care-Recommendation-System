"""
API routes.

POST  /api/v1/checkin                  — submit daily check-in, trigger full pipeline
GET   /api/v1/recommendation/{user_id} — fetch latest recommendation for a user
GET   /api/v1/history/{user_id}        — fetch check-in history
GET   /api/v1/health                   — liveness probe
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import get_db
from app.models.checkin import CheckIn
from app.models.recommendation import Recommendation
from app.models.schemas import (
    CheckInCreate, CheckInResponse,
    RecommendationResponse, RecommendationPlan,
    HistoryItem,
)
from app.ml.classifier import classify_wellness
from app.services.recommender import create_recommendation

router = APIRouter(prefix="/api/v1", tags=["selfcare"])


# ── POST /checkin ──────────────────────────────────────────────────────────────

@router.post("/checkin", response_model=RecommendationResponse, status_code=201)
def submit_checkin(payload: CheckInCreate, db: Session = Depends(get_db)):
    """
    Accept user check-in data.
    Runs ML classification → RAG retrieval → LLM plan generation.
    Returns the personalized recommendation immediately.
    """
    # 1. Classify wellness label
    mood_label = classify_wellness(
        payload.mood, payload.sleep_hours,
        payload.stress_level, payload.activity_level,
    )

    # 2. Persist check-in
    checkin = CheckIn(
        user_id=payload.user_id,
        mood=payload.mood,
        sleep_hours=payload.sleep_hours,
        stress_level=payload.stress_level,
        activity_level=payload.activity_level,
        note=payload.note,
        mood_label=mood_label,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    # 3. Run full recommendation pipeline
    rec = create_recommendation(db, checkin)

    return RecommendationResponse(
        user_id=rec.user_id,
        checkin_id=rec.checkin_id,
        mood_label=rec.mood_label,
        recommendations=RecommendationPlan(
            morning=rec.morning,
            afternoon=rec.afternoon,
            evening=rec.evening,
            focus_tip=rec.focus_tip,
        ),
        generated_at=rec.created_at or datetime.utcnow(),
    )


# ── GET /recommendation/{user_id} ─────────────────────────────────────────────

@router.get("/recommendation/{user_id}", response_model=RecommendationResponse)
def get_latest_recommendation(user_id: str, db: Session = Depends(get_db)):
    """Fetch the most recent recommendation for a user."""
    rec = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
        .first()
    )
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for user '{user_id}'. Submit a check-in first.",
        )

    return RecommendationResponse(
        user_id=rec.user_id,
        checkin_id=rec.checkin_id,
        mood_label=rec.mood_label,
        recommendations=RecommendationPlan(
            morning=rec.morning,
            afternoon=rec.afternoon,
            evening=rec.evening,
            focus_tip=rec.focus_tip,
        ),
        generated_at=rec.created_at or datetime.utcnow(),
    )


# ── GET /history/{user_id} ────────────────────────────────────────────────────

@router.get("/history/{user_id}", response_model=list[HistoryItem])
def get_user_history(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Return up to `limit` recent check-ins for the user."""
    rows = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user_id)
        .order_by(CheckIn.created_at.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for user '{user_id}'.",
        )
    return [
        HistoryItem(
            checkin_id=r.id,
            mood=r.mood,
            sleep_hours=r.sleep_hours,
            stress_level=r.stress_level,
            activity_level=r.activity_level,
            mood_label=r.mood_label,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "selfcare-ai"}
