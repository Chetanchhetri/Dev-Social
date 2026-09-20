# User profile, skills, XP & badges
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from db.session import Base

class UserRole(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    USER = "USER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)