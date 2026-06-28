"""
routers/auth.py — Authentication
POST /auth/demo-login  → dev-only, creates/gets demo user, returns JWT
GET  /auth/me          → returns current user profile
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt
import requests
from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.user import TokenResponse, UserOut
from app.routers.deps import get_current_user
from app.services.google_calendar import get_google_flow

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

@router.get("/google/login")
def google_login():
    flow = get_google_flow()
    
    # Disable PKCE to avoid cookie domain mismatch issues (localhost vs 127.0.0.1)
    flow.autogenerate_code_verifier = False
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' # force prompt to get refresh token
    )
    return RedirectResponse(auth_url)

@router.get("/google/callback")
def google_callback(request: Request, db: Session = Depends(get_db)):
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    state = request.query_params.get("state")
    flow = get_google_flow(state=state)
        
    flow.fetch_token(authorization_response=str(request.url))
    
    credentials = flow.credentials
    # Get user info from Google
    user_info = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', 
                             headers={'Authorization': f'Bearer {credentials.token}'}).json()
    
    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture", "")
    
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=picture,
            google_access_token=credentials.token,
            google_refresh_token=credentials.refresh_token,
            google_token_expiry=credentials.expiry,
            preferences={
                "focus_mode": "pomodoro", "pomodoro_work_mins": 25, "pomodoro_break_mins": 5,
                "pomodoro_long_break_mins": 20, "deepwork_block_mins": 90,
                "streak_count": 0, "last_streak_date": str(datetime.now().date()),
                "preferred_style": None, "total_focus_minutes": 0,
                "shutdown_time": "17:00"
            }
        )
        db.add(user)
    else:
        # Update tokens
        user.google_access_token = credentials.token
        if credentials.refresh_token:
            user.google_refresh_token = credentials.refresh_token
        user.google_token_expiry = credentials.expiry
    
    db.commit()
    db.refresh(user)
    
    token = create_jwt(user.id)
    # Redirect to frontend root with token in URL search params
    return RedirectResponse(f"{settings.FRONTEND_URL}/?token={token}")

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)

from app.schemas.user import UserPreferencesUpdate

@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(data: UserPreferencesUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    current_prefs = user.preferences or {}
    current_prefs.update(data.preferences)
    
    # We must assign a new dict or use flag_modified for SQLAlchemy to detect JSON mutation
    user.preferences = dict(current_prefs)
    
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
