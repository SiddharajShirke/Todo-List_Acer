"""
models/channel.py — Channel Entity
Channels are user-defined tags/categories for tasks (e.g., #work, #personal, #health).
"""
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#10B981")   # Default green
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="channels")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="channel")
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship("WeeklyPlan", back_populates="channel")
