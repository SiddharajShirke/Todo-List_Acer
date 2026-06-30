"""
ai/tools/supabase_tools.py — LangGraph Tool Definitions

All tools are thin wrappers over existing SQLAlchemy models.
No business logic is duplicated here — tools only query/write data.
Every tool logs to agent_tool_logs table (failures are silent).

Architecture rule: The Brain LLM NEVER imports Supabase or SQLAlchemy directly.
Only tools touch the database.
"""
import time
import json
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional
from langchain_core.tools import tool
from loguru import logger
from app.services.redis_service import redis_cache


# ── Tool Logging Helper ────────────────────────────────────────────────────────

def _log_tool(thread_id: str, tool_name: str, tool_input: dict,
              tool_output, status: str, error_msg: Optional[str], exec_ms: int):
    """Fire-and-forget tool log. Never raises."""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(
                __import__('sqlalchemy').text(
                    "INSERT INTO agent_tool_logs "
                    "(thread_id, tool_name, tool_input, tool_output, status, error_message, execution_ms) "
                    "VALUES (:tid, :tn, :ti, :to, :st, :em, :ms)"
                ),
                {
                    "tid": thread_id or "unknown",
                    "tn": tool_name,
                    "ti": json.dumps(tool_input),
                    "to": json.dumps(tool_output) if tool_output is not None else None,
                    "st": status,
                    "em": error_msg,
                    "ms": exec_ms,
                }
            )
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Tool log failed (non-fatal): {e}")


def _run_tool(tool_name: str, tool_input: dict, fn, thread_id: str = "unknown"):
    """Execute fn(), log result, re-raise on error."""
    start = time.time()
    try:
        result = fn()
        exec_ms = int((time.time() - start) * 1000)
        _log_tool(thread_id, tool_name, tool_input, result, "success", None, exec_ms)
        return result
    except Exception as e:
        exec_ms = int((time.time() - start) * 1000)
        _log_tool(thread_id, tool_name, tool_input, None, "error", str(e), exec_ms)
        raise


# ── Serialisation Helpers ──────────────────────────────────────────────────────

import re

def _clean_id(id_str: str) -> int:
    """Safely extract the integer ID if the LLM passes something like 'user_1'"""
    if not id_str:
        return 0
    match = re.search(r'\d+', str(id_str))
    return int(match.group()) if match else 0


def _task_to_dict(t) -> dict:
    return {
        "id": str(t.id),
        "title": t.title,
        "description": t.description,
        "is_done": t.is_done,
        "priority": t.priority,
        "due_date": str(t.due_date) if t.due_date else None,
        "planned_date": str(t.planned_date) if t.planned_date else None,
        "estimated_minutes": t.estimated_minutes,
        "commitment_id": str(t.commitment_id) if t.commitment_id else None,
    }


def _commitment_to_dict(c) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "type": c.type,
        "due_date": str(c.due_date) if c.due_date else None,
        "amount": float(c.amount) if c.amount else None,
        "priority_score": c.priority_score,
        "risk_score": c.risk_score,
        "root_cause": c.root_cause,
        "is_done": c.is_done,
    }


