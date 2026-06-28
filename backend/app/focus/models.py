"""
models/focus_session.py — Focus Session Entity

Modes:   pomodoro | deepwork | flowtime | break
Status:  pending → running → completed | cancelled | interrupted

is_break=True sessions are excluded from focus time analytics.
contributed_to_streak: True only if session completed AND > 25 min (non-break).
"""
from sqlalchemy import BigInteger, String, DateTime, Boolean, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    daily_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("daily_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    # ── Session Config ─────────────────────────────────────────────────
    mode: Mapped[str] = mapped_column(String(20), nullable=False)               # pomodoro, deepwork, flowtime, break
    status: Mapped[str] = mapped_column(String(20), default="pending")          # pending, running, completed, cancelled, interrupted

    # ── Timing ─────────────────────────────────────────────────────────
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, default=25)
    actual_duration_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # ── Pomodoro Metadata ──────────────────────────────────────────────
    pomodoro_number: Mapped[int] = mapped_column(Integer, default=1)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Ratings ────────────────────────────────────────────────────────
    flow_rating: Mapped[float] = mapped_column(Float, nullable=True)            # 1.0–5.0 user self-rating
    contributed_to_streak: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="focus_sessions")
    task: Mapped["Task"] = relationship("Task", back_populates="focus_sessions")
    daily_plan: Mapped["DailyPlan"] = relationship("DailyPlan", back_populates="focus_sessions")
