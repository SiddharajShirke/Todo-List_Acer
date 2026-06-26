"""
routers/reminders.py — Reminders
GET /api/reminders             → all reminders for user (most recent first)
POST /api/reminders/{id}/action → record user action (pay_now, later, already_done, dismiss)
"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import User
from app.models.reminder import Reminder
from app.routers.deps import get_current_user

router = APIRouter(prefix="/api/reminders", tags=["reminders"])

@router.get("")
def list_reminders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    reminders = db.query(Reminder).filter(Reminder.user_id == user.id).order_by(Reminder.sent_at.desc()).limit(50).all()
    return [{
        "id": r.id, "commitment_id": r.commitment_id, "style": r.style,
        "message": r.message, "sent_at": r.sent_at, "user_action": r.user_action
    } for r in reminders]

@router.post("/{reminder_id}/action")
def record_action(reminder_id: int, action: str = Body(embed=True), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == user.id).first()
    if not r:
        return {"message": "Not found"}
    r.user_action = action
    r.action_time = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Action recorded"}
