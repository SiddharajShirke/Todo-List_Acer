"""
workers/celery_app.py — Celery App + Beat Schedule
Redis is used as both broker and result backend.
Beat schedule runs 3 periodic tasks:
  1. Every 30 min → score_all_commitments (refreshes priority/risk scores)
  2. Daily at 9am → send_morning_reminders
  3. Daily at 6pm → send_evening_reminders

Start worker:  celery -A app.workers.celery_app worker --loglevel=info
Start beat:    celery -A app.workers.celery_app beat --loglevel=info
Monitor:       celery -A app.workers.celery_app flower --port=5555
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "ai_productivity",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "score-all-commitments-every-30min": {
            "task": "app.workers.tasks.score_all_commitments",
            "schedule": 1800,  # every 30 minutes
        },
        "send-morning-reminders": {
            "task": "app.workers.tasks.send_morning_reminders",
            "schedule": crontab(hour=9, minute=0),
        },
        "send-evening-reminders": {
            "task": "app.workers.tasks.send_evening_reminders",
            "schedule": crontab(hour=18, minute=0),
        },
        "mark-missed-commitments": {
            "task": "app.workers.tasks.mark_missed_commitments",
            "schedule": crontab(hour=23, minute=59),
        },
    },
)
