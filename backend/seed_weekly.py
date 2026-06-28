import os
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User
from app.models.channel import Channel
from app.models.commitment import Commitment
from app.models.weekly_plan import WeeklyPlan

def seed_weekly():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "sanjh.kanchan14@gmail.com"))
        if not user:
            print("User not found.")
            return

        channels = db.scalars(select(Channel).where(Channel.user_id == user.id)).all()
        commitments = db.scalars(select(Commitment).where(Commitment.user_id == user.id)).all()

        if not channels or not commitments:
            print("No channels or commitments found to link weekly plans to.")
            return

        now = datetime.now(timezone.utc)
        
        # Start of the current week (Monday)
        current_week_start = now - timedelta(days=now.weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # We will create plans for the current week, last week, and next week
        weeks = [
            current_week_start - timedelta(days=7),
            current_week_start,
            current_week_start + timedelta(days=7)
        ]

        print("Generating Weekly Plans...")
        
        for week_start in weeks:
            week_start_date = week_start.date()
            week_end_date = (week_start + timedelta(days=6)).date()
            
            # Create 2-4 plans per week
            num_plans = random.randint(2, 4)
            for _ in range(num_plans):
                comm = random.choice(commitments)
                ch = random.choice(channels)
                
                wp = WeeklyPlan(
                    user_id=user.id,
                    title=f"Progress on {comm.title}",
                    description="This is an auto-generated weekly plan.",
                    channel_id=ch.id,
                    commitment_id=comm.id,
                    week_start_date=week_start_date,
                    week_end_date=week_end_date,
                    status=random.choice(["planned", "in_progress", "done", "missed"]),
                    target_focus_hours=random.choice([2.0, 5.0, 10.0, 15.0])
                )
                db.add(wp)

        db.commit()
        print("✅ Weekly plans seeded successfully!")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_weekly()
