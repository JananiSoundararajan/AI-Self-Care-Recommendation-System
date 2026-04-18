from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base


class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    mood = Column(Integer, nullable=False)          # 1–10
    sleep_hours = Column(Float, nullable=False)     # e.g. 6.5
    stress_level = Column(Integer, nullable=False)  # 1–10
    activity_level = Column(Integer, nullable=False)  # 1–10
    note = Column(Text, nullable=True)
    mood_label = Column(String, nullable=True)      # low / medium / high (ML output)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
