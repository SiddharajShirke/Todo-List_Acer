from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class TaskOut(BaseModel):
    id: int
    commitment_id: int
    title: str
    description: Optional[str]
    order_index: int
    is_done: bool
    estimated_minutes: int
    actual_minutes: int
    pomodoros_estimated: int
    pomodoros_completed: int
    class Config: from_attributes = True
