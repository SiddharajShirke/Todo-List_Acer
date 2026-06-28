"""
routers/auth.py — Authentication (Dual Auth Support)

Supported auth flows:
  1. Google OAuth (existing flow — unchanged)
     GET  /auth/google/login    → redirect to Google consent screen
     GET  /auth/google/callback → exchange code, create/update user, return JWT
  
  2. Supabase Auth (NEW — for email/password, magic link, social via Supabase)
     POST /auth/supabase        → verify Supabase JWT, create/sync user, return our app JWT
  
  3. Demo Login (dev only)
     POST /auth/demo-login      → quick dev login

Common:
  GET  /auth/me                → current user profile
  PATCH /auth/me/preferences   → update user preferences
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt
import requests as http_requests
from app.database import get_db, get_supabase_anon
from app.config import settings
from app.models.user import User
from app.schemas.user import TokenResponse, UserOut, UserPreferencesUpdate
from app.routers.deps import get_current_user
from app.services.google_calendar import get_google_flow
from pydantic import BaseModel
from typing import Optional
from loguru import logger

router = APIRouter(prefix="/auth", tags=["auth"])


# ── JWT Helpers ────────────────────────────────────────────────────────────────
def create_jwt(user_id: int) -> str:
    """Create our application JWT (not Supabase JWT)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _get_or_create_user_by_email(email: str, db: Session, **kwargs) -> User:
    """Find user by email or create if new. Handles merging of auth providers."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, **kwargs)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created: {email}")
    return user


# ── Demo Login (Dev Only) ──────────────────────────────────────────────────────
@router.post("/demo-login", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)):
    """Dev-only demo login — creates a demo user if needed, returns JWT."""
    user = db.query(User).filter(User.email == "demo@aiproductivity.app").first()
    if not user:
        user = User(
            email="demo@aiproductivity.app",
            name="Demo User",
            avatar_url="",
            preferences={
                "focus_mode": "pomodoro", "pomodoro_work_mins": 25, "pomodoro_break_mins": 5,
                "pomodoro_long_break_mins": 20, "deepwork_block_mins": 90,
                "streak_count": 3, "last_streak_date": str(datetime.now().date()),
                "preferred_style": None, "total_focus_minutes": 120,
                "shutdown_time": "17:00",
            }
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_jwt(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ── Google OAuth Flow ──────────────────────────────────────────────────────────
@router.get("/google/login")
def google_login(token: Optional[str] = None):
    """Redirect user to Google OAuth consent screen."""
    flow = get_google_flow()
    flow.autogenerate_code_verifier = False  # Disable PKCE for localhost compatibility
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=token if token else "no_token"
    )
    return RedirectResponse(auth_url)


@router.get("/google/callback")
def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback. Creates/updates user, returns app JWT via redirect."""
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

    state = request.query_params.get("state")
    flow = get_google_flow(state=state)
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    # Fetch Google user profile
    user_info = http_requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {credentials.token}'}
    ).json()

    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture", "")

    # If state contains our app JWT, decode it to find the explicit logged-in user
    user_id_from_token = None
    if state and state != "no_token":
        try:
            payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id_from_token = int(payload.get("sub"))
        except Exception as e:
            logger.warning(f"Invalid state token provided to Google callback: {e}")

    user = None
    if user_id_from_token:
        user = db.query(User).filter(User.id == user_id_from_token).first()
    
    if not user:
        # Fallback to finding by google_id or email
        user = db.query(User).filter(User.google_id == google_id).first()
        if not user:
            user = db.query(User).filter(User.email == email).first()

    if not user:
        # New user — create
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
                "shutdown_time": "17:00",
            }
        )
        db.add(user)
    else:
        # Existing user — update tokens + link google_id if not set
        if not user.google_id:
            user.google_id = google_id
        user.google_access_token = credentials.token
        if credentials.refresh_token:
            user.google_refresh_token = credentials.refresh_token
        user.google_token_expiry = credentials.expiry
        user.avatar_url = picture
        user.name = name

    db.commit()
    db.refresh(user)

    token = create_jwt(user.id)
    logger.info(f"Google login successful: {email}")
    return RedirectResponse(f"{settings.FRONTEND_URL}/?token={token}")


# ── Supabase Auth Flow (NEW) ───────────────────────────────────────────────────
class SupabaseAuthRequest(BaseModel):
    supabase_access_token: str   # JWT issued by Supabase Auth


@router.post("/supabase", response_model=TokenResponse)
def supabase_auth(payload: SupabaseAuthRequest, db: Session = Depends(get_db)):
    """
    Verify a Supabase Auth JWT and issue our application JWT.
    
    Flow (frontend):
      1. User signs in via Supabase Auth (email/password, magic link, social)
      2. Supabase returns an access_token
      3. Frontend sends that token here
      4. We verify it, create/sync the user in our DB, return our app JWT
    
    This keeps our app JWT as the single auth token used across all API calls.
    """
    supabase = get_supabase_anon()
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )

    try:
        # Verify the Supabase JWT and get user data
        response = supabase.auth.get_user(payload.supabase_access_token)
        sb_user = response.user
        if not sb_user:
            raise HTTPException(status_code=401, detail="Invalid Supabase token")
    except Exception as e:
        logger.error(f"Supabase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Supabase token verification failed")

    supabase_uid = sb_user.id
    email = sb_user.email
    name = (sb_user.user_metadata or {}).get("full_name") or (sb_user.user_metadata or {}).get("name", "")
    avatar_url = (sb_user.user_metadata or {}).get("avatar_url", "")

    # Find existing user by supabase_uid or email
    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        # New user via Supabase Auth
        user = User(
            supabase_uid=supabase_uid,
            email=email,
            name=name,
            avatar_url=avatar_url,
            preferences={
                "focus_mode": "pomodoro", "pomodoro_work_mins": 25, "pomodoro_break_mins": 5,
                "pomodoro_long_break_mins": 20, "deepwork_block_mins": 90,
                "streak_count": 0, "last_streak_date": str(datetime.now().date()),
                "preferred_style": None, "total_focus_minutes": 0,
                "shutdown_time": "17:00",
            }
        )
        db.add(user)
        logger.info(f"New user via Supabase Auth: {email}")
    else:
        # Link supabase_uid to existing account
        if not user.supabase_uid:
            user.supabase_uid = supabase_uid
        if name and not user.name:
            user.name = name
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url

    db.commit()
    db.refresh(user)

    token = create_jwt(user.id)
    logger.info(f"Supabase auth login: {email}")
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ── Current User ───────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(data: UserPreferencesUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    current_prefs = dict(user.preferences or {})
    current_prefs.update(data.preferences)
    user.preferences = current_prefs
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
