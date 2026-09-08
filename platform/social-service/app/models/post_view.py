import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from app.core.db import Base


class PostView(Base):
    __tablename__ = "post_views"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_post_view_post_user", "post_id", "user_id", unique=True),)