def _focus_to_dict(s) -> dict:
    return {
        "id": str(s.id),
        "mode": s.mode,
        "status": s.status,
        "actual_duration_minutes": s.actual_duration_minutes,
        "started_at": str(s.started_at) if s.started_at else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# READ TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@tool
@redis_cache(expire=30)
def fetch_tasks(user_id: str, status: Optional[str] = None, date: Optional[str] = None) -> list:
    """Fetch tasks for the user. Optionally filter by status (pending/completed) or date (YYYY-MM-DD)."""
    from app.database import SessionLocal
    from app.models.task import Task

    def _run():
        db = SessionLocal()
        try:
            q = db.query(Task).filter(Task.user_id == _clean_id(user_id))
            if status == "completed":
                q = q.filter(Task.is_done == True)
            elif status == "pending":
                q = q.filter(Task.is_done == False)
            if date:
                from datetime import date as dt
                q = q.filter(Task.planned_date == dt.fromisoformat(date))
            return [_task_to_dict(t) for t in q.order_by(Task.order_index).all()]
        finally:
            db.close()

    return _run_tool("fetch_tasks", {"user_id": user_id, "status": status, "date": date}, _run)


@tool
@redis_cache(expire=30)
def fetch_commitments(user_id: str, type: Optional[str] = None) -> list:
    """Fetch user commitments. Type can be bill, interview, assignment, or event."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment

    def _run():
        db = SessionLocal()
        try:
            q = db.query(Commitment).filter(
                Commitment.user_id == _clean_id(user_id),
                Commitment.is_done == False
            )
            if type:
                q = q.filter(Commitment.type == type)
            return [_commitment_to_dict(c) for c in
                    q.order_by(Commitment.priority_score.desc()).all()]
        finally:
            db.close()

    return _run_tool("fetch_commitments", {"user_id": user_id, "type": type}, _run)


@tool
def fetch_overdue_tasks(user_id: str) -> list:
    """Fetch all overdue tasks for the user sorted by urgency."""
    from app.database import SessionLocal
    from app.models.task import Task
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            today = dt.today()
            tasks = db.query(Task).filter(
                Task.user_id == _clean_id(user_id),
                Task.is_done == False,
                Task.due_date < today,
            ).order_by(Task.due_date).all()
            return [_task_to_dict(t) for t in tasks]
        finally:
            db.close()

    return _run_tool("fetch_overdue_tasks", {"user_id": user_id}, _run)


@tool
def fetch_daily_plan(user_id: str, date: str) -> dict:
    """Fetch the user's daily plan including morning intention and tasks for the given date (YYYY-MM-DD)."""
    from app.database import SessionLocal
    from app.models.daily_plan import DailyPlan
    from app.models.task import Task
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            target = dt.fromisoformat(date)
            plan = db.query(DailyPlan).filter(
                DailyPlan.user_id == _clean_id(user_id),
                DailyPlan.plan_date == target
            ).first()
            if not plan:
                return {"date": date, "morning_intention": None, "tasks": [], "is_complete": False}
            tasks = db.query(Task).filter(
                Task.daily_plan_id == plan.id,
                Task.user_id == _clean_id(user_id)
            ).all()
            return {
                "id": str(plan.id),
                "date": str(plan.plan_date),
                "morning_intention": plan.morning_intention,
                "energy_level": plan.energy_level,
                "mood": plan.mood,
                "is_complete": plan.is_complete,
                "tasks": [_task_to_dict(t) for t in tasks],
            }
        finally:
            db.close()

    return _run_tool("fetch_daily_plan", {"user_id": user_id, "date": date}, _run)


@tool
def fetch_focus_sessions(user_id: str, date_range: Optional[str] = "today") -> list:
    """Fetch focus/Pomodoro sessions for the user. date_range: today/week/month."""
    from app.database import SessionLocal
    from app.focus.models import FocusSession
    from datetime import datetime, timedelta

    def _run():
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            if date_range == "week":
                start = now - timedelta(days=7)
            elif date_range == "month":
                start = now - timedelta(days=30)
            else:  # today
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            sessions = db.query(FocusSession).filter(
                FocusSession.user_id == int(user_id),
                FocusSession.status == "completed",
                FocusSession.is_break == False,
                FocusSession.started_at >= start,
            ).order_by(FocusSession.started_at.desc()).all()
            return [_focus_to_dict(s) for s in sessions]
        finally:
            db.close()

    return _run_tool("fetch_focus_sessions", {"user_id": user_id, "date_range": date_range}, _run)


@tool
def fetch_productivity_stats(user_id: str, period: str = "day") -> dict:
    """Fetch productivity statistics for the user. period: day/week/month."""
    from app.database import SessionLocal
    from app.focus.models import FocusSession
    from app.models.commitment import Commitment
    from datetime import datetime, timedelta
    from sqlalchemy import func

    def _run():
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            if period == "week":
                start = now - timedelta(days=7)
            elif period == "month":
                start = now - timedelta(days=30)
            else:
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            sessions = db.query(FocusSession).filter(
                FocusSession.user_id == _clean_id(user_id),
                FocusSession.status == "completed",
                FocusSession.is_break == False,
                FocusSession.started_at >= start,
            ).all()
            total_mins = sum(s.actual_duration_minutes for s in sessions)
            pomodoros = sum(1 for s in sessions if s.mode == "pomodoro")
            done_commitments = db.query(func.count(Commitment.id)).filter(
                Commitment.user_id == _clean_id(user_id),
                Commitment.is_done == True,
                Commitment.updated_at >= start,
            ).scalar() or 0
            return {
                "period": period,
                "total_focus_hours": round(total_mins / 60, 1),
                "total_focus_minutes": total_mins,
                "pomodoros_completed": pomodoros,
                "commitments_completed": done_commitments,
                "sessions_count": len(sessions),
            }
        finally:
            db.close()

    return _run_tool("fetch_productivity_stats", {"user_id": user_id, "period": period}, _run)


# ══════════════════════════════════════════════════════════════════════════════
# WRITE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@tool
def create_task(user_id: str, title: str, due_date: Optional[str] = None,
                priority: str = "medium", commitment_id: Optional[str] = None) -> dict:
    """
    Create a new task for the user in the database. Priority can be low/medium/high/urgent.
    CRITICAL: This ONLY creates the task in the database. You MUST immediately call `sync_task_to_google_calendar` with the returned task ID so it shows up on their live Google Calendar!
    """
    from app.database import SessionLocal
    from app.models.task import Task
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            parsed_date = dt.fromisoformat(due_date) if due_date else None
            task = Task(
                user_id=_clean_id(user_id),
                title=title,
                priority=priority,
                due_date=parsed_date,
                planned_date=parsed_date, # Required to show up in Calendar and Daily Planning
                commitment_id=_clean_id(commitment_id) if commitment_id else None,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return _task_to_dict(task)
        finally:
            db.close()

    return _run_tool("create_task", {"user_id": user_id, "title": title,
                                      "due_date": due_date, "priority": priority}, _run)


@tool
def update_task_status(task_id: str, status: str) -> dict:
    """
    Update the status of a task. status: completed sets is_done=True, pending sets is_done=False.
    CRITICAL: You MUST immediately call `sync_task_to_google_calendar` with this task_id afterward to keep their live calendar in sync!
    """
    from app.database import SessionLocal
    from app.models.task import Task

    def _run():
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == _clean_id(task_id)).first()
            if not task:
                return {"error": f"Task {task_id} not found"}
            task.is_done = (status == "completed")
            db.commit()
            db.refresh(task)
            return _task_to_dict(task)
        finally:
            db.close()

    return _run_tool("update_task_status", {"task_id": task_id, "status": status}, _run)


@tool
def sync_task_to_google_calendar(task_id: str) -> dict:
    """
    Use this tool IMMEDIATELY after creating or updating a task to push the changes to the user's live Google Calendar.
    Requires the task_id of the task that was just created or modified.
    """
    from app.database import SessionLocal
    from app.models.task import Task
    from app.models.user import User
    from app.services.google_calendar import create_calendar_event, update_calendar_event

    def _run():
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == _clean_id(task_id)).first()
            if not task:
                return {"error": f"Task {task_id} not found."}
            
            user = db.query(User).filter(User.id == task.user_id).first()
            if not user or not user.google_access_token:
                return {"error": "User does not have a connected Google account."}

            if task.google_event_id:
                try:
                    update_calendar_event(user, task, db=db)
                    return {"status": "success", "message": f"Task {task_id} updated on Google Calendar."}
                except Exception as e:
                    return {"error": f"Failed to update task on Google Calendar: {str(e)}"}
            else:
                try:
                    event_id = create_calendar_event(user, task, db=db)
                    if event_id:
                        task.google_event_id = event_id
                        db.commit()
                        db.refresh(task)
                        return {"status": "success", "message": f"Task {task_id} synced to Google Calendar with event_id {event_id}."}
                    else:
                        return {"error": "Failed to create Google Calendar event (unknown error)."}
                except Exception as e:
                    return {"error": f"Failed to sync task to Google Calendar: {str(e)}"}
        finally:
            db.close()
            
    return _run_tool("sync_task_to_google_calendar", {"task_id": task_id}, _run)


