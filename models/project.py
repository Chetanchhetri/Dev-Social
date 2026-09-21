import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, BigInteger, Enum
import enum
from db.session import Base

class OperationState(str, enum.Enum):
    CREATED = "CREATED"
    RESERVED = "RESERVED"
    STAGED = "STAGED"
    PROMOTED = "PROMOTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    source_type = Column(String(20), nullable=False)  # "GITHUB" or "ZIP"
    github_url = Column(String(255), nullable=True)
    
    disk_directory = Column(String(255), nullable=False)
    disk_size_bytes = Column(BigInteger, default=0, nullable=False)
    
    file_tree = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectOperation(Base):
    __tablename__ = "project_operations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_uuid = Column(String(36), nullable=False)
    
    state = Column(Enum(OperationState), default=OperationState.CREATED, nullable=False)
    reserved_bytes = Column(BigInteger, nullable=False)
    actual_bytes = Column(BigInteger, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)