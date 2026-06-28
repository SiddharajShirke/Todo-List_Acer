"""
models/daily_plan.py — Daily Planning Entity (NEW MODULE)

A DailyPlan represents the user's structured intentions for a single day.
Linked to an optional WeeklyPlan for hierarchy: Commitment → WeeklyPlan → DailyPlan → Tasks.

Fields:
  - morning_intention: User's written startup ritual (what they commit to today)
  - shutdown_time: Planned end-of-work time
  - energy_level (1-5): User-set energy at start of day
  - mood: Start-of-day mood tag
  - notes: End-of-day freeform reflection
  - is_complete: User explicitly marks the day done (triggers shutdown ritual)
"""
from sqlalchemy import BigInteger, String, Text, Date, Time, SmallInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Day Scope ──────────────────────────────────────────────────────
    plan_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    weekly_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("weekly_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    # ── Morning Startup Ritual ─────────────────────────────────────────
    morning_intention: Mapped[str] = mapped_column(Text, nullable=True)     # User's written day intention
    shutdown_time: Mapped[Time] = mapped_column(Time, nullable=True)         # Planned shutdown time

    # ── Daily State ────────────────────────────────────────────────────
    energy_level: Mapped[int] = mapped_column(SmallInteger, nullable=True)  # 1-5 scale
    mood: Mapped[str] = mapped_column(String(50), nullable=True)            # focused, tired, motivated, anxious, neutral

    # ── End-of-Day ─────────────────────────────────────────────────────
    notes: Mapped[str] = mapped_column(Text, nullable=True)                 # Freeform end-of-day reflection
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)       # Shutdown ritual completed

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="daily_plans")
    weekly_plan: Mapped["WeeklyPlan"] = relationship("WeeklyPlan", back_populates="daily_plans")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="daily_plan")
    focus_sessions: Mapped[list["FocusSession"]] = relationship("FocusSession", back_populates="daily_plan")
    highlights: Mapped[list["DailyHighlight"]] = relationship("DailyHighlight", back_populates="daily_plan")
