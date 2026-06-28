from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FocusStartRequest(BaseModel):
    task_id: Optional[int] = None
    mode: str = "pomodoro"
    planned_duration_minutes: int = 25
    pomodoro_number: int = 1
    is_break: bool = False

class FocusStopRequest(BaseModel):
    session_id: int
    status: str = "completed"
    flow_rating: Optional[float] = None

class FocusSessionOut(BaseModel):
    id: int
    task_id: Optional[int]
    mode: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    planned_duration_minutes: int
    actual_duration_minutes: int
    pomodoro_number: int
    is_break: bool
    class Config: from_attributes = True
