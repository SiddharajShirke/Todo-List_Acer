"""
routers/tasks.py — Subtask Management
PATCH /api/tasks/{id}/done  → mark task done
GET  /api/tasks/{commitment_id}/recovery-plan → LLM recovery plan for high-risk
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task
from app.models.commitment import Commitment
from app.models.user import User
from app.routers.deps import get_current_user
from app.services.llm_service import LLMService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.patch("/{task_id}/done")
def mark_task_done(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_done = True
    db.commit()
    return {"message": "Task completed"}

@router.get("/{commitment_id}/recovery-plan")
async def recovery_plan(commitment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Commitment).filter(Commitment.id == commitment_id, Commitment.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    if c.risk_score < 0.5:
        return {"plan": "Risk is low — no recovery plan needed yet."}
    llm = LLMService()
    plan = await llm.generate_recovery_plan(c)
    return {"plan": plan}
