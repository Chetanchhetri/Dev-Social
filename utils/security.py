import hashlib
import random
from datetime import datetime, timedelta
import jwt
from config.settings import settings

def hash_password(password: str) -> str:
    """Hashes plain password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored SHA-256 hash."""
    return hash_password(plain_password) == hashed_password

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)