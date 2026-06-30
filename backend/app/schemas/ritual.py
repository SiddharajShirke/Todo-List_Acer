from pydantic import BaseModel, ConfigDict
from datetime import date as dt, datetime
from typing import Optional


class DailyHighlightOut(BaseModel):
    id: int
    user_id: int
    daily_plan_id: Optional[int] = None
    date: dt
    highlight_type: str
    content: str
    ai_summary: Optional[str] = None
    tasks_completed: int
    focus_minutes: int
    mood_end: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyHighlightCreate(BaseModel):
    date: dt
    daily_plan_id: Optional[int] = None
    highlight_type: Optional[str] = "shutdown"
    content: str
    mood_end: Optional[str] = None


class ShutdownRequest(BaseModel):
    date: Optional[dt] = None
    daily_plan_id: Optional[int] = None
    mood_end: Optional[str] = None
