import os
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

# Load environment first
load_dotenv('.env')

from app.database import engine
from app.models import (
    User, Channel, Commitment, WeeklyPlan, DailyPlan, 
    Task, FocusSession, DailyHighlight
)

def seed_database():
    with Session(engine) as db:
        # 1. Get or Create User
        # Try to find the user that recently logged in
        user = db.scalar(select(User).where(User.email == "sanjh.kanchan14@gmail.com"))
        if not user:
            # Fallback to the first user in the DB
            user = db.scalar(select(User))
            
        if not user:
            print("No user found in the database. Creating a demo user...")
            user = User(
                email="demo@example.com",
                name="Demo User",
                preferences={}
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        print(f"Seeding data for user: {user.email} (ID: {user.id})")
        
        # 2. Clear existing demo data (optional, but good for idempotency if run multiple times)
        # We will just append data to make it look full.

        # 3. Create Channels
        channel_names = [
            ("Work & Career", "💼", "#3B82F6"),
            ("Health & Fitness", "💪", "#10B981"),
            ("Personal Growth", "📚", "#8B5CF6"),
            ("Side Project", "🚀", "#F59E0B"),
            ("Life Admin", "📝", "#64748B")
        ]
        channels = []
        for name, icon, color in channel_names:
            ch = db.scalar(select(Channel).where(Channel.name == name, Channel.user_id == user.id))
            if not ch:
                ch = Channel(name=f"{icon} {name}", color=color, user_id=user.id)
                db.add(ch)
            channels.append(ch)
        db.commit()
        for ch in channels: db.refresh(ch)
        
        # Generate data for the past 14 days
        now = datetime.now(timezone.utc)
        
        # 4. Create Commitments
        commitment_templates = [
            ("Finish Q3 Roadmap", "project", 0.1),
            ("Daily Standup", "habit", 0.5),
            ("Prepare Board Presentation", "project", 0.8),
            ("Gym / Weightlifting", "habit", 0.2),
            ("Run 5k", "habit", 0.3),
            ("Read 20 pages", "habit", 0.1),
            ("Complete React Course", "project", 0.4),
            ("Launch V1 of SaaS", "project", 0.7),
            ("Write Blog Post", "goal", 0.2),
            ("Pay Utility Bills", "deadline", 0.1),
            ("Grocery Shopping", "deadline", 0.1)
        ]
        
        commitments = []
        for title, ctype, risk in commitment_templates:
            c = db.scalar(select(Commitment).where(Commitment.title == title, Commitment.user_id == user.id))
            if not c:
                c = Commitment(
                    title=title, 
                    user_id=user.id,
                    type=ctype,
                    due_date=(now + timedelta(days=30)).date(),
                    risk_score=risk,
                    metadata_json={"frequency": "weekly" if ctype == "habit" else "once"}
                )
                db.add(c)
            commitments.append(c)
        db.commit()
        for c in commitments: db.refresh(c)

        print("Generating Daily Plans, Tasks, and Focus Sessions...")
        # We will generate about 5-8 tasks per day for 14 days = ~100 tasks
        
        for days_ago in range(14, -1, -1):
            target_date = (now - timedelta(days=days_ago)).date()
            
            # Create Daily Plan
            dp = db.scalar(select(DailyPlan).where(DailyPlan.plan_date == target_date, DailyPlan.user_id == user.id))
            if not dp:
                dp = DailyPlan(
                    user_id=user.id,
                    plan_date=target_date,
                    morning_intention="Stay focused on deep work. Don't skip the gym.",
                    is_complete=True if days_ago > 0 else False,
                    mood=random.choice(["energetic", "focused", "calm", "tired", "anxious"]),
                    notes="Good progress today." if days_ago > 0 else None
                )
                db.add(dp)
                db.commit()
                db.refresh(dp)
            
            # Create 5-8 tasks for this day
            num_tasks = random.randint(5, 8)
            for _ in range(num_tasks):
                comm = random.choice(commitments)
                ch = random.choice(channels)
                is_done = True if days_ago > 0 else random.choice([True, False, False])
                
                t = Task(
                    title=f"{comm.title} - Step {random.randint(1, 10)}",
                    user_id=user.id,
                    commitment_id=comm.id,
                    channel_id=ch.id,
                    daily_plan_id=dp.id,
                    planned_date=target_date,
                    is_done=is_done,
                    priority=random.choice(["none", "low", "medium", "high", "urgent"]),
                    estimated_minutes=random.choice([15, 25, 45, 60]),
                    actual_minutes=random.choice([20, 30, 50, 60]) if is_done else 0,
                )
                db.add(t)
            
            # Create a Focus Session or two for this day
            if days_ago > 0 and random.random() > 0.3:
                session_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(hours=random.randint(9, 16))
                duration = random.choice([25, 50, 90])
                fs = FocusSession(
                    user_id=user.id,
                    daily_plan_id=dp.id,
                    started_at=session_start,
                    ended_at=session_start + timedelta(minutes=duration),
                    planned_duration_minutes=duration,
                    actual_duration_minutes=duration,
                    mode="pomodoro" if duration < 50 else "deepwork",
                    status="completed"
                )
                db.add(fs)
                
            # Create Daily Highlight (Shutdown) for past days
            if days_ago > 0:
                dh = db.scalar(select(DailyHighlight).where(DailyHighlight.daily_plan_id == dp.id))
                if not dh:
                    dh = DailyHighlight(
                        user_id=user.id,
                        daily_plan_id=dp.id,
                        date=target_date,
                        highlight_type="shutdown",
                        content="Productive day overall.",
                        tasks_completed=random.randint(4, 7),
                        focus_minutes=random.randint(50, 150),
                        mood_end=random.choice(["accomplished", "tired", "satisfied"]),
                        ai_summary="You maintained good focus today. Try to keep distractions lower tomorrow."
                    )
                    db.add(dh)

        db.commit()
        
        print("✅ Database successfully populated with 14 days of realistic dummy data!")
        print("Data includes: 5 Channels, 11 Commitments, 14 Daily Plans, ~100 Tasks, Focus Sessions, and Highlights.")

if __name__ == "__main__":
    seed_database()
