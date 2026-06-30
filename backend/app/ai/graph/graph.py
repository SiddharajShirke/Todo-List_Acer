"""
ai/graph/graph.py — LangGraph Agentic Graph (Production)

Graph flow:
  START → hydrate_context → brain → [tools_condition] → tools → brain → ... → END

Brain: ChatNVIDIA (primary) with ChatGoogleGenerativeAI (fallback)
Checkpointer: AsyncPostgresSaver (initialized at startup, passed in via build_graph())
Context: Hydrated from DB at every graph entry — Brain ALWAYS has real user data.
"""
from __future__ import annotations

import os
from typing import Any
from loguru import logger

from langchain_core.messages import SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.ai.graph.state import AgentState
from app.ai.tools.supabase_tools import ALL_TOOLS
from app.config import settings


# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a productivity-focused AI assistant with access to the user's real task data, commitments, focus history, and productivity stats via tools.

Rules:
1. NEVER assume task data — always fetch it first using tools before answering
2. NEVER access the database directly — only use provided tools
3. When a user says they are behind or stressed → fetch_overdue_tasks first
4. When planning the day → fetch_daily_plan and fetch_tasks first
5. Before creating a task → confirm with the user if the intent is ambiguous
6. After creating/updating data → confirm what you did in plain language
7. Keep responses conversational, warm, and motivating — not robotic
8. When asked about focus or Pomodoro sessions → use fetch_focus_sessions
9. For recovery plans → use fetch_commitments then generate_recovery_plan
"""


# ── Brain LLM (NVIDIA primary, Google GenAI fallback) ─────────────────────────

def _build_brain():
    """Build the LangChain Brain: ChatNVIDIA → fallback ChatGoogleGenerativeAI."""
    nvidia_llm = ChatNVIDIA(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        model=settings.NVIDIA_MODEL,
        temperature=0.3,
        max_tokens=1024,
        timeout=120,
    )
    gemini_llm = ChatGoogleGenerativeAI(
        google_api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        temperature=0.3,
        max_output_tokens=1024,
        timeout=120,
    )
    # LangChain native fallback chain — NVIDIA first, Gemini on any exception
    return nvidia_llm.with_fallbacks([gemini_llm])


# ── Graph Nodes ────────────────────────────────────────────────────────────────

async def brain_node(state: AgentState, brain_with_tools: Any) -> dict:
    """
    Brain node — calls the LLM with tools bound.
    Prepends a context summary so the LLM always knows the user's current situation.
    """
    messages = list(state.get("messages", []))
    
    # Sanitize ToolMessages: Ensure no tool message has content=None
    for msg in messages:
        if getattr(msg, "type", "") == "tool" and msg.content is None:
            msg.content = "null"

    from datetime import datetime
    now = datetime.now()
    current_date = now.strftime("%A, %Y-%m-%d %H:%M:%S")
    user_id = state.get("user_id", "")
    
    dynamic_context = (
        f"CRITICAL SYSTEM DATE: Today is {current_date}. You MUST use this to calculate any relative dates.\n"
        f"CRITICAL: Your assigned user_id is '{user_id}'. You MUST use exactly '{user_id}' for all tool calls requiring a user_id.\n"
        f"IMPORTANT: You have zero context right now. You MUST use your tools (like fetch_tasks) to get the user's data before answering questions.\n"
        f"MANDATORY GOOGLE CALENDAR RULE: Whenever you use the `create_task` or `update_task_status` tool, you MUST immediately use the `sync_task_to_google_calendar` tool with the newly generated task ID in the very next step. If you do not call sync_task_to_google_calendar, the task will be invisible to the user's live calendar."
    )

    system_msg = SystemMessage(content=SYSTEM_PROMPT + "\n\n" + dynamic_context)
    all_messages = [system_msg] + messages

    response = await brain_with_tools.ainvoke(all_messages)

    # Track tool calls made in this turn
    tool_calls_made = list(state.get("tool_calls_made", []))
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if tool_name and tool_name not in tool_calls_made:
                tool_calls_made.append(tool_name)

    return {
        "messages": [response],
        "tool_calls_made": tool_calls_made,
        "final_response": response.content if hasattr(response, "content") else str(response),
    }


# ── Graph Builder ──────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Build and compile the LangGraph agentic graph.

    Args:
        checkpointer: AsyncPostgresSaver instance from app.state (initialized in main.py lifespan)

    Returns:
        Compiled CompiledGraph ready for ainvoke()
    """
    brain_base = _build_brain()
    brain_with_tools = brain_base.bind_tools(ALL_TOOLS)

    # Wrap brain_node so it closes over brain_with_tools
    async def _brain_node(state: AgentState) -> dict:
        return await brain_node(state, brain_with_tools)

    builder = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    builder.add_node("brain", _brain_node)
    builder.add_node("tools", ToolNode(tools=ALL_TOOLS))

    # ── Edges ──────────────────────────────────────────────────────────────
    builder.add_edge(START, "brain")
    builder.add_conditional_edges("brain", tools_condition)  # → "tools" or END
    builder.add_edge("tools", "brain")                       # always loop back

    # ── Compile ────────────────────────────────────────────────────────────
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    graph = builder.compile(**compile_kwargs)
    logger.success("✅ LangGraph agentic graph compiled successfully")
    return graph
