from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Request schemas ────────────────────────────────────────────────────────────

class CheckInCreate(BaseModel):
    user_id: str = Field(..., example="user_42")
    mood: int = Field(..., ge=1, le=10, example=4)
    sleep_hours: float = Field(..., ge=0, le=24, example=5.5)
    stress_level: int = Field(..., ge=1, le=10, example=8)
    activity_level: int = Field(..., ge=1, le=10, example=3)
    note: Optional[str] = Field(None, example="Big deadline tomorrow, feeling anxious")


# ── Response schemas ───────────────────────────────────────────────────────────

class CheckInResponse(BaseModel):
    checkin_id: int
    user_id: str
    mood_label: str
    message: str

    class Config:
        from_attributes = True


class RecommendationPlan(BaseModel):
    morning: str
    afternoon: str
    evening: str
    focus_tip: Optional[str] = None


class RecommendationResponse(BaseModel):
    user_id: str
    checkin_id: int
    mood_label: str
    recommendations: RecommendationPlan
    generated_at: datetime

    class Config:
        from_attributes = True


class HistoryItem(BaseModel):
    checkin_id: int
    mood: int
    sleep_hours: float
    stress_level: int
    activity_level: int
    mood_label: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
