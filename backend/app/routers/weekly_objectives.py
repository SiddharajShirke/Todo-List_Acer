from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.weekly_objective import WeeklyObjective
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.weekly_objective import WeeklyObjectiveCreate, WeeklyObjectiveUpdate, WeeklyObjectiveOut
from app.services.google_calendar import delete_calendar_event, update_calendar_event
from app.models.task import Task
from typing import List

router = APIRouter(prefix="/api/weekly-objectives", tags=["weekly-objectives"])

@router.get("", response_model=List[WeeklyObjectiveOut])
def get_weekly_objectives(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(WeeklyObjective).filter(WeeklyObjective.user_id == user.id).all()

@router.post("", response_model=WeeklyObjectiveOut)
def create_weekly_objective(data: WeeklyObjectiveCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = WeeklyObjective(
        user_id=user.id,
        title=data.title,
        channel_id=data.channel_id,
        week_start_date=data.week_start_date,
        week_end_date=data.week_end_date,
        status=data.status
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/{obj_id}", response_model=WeeklyObjectiveOut)
def update_weekly_objective(obj_id: int, data: WeeklyObjectiveUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.query(WeeklyObjective).filter(WeeklyObjective.id == obj_id, WeeklyObjective.user_id == user.id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    
    title_changed = data.title is not None and data.title != obj.title

    if data.title is not None: obj.title = data.title
    if data.channel_id is not None: obj.channel_id = data.channel_id
    if data.week_start_date is not None: obj.week_start_date = data.week_start_date
    if data.week_end_date is not None: obj.week_end_date = data.week_end_date
    if data.status is not None: obj.status = data.status

    db.commit()
    db.refresh(obj)
    
    if title_changed:
        tasks = db.query(Task).filter(Task.weekly_objective_id == obj_id).all()
        for task in tasks:
            task.title = obj.title
            if data.channel_id is not None:
                task.channel_id = data.channel_id
            db.commit()
            if user.google_access_token and task.google_event_id:
                update_calendar_event(user, task)

    return obj

@router.delete("/{obj_id}")
def delete_weekly_objective(obj_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.query(WeeklyObjective).filter(WeeklyObjective.id == obj_id, WeeklyObjective.user_id == user.id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    
    tasks = db.query(Task).filter(Task.weekly_objective_id == obj_id).all()
    for task in tasks:
        if task.google_event_id:
            delete_calendar_event(user, task.google_event_id)
        db.delete(task)
        
    db.delete(obj)
    db.commit()
    return {"message": "Objective deleted"}
