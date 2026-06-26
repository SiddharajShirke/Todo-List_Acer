"""
workers/tasks.py — Celery Task Definitions

score_all_commitments: runs priority + risk + root_cause for every active commitment
send_morning_reminders: generates and saves AI reminders at 9am
send_evening_reminders: gentle follow-up at 6pm for high-risk items
mark_missed_commitments: marks past-due commitments as is_missed=True

Reminder generation is SYNCHRONOUS in worker context (no async LLM call here).
For async LLM calls, use asyncio.run() or schedule them as subtasks.
"""
from celery import shared_task
from loguru import logger
from datetime import date, datetime

@shared_task(name="app.workers.tasks.score_all_commitments")
def score_all_commitments():
    """Refresh priority_score, risk_score, root_cause for all active commitments."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    from app.services.priority_engine import PriorityEngine
    from app.services.risk_engine import RiskEngine
    from app.services.root_cause_engine import RootCauseEngine
    db = SessionLocal()
    try:
        active = db.query(Commitment).filter(Commitment.is_done == False, Commitment.is_missed == False).all()
        logger.info(f"Scoring {len(active)} active commitments")
        for c in active:
            c.priority_score = PriorityEngine.score(c)
            c.risk_score = RiskEngine.score(c)
            rc = RootCauseEngine.predict(c)
            c.root_cause = rc["root_cause"]
            c.root_cause_score = rc["score"]
        db.commit()
        logger.success(f"Scored {len(active)} commitments")
    except Exception as e:
        logger.error(f"score_all_commitments error: {e}")
        db.rollback()
    finally:
        db.close()

@shared_task(name="app.workers.tasks.send_morning_reminders")
def send_morning_reminders():
    """Generate AI reminders for high-priority/high-risk commitments."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    from app.models.reminder import Reminder
    from app.services.intervention_engine import InterventionEngine
    db = SessionLocal()
    try:
        high_priority = db.query(Commitment).filter(
            Commitment.is_done == False,
            Commitment.priority_score >= 40,
        ).all()
        logger.info(f"Sending reminders for {len(high_priority)} commitments")
        for c in high_priority:
            user = c.user
            style = InterventionEngine.select_style(c, user)
            message = InterventionEngine.generate_message(c, style, user)
            reminder = Reminder(
                user_id=user.id,
                commitment_id=c.id,
                style=style,
                message=message,
            )
            db.add(reminder)
        db.commit()
        logger.success("Morning reminders sent")
    except Exception as e:
        logger.error(f"send_morning_reminders error: {e}")
        db.rollback()
    finally:
        db.close()

@shared_task(name="app.workers.tasks.send_evening_reminders")
def send_evening_reminders():
    """Evening follow-up for high-risk commitments (risk >= 0.6)."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    from app.models.reminder import Reminder
    from app.services.intervention_engine import InterventionEngine
    db = SessionLocal()
    try:
        high_risk = db.query(Commitment).filter(
            Commitment.is_done == False,
            Commitment.risk_score >= 0.6,
        ).all()
        for c in high_risk:
            user = c.user
            message = f"🚨 Still pending: '{c.title}' due {c.due_date}. Don't let it slip through!"
            reminder = Reminder(user_id=user.id, commitment_id=c.id, style="deadline", message=message)
            db.add(reminder)
        db.commit()
    except Exception as e:
        logger.error(f"send_evening_reminders error: {e}")
        db.rollback()
    finally:
        db.close()

@shared_task(name="app.workers.tasks.mark_missed_commitments")
def mark_missed_commitments():
    """Mark past-due commitments as is_missed=True at end of day."""
    from app.database import SessionLocal
    from app.models.commitment import Commitment
    db = SessionLocal()
    today = date.today()
    try:
        missed = db.query(Commitment).filter(
            Commitment.is_done == False,
            Commitment.is_missed == False,
            Commitment.due_date < today,
        ).all()
        for c in missed:
            c.is_missed = True
        db.commit()
        logger.info(f"Marked {len(missed)} commitments as missed")
    except Exception as e:
        logger.error(f"mark_missed_commitments error: {e}")
        db.rollback()
    finally:
        db.close()
