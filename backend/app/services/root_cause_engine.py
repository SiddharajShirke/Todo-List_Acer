"""
services/root_cause_engine.py — Root Cause Predictor
Classifies WHY a commitment is likely to be missed.
Categories match intervention styles in intervention_engine.py

Root causes:
  too_large       → Break down further
  forgot          → Set reminders
  low_motivation  → Achievement/reward framing
  procrastination → Consequence-driven nudge
  time_crunch     → Deadline urgency framing
  external_block  → Needs external input (waiting on others)
"""
from datetime import date

class RootCauseEngine:
    @classmethod
    def predict(cls, commitment) -> dict:
        today = date.today()
        try:
            days = max(0, (commitment.due_date - today).days)
        except:
            days = 7

        tasks = getattr(commitment, "tasks", [])
        task_count = len(tasks)
        done_count = sum(1 for t in tasks if t.is_done)
        completion_rate = done_count / task_count if task_count > 0 else 0.0

        # Rule-based classification
        if task_count >= 5 and completion_rate < 0.3:
            return {"root_cause": "too_large", "score": 0.8}
        if days <= 2:
            return {"root_cause": "time_crunch", "score": 0.85}
        if days <= 7 and completion_rate == 0.0:
            return {"root_cause": "procrastination", "score": 0.75}
        if commitment.type == "interview" and task_count == 0:
            return {"root_cause": "low_motivation", "score": 0.65}
        if days > 14 and completion_rate == 0.0:
            return {"root_cause": "forgot", "score": 0.70}

        return {"root_cause": "time_crunch", "score": 0.50}
