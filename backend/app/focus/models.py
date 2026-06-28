"""
models/focus_session.py — Focus Session Entity
Modes: pomodoro | flowtime | deepwork | break
Status: pending → running → completed | cancelled | interrupted
is_break=True sessions are excluded from focus time analytics.
"""
from sqlalchemy import Integer, String, Integer, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class FocusSession(Base):
    __tablename__ = "focus_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, default=25)
    actual_duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    pomodoro_number: Mapped[int] = mapped_column(Integer, default=1)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)
    flow_rating: Mapped[float] = mapped_column(Float, nullable=True)
    contributed_to_streak: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped["User"] = relationship("User", back_populates="focus_sessions")
    task: Mapped["Task"] = relationship("Task", back_populates="focus_sessions")
