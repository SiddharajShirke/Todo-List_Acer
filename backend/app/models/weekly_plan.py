"""
models/weekly_plan.py — Weekly Planning Entity

Replaces the old weekly_objectives table with a richer structure.
A WeeklyPlan represents a user's intention block for a specific week,
optionally linked to a Commitment and Channel.

Status lifecycle: planned → in_progress → done | missed
"""
from sqlalchemy import BigInteger, String, Text, Date, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Plan Scope ─────────────────────────────────────────────────────
    week_start_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)   # Monday
    week_end_date: Mapped[Date] = mapped_column(Date, nullable=False)                  # Sunday
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Linked Entities ────────────────────────────────────────────────
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    commitment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True)

    # ── Focus Tracking ─────────────────────────────────────────────────
    target_focus_hours: Mapped[float] = mapped_column(Float, default=0.0)   # Planned hours
    actual_focus_hours: Mapped[float] = mapped_column(Float, default=0.0)   # Tracked hours

    # ── Status & AI ────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(20), default="planned")      # planned, in_progress, done, missed
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)      # Was this AI-suggested?

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="weekly_plans")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="weekly_plans")
    commitment: Mapped["Commitment"] = relationship("Commitment", back_populates="weekly_plans")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="weekly_plan")
    daily_plans: Mapped[list["DailyPlan"]] = relationship("DailyPlan", back_populates="weekly_plan")
