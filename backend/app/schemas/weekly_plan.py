from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.schemas.task import TaskOut


class WeeklyPlanBase(BaseModel):
    title: str
    description: Optional[str] = None
    channel_id: Optional[int] = None
    commitment_id: Optional[int] = None
    week_start_date: date
    week_end_date: date
    status: Optional[str] = "planned"
    target_focus_hours: Optional[float] = 0.0


class WeeklyPlanCreate(WeeklyPlanBase):
    pass


class WeeklyPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    channel_id: Optional[int] = None
    commitment_id: Optional[int] = None
    week_start_date: Optional[date] = None
    week_end_date: Optional[date] = None
    status: Optional[str] = None
    target_focus_hours: Optional[float] = None
    actual_focus_hours: Optional[float] = None


class WeeklyPlanOut(WeeklyPlanBase):
    id: int
    user_id: int
    actual_focus_hours: float
    ai_generated: bool
    created_at: datetime
    updated_at: datetime
    tasks: List[TaskOut] = []

    model_config = ConfigDict(from_attributes=True)
