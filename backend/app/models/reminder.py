"""
models/reminder.py — Reminder + Feedback Entities

Reminder: AI-generated nudge messages (deadline | achievement | consequence | streak)
Feedback: user postponement reasons — feeds Root Cause and Personalization engines
"""
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    commitment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False)

    style: Mapped[str] = mapped_column(String(50), nullable=False)          # deadline, achievement, consequence, streak
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_action: Mapped[str] = mapped_column(String(50), nullable=True)     # dismissed, postponed, done
    action_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="reminders")
    commitment: Mapped["Commitment"] = relationship("Commitment", back_populates="reminders")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    commitment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False)

    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    feedback_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="feedbacks")
    commitment: Mapped["Commitment"] = relationship("Commitment", back_populates="feedbacks")
