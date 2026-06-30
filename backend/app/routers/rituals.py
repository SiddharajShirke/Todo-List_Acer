"""
routers/rituals.py — Daily Ritual & Highlight API

Shutdown Ritual: AI generates an end-of-day highlight from completed tasks.
Startup Ritual: User sets morning intention, energy, mood.

Enhanced with:
  - Metric snapshots (tasks_completed, focus_minutes) at shutdown time
  - mood_end captured at shutdown
  - Linked to DailyPlan for full day context
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date as date_type
from typing import Optional
from app.database import get_db
from app.models.daily_highlight import DailyHighlight
from app.models.daily_plan import DailyPlan
from app.models.task import Task
from app.focus.models import FocusSession
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.ritual import DailyHighlightOut, DailyHighlightCreate, ShutdownRequest
from app.services.hybrid_client import HybridClient

router = APIRouter(prefix="/api/rituals", tags=["rituals"])


# ── Shutdown Ritual (AI Daily Highlight) ───────────────────────────────────────
@router.post("/shutdown", response_model=DailyHighlightOut)
async def generate_shutdown_highlight(
    data: ShutdownRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    End-of-day shutdown ritual.
    1. Gathers completed tasks and focus minutes for the day
    2. Sends to AI for a coaching/journal highlight
    3. Saves/updates the DailyHighlight with snapshot metrics
    """
    target_date = data.date or date_type.today()

    # Gather completed tasks for the day
    tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.planned_date == target_date,
        Task.is_done == True
    ).all()
    task_titles = [t.title for t in tasks]
    tasks_completed = len(tasks)

    # Gather focus minutes for the day
    from datetime import datetime
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())
    focus_sessions = db.query(FocusSession).filter(
        FocusSession.user_id == user.id,
        FocusSession.status == "completed",
        FocusSession.is_break == False,
        FocusSession.started_at >= day_start,
        FocusSession.started_at <= day_end,
    ).all()
    focus_minutes = sum(s.actual_duration_minutes for s in focus_sessions)

    # Build AI prompt with full context
    task_summary = ", ".join(task_titles) if task_titles else "No tasks completed"
    prompt_text = (
        f"Generate a detailed, journal-style daily highlight based on this productivity session. "
        f"Date: {target_date}. Completed tasks: {task_summary}. "
        f"Total focus time: {focus_minutes} minutes. "
        f"End-of-day mood: {data.mood_end or 'not specified'}. "
        "Structure your response strictly using markdown:\n"
        "### 📝 Today's Reflection\n"
        "(Write a personalized 2-3 sentence reflection on the day's overall effort)\n\n"
        "### 🎯 Task Explanations & AI Coaching\n"
        "(For EVERY single task completed, list it as a bullet point and provide a 1-sentence explanation of its impact, plus a micro-recommendation for tomorrow based on that specific task.)"
    )

    # Call AI
    client = HybridClient()
    ai_content = client.generate(
        prompt=prompt_text,
        system_instr="You are a supportive productivity coach generating personalized end-of-day journal entries.",
        temperature=0.7
    )

    # AI summary (shorter version for display)
    summary_prompt = f"Summarize this daily highlight in one sentence: {ai_content}"
    ai_summary = client.generate(prompt=summary_prompt, system_instr="Summarize concisely.", temperature=0.3)

    # Find linked daily plan
    daily_plan = db.query(DailyPlan).filter(
        DailyPlan.user_id == user.id,
        DailyPlan.plan_date == target_date
    ).first()

    # Upsert the daily highlight
    hl = db.query(DailyHighlight).filter(
        DailyHighlight.user_id == user.id,
        DailyHighlight.date == target_date,
        DailyHighlight.highlight_type == "shutdown"
    ).first()

    if not hl:
        hl = DailyHighlight(
            user_id=user.id,
            date=target_date,
            highlight_type="shutdown",
            daily_plan_id=daily_plan.id if daily_plan else data.daily_plan_id,
        )
        db.add(hl)

    hl.content = ai_content
    hl.ai_summary = ai_summary
    hl.tasks_completed = tasks_completed
    hl.focus_minutes = focus_minutes
    hl.mood_end = data.mood_end

    db.commit()
    db.refresh(hl)
    return hl


