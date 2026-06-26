"""
services/graph_service.py — Subtask Decomposition
Deterministic (no LLM API call) — maps commitment type to standard subtask templates.
Produces 3-5 actionable steps with time estimates.
"""
import math
from datetime import date, timedelta

TEMPLATES = {
    "bill": [
        {"title": "Verify exact amount and due date", "estimated_minutes": 5},
        {"title": "Log in to payment portal / app", "estimated_minutes": 5},
        {"title": "Complete payment and save confirmation", "estimated_minutes": 10},
        {"title": "Screenshot or note confirmation number", "estimated_minutes": 5},
    ],
    "interview": [
        {"title": "Research company — products, mission, recent news", "estimated_minutes": 40},
        {"title": "Prepare STAR answers for common questions", "estimated_minutes": 60},
        {"title": "Review job description and match skills", "estimated_minutes": 30},
        {"title": "Prepare questions to ask the interviewer", "estimated_minutes": 20},
        {"title": "Mock interview (practice out loud or record)", "estimated_minutes": 30},
    ],
    "assignment": [
        {"title": "Read full brief / requirements", "estimated_minutes": 20},
        {"title": "Research and gather materials", "estimated_minutes": 40},
        {"title": "Create outline / structure", "estimated_minutes": 30},
        {"title": "Write / develop first draft", "estimated_minutes": 90},
        {"title": "Review, refine, and submit", "estimated_minutes": 30},
    ],
    "event": [
        {"title": "Confirm attendance and add to calendar", "estimated_minutes": 5},
        {"title": "Plan travel / logistics", "estimated_minutes": 15},
        {"title": "Prepare materials or outfit", "estimated_minutes": 20},
    ],
    "other": [
        {"title": "Define what exactly needs to be done", "estimated_minutes": 15},
        {"title": "Take the first concrete action step", "estimated_minutes": 25},
        {"title": "Review outcome and follow up", "estimated_minutes": 15},
    ],
}

class GraphService:
    @classmethod
    def decompose(cls, commitment) -> list:
        """Returns list of task dicts for DB creation."""
        template = TEMPLATES.get(commitment.type, TEMPLATES["other"])
        tasks = []
        today = date.today()
        try:
            due = commitment.due_date
            total_days = max(1, (due - today).days)
        except:
            due = today + timedelta(days=7)
            total_days = 7

        for i, t in enumerate(template):
            step_date = today + timedelta(days=max(0, total_days - len(template) + i))
            mins = t["estimated_minutes"]
            tasks.append({
                "title": t["title"],
                "description": None,
                "due_date": min(step_date, due),
                "order_index": i,
                "estimated_minutes": mins,
                "pomodoros_estimated": max(1, math.ceil(mins / 25)),
            })
        return tasks
