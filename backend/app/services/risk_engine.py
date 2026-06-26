"""
services/risk_engine.py — Risk Score (0.0–1.0)
Estimates probability of missing the commitment.

Factors:
  - days_to_due: fewer = higher risk
  - task completion rate: lower = higher risk
  - amount: high amounts = higher risk
  - type: interview/bill = higher risk base
"""
from datetime import date

class RiskEngine:
    TYPE_BASE_RISK = {"interview": 0.3, "bill": 0.2, "assignment": 0.15, "event": 0.1, "other": 0.05}

    @classmethod
    def score(cls, commitment) -> float:
        today = date.today()
        try:
            days = max(0, (commitment.due_date - today).days)
        except:
            days = 7

        # Urgency factor
        if days <= 1:
            urgency_risk = 0.5
        elif days <= 3:
            urgency_risk = 0.35
        elif days <= 7:
            urgency_risk = 0.25
        elif days <= 14:
            urgency_risk = 0.15
        else:
            urgency_risk = 0.05

        # Task completion factor
        tasks = getattr(commitment, "tasks", [])
        task_risk = 0.0
        if tasks:
            done = sum(1 for t in tasks if t.is_done)
            completion_rate = done / len(tasks)
            task_risk = (1 - completion_rate) * 0.25

        base_risk = cls.TYPE_BASE_RISK.get(commitment.type, 0.05)
        raw = min(1.0, urgency_risk + task_risk + base_risk)
        return round(raw, 3)
