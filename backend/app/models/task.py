"""
models/task.py — Task Entity

Tasks are atomic units of work, either:
  1. AI-decomposed subtasks of a Commitment
  2. Standalone tasks created by the user in Today view
  3. Weekly-planned tasks linked to a WeeklyPlan

Hierarchy: Commitment → WeeklyPlan → DailyPlan → Task

pomodoros_estimated = ceil(estimated_minutes / 25)
pomodoros_completed: incremented after each completed Pomodoro session on this task
"""
from sqlalchemy import BigInteger, String, Text, Date, Time, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ── Owner + Links ──────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    commitment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("commitments.id", ondelete="CASCADE"), nullable=True, index=True)
    weekly_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("weekly_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    daily_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("daily_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)

    # ── Core Fields ────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="none")       # none, low, medium, high, urgent
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Scheduling ─────────────────────────────────────────────────────
    due_date: Mapped[Date] = mapped_column(Date, nullable=True)
    planned_date: Mapped[Date] = mapped_column(Date, nullable=True, index=True)
    start_time: Mapped[Time] = mapped_column(Time, nullable=True)
    end_time: Mapped[Time] = mapped_column(Time, nullable=True)

    # ── Time Tracking ──────────────────────────────────────────────────
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=25)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    pomodoros_estimated: Mapped[int] = mapped_column(Integer, default=1)
    pomodoros_completed: Mapped[int] = mapped_column(Integer, default=0)

    # ── External Integrations ──────────────────────────────────────────
    google_event_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User")
    commitment: Mapped["Commitment"] = relationship("Commitment", back_populates="tasks")
    weekly_plan: Mapped["WeeklyPlan"] = relationship("WeeklyPlan", back_populates="tasks")
    daily_plan: Mapped["DailyPlan"] = relationship("DailyPlan", back_populates="tasks")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="tasks")
    focus_sessions: Mapped[list["FocusSession"]] = relationship("FocusSession", back_populates="task")
