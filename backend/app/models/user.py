"""
models/user.py — User ORM Model
preferences JSON field stores: focus_mode, pomodoro_work_mins, streak_count, preferred_style, total_focus_minutes
"""
from sqlalchemy import Integer, Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    google_access_token: Mapped[str] = mapped_column(String(2048), nullable=True)
    google_refresh_token: Mapped[str] = mapped_column(String(2048), nullable=True)
    google_token_expiry: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    commitments: Mapped[list["Commitment"]] = relationship("Commitment", back_populates="user", cascade="all, delete-orphan")
    focus_sessions: Mapped[list["FocusSession"]] = relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

    @property
    def default_preferences(self) -> dict:
        return {"focus_mode": "pomodoro", "pomodoro_work_mins": 25, "pomodoro_break_mins": 5,
                "pomodoro_long_break_mins": 20, "deepwork_block_mins": 90,
                "streak_count": 0, "last_streak_date": "", "preferred_style": None, "total_focus_minutes": 0,
                "shutdown_time": "17:00"}
