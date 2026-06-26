"""
routers/auth.py — Authentication
POST /auth/demo-login  → dev-only, creates/gets demo user, returns JWT
GET  /auth/me          → returns current user profile
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.user import TokenResponse, UserOut
from app.routers.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

def create_jwt(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

@router.post("/demo-login", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)):
    """Dev-only demo login — creates a demo user if needed, returns JWT."""
    user = db.query(User).filter(User.google_id == "demo_user_001").first()
    if not user:
        user = User(
            google_id="demo_user_001",
            email="demo@aiproductivity.app",
            name="Demo User",
            avatar_url="",
            preferences={
                "focus_mode": "pomodoro", "pomodoro_work_mins": 25, "pomodoro_break_mins": 5,
                "pomodoro_long_break_mins": 20, "deepwork_block_mins": 90,
                "streak_count": 3, "last_streak_date": str(datetime.now().date()),
                "preferred_style": None, "total_focus_minutes": 120,
            }
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_jwt(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
