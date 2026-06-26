"""
services/intervention_engine.py — Intervention Style Selector
Maps root_cause + user preferences to a reminder style.

Styles:
  deadline      → "Only X days left. You must pay ₹2,400 by June 30."
  achievement   → "You're 60% done! Finish 2 more tasks to complete this."
  consequence   → "Unpaid bills may lead to service disconnection."
  streak        → "Keep your 5-day focus streak alive! 1 Pomodoro = done."
"""
from app.models.user import User

STYLE_MAP = {
    "time_crunch":     "deadline",
    "forgot":          "deadline",
    "procrastination": "consequence",
    "low_motivation":  "achievement",
    "too_large":       "streak",
    "external_block":  "achievement",
}

class InterventionEngine:
    @classmethod
    def select_style(cls, commitment, user: User) -> str:
        prefs = user.preferences or {}
        preferred = prefs.get("preferred_style")
        if preferred:
            return preferred
        return STYLE_MAP.get(commitment.root_cause or "time_crunch", "deadline")

    @classmethod
    def generate_message(cls, commitment, style: str, user: User) -> str:
        prefs = user.preferences or {}
        streak = prefs.get("streak_count", 0)
        name = user.name or "there"
        from datetime import date
        try:
            days = max(0, (commitment.due_date - date.today()).days)
        except:
            days = 7

        if style == "deadline":
            amount_str = f" ₹{int(commitment.amount):,}" if commitment.amount else ""
            return f"⏰ Hey {name}, only {days} day{'s' if days != 1 else ''} left to complete: {commitment.title}{amount_str}. Act now!"
        elif style == "achievement":
            tasks = getattr(commitment, "tasks", [])
            done = sum(1 for t in tasks if t.is_done)
            total = len(tasks)
            if total > 0:
                pct = int(done / total * 100)
                return f"🏆 Great progress! You're {pct}% done with '{commitment.title}'. {total - done} task{'s' if total - done != 1 else ''} left!"
            return f"🏆 You can do this! Complete '{commitment.title}' to reach your goal."
        elif style == "consequence":
            return f"⚠️ Heads up, {name}: Missing '{commitment.title}' by {commitment.due_date} could have consequences. Take 1 step now."
        elif style == "streak":
            return f"🔥 You're on a {streak}-day streak! Complete 1 Pomodoro on '{commitment.title}' to keep it going."
        return f"📌 Reminder: '{commitment.title}' is due {commitment.due_date}."
