"""
routers/ai.py — LangGraph Agentic AI Endpoints (ACTIVATED)

Paradigm 2 endpoints — all powered by the LangGraph graph.
Graph is compiled once at startup (app.state.graph) and reused per request.
Thread ID provides multi-turn memory via PostgresSaver checkpointer.

Endpoints:
  POST /api/ai/chat     ← PRIMARY: general agentic chat with tool access
  POST /api/ai/plan     ← Planning session for a specific commitment
  POST /api/ai/recover  ← Recovery plan for a high-risk commitment
  POST /api/ai/extract  ← DORMANT: direct service already handles this
  POST /api/ai/reminder ← DORMANT: Celery already handles this
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.routers.deps import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── Request / Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    session_type: Optional[str] = "chat"


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    tool_calls_made: List[str] = []
    session_type: str


class PlanRequest(BaseModel):
    commitment_id: str
    message: Optional[str] = None


class RecoverRequest(BaseModel):
    commitment_id: str


# ── Helper: get or register agent session ──────────────────────────────────────

def _upsert_session(db: Session, user_id: int, thread_id: str, session_type: str):
    """Insert or update agent_session record. Failures are non-fatal."""
    try:
        from sqlalchemy import text
        db.execute(
            text(
                "INSERT INTO agent_sessions (user_id, thread_id, session_type) "
                "VALUES (:uid, :tid, :stype) "
                "ON CONFLICT (thread_id) DO UPDATE SET updated_at = now()"
            ),
            {"uid": user_id, "tid": thread_id, "stype": session_type}
        )
        db.commit()
    except Exception as e:
        logger.warning(f"agent_sessions upsert failed (non-fatal): {e}")


def _build_initial_state(user_id: str, session_type: str, message: str) -> dict:
    """Build the initial AgentState dict for a new graph invocation."""
    return {
        "user_id": user_id,
        "session_type": session_type,
        "messages": [HumanMessage(content=message)],
        "current_tasks": [],
        "overdue_tasks": [],
        "commitments": [],
        "daily_plan": None,
        "risk_flags": [],
        "priority_scores": {},
        "root_cause": None,
        "focus_sessions": [],
        "total_focus_mins": 0,
        "distraction_count": 0,
        "tool_calls_made": [],
        "needs_clarification": False,
        "final_response": None,
    }


async def _invoke_graph(request: Request, user_id: str, session_type: str,
                         message: str, thread_id: str) -> dict:
    """Invoke the compiled graph and return the raw result state."""
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="AI graph not initialized. Server is starting up.")

    initial_state = _build_initial_state(user_id, session_type, message)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }
    try:
        result = await graph.ainvoke(initial_state, config)
        return result
    except Exception as e:
        logger.error(f"[ai/chat] Graph invocation failed for user={user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")


def _extract_response(result: dict) -> tuple[str, list]:
    """Extract the final text response and list of tool calls from graph result."""
    messages = result.get("messages", [])
    response_text = ""
    if messages:
        last = messages[-1]
        response_text = last.content if hasattr(last, "content") else str(last)
    tool_calls = result.get("tool_calls_made", [])
    return response_text, tool_calls


# ── POST /api/ai/chat ──────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Primary agentic chat endpoint.
    Maintains multi-turn memory via thread_id (PostgresSaver checkpointer).
    Brain has full tool access to read/write user tasks, commitments, and focus data.
    """
    thread_id = payload.thread_id or str(uuid.uuid4())
    user_id = str(current_user.id)
    session_type = payload.session_type or "chat"

    _upsert_session(db, current_user.id, thread_id, session_type)

    result = await _invoke_graph(request, user_id, session_type, payload.message, thread_id)
    response_text, tool_calls = _extract_response(result)

    logger.info(f"[ai/chat] user={user_id} thread={thread_id} tools={tool_calls}")

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        tool_calls_made=tool_calls,
        session_type=session_type,
    )


# ── POST /api/ai/plan ──────────────────────────────────────────────────────────

@router.post("/plan", response_model=ChatResponse)
async def plan_commitment(
    payload: PlanRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Planning session: Brain fetches the commitment and calls decompose_commitment tool.
    Creates a new thread per planning session.
    """
    thread_id = str(uuid.uuid4())
    user_id = str(current_user.id)
    session_type = "planning"

    message = (
        payload.message
        or f"Create a detailed step-by-step execution plan for commitment ID {payload.commitment_id}. "
           f"First fetch the commitment details, then decompose it into actionable sub-tasks with time estimates."
    )

    _upsert_session(db, current_user.id, thread_id, session_type)
    result = await _invoke_graph(request, user_id, session_type, message, thread_id)
    response_text, tool_calls = _extract_response(result)

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        tool_calls_made=tool_calls,
        session_type=session_type,
    )


# ── POST /api/ai/recover ───────────────────────────────────────────────────────

@router.post("/recover", response_model=ChatResponse)
async def recover_commitment(
    payload: RecoverRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recovery session: Brain fetches overdue tasks and commitment, then calls generate_recovery_plan.
    Returns a 4-6 step actionable recovery plan.
    """
    thread_id = str(uuid.uuid4())
    user_id = str(current_user.id)
    session_type = "recovery"

    message = (
        f"Generate a recovery plan for commitment ID {payload.commitment_id}. "
        f"First fetch the commitment details and overdue tasks, then generate a concrete recovery plan."
    )

    _upsert_session(db, current_user.id, thread_id, session_type)
    result = await _invoke_graph(request, user_id, session_type, message, thread_id)
    response_text, tool_calls = _extract_response(result)

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        tool_calls_made=tool_calls,
        session_type=session_type,
    )


# ── DORMANT ENDPOINTS (kept for backward compat, not wired to graph) ───────────

from app.schemas.ai import (
    ExtractRequest, CommitmentOutput,
    TaskPlanRequest, TaskPlanOutput,
    ReminderRequest, ReminderOutput,
)
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService


@router.post("/extract", response_model=CommitmentOutput)
async def extract_commitment_dormant(
    request: ExtractRequest, current_user: User = Depends(get_current_user)
):
    """DORMANT — Commitment extraction is handled by POST /api/commitments/ingest (direct service)."""
    raise HTTPException(
        status_code=501,
        detail="Use POST /api/commitments/ingest for AI text extraction. "
               "This endpoint is reserved for future graph-based extraction."
    )


@router.post("/reminder", response_model=ReminderOutput)
async def generate_reminder_dormant(
    request: ReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """DORMANT — Reminders are handled by Celery workers and InterventionEngine."""
    raise HTTPException(
        status_code=501,
        detail="Reminders are generated automatically by the scheduler. "
               "Use GET /api/reminders to view pending reminders."
    )
