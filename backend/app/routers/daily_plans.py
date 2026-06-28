"""
routers/daily_plans.py — Daily Planning CRUD API (NEW MODULE)

Manages DailyPlan records — the user's structured daily intention blocks.

Data flow:
  1. User opens the Today page → GET /api/daily-plans/today (auto-creates if missing)
  2. User sets morning intention, energy level, mood → PATCH /api/daily-plans/{id}
  3. Tasks are created/assigned with daily_plan_id → tasks router
  4. At end of day, user marks complete → PATCH /api/daily-plans/{id}/complete
     This triggers the shutdown ritual (AI generates daily highlight)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date as date_type, datetime
from typing import List, Optional
from app.database import get_db
from app.models.daily_plan import DailyPlan
from app.models.task import Task
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.daily_plan import DailyPlanCreate, DailyPlanUpdate, DailyPlanOut

router = APIRouter(prefix="/api/daily-plans", tags=["daily-plans"])


def _get_plan_or_404(plan_id: int, user: User, db: Session) -> DailyPlan:
    plan = db.query(DailyPlan).filter(DailyPlan.id == plan_id, DailyPlan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Daily plan not found")
    return plan


# ── Get Today's Plan (auto-creates if not exists) ──────────────────────────────
@router.get("/today", response_model=DailyPlanOut)
def get_or_create_today(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns today's DailyPlan. Creates it automatically if it doesn't exist yet.
    This is the primary entry point for the Today/Daily Planning page.
    """
    today = date_type.today()
    plan = db.query(DailyPlan).filter(DailyPlan.user_id == user.id, DailyPlan.plan_date == today).first()
    if not plan:
        plan = DailyPlan(user_id=user.id, plan_date=today)
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


# ── Get by Specific Date ───────────────────────────────────────────────────────
@router.get("/date/{plan_date}", response_model=DailyPlanOut)
def get_by_date(plan_date: date_type, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get daily plan for a specific date. Returns 404 if not created yet."""
    plan = db.query(DailyPlan).filter(DailyPlan.user_id == user.id, DailyPlan.plan_date == plan_date).first()
    if not plan:
        raise HTTPException(status_code=404, detail=f"No daily plan found for {plan_date}")
    return plan


# ── List Plans (paginated) ─────────────────────────────────────────────────────
@router.get("", response_model=List[DailyPlanOut])
def list_daily_plans(
    limit: int = Query(30, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List past daily plans, most recent first."""
    return (db.query(DailyPlan)
            .filter(DailyPlan.user_id == user.id)
            .order_by(DailyPlan.plan_date.desc())
            .offset(offset)
            .limit(limit)
            .all())


# ── Create Plan ────────────────────────────────────────────────────────────────
@router.post("", response_model=DailyPlanOut)
def create_daily_plan(data: DailyPlanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Prevent duplicate plans for the same date
    existing = db.query(DailyPlan).filter(DailyPlan.user_id == user.id, DailyPlan.plan_date == data.plan_date).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Daily plan for {data.plan_date} already exists. Use PATCH to update it.")

    plan = DailyPlan(
        user_id=user.id,
        plan_date=data.plan_date,
        weekly_plan_id=data.weekly_plan_id,
        morning_intention=data.morning_intention,
        shutdown_time=data.shutdown_time,
        energy_level=data.energy_level,
        mood=data.mood,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ── Update Plan ────────────────────────────────────────────────────────────────
@router.patch("/{plan_id}", response_model=DailyPlanOut)
def update_daily_plan(plan_id: int, data: DailyPlanUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = _get_plan_or_404(plan_id, user, db)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


# ── Mark Complete (triggers shutdown ritual) ───────────────────────────────────
@router.patch("/{plan_id}/complete", response_model=DailyPlanOut)
def complete_daily_plan(
    plan_id: int,
    notes: Optional[str] = None,
    mood_end: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Mark a daily plan as complete. This is the 'shutdown' action.
    Optionally accepts end-of-day notes and mood.
    Frontend should then call POST /api/rituals/shutdown to generate the AI highlight.
    """
    plan = _get_plan_or_404(plan_id, user, db)
    plan.is_complete = True
    if notes:
        plan.notes = notes
    db.commit()
    db.refresh(plan)
    return plan


# ── Delete Plan ────────────────────────────────────────────────────────────────
@router.delete("/{plan_id}")
def delete_daily_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = _get_plan_or_404(plan_id, user, db)
    db.delete(plan)
    db.commit()
    return {"message": "Daily plan deleted", "id": plan_id}


# ── Stats for a Daily Plan ─────────────────────────────────────────────────────
@router.get("/{plan_id}/stats")
def daily_plan_stats(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return task completion stats for a specific daily plan."""
    plan = _get_plan_or_404(plan_id, user, db)
    tasks = db.query(Task).filter(Task.daily_plan_id == plan_id, Task.user_id == user.id).all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.is_done)
    total_mins = sum(t.actual_minutes for t in tasks)
    return {
        "plan_date": plan.plan_date,
        "tasks_total": total,
        "tasks_done": done,
        "tasks_pending": total - done,
        "total_focus_minutes": total_mins,
        "completion_rate": round(done / total * 100) if total > 0 else 0,
    }