@tool
def create_commitment(user_id: str, type: str, title: str, due_date: str,
                      amount: Optional[float] = None) -> dict:
    """Create a new commitment (bill/interview/assignment/event) with automatic risk and priority scoring."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    from app.services.priority_engine import PriorityEngine
    from app.services.risk_engine import RiskEngine
    from app.services.root_cause_engine import RootCauseEngine
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            c = Commitment(
                user_id=_clean_id(user_id),
                type=type,
                title=title,
                due_date=dt.fromisoformat(due_date),
                amount=amount,
                source="ai_chat",
            )
            db.add(c)
            db.flush()
            c.priority_score = PriorityEngine.score(c)
            c.risk_score = RiskEngine.score(c)
            rc = RootCauseEngine.predict(c)
            c.root_cause = rc["root_cause"]
            c.root_cause_score = rc["score"]
            db.commit()
            db.refresh(c)
            return _commitment_to_dict(c)
        finally:
            db.close()

    return _run_tool("create_commitment",
                     {"user_id": user_id, "type": type, "title": title, "due_date": due_date}, _run)


@tool
def set_daily_highlight(user_id: str, date: str, highlight_text: str,
                        task_ids: Optional[list] = None) -> dict:
    """Set the highlight / journal entry for a given day."""
    from app.database import SessionLocal
    from app.models.daily_highlight import DailyHighlight
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            target = dt.fromisoformat(date)
            hl = db.query(DailyHighlight).filter(
                DailyHighlight.user_id == _clean_id(user_id),
                DailyHighlight.date == target,
                DailyHighlight.highlight_type == "ai_chat",
            ).first()
            if not hl:
                hl = DailyHighlight(
                    user_id=_clean_id(user_id),
                    date=target,
                    highlight_type="ai_chat",
                )
                db.add(hl)
            hl.content = highlight_text
            db.commit()
            db.refresh(hl)
            return {"id": str(hl.id), "date": str(hl.date), "content": hl.content}
        finally:
            db.close()

    return _run_tool("set_daily_highlight",
                     {"user_id": user_id, "date": date, "highlight_text": highlight_text[:100]}, _run)


@tool
def create_reminder(user_id: str, commitment_id: str, remind_at: str, style: str) -> dict:
    """Create a reminder for a commitment. Style: Deadline/Achievement/Consequence/Streak."""
    from app.database import SessionLocal
    from app.models.reminder import Reminder
    from app.models.commitment import Commitment
    from app.services.intervention_engine import InterventionEngine
    from app.models.user import User

    def _run():
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == _clean_id(user_id)).first()
            commitment = db.query(Commitment).filter(Commitment.id == _clean_id(commitment_id)).first()
            if not user or not commitment:
                return {"error": "User or commitment not found"}
            msg = InterventionEngine.generate_message(commitment, style.lower(), user)
            reminder = Reminder(
                user_id=_clean_id(user_id),
                commitment_id=_clean_id(commitment_id),
                style=style.lower(),
                message=msg,
            )
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            return {"id": str(reminder.id), "message": reminder.message, "style": reminder.style}
        finally:
            db.close()

    return _run_tool("create_reminder",
                     {"user_id": user_id, "commitment_id": commitment_id, "style": style}, _run)


@tool
def log_focus_session(user_id: str, task_id: Optional[str], duration_mins: int,
                      session_type: str = "pomodoro", distraction_count: int = 0) -> dict:
    """Log a completed focus or Pomodoro session for a task."""
    from app.database import SessionLocal
    from app.focus.models import FocusSession
    from datetime import datetime

    def _run():
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            session = FocusSession(
                user_id=_clean_id(user_id),
                task_id=_clean_id(task_id) if task_id else None,
                mode=session_type,
                status="completed",
                started_at=now - __import__('datetime').timedelta(minutes=duration_mins),
                ended_at=now,
                actual_duration_minutes=duration_mins,
                planned_duration_minutes=duration_mins,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return _focus_to_dict(session)
        finally:
            db.close()

    return _run_tool("log_focus_session",
                     {"user_id": user_id, "duration_mins": duration_mins, "session_type": session_type}, _run)


# ══════════════════════════════════════════════════════════════════════════════
# AI TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@tool
def decompose_commitment(commitment_id: str, title: str, due_date: str, type: str) -> list:
    """Break down a high-level commitment into granular actionable sub-tasks with time estimates."""
    from app.services.graph_service import GraphService

    class _FakeCommitment:
        pass

    def _run():
        from datetime import date as dt
        fc = _FakeCommitment()
        fc.type = type
        fc.title = title
        try:
            fc.due_date = dt.fromisoformat(due_date)
        except Exception:
            fc.due_date = dt.today() + __import__('datetime').timedelta(days=7)
        tasks = GraphService.decompose(fc)
        return [{"title": t["title"], "estimated_minutes": t["estimated_minutes"],
                 "due_date": str(t["due_date"])} for t in tasks]

    return _run_tool("decompose_commitment",
                     {"commitment_id": commitment_id, "title": title, "type": type}, _run)


@tool
def generate_recovery_plan(commitment_id: str, root_cause: str, deadline: str,
                           overdue_count: int = 0) -> list:
    """Generate a 4-6 step recovery plan for a behind-schedule commitment based on its root cause."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment

    def _run():
        db = SessionLocal()
        try:
            commitment = db.query(Commitment).filter(
                Commitment.id == _clean_id(commitment_id)
            ).first()
            if not commitment:
                return [f"Could not find commitment {commitment_id}. Please verify the ID."]
            import asyncio
            from app.services.llm_service import LLMService
            llm = LLMService()
            try:
                plan_text = asyncio.get_event_loop().run_until_complete(
                    llm.generate_recovery_plan(commitment)
                )
            except RuntimeError:
                loop = asyncio.new_event_loop()
                plan_text = loop.run_until_complete(llm.generate_recovery_plan(commitment))
                loop.close()
            return [line.strip() for line in plan_text.split("\n") if line.strip()]
        finally:
            db.close()

    return _run_tool("generate_recovery_plan",
                     {"commitment_id": commitment_id, "root_cause": root_cause}, _run)


