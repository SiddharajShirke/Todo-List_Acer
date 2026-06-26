from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from app.schemas.task import TaskOut

class CommitmentCreate(BaseModel):
    type: str
    title: str
    description: Optional[str] = None
    due_date: date
    amount: Optional[float] = None

class CommitmentIngest(BaseModel):
    raw_text: str
    source: str = "manual"

class CommitmentOut(BaseModel):
    id: int
    type: str
    title: str
    description: Optional[str]
    due_date: date
    amount: Optional[float]
    source: str
    priority_score: float
    risk_score: float
    root_cause: Optional[str]
    is_done: bool
    is_missed: bool
    tasks: List[TaskOut] = []
    created_at: datetime
    days_until_due: Optional[int] = None
    class Config: from_attributes = True
