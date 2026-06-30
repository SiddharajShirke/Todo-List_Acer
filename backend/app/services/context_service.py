"""
services/context_service.py — Graph Context Hydration Service

build_graph_context() is called by the hydrate_context node at every graph entry.
Returns a plain dict (JSON-serializable) mapping to AgentState context/intelligence/focus layers.

Rules:
- Wrap each service call in try/except — a failure must not crash the graph
- Return plain dicts only — no SQLAlchemy instances
- No LLM calls here — purely a data aggregation layer
"""
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session


# ── Legacy method (kept for backward compat with old dormant routers/ai.py) ────
class ContextService:
    @staticmethod
    def build_context(db: Session, user_id: int, commitment_id: int = None):
        """Legacy — used by old /api/ai/* dormant endpoints. Do not remove."""
        from app.models.commitment import Commitment
        from app.models.task import Task
        from app.schemas.ai import Context

        today = date.today()
        active_commitment = None
        if commitment_id:
            c = db.query(Commitment).filter(
                Commitment.id == commitment_id, Commitment.user_id == user_id
            ).first()
            if c:
                active_commitment = {
                    "id": c.id, "title": c.title,
                    "due_date": str(c.due_date) if c.due_date else None,
                    "priority": c.priority_score,
                }
        pending_tasks = db.query(Task).filter(
            Task.user_id == user_id, Task.is_done == False
        ).all()
        tasks_data = [
            {"id": t.id, "title": t.title,
             "due_date": str(t.due_date) if t.due_date else None}
            for t in pending_tasks
        ]
        return Context(
            date=today,
            user_id=user_id,
            active_commitment=active_commitment,
            tasks=tasks_data,
            calendar_events=[],
            conversation_history=[],
        )


# ── Active graph context builder ───────────────────────────────────────────────

async def build_graph_context(user_id: str) -> dict:
    """
    Called by hydrate_context_node. Returns all AgentState context layers as a dict.
    Each sub-call is wrapped in try/except — partial failures return empty defaults.
    """
    uid = int(user_id)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    results = await asyncio.gather(
        _fetch_current_tasks(uid, today),
        _fetch_overdue_tasks(uid, today),
        _fetch_commitments(uid),
        _fetch_daily_plan(uid, today),
        _fetch_focus_today(uid, today_start),
        return_exceptions=True,
    )

    current_tasks   = results[0] if not isinstance(results[0], Exception) else []
    overdue_tasks   = results[1] if not isinstance(results[1], Exception) else []
    commitments     = results[2] if not isinstance(results[2], Exception) else []
    daily_plan      = results[3] if not isinstance(results[3], Exception) else None
    focus_data      = results[4] if not isinstance(results[4], Exception) else {"sessions": [], "total_mins": 0}

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.warning(f"[context_service] sub-call {i} failed: {r}")

    # Risk flags — commitments with risk_score >= 0.5
    risk_flags = [
        str(c["id"]) for c in commitments
        if (c.get("risk_score") or 0) >= 0.5
    ]

    # Priority scores — map task_id → priority rank
    priority_map = {str(t["id"]): i for i, t in enumerate(current_tasks)}

    # Root cause — dominant pattern from most high-risk commitment
    root_cause = None
    high_risk = [c for c in commitments if (c.get("risk_score") or 0) >= 0.5]
    if high_risk:
        root_cause = high_risk[0].get("root_cause")

    return {
        "current_tasks":    current_tasks,
        "overdue_tasks":    overdue_tasks,
        "commitments":      commitments,
        "daily_plan":       daily_plan,
        "risk_flags":       risk_flags,
        "priority_scores":  priority_map,
        "root_cause":       root_cause,
        "focus_sessions":   focus_data["sessions"],
        "total_focus_mins": focus_data["total_mins"],
        "distraction_count": 0,
    }


# ── Private async sub-fetchers (run in thread executor to avoid blocking) ──────

async def _fetch_current_tasks(uid: int, today: date) -> list:
    def _sync():
        from app.database import SessionLocal
        from app.models.task import Task
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.user_id == uid,
                Task.planned_date == today,
            ).order_by(Task.order_index).all()
            return [_t(t) for t in tasks]
        finally:
            db.close()
    return await asyncio.to_thread(_sync)


async def _fetch_overdue_tasks(uid: int, today: date) -> list:
    def _sync():
        from app.database import SessionLocal
        from app.models.task import Task
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.user_id == uid,
                Task.is_done == False,
                Task.due_date < today,
            ).order_by(Task.due_date).all()
            return [_t(t) for t in tasks]
        finally:
            db.close()
    return await asyncio.to_thread(_sync)


async def _fetch_commitments(uid: int) -> list:
    def _sync():
        from app.database import SessionLocal
        from app.models.commitment import Commitment
        db = SessionLocal()
        try:
            items = db.query(Commitment).filter(
                Commitment.user_id == uid,
                Commitment.is_done == False,
            ).order_by(Commitment.priority_score.desc()).all()
            return [_c(c) for c in items]
        finally:
            db.close()
    return await asyncio.to_thread(_sync)


async def _fetch_daily_plan(uid: int, today: date) -> Optional[dict]:
    def _sync():
        from app.database import SessionLocal
        from app.models.daily_plan import DailyPlan
        db = SessionLocal()
        try:
            plan = db.query(DailyPlan).filter(
                DailyPlan.user_id == uid,
                DailyPlan.plan_date == today,
            ).first()
            if not plan:
                return None
            return {
                "id": str(plan.id),
                "date": str(plan.plan_date),
                "morning_intention": plan.morning_intention,
                "energy_level": plan.energy_level,
                "mood": plan.mood,
                "is_complete": plan.is_complete,
            }
        finally:
            db.close()
    return await asyncio.to_thread(_sync)


async def _fetch_focus_today(uid: int, today_start: datetime) -> dict:
    def _sync():
        from app.database import SessionLocal
        from app.focus.models import FocusSession
        db = SessionLocal()
        try:
            sessions = db.query(FocusSession).filter(
                FocusSession.user_id == uid,
                FocusSession.status == "completed",
                FocusSession.is_break == False,
                FocusSession.started_at >= today_start,
            ).all()
            total_mins = sum(s.actual_duration_minutes for s in sessions)
            return {
                "sessions": [
                    {"id": str(s.id), "mode": s.mode,
                     "actual_duration_minutes": s.actual_duration_minutes}
                    for s in sessions
                ],
                "total_mins": total_mins,
            }
        finally:
            db.close()
    return await asyncio.to_thread(_sync)


# ── Serialization helpers ──────────────────────────────────────────────────────

def _t(task) -> dict:
    return {
        "id": str(task.id), "title": task.title,
        "is_done": task.is_done, "priority": task.priority,
        "due_date": str(task.due_date) if task.due_date else None,
        "planned_date": str(task.planned_date) if task.planned_date else None,
        "commitment_id": str(task.commitment_id) if task.commitment_id else None,
    }


def _c(commitment) -> dict:
    return {
        "id": str(commitment.id), "title": commitment.title,
        "type": commitment.type,
        "due_date": str(commitment.due_date) if commitment.due_date else None,
        "priority_score": commitment.priority_score,
        "risk_score": commitment.risk_score,
        "root_cause": commitment.root_cause,
        "is_done": commitment.is_done,
    }
