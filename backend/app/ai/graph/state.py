"""
ai/graph/state.py — LangGraph Agent State Definition

AgentState is the single source of truth flowing through every graph node.
All fields MUST be JSON-serializable — no SQLAlchemy instances, no DB sessions.

Layers:
  IDENTITY       — who is this session for
  CONVERSATION   — LangGraph-managed message history (add_messages reducer)
  TASK CONTEXT   — hydrated by hydrate_context node at graph entry
  INTELLIGENCE   — risk flags, priority scores, root cause
  FOCUS          — today's Pomodoro/deep work sessions
  EXECUTION      — tool tracking, clarification flags, final response
"""
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── IDENTITY ──────────────────────────────────────────────────────────
    user_id: str                                    # str(user.id) from JWT
    session_type: str                               # 'chat' | 'planning' | 'recovery'

    # ── CONVERSATION ──────────────────────────────────────────────────────
    # add_messages reducer: LangGraph appends new messages instead of overwriting
    messages: Annotated[list[BaseMessage], add_messages]

    # ── TASK CONTEXT (hydrated by hydrate_context node) ───────────────────
    current_tasks: list[dict]                       # today's tasks
    overdue_tasks: list[dict]                       # past-due tasks
    commitments: list[dict]                         # active commitments
    daily_plan: Optional[dict]                      # today's DailyPlan

    # ── INTELLIGENCE (hydrated by hydrate_context node) ───────────────────
    risk_flags: list[str]                           # commitment IDs with risk_score >= 0.5
    priority_scores: dict                           # {str(task_id): float}
    root_cause: Optional[str]                       # 'procrastination' | 'time_crunch' | etc.

    # ── FOCUS ─────────────────────────────────────────────────────────────
    focus_sessions: list[dict]                      # today's focus sessions
    total_focus_mins: int                           # sum of today's session durations
    distraction_count: int                          # today's total distractions

    # ── EXECUTION ─────────────────────────────────────────────────────────
    tool_calls_made: list[str]                      # names of tools called so far
    needs_clarification: bool                       # Brain needs user input
    final_response: Optional[str]                   # last AI text response (for quick access)


# ── Legacy AIState (kept for backward compat with old dormant agents) ──────────
# These old agents are NOT used by the new graph. Preserved to avoid import errors.
from typing import Dict, Any

class AIState(TypedDict):
    user_id: int
    action: str
    context: Optional[Dict[str, Any]]
    memory: Optional[Dict[str, Any]]
    input: Optional[Any]
    response: Optional[Any]
