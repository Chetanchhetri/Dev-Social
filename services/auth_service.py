from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.user import User, UserRole
from schemas.user_schema import UserRegister, VerifyOTP, UserLogin
from utils.security import hash_password, verify_password, generate_otp, create_access_token
from utils.email_send import send_otp_email
from config.settings import settings

class AuthService:

    @staticmethod
    def register_user(db: Session, data: UserRegister):
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),  # Stores SHA-256 hash
            role=UserRole(data.role.value),
            is_verified=False,
            otp_code=otp,
            otp_expires_at=otp_expiry
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        send_otp_email(user.email, otp)
        return {"message": f"Registration successful as {user.role.value}. OTP sent to email."}

    @staticmethod
    def verify_otp(db: Session, data: VerifyOTP):
        user = db.query(User).filter(User.email == data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_verified:
            return {"message": "Account is already verified."}

        if user.otp_code != data.otp or user.otp_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        user.is_verified = True
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        return {
            "message": "Account verified successfully", 
            "access_token": token, 
            "token_type": "bearer", 
            "role": user.role.value
        }

    @staticmethod
    def login_user(db: Session, data: UserLogin):
        user = db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Account not verified. Please verify your OTP.")

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        return {"access_token": token, "token_type": "bearer", "role": user.role.value}