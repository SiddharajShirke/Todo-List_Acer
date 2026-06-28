from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.deps import get_current_user
from app.models.user import User
from app.services.google_calendar import get_calendar_events
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

@router.get("/events")
def get_events(
    days: int = Query(4, description="Number of days to fetch events for (including today)"),
    time_min: str = Query(None, description="ISO format start date"),
    time_max: str = Query(None, description="ISO format end date"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if time_min and time_max:
        # Use provided custom range
        t_min = time_min
        t_max = time_max
    else:
        # Default 4-day view starting from today
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days)
        t_min = start.isoformat()
        t_max = end.isoformat()
    
    events = get_calendar_events(user, t_min, t_max, db=db)
    return events
