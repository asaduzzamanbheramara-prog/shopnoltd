import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.core.db import Base


class Post(Base):
    __tablename__ = "posts"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    media = Column(String, default=list)  # JSON array of object keys in MinIO
    visibility = Column(String(16), default="public")  # public, tenant, friends, private
    auto_posted: bool = False  # legacy column ignored
    auto_posted2: bool = False
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow, index=True)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Like(Base):
    __tablename__ = "likes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(
        String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_like_post_user", "post_id", "user_id", unique=True),)


class Share(Base):
    __tablename__ = "shares"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(
        String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    target = Column(String(16), default="internal")  # internal, twitter, facebook, linkedin, copy
    created_at = Column(DateTime, default=datetime.utcnow)


class Follow(Base):
    __tablename__ = "follows"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String(64), nullable=False, index=True)
    followee_id = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="accepted")  # accepted, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_follow_pair", "follower_id", "followee_id", unique=True),)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(
        String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