@tool
def get_intervention_message(user_id: str, commitment_id: str, style: str) -> str:
    """Generate a personalized intervention message. Style: Deadline/Achievement/Consequence/Streak."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    from app.models.user import User
    from app.services.intervention_engine import InterventionEngine

    def _run():
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == _clean_id(user_id)).first()
            commitment = db.query(Commitment).filter(
                Commitment.id == _clean_id(commitment_id)
            ).first()
            if not user or not commitment:
                return "Could not generate intervention — user or commitment not found."
            return InterventionEngine.generate_message(commitment, style.lower(), user)
        finally:
            db.close()

    return _run_tool("get_intervention_message",
                     {"user_id": user_id, "commitment_id": commitment_id, "style": style}, _run)


@tool
def generate_daily_highlights(user_id: str, date: str) -> str:
    """Generate a dynamic daily highlight using LLM based on tasks completed on the given date."""
    from app.database import SessionLocal
    from app.models.task import Task
    from app.models.daily_highlight import DailyHighlight
    from app.services.hybrid_client import HybridClient
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            target_date = dt.fromisoformat(date)
            # Gather tasks
            tasks = db.query(Task).filter(
                Task.user_id == _clean_id(user_id),
                Task.planned_date == target_date,
                Task.is_done == True
            ).all()
            
            task_titles = [t.title for t in tasks]
            task_summary = ", ".join(task_titles) if task_titles else "No tasks completed"
            
            prompt_text = (
                f"Generate a detailed, journal-style daily highlight based on this productivity session. "
                f"Date: {target_date}. Completed tasks: {task_summary}. "
                "Structure your response strictly using markdown:\n"
                "### 📝 Today's Reflection\n"
                "(Write a personalized 2-3 sentence reflection on the day's overall effort)\n\n"
                "### 🎯 Task Explanations & AI Coaching\n"
                "(For EVERY single task completed, list it as a bullet point and provide a 1-sentence explanation of its impact, plus a micro-recommendation for tomorrow based on that specific task.)"
            )
            
            client = HybridClient()
            ai_content = client.generate(
                prompt=prompt_text,
                system_instr="You are a supportive productivity coach generating highly personalized, task-by-task end-of-day journal entries.",
                temperature=0.7
            )
            
            # Save or Update
            hl = db.query(DailyHighlight).filter(
                DailyHighlight.user_id == _clean_id(user_id),
                DailyHighlight.date == target_date,
                DailyHighlight.highlight_type == "shutdown"
            ).first()
            
            # Simple AI summary for the footer
            summary = client.generate(f"Summarize this in exactly one short sentence: {ai_content}", "Summarizer", 0.3)
            
            if not hl:
                hl = DailyHighlight(
                    user_id=_clean_id(user_id),
                    date=target_date,
                    highlight_type="shutdown",
                    content=ai_content,
                    ai_summary=summary,
                    tasks_completed=len(tasks)
                )
                db.add(hl)
            else:
                hl.content = ai_content
                hl.ai_summary = summary
                hl.tasks_completed = len(tasks)
                
            db.commit()
            return f"Daily Highlight generated and saved for {date}:\n{ai_content}"
        except Exception as e:
            return f"Failed to generate daily highlight: {e}"
        finally:
            db.close()

    return _run_tool("generate_daily_highlights", {"user_id": user_id, "date": date}, _run)


@tool
def generate_weekly_review(user_id: str, start_date: str, end_date: str) -> str:
    """Generate a dynamic weekly review using LLM based on tasks completed over the given week range."""
    from app.database import SessionLocal
    from app.models.task import Task
    from app.services.hybrid_client import HybridClient
    from datetime import date as dt

    def _run():
        db = SessionLocal()
        try:
            start_dt = dt.fromisoformat(start_date)
            end_dt = dt.fromisoformat(end_date)
            
            # Gather tasks
            tasks = db.query(Task).filter(
                Task.user_id == _clean_id(user_id),
                Task.planned_date >= start_dt,
                Task.planned_date <= end_dt
            ).all()
            
            completed_tasks = [t.title for t in tasks if t.is_done]
            pending_tasks = [t.title for t in tasks if not t.is_done]
            
            prompt_text = (
                f"Generate a highly detailed, comprehensive Weekly Review for the week of {start_date} to {end_date}. "
                f"Completed {len(completed_tasks)} tasks: {', '.join(completed_tasks) if completed_tasks else 'None'}. "
                f"Pending {len(pending_tasks)} tasks: {', '.join(pending_tasks) if pending_tasks else 'None'}. "
                "Structure the review strictly using markdown format:\n"
                "### 🏆 The Wins (Completed Tasks)\n"
                "(List EVERY completed task as a bullet point. For each, add a brief AI coaching note explaining its value and a recommendation on how to build on this momentum.)\n\n"
                "### 🚧 The Bottlenecks (Pending Tasks)\n"
                "(List EVERY pending task as a bullet point. For each, diagnose a potential reason it stalled and provide a specific, actionable micro-step to unblock it next week.)\n\n"
                "### 🚀 Focus for Next Week\n"
                "(A final 2-3 sentence strategic overview.)"
            )
            
            client = HybridClient()
            ai_content = client.generate(
                prompt=prompt_text,
                system_instr="You are an elite productivity strategist performing a weekly performance review.",
                temperature=0.7
            )
            
            return f"Weekly Review generated:\n{ai_content}"
        except Exception as e:
            return f"Failed to generate weekly review: {e}"
        finally:
            db.close()

    return _run_tool("generate_weekly_review", {"user_id": user_id, "start_date": start_date, "end_date": end_date}, _run)


# ── All tools list (imported by graph.py) ─────────────────────────────────────
ALL_TOOLS = [
    fetch_tasks,
    fetch_commitments,
    fetch_overdue_tasks,
    fetch_daily_plan,
    fetch_focus_sessions,
    fetch_productivity_stats,
    create_task,
    update_task_status,
    create_commitment,
    set_daily_highlight,
    create_reminder,
    log_focus_session,
    decompose_commitment,
    generate_recovery_plan,
    get_intervention_message,
    sync_task_to_google_calendar,
    generate_daily_highlights,
    generate_weekly_review,
]
