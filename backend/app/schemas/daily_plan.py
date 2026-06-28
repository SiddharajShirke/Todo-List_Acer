from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time, datetime


class DailyPlanBase(BaseModel):
    plan_date: date
    weekly_plan_id: Optional[int] = None
    morning_intention: Optional[str] = None
    shutdown_time: Optional[time] = None
    energy_level: Optional[int] = None    # 1-5
    mood: Optional[str] = None             # focused, tired, motivated, anxious, neutral


class DailyPlanCreate(DailyPlanBase):
    pass


class DailyPlanUpdate(BaseModel):
    weekly_plan_id: Optional[int] = None
    morning_intention: Optional[str] = None
    shutdown_time: Optional[time] = None
    energy_level: Optional[int] = None
    mood: Optional[str] = None
    notes: Optional[str] = None
    is_complete: Optional[bool] = None


class DailyPlanOut(DailyPlanBase):
    id: int
    user_id: int
    notes: Optional[str] = None
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
