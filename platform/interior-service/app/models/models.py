from sqlalchemy import Column, String, DateTime, Integer, JSON, Float
import uuid
from datetime import datetime
from app.core.db import Base
class Project(Base):
    __tablename__ = "interior_projects"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(String(2000))
    style = Column(String(64), default="modern")
    budget = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class Model3D(Base):
    __tablename__ = "interior_models"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256))
    format = Column(String(16))  # glb, obj, fbx
    file_path = Column(String(512))
    thumbnail = Column(String(512))
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class Room(Base):
    __tablename__ = "interior_rooms"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128))
    width_m = Column(Float, default=4.0)
    length_m = Column(Float, default=5.0)
    height_m = Column(Float, default=2.7)
    color = Column(String(16), default="#ffffff")
    furniture = Column(JSON, default=list)
