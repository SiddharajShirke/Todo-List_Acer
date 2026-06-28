from app.database import SessionLocal
from app.models.task import Task
from app.models.user import User
from app.services.google_calendar import delete_calendar_event

db = SessionLocal()
try:
    tasks = db.query(Task).all()
    print(f'Found {len(tasks)} tasks.')
    
    for task in tasks:
        user = db.query(User).filter(User.id == task.user_id).first()
        if user and task.google_event_id:
            try:
                delete_calendar_event(user, task.google_event_id)
                print(f'Deleted calendar event for task: {task.title}')
            except Exception as e:
                print(f'Failed to delete calendar event for task {task.title}: {e}')
                
        db.delete(task)
        
    db.commit()
    print('All tasks deleted from database.')
finally:
    db.close()
