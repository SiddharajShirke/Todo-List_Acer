"""
routers/analytics.py — Analytics Data API
GET /api/analytics/report → full report: daily + weekly + monthly
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.focus.models import FocusSession
from app.models.commitment import Commitment
from app.routers.deps import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/report")
def full_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = datetime.now().date()
    uid = user.id

    # ── Daily ──────────────────────────────────────────────────────
    start_today = datetime.combine(today, datetime.min.time())
    daily_sessions = db.query(FocusSession).filter(
        FocusSession.user_id == uid,
        FocusSession.status == "completed",
        FocusSession.is_break == False,
        FocusSession.started_at >= start_today,
    ).all()
    daily_mins = sum(s.actual_duration_minutes for s in daily_sessions)
    daily_pomodoros = sum(1 for s in daily_sessions if s.mode == "pomodoro")
    daily_tasks_done = db.query(func.count()).select_from(Commitment).filter(
        Commitment.user_id == uid, Commitment.is_done == True,
        Commitment.updated_at >= start_today).scalar() or 0

    hourly = {h: 0 for h in range(24)}
    for s in daily_sessions:
        if s.started_at:
            h = s.started_at.hour
            hourly[h] = hourly.get(h, 0) + s.actual_duration_minutes

    prefs = user.preferences or {}

    # ── Weekly ────────────────────────────────────────────────────
    week_labels, week_focus, week_poms = [], [], []
    total_week_mins = 0
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        s_day = datetime.combine(d, datetime.min.time())
        e_day = datetime.combine(d + timedelta(days=1), datetime.min.time())
        sessions = db.query(FocusSession).filter(
            FocusSession.user_id == uid, FocusSession.status == "completed",
            FocusSession.is_break == False,
            FocusSession.started_at >= s_day, FocusSession.started_at < e_day).all()
        mins = sum(s.actual_duration_minutes for s in sessions)
        poms = sum(1 for s in sessions if s.mode == "pomodoro")
        week_labels.append(d.strftime("%a"))
        week_focus.append(round(mins / 60, 1))
        week_poms.append(poms)
        total_week_mins += mins

    # ── Monthly ───────────────────────────────────────────────────
    thirty_ago = today - timedelta(days=30)
    start_30 = datetime.combine(thirty_ago, datetime.min.time())
    monthly_sessions = db.query(FocusSession).filter(
        FocusSession.user_id == uid, FocusSession.status == "completed",
        FocusSession.is_break == False, FocusSession.started_at >= start_30).all()
    monthly_total_mins = sum(s.actual_duration_minutes for s in monthly_sessions)
    monthly_done = db.query(func.count()).select_from(Commitment).filter(
        Commitment.user_id == uid, Commitment.is_done == True,
        Commitment.updated_at >= start_30).scalar() or 0

    commitment_types = db.query(Commitment.type, func.count()).filter(
        Commitment.user_id == uid, Commitment.is_done == True,
        Commitment.updated_at >= start_30).group_by(Commitment.type).all()
    project_distribution = [{"type": t, "hours": c * 2, "percentage": round(c / max(monthly_done, 1) * 100)} for t, c in commitment_types]

    return {
        "daily": {
            "total_hours": f"{round(daily_mins / 60, 1)}",
            "total_minutes": daily_mins,
            "pomodoros_completed": daily_pomodoros,
            "tasks_completed": daily_tasks_done,
            "streak": prefs.get("streak_count", 0),
            "hourly_breakdown": {
                "labels": [f"{h}:00" for h in range(24)],
                "data": [hourly.get(h, 0) for h in range(24)],
            },
        },
        "weekly": {
            "labels": week_labels,
            "focus_hours": week_focus,
            "pomodoros": week_poms,
            "total_this_week": total_week_mins,
            "avg_daily_minutes": round(total_week_mins / 7),
        },
        "monthly": {
            "total_focus_hours": round(monthly_total_mins / 60, 1),
            "commitments_completed": monthly_done,
            "project_distribution": project_distribution,
        },
    }
