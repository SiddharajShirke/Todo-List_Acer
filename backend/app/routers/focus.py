"""
routers/focus.py — Focus Session Management
POST /api/focus/start      → create + start a session
POST /api/focus/stop       → end session, update streak
GET  /api/focus/active     → current running session
GET  /api/focus/recommend  → AI next task recommendation
GET  /api/focus/today      → today's stats (focus hours, pomodoros)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import User
from app.models.focus_session import FocusSession
from app.models.task import Task
from app.models.commitment import Commitment
from app.schemas.focus_session import FocusStartRequest, FocusStopRequest, FocusSessionOut
from app.routers.deps import get_current_user
from app.services.focus_service import FocusService

router = APIRouter(prefix="/api/focus", tags=["focus"])

@router.post("/start", response_model=FocusSessionOut)
def start_session(payload: FocusStartRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    active = db.query(FocusSession).filter(FocusSession.user_id == user.id, FocusSession.status == "running").first()
    if active:
        active.status = "interrupted"
        active.ended_at = datetime.now(timezone.utc)
        db.flush()

    session = FocusSession(
        user_id=user.id,
        task_id=payload.task_id,
        mode=payload.mode,
        status="running",
        started_at=datetime.now(timezone.utc),
        planned_duration_minutes=payload.planned_duration_minutes,
        pomodoro_number=payload.pomodoro_number,
        is_break=payload.is_break,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.post("/stop")
def stop_session(payload: FocusStopRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(FocusSession).filter(FocusSession.id == payload.session_id, FocusSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    now = datetime.now(timezone.utc)
    session.status = payload.status
    session.ended_at = now
    session.flow_rating = payload.flow_rating
    if session.started_at:
        session.actual_duration_minutes = int((now - session.started_at).total_seconds() / 60)

    if not session.is_break and session.status == "completed":
        if session.task_id:
            task = db.query(Task).filter(Task.id == session.task_id).first()
            if task:
                task.pomodoros_completed += 1
                task.actual_minutes += session.actual_duration_minutes
        FocusService.update_streak(user, db)
        session.contributed_to_streak = True

    db.commit()
    return {"message": "Session ended", "duration_minutes": session.actual_duration_minutes}

@router.get("/active")
def active_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(FocusSession).filter(FocusSession.user_id == user.id, FocusSession.status == "running").first()
    return {"session": FocusSessionOut.model_validate(session) if session else None}

@router.get("/recommend")
def recommend_task(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return top-priority incomplete task for AI next-session recommendation."""
    today = datetime.now().date()
    from sqlalchemy import and_
    tasks = (db.query(Task)
             .join(Commitment)
             .filter(and_(Task.user_id == user.id, Task.is_done == False, Commitment.is_done == False))
             .order_by(Commitment.priority_score.desc(), Task.order_index)
             .limit(5)
             .all())
    if not tasks:
        return {"recommendation": None}
    top = tasks[0]
    return {
        "recommendation": {
            "task_id": top.id,
            "task_title": top.title,
            "commitment_title": top.commitment.title if top.commitment else "",
            "commitment_type": top.commitment.type if top.commitment else "other",
            "priority_score": top.commitment.priority_score if top.commitment else 0,
            "risk_score": top.commitment.risk_score if top.commitment else 0,
            "pomodoros_estimated": top.pomodoros_estimated,
            "pomodoros_completed": top.pomodoros_completed,
        }
    }

@router.get("/today")
def today_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = datetime.now().date()
    sessions = db.query(FocusSession).filter(
        FocusSession.user_id == user.id,
        FocusSession.status == "completed",
        FocusSession.is_break == False,
        FocusSession.started_at >= datetime.combine(today, datetime.min.time()),
    ).all()
    total_mins = sum(s.actual_duration_minutes for s in sessions)
    pomodoros = sum(1 for s in sessions if s.mode == "pomodoro")
    prefs = user.preferences or {}
    return {
        "total_minutes": total_mins,
        "total_hours": round(total_mins / 60, 1),
        "pomodoros_completed": pomodoros,
        "sessions_count": len(sessions),
        "streak_days": prefs.get("streak_count", 0),
    }

@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Returns all incomplete tasks for focus session task picker."""
    tasks = (db.query(Task)
             .join(Commitment)
             .filter(Task.user_id == user.id, Task.is_done == False, Commitment.is_done == False)
             .order_by(Commitment.priority_score.desc())
             .all())
    return [{"id": t.id, "title": t.title, "commitment_title": t.commitment.title if t.commitment else ""} for t in tasks]