# ── Manual Highlight Create ────────────────────────────────────────────────────
@router.post("/highlights", response_model=DailyHighlightOut)
def create_highlight(
    data: DailyHighlightCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a manual highlight (e.g., gratitude, milestone note)."""
    hl = DailyHighlight(
        user_id=user.id,
        date=data.date,
        daily_plan_id=data.daily_plan_id,
        highlight_type=data.highlight_type or "shutdown",
        content=data.content,
        mood_end=data.mood_end,
    )
    db.add(hl)
    db.commit()
    db.refresh(hl)
    return hl


# ── List All Highlights ────────────────────────────────────────────────────────
@router.get("/highlights", response_model=list[DailyHighlightOut])
def get_highlights(
    limit: int = Query(30, le=100),
    highlight_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(DailyHighlight).filter(DailyHighlight.user_id == user.id)
    if highlight_type:
        query = query.filter(DailyHighlight.highlight_type == highlight_type)
    return query.order_by(DailyHighlight.date.desc()).limit(limit).all()


# ── Get Highlight for a Specific Date ─────────────────────────────────────────
@router.get("/highlights/{target_date}", response_model=list[DailyHighlightOut])
def get_highlight_by_date(
    target_date: date_type,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(DailyHighlight).filter(
        DailyHighlight.user_id == user.id,
        DailyHighlight.date == target_date
    ).all()


# ── Delete Highlight ───────────────────────────────────────────────────────────
@router.delete("/highlights/{highlight_id}")
def delete_highlight(highlight_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hl = db.query(DailyHighlight).filter(DailyHighlight.id == highlight_id, DailyHighlight.user_id == user.id).first()
    if not hl:
        raise HTTPException(status_code=404, detail="Highlight not found")
    db.delete(hl)
    db.commit()
    return {"message": "Highlight deleted", "id": highlight_id}


# ── Weekly Review Generation ───────────────────────────────────────────────────
from pydantic import BaseModel
class WeeklyReviewRequest(BaseModel):
    start_date: str
    end_date: str

@router.post("/weekly-review")
def generate_weekly_review_endpoint(
    data: WeeklyReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Generate a dynamic weekly review using LLM based on tasks completed over the given week range."""
    from datetime import date as dt
    start_dt = dt.fromisoformat(data.start_date)
    end_dt = dt.fromisoformat(data.end_date)
    
    tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.planned_date >= start_dt,
        Task.planned_date <= end_dt
    ).all()
    
    completed_tasks = [t.title for t in tasks if t.is_done]
    pending_tasks = [t.title for t in tasks if not t.is_done]
    
    prompt_text = (
        f"Generate a comprehensive Weekly Review for the week of {data.start_date} to {data.end_date}. "
        f"Completed {len(completed_tasks)} tasks: {', '.join(completed_tasks) if completed_tasks else 'None'}. "
        f"Pending {len(pending_tasks)} tasks: {', '.join(pending_tasks) if pending_tasks else 'None'}. "
        "Structure the review strictly into three parts using markdown: \n"
        "### 🏆 The Wins (celebrate completions)\n"
        "### 🚧 The Bottlenecks (acknowledge pending items)\n"
        "### 🚀 Focus for Next Week\n"
        "Keep it actionable, highly motivating, and provide a direct recommendation for improvement."
    )
    
    client = HybridClient()
    ai_content = client.generate(
        prompt=prompt_text,
        system_instr="You are an elite productivity strategist performing a weekly performance review. Use markdown.",
        temperature=0.7
    )
    
    return {"content": ai_content, "start_date": data.start_date, "end_date": data.end_date}
