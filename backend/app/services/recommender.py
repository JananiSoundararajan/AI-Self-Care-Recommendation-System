"""
Recommendation service.

Orchestrates the full pipeline:
  1. Classify wellness state (ML)
  2. Retrieve relevant wellness tips (ChromaDB RAG)
  3. Build history summary from DB
  4. Generate personalized plan (LLM)
  5. Persist recommendation
  6. Return structured response
"""

import logging
from sqlalchemy.orm import Session
from app.models.checkin import CheckIn
from app.models.recommendation import Recommendation
from app.ml.classifier import classify_wellness
from app.services.memory import retrieve_context
from app.services.llm import generate_plan

logger = logging.getLogger(__name__)


def get_user_history(db: Session, user_id: str, limit: int = 7) -> list[dict]:
    """Fetch the user's last N check-ins as plain dicts for the LLM prompt."""
    rows = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user_id)
        .order_by(CheckIn.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "mood": r.mood,
            "sleep_hours": r.sleep_hours,
            "stress_level": r.stress_level,
            "activity_level": r.activity_level,
            "created_at": str(r.created_at)[:10] if r.created_at else "unknown",
        }
        for r in rows
    ]


def create_recommendation(
    db: Session,
    checkin: CheckIn,
) -> Recommendation:
    """Full pipeline: ML → RAG → LLM → DB persist → return."""

    # 1. ML classification (already stored on checkin, re-used here)
    mood_label = checkin.mood_label or classify_wellness(
        checkin.mood, checkin.sleep_hours, checkin.stress_level, checkin.activity_level
    )

    # 2. RAG: build a context query and retrieve relevant tips
    rag_query = (
        f"stress {checkin.stress_level}/10, "
        f"sleep {checkin.sleep_hours} hours, "
        f"mood {checkin.mood}/10, "
        f"activity {checkin.activity_level}/10. "
        f"{checkin.note or ''}"
    )
    rag_tips = retrieve_context(rag_query, n_results=3)

    # 3. Recent history
    history = get_user_history(db, checkin.user_id, limit=7)

    # 4. LLM plan generation
    plan = generate_plan(
        mood=checkin.mood,
        sleep_hours=checkin.sleep_hours,
        stress_level=checkin.stress_level,
        activity_level=checkin.activity_level,
        mood_label=mood_label,
        note=checkin.note,
        history=history,
        rag_context=rag_tips,
    )

    # 5. Persist
    rec = Recommendation(
        user_id=checkin.user_id,
        checkin_id=checkin.id,
        mood_label=mood_label,
        morning=plan.get("morning", ""),
        afternoon=plan.get("afternoon", ""),
        evening=plan.get("evening", ""),
        focus_tip=plan.get("focus_tip"),
        raw_plan=str(plan),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    logger.info(f"Recommendation {rec.id} created for user {checkin.user_id}")
    return rec
