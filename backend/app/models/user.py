"""
models/user.py — User ORM Model

Supports dual auth:
  - google_id: Google OAuth (our custom flow, still active)
  - supabase_uid: Supabase Auth user UUID (for Supabase Auth sign-ins)
  - A user may have either or both set depending on how they authenticated.

preferences JSONB stores:
  focus_mode, pomodoro_work_mins, pomodoro_break_mins, pomodoro_long_break_mins,
  deepwork_block_mins, streak_count, last_streak_date, preferred_style,
  total_focus_minutes, shutdown_time
"""
from sqlalchemy import BigInteger, String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ── Auth identifiers ───────────────────────────────────────────────
    # Google OAuth (custom FastAPI flow)
    google_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=True, index=True)
    # Supabase Auth UUID (for users who sign in via Supabase Auth)
    supabase_uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=True, index=True)

    # ── Profile ────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Google OAuth tokens (for Calendar sync) ───────────────────────
    google_access_token: Mapped[str] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
    google_token_expiry: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── User Preferences (JSONB) ───────────────────────────────────────
    preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    commitments: Mapped[list["Commitment"]] = relationship("Commitment", back_populates="user", cascade="all, delete-orphan")
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    focus_sessions: Mapped[list["FocusSession"]] = relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship("WeeklyPlan", back_populates="user", cascade="all, delete-orphan")
    daily_plans: Mapped[list["DailyPlan"]] = relationship("DailyPlan", back_populates="user", cascade="all, delete-orphan")
    daily_highlights: Mapped[list["DailyHighlight"]] = relationship("DailyHighlight", back_populates="user", cascade="all, delete-orphan")

    @property
    def default_preferences(self) -> dict:
        return {
            "focus_mode": "pomodoro",
            "pomodoro_work_mins": 25,
            "pomodoro_break_mins": 5,
            "pomodoro_long_break_mins": 20,
            "deepwork_block_mins": 90,
            "streak_count": 0,
            "last_streak_date": "",
            "preferred_style": None,
            "total_focus_minutes": 0,
            "shutdown_time": "17:00",
        }
