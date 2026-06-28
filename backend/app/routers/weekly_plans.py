"""
routers/weekly_plans.py — Weekly Planning CRUD API

Manages WeeklyPlan records — the user's weekly intention blocks.
Replaces the old /api/weekly-objectives endpoint.

Frontend compatibility: The old route /api/weekly-objectives is preserved
as an alias so existing frontend code continues to work during transition.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.weekly_plan import WeeklyPlan
from app.models.task import Task
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.weekly_plan import WeeklyPlanCreate, WeeklyPlanUpdate, WeeklyPlanOut
from app.services.google_calendar import delete_calendar_event, update_calendar_event

# Both routes for backward compatibility during frontend migration
router = APIRouter(tags=["weekly-plans"])


def _get_plan_or_404(plan_id: int, user: User, db: Session) -> WeeklyPlan:
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id, WeeklyPlan.user_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return plan


# ── List ───────────────────────────────────────────────────────────────────────
@router.get("/api/weekly-plans", response_model=List[WeeklyPlanOut])
@router.get("/api/weekly-objectives", response_model=List[WeeklyPlanOut])   # backward compat
def list_weekly_plans(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(WeeklyPlan).filter(WeeklyPlan.user_id == user.id).order_by(WeeklyPlan.week_start_date.desc()).all()


# ── Create ─────────────────────────────────────────────────────────────────────
@router.post("/api/weekly-plans", response_model=WeeklyPlanOut)
@router.post("/api/weekly-objectives", response_model=WeeklyPlanOut)         # backward compat
def create_weekly_plan(data: WeeklyPlanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = WeeklyPlan(
        user_id=user.id,
        title=data.title,
        description=data.description,
        channel_id=data.channel_id,
        commitment_id=data.commitment_id,
        week_start_date=data.week_start_date,
        week_end_date=data.week_end_date,
        status=data.status or "planned",
        target_focus_hours=data.target_focus_hours or 0.0,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ── Update ─────────────────────────────────────────────────────────────────────
@router.put("/api/weekly-plans/{plan_id}", response_model=WeeklyPlanOut)
@router.put("/api/weekly-objectives/{plan_id}", response_model=WeeklyPlanOut)  # backward compat
def update_weekly_plan(plan_id: int, data: WeeklyPlanUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = _get_plan_or_404(plan_id, user, db)

    old_title = plan.title
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)

    # Propagate title and channel changes to linked tasks (and Google Calendar events)
    if "title" in updates or "channel_id" in updates:
        tasks = db.query(Task).filter(Task.weekly_plan_id == plan_id).all()
        for task in tasks:
            if "title" in updates:
                task.title = updates["title"]
            if "channel_id" in updates:
                task.channel_id = updates["channel_id"]
            db.commit()
            if user.google_access_token and task.google_event_id:
                update_calendar_event(user, task, db=db)

    return plan


# ── Delete ─────────────────────────────────────────────────────────────────────
@router.delete("/api/weekly-plans/{plan_id}")
@router.delete("/api/weekly-objectives/{plan_id}")                             # backward compat
def delete_weekly_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = _get_plan_or_404(plan_id, user, db)

    # Clean up Google Calendar events for linked tasks
    tasks = db.query(Task).filter(Task.weekly_plan_id == plan_id).all()
    for task in tasks:
        if user.google_access_token and task.google_event_id:
            delete_calendar_event(user, task.google_event_id, db=db)
        db.delete(task)

    db.delete(plan)
    db.commit()
    return {"message": "Weekly plan deleted", "id": plan_id}


# ── Get by date range ──────────────────────────────────────────────────────────
@router.get("/api/weekly-plans/by-week", response_model=List[WeeklyPlanOut])
def get_plans_for_week(
    week_start: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all weekly plans for a specific week start date (YYYY-MM-DD)."""
    from datetime import date
    try:
        start = date.fromisoformat(week_start)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid week_start date format. Use YYYY-MM-DD")

    plans = db.query(WeeklyPlan).filter(
        WeeklyPlan.user_id == user.id,
        WeeklyPlan.week_start_date == start
    ).all()
    return plans
