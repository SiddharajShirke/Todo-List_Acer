"""
services/focus_service.py — Focus Session + Streak Logic
Handles: break schedule, session counting, streak tracking.

Pomodoro Rules (standard): 4 x 25-min work → 5-min short break → 20-min long break after 4
Flowtime: user decides when to stop, session is whatever duration they ran
DeepWork: single 90-min block
"""
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.models.user import User

class FocusService:
    POMODORO_WORK_DEFAULT = 25
    POMODORO_SHORT_BREAK = 5
    POMODORO_LONG_BREAK = 20
    POMODORO_LONG_BREAK_INTERVAL = 4

    @classmethod
    def next_session_info(cls, current_number: int, prefs: dict) -> dict:
        """Compute what comes after current pomodoro number."""
        work_mins = prefs.get("pomodoro_work_mins", cls.POMODORO_WORK_DEFAULT)
        if current_number % cls.POMODORO_LONG_BREAK_INTERVAL == 0:
            return {"next": "break", "duration": prefs.get("pomodoro_long_break_mins", cls.POMODORO_LONG_BREAK), "label": "Long Break 🌿"}
        else:
            return {"next": "break", "duration": prefs.get("pomodoro_break_mins", cls.POMODORO_SHORT_BREAK), "label": "Short Break ☕"}

    @classmethod
    def update_streak(cls, user: User, db: Session):
        """Update streak_count in user.preferences based on today's activity."""
        prefs = dict(user.preferences or {})
        today_str = str(date.today())
        yesterday_str = str(date.today().replace(day=date.today().day - 1))
        last = prefs.get("last_streak_date", "")
        if last == today_str:
            return
        if last == yesterday_str:
            prefs["streak_count"] = prefs.get("streak_count", 0) + 1
        else:
            prefs["streak_count"] = 1
        prefs["last_streak_date"] = today_str
        user.preferences = prefs
        db.commit()
