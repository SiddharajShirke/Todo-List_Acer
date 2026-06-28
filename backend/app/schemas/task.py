from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Optional, List


class TaskOut(BaseModel):
    id: int
    commitment_id: Optional[int] = None
    weekly_plan_id: Optional[int] = None
    daily_plan_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    order_index: int
    is_done: bool
    estimated_minutes: int
    actual_minutes: int
    pomodoros_estimated: int
    pomodoros_completed: int
    priority: str
    channel_id: Optional[int] = None
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    google_event_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[str] = "none"
    channel_id: Optional[int] = None
    weekly_plan_id: Optional[int] = None
    daily_plan_id: Optional[int] = None
    commitment_id: Optional[int] = None
    estimated_minutes: Optional[int] = 25
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None
    priority: Optional[str] = None
    channel_id: Optional[int] = None
    weekly_plan_id: Optional[int] = None
    daily_plan_id: Optional[int] = None
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    estimated_minutes: Optional[int] = None
    order_index: Optional[int] = None
