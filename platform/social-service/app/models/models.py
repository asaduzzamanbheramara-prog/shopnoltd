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
    visibility = Column(String(16), default="public")
    auto_posted: bool = False
    auto_posted2: bool = False
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow, index=True)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    author_id = Column(String(64), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    slug = Column(String(320), nullable=False, unique=True, index=True)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    cover_image = Column(String(1024), nullable=True)
    status = Column(String(16), nullable=False, default="draft", index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Like(Base):
    __tablename__ = "likes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_like_post_user", "post_id", "user_id", unique=True),)


class Share(Base):
    __tablename__ = "shares"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    target = Column(String(16), default="internal")
    created_at = Column(DateTime, default=datetime.utcnow)


class Follow(Base):
    __tablename__ = "follows"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String(64), nullable=False, index=True)
    followee_id = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="accepted")
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_follow_pair", "follower_id", "followee_id", unique=True),)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
