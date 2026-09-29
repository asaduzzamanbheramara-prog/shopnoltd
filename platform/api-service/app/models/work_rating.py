import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from app.core.db import Base

class WorkRating(Base):
    __tablename__ = "work_ratings"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(String(64), ForeignKey("work_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    rater_id = Column(String(128), nullable=False, index=True)
    rated_id = Column(String(128), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("ix_work_rating_unique", "submission_id", "rater_id", unique=True),)
