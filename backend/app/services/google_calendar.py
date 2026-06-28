"""
google_calendar.py — Google Calendar Integration Service

Key features:
  - Auto-refreshes expired access tokens using the stored refresh_token
  - Persists refreshed tokens back to the DB so the next call doesn't fail
  - Tags all app-created events with the user's ID via extendedProperties
    (prevents calendar events from one user leaking into another's view)
  - Marks completed tasks with a ✅ prefix in the calendar summary
"""
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.config import settings
from datetime import datetime, timedelta, timezone
import os

# Allow HTTP for local development OAuth flows
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]


def get_google_flow(state=None):
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "project_id": "ai-productivity",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state
    )
    return flow


def get_calendar_service(user, db=None):
    """
    Build and return a Google Calendar API service client.
    
    Auto-refreshes the access token if expired using the stored refresh_token.
    If `db` is provided, persists the new access token back to the database.
    Returns None if the user has no Google tokens connected.
    """
    if not user.google_access_token or not user.google_refresh_token:
        return None

    # Check if the token is expired (with 60s buffer)
    now = datetime.now(timezone.utc)
    expiry = user.google_token_expiry
    
    # google-auth Credentials expects a NAIVE UTC datetime for expiry
    if expiry and expiry.tzinfo is not None:
        expiry_naive = expiry.replace(tzinfo=None)
    elif expiry:
        expiry_naive = expiry
    else:
        expiry_naive = None

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
        expiry=expiry_naive
    )

    # Refresh the token if it's expired or about to expire
    token_expired = expiry_naive is None or datetime.utcnow() >= (expiry_naive - timedelta(seconds=60))
    if token_expired:
        try:
            creds.refresh(GoogleAuthRequest())
            # Persist the refreshed token back to DB so next call works too
            user.google_access_token = creds.token
            if creds.refresh_token:
                user.google_refresh_token = creds.refresh_token
            user.google_token_expiry = creds.expiry  # naive UTC datetime from google-auth
            if db:
                db.commit()
        except Exception as e:
            print(f"Failed to refresh Google token for user {user.id}: {e}")
            return None

    try:
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Failed to build calendar service for user {user.id}: {e}")
        return None


def create_calendar_event(user, task, db=None):
    service = get_calendar_service(user, db=db)
    if not service:
        return None

    if not task.planned_date:
        return None

    date_str = task.planned_date.isoformat()
    end_date = task.planned_date + timedelta(days=1)
    end_date_str = end_date.isoformat()

    summary = task.title
    if getattr(task, 'is_done', False):
        summary = f"✅ {task.title}"

    event = {
        'summary': summary,
        'description': task.description or '',
        'start': {'date': date_str},
        'end': {'date': end_date_str},
        'extendedProperties': {
            'private': {
                'app_user_id': str(user.id),
                'app_task_id': str(task.id)
            }
        }
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return created_event.get('id')
    except Exception as e:
        print(f"Failed to create Google Calendar event for user {user.id}: {e}")
        return None


def update_calendar_event(user, task, db=None):
    if not task.google_event_id:
        return create_calendar_event(user, task, db=db)

    service = get_calendar_service(user, db=db)
    if not service:
        return None

    if not task.planned_date:
        return None

    date_str = task.planned_date.isoformat()
    end_date = task.planned_date + timedelta(days=1)
    end_date_str = end_date.isoformat()

    summary = task.title
    if getattr(task, 'is_done', False):
        summary = f"✅ {task.title}"

    event = {
        'summary': summary,
        'description': task.description or '',
        'start': {'date': date_str},
        'end': {'date': end_date_str},
        'extendedProperties': {
            'private': {
                'app_user_id': str(user.id),
                'app_task_id': str(task.id)
            }
        }
    }

    try:
        updated_event = service.events().update(
            calendarId='primary',
            eventId=task.google_event_id,
            body=event
        ).execute()
        return updated_event.get('id')
    except Exception as e:
        print(f"Failed to update Google Calendar event for user {user.id}: {e}")
        return task.google_event_id


def delete_calendar_event(user, event_id, db=None):
    service = get_calendar_service(user, db=db)
    if not service or not event_id:
        return
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
    except Exception as e:
        print(f"Failed to delete Google Calendar event: {e}")


def get_calendar_events(user, time_min: str, time_max: str, db=None):
    service = get_calendar_service(user, db=db)
    if not service:
        return []
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        all_events = events_result.get('items', [])
        # Filter: keep native Google events (no app_user_id) AND events belonging to THIS user
        filtered_events = []
        for e in all_events:
            props = e.get('extendedProperties', {}).get('private', {})
            event_user_id = props.get('app_user_id')
            if event_user_id is None or event_user_id == str(user.id):
                filtered_events.append(e)
        return filtered_events
    except Exception as e:
        print(f"Failed to fetch Google Calendar events for user {user.id}: {e}")
        return []
