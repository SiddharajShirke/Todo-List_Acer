"""
models/task.py — Subtask Entity
LLM-generated decomposition of a Commitment.
pomodoros_estimated = ceil(estimated_minutes / 25)
pomodoros_completed incremented after each Pomodoro session on this task.
"""
from sqlalchemy import BigInteger, String, Text, Date, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    commitment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    due_date: Mapped[Date] = mapped_column(Date, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=25)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    pomodoros_estimated: Mapped[int] = mapped_column(Integer, default=1)
    pomodoros_completed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    commitment: Mapped["Commitment"] = relationship("Commitment", back_populates="tasks")
    focus_sessions: Mapped[list] = relationship("FocusSession", back_populates="task")
