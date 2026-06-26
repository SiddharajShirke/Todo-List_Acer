"""
services/priority_engine.py — Priority Score (0–100)

Formula:
  base_score = urgency_weight * urgency_score + financial_weight * financial_score
               + type_weight * type_score
  final = clamp(0, 100, base_score)

Factors:
  - urgency: days_until_due (closer = higher)
  - financial: log(amount) normalized
  - type: interview > bill > assignment > event > other
"""
from datetime import date
import math

class PriorityEngine:
    TYPE_WEIGHTS = {"interview": 25, "bill": 20, "assignment": 15, "event": 10, "other": 5}
    URGENCY_MAX_DAYS = 30

    @classmethod
    def score(cls, commitment) -> float:
        today = date.today()
        try:
            days_left = (commitment.due_date - today).days
        except:
            days_left = 14

        # Urgency (0-40 points): inverse of days left
        if days_left <= 0:
            urgency_score = 40
        elif days_left >= cls.URGENCY_MAX_DAYS:
            urgency_score = 5
        else:
            ratio = 1 - (days_left / cls.URGENCY_MAX_DAYS)
            urgency_score = 5 + (35 * ratio)

        # Type weight (0-25 points)
        type_score = cls.TYPE_WEIGHTS.get(commitment.type, 5)

        # Financial weight (0-20 points)
        financial_score = 0
        if commitment.amount and commitment.amount > 0:
            financial_score = min(20, math.log10(float(commitment.amount) + 1) * 4)

        # Risk penalty bonus (0-15 points)
        risk_bonus = (getattr(commitment, "risk_score", 0) or 0) * 15

        raw = urgency_score + type_score + financial_score + risk_bonus
        return round(min(100, max(0, raw)), 2)
