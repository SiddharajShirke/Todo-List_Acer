"""
models/commitment.py — Core Commitment Entity

A Commitment is a high-level goal or project the user is working toward.
- priority_score (0-100): computed by PriorityEngine (urgency × impact × risk)
- risk_score (0.0-1.0): computed by RiskEngine
- root_cause: AI-predicted procrastination root cause
- metadata_json (JSONB): raw_text, confidence, external IDs, AI reasoning
"""
from sqlalchemy import BigInteger, String, Text, Date, Numeric, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Core Fields ────────────────────────────────────────────────────
    type: Mapped[str] = mapped_column(String(50), nullable=False)          # project, habit, deadline, goal, financial
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    due_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric, nullable=True)           # For financial commitments
    source: Mapped[str] = mapped_column(String(50), default="manual")      # manual, ai, import, google_calendar

    # ── AI Scoring ─────────────────────────────────────────────────────
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    root_cause: Mapped[str] = mapped_column(String(100), nullable=True)
    root_cause_score: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Status ─────────────────────────────────────────────────────────
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    is_missed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Metadata (JSONB) ───────────────────────────────────────────────
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="commitments")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="commitment", cascade="all, delete-orphan", order_by="Task.order_index")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="commitment", cascade="all, delete-orphan")
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="commitment", cascade="all, delete-orphan")
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship("WeeklyPlan", back_populates="commitment")
