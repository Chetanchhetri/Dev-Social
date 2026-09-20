# OAuth, login, registration
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from schemas.user_schema import UserRegister, VerifyOTP, UserLogin, TokenResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    return AuthService.register_user(db, data)

@router.post("/verify-otp")
def verify_otp(data: VerifyOTP, db: Session = Depends(get_db)):
    return AuthService.verify_otp(db, data)

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    return AuthService.login_user(db, data)