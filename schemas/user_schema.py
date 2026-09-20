from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class PublicUserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[PublicUserRole] = PublicUserRole.USER

class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str