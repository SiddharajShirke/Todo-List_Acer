"""
models/daily_highlight.py — Daily Highlight Entity
Stores AI-generated journal highlights for the daily shutdown ritual.
"""
from sqlalchemy import Integer, Text, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class DailyHighlight(Base):
    __tablename__ = "daily_highlights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
