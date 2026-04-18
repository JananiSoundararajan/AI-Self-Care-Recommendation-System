from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    checkin_id = Column(Integer, ForeignKey("checkins.id"), nullable=False)
    mood_label = Column(String, nullable=False)
    morning = Column(Text, nullable=False)
    afternoon = Column(Text, nullable=False)
    evening = Column(Text, nullable=False)
    focus_tip = Column(Text, nullable=True)
    raw_plan = Column(Text, nullable=True)   # full LLM output stored for debug
    created_at = Column(DateTime(timezone=True), server_default=func.now())
