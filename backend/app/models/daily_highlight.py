"""
models/daily_highlight.py — Daily Highlight Entity

AI-generated or manually written highlights for the daily shutdown ritual.
Enhanced with richer fields:
  - highlight_type: startup (morning), shutdown (evening), milestone, gratitude
  - ai_summary: AI-generated natural language summary of the day
  - tasks_completed/focus_minutes: snapshot metrics captured at shutdown time
  - mood_end: end-of-day mood (separate from DailyPlan.mood which is morning mood)
"""
from sqlalchemy import BigInteger, String, Text, Date, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class DailyHighlight(Base):
    __tablename__ = "daily_highlights"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    daily_plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("daily_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    # ── Core ───────────────────────────────────────────────────────────
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    highlight_type: Mapped[str] = mapped_column(String(20), default="shutdown")  # startup, shutdown, milestone, gratitude
    content: Mapped[str] = mapped_column(Text, nullable=False)                   # Main highlight text

    # ── AI-Generated Summary ───────────────────────────────────────────
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)                 # AI coaching summary

    # ── Day Snapshot Metrics (captured at shutdown time) ───────────────
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    focus_minutes: Mapped[int] = mapped_column(Integer, default=0)
    mood_end: Mapped[str] = mapped_column(String(50), nullable=True)             # End-of-day mood

    # ── Timestamps ─────────────────────────────────────────────────────
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="daily_highlights")
    daily_plan: Mapped["DailyPlan"] = relationship("DailyPlan", back_populates="highlights")
