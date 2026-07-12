from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Float
import uuid
from datetime import datetime
from app.core.db import Base
class Course(Base):
    __tablename__ = "courses"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    instructor_id = Column(String(64), nullable=False, index=True)
    code = Column(String(64), unique=True, nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    level = Column(String(32), default="beginner")  # beginner, intermediate, advanced
    price = Column(Float, default=0)
    duration_hours = Column(Integer, default=0)
    cover_image = Column(String(512))
    published = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(64), nullable=False, index=True)
    idx = Column(Integer, default=0)
    title = Column(String(256))
    content = Column(Text)
    video_url = Column(String(512))
    duration_min = Column(Integer, default=0)
    resources = Column(JSON, default=list)
class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="active")  # active, completed, dropped
    progress_pct = Column(Float, default=0)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(64), nullable=False, index=True)
    lesson_id = Column(String(64), index=True, nullable=True)
    title = Column(String(256))
    questions = Column(JSON, default=list)  # [{q, choices, correct}]
    passing_score = Column(Integer, default=70)
class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    score = Column(Float)
    passed = Column(Integer, default=0)
    answers = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    enrollment_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    course_id = Column(String(64), nullable=False, index=True)
    serial = Column(String(64), unique=True, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)
